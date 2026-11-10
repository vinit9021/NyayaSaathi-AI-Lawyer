"""Bounded in-memory WAV transcription. No translation, logging, or file writes."""
from dataclasses import dataclass, replace, field
from hashlib import sha256
from io import BytesIO
import wave
import groq

from nyayasaathi.config import Settings

MESSAGES = {
    'invalid_audio': 'Record a non-empty PCM WAV clip (maximum 60 seconds / 5 MB).',
    'missing_credentials': 'Voice is unavailable. You can still type your message.',
    'consent_required': 'Permit Groq audio processing before transcription.',
    'authentication': 'Voice service authentication failed. Please use text while the owner checks configuration.',
    'quota': 'Voice service quota is unavailable. Please use text or try later.',
    'timeout': 'Transcription timed out. Please use text or record again later.',
    'unavailable': 'Voice service is unavailable. Your text conversation is unchanged.',
    'invalid_response': 'No usable transcript was returned. Please type or record again.',
    'limit': 'Recording limit reached for this case. Continue by typing.',
    'duplicate': 'This recording was already processed. Edit its transcript or record a new clip.',
}


class SpeechError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(MESSAGES[code])


def validate_audio(data: bytes) -> float:
    if not isinstance(data, bytes) or not 44 < len(data) <= 5 * 1024 * 1024:
        raise SpeechError('invalid_audio')
    try:
        with wave.open(BytesIO(data), 'rb') as audio:
            if (audio.getcomptype() != 'NONE' or audio.getsampwidth() != 2
                    or audio.getnchannels() not in (1, 2) or not 8000 <= audio.getframerate() <= 48000):
                raise ValueError
            duration = audio.getnframes() / audio.getframerate()
            if not 0 < duration <= 60:
                raise ValueError
            frames = audio.readframes(audio.getnframes())
            if len(frames) != audio.getnframes() * audio.getnchannels() * 2 or not any(frames):
                raise ValueError
            return duration
    except (wave.Error, EOFError, ValueError, ZeroDivisionError):
        raise SpeechError('invalid_audio') from None


class GroqSpeech:
    def __init__(self, settings: Settings, *, sdk_client=None):
        self.settings = settings
        self.sdk_client = sdk_client

    def transcribe(self, data: bytes, *, consent: bool) -> str:
        if not consent:
            raise SpeechError('consent_required')
        validate_audio(data)
        if not self.settings.groq_api_key:
            raise SpeechError('missing_credentials')
        client = self.sdk_client
        try:
            if client is None:
                client = groq.Groq(api_key=self.settings.groq_api_key,
                                   timeout=self.settings.speech_timeout_seconds, max_retries=0)
            # No language hint: Hindi/Hinglish must not be forced into English.
            response = client.audio.transcriptions.create(
                file=('recording.wav', data, 'audio/wav'), model=self.settings.groq_model,
                response_format='json', temperature=0)
            text = response.text
            if not isinstance(text, str) or not text.strip() or len(text) > 4000:
                raise SpeechError('invalid_response')
            return text.strip()
        except SpeechError:
            raise
        except groq.APITimeoutError:
            raise SpeechError('timeout') from None
        except groq.AuthenticationError:
            raise SpeechError('authentication') from None
        except groq.RateLimitError:
            raise SpeechError('quota') from None
        except Exception:
            raise SpeechError('unavailable') from None
        finally:
            if self.sdk_client is None and client is not None:
                try:
                    client.close()
                except Exception:
                    pass


@dataclass(frozen=True)
class VoiceState:
    attempted: tuple[str, ...] = ()
    transcript: str = field(default='', repr=False)
    pending_id: str | None = None
    error: str | None = None


def transcribe_once(state: VoiceState, data: bytes, service: GroqSpeech, *, consent: bool) -> VoiceState:
    if not consent:
        return replace(state, error='consent_required')
    try:
        validate_audio(data)
    except SpeechError as error:
        return replace(state, error=error.code)
    digest = sha256(data).hexdigest()
    if digest in state.attempted:
        return replace(state, error='duplicate')
    if len(state.attempted) >= 10:
        return replace(state, error='limit')
    updated = replace(state, attempted=state.attempted + (digest,), transcript='', pending_id=None, error=None)
    try:
        return replace(updated, transcript=service.transcribe(data, consent=True), pending_id='voice-' + digest)
    except SpeechError as error:
        return replace(updated, error=error.code)


def consume_transcript(state: VoiceState, edited: str) -> tuple[VoiceState, str, str]:
    if state.pending_id is None or not isinstance(edited, str) or not edited.strip() or len(edited) > 4000:
        raise SpeechError('invalid_response')
    return replace(state, transcript='', pending_id=None, error=None), edited.strip(), state.pending_id
