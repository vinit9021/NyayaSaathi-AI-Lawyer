from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock
import wave

import groq
import httpx
import pytest

from nyayasaathi.config import Settings
from nyayasaathi.speech import GroqSpeech, SpeechError, VoiceState, validate_audio, transcribe_once, consume_transcript

pytestmark = pytest.mark.offline


def wav(seconds=.1, rate=16000, width=2, channels=1, silent=False):
    buffer = BytesIO()
    with wave.open(buffer, 'wb') as audio:
        audio.setparams((channels, width, rate, 0, 'NONE', 'not compressed'))
        audio.writeframes((b'\0' if silent else b'\x01') * int(seconds * rate) * channels * width)
    return buffer.getvalue()


@pytest.mark.parametrize('data', [b'', b'not audio', b'x' * (5 * 1024 * 1024 + 1),
    wav(61), wav(width=1), wav(rate=4000), wav(silent=True), wav()[:-8]])
def test_invalid_recordings_rejected_before_network(data):
    sdk = Mock()
    with pytest.raises(SpeechError):
        GroqSpeech(Settings(groq_api_key='synthetic'), sdk_client=sdk).transcribe(data, consent=True)
    sdk.audio.transcriptions.create.assert_not_called()


@pytest.mark.parametrize('text', ['I paid INR 4500 for a damaged mixer.', 'मैंने 4500 रुपये दिए।', 'Mera deposit 20000 wapas nahi mila.'])
def test_multilingual_transcription_not_translation(text):
    sdk = Mock()
    sdk.audio.transcriptions.create.return_value = SimpleNamespace(text=text)
    result = GroqSpeech(Settings(groq_api_key='synthetic', groq_model='configured-whisper'), sdk_client=sdk).transcribe(wav(), consent=True)
    assert result == text
    request = sdk.audio.transcriptions.create.call_args.kwargs
    assert request['model'] == 'configured-whisper' and 'language' not in request
    assert request['file'][0] == 'recording.wav'
    sdk.audio.translations.create.assert_not_called()


def test_missing_key_and_consent_do_not_call():
    for consent, code in [(False, 'consent_required'), (True, 'missing_credentials')]:
        with pytest.raises(SpeechError) as error:
            GroqSpeech(Settings()).transcribe(wav(), consent=consent)
        assert error.value.code == code


@pytest.mark.parametrize('text', ['', None, 'x' * 4001, []])
def test_invalid_transcript(text):
    sdk = Mock()
    sdk.audio.transcriptions.create.return_value = SimpleNamespace(text=text)
    with pytest.raises(SpeechError) as error:
        GroqSpeech(Settings(groq_api_key='synthetic'), sdk_client=sdk).transcribe(wav(), consent=True)
    assert error.value.code == 'invalid_response'


@pytest.mark.parametrize('status,expected', [(401, 'authentication'), (429, 'quota'), (503, 'unavailable')])
def test_provider_failures_sanitized_and_no_retry(status, expected):
    sdk = Mock()
    response = httpx.Response(status, request=httpx.Request('POST', 'https://example.invalid'))
    error_type = {401: groq.AuthenticationError, 429: groq.RateLimitError, 503: groq.InternalServerError}[status]
    sdk.audio.transcriptions.create.side_effect = error_type('private-auth-detail', response=response, body=None)
    with pytest.raises(SpeechError) as error:
        GroqSpeech(Settings(groq_api_key='synthetic'), sdk_client=sdk).transcribe(wav(), consent=True)
    assert error.value.code == expected and 'private-auth' not in str(error.value)
    assert sdk.audio.transcriptions.create.call_count == 1


def test_timeout_and_sdk_settings(monkeypatch):
    sdk = Mock()
    sdk.audio.transcriptions.create.side_effect = groq.APITimeoutError(request=httpx.Request('POST', 'https://example.invalid'))
    constructor = Mock(return_value=sdk)
    monkeypatch.setattr('nyayasaathi.speech.groq.Groq', constructor)
    with pytest.raises(SpeechError) as error:
        GroqSpeech(Settings(groq_api_key='synthetic', speech_timeout_seconds=20)).transcribe(wav(), consent=True)
    assert error.value.code == 'timeout'
    assert constructor.call_args.kwargs['max_retries'] == 0
    assert constructor.call_args.kwargs['timeout'] == 20
    sdk.close.assert_called_once()


def test_audio_and_transcript_deduplication_and_correction():
    service = Mock()
    service.transcribe.return_value = 'I paid 450'
    state = transcribe_once(VoiceState(), wav(), service, consent=True)
    assert state.transcript == 'I paid 450' and state.pending_id
    duplicate = transcribe_once(state, wav(), service, consent=True)
    assert duplicate.error == 'duplicate' and duplicate.transcript == 'I paid 450'
    service.transcribe.assert_called_once()
    consumed, text, submission = consume_transcript(state, 'I paid INR 4500')
    assert text == 'I paid INR 4500' and submission.startswith('voice-')
    assert not consumed.transcript and not consumed.pending_id
    with pytest.raises(SpeechError):
        consume_transcript(consumed, text)


def test_failed_recording_cannot_repeat_automatically_and_limit_applies():
    service = Mock()
    service.transcribe.side_effect = SpeechError('quota')
    state = transcribe_once(VoiceState(), wav(), service, consent=True)
    assert transcribe_once(state, wav(), service, consent=True).error == 'duplicate'
    assert transcribe_once(VoiceState(attempted=tuple(str(i) for i in range(10))), wav(), service, consent=True).error == 'limit'
    assert service.transcribe.call_count == 1


def test_consent_does_not_consume_recording():
    service = Mock()
    state = transcribe_once(VoiceState(), wav(), service, consent=False)
    assert state.error == 'consent_required' and not state.attempted
    service.transcribe.assert_not_called()
