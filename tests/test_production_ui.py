from dataclasses import replace
from unittest.mock import Mock
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from nyayasaathi.config import Settings
from nyayasaathi.speech import VoiceState
from tests.test_gemini_ui_pipeline import sdk_response
from tests.test_speech import wav

pytestmark = pytest.mark.offline
APP = str(Path(__file__).resolve().parents[1] / 'app.py')


def setup(monkeypatch, **updates):
    settings = replace(Settings(gemini_api_key='synthetic', gemini_model='configured-test', groq_api_key='synthetic-voice'), **updates)
    monkeypatch.setattr('nyayasaathi.config.load_streamlit_settings', lambda **_: settings)
    sdk = Mock()
    sdk.models.generate_content.return_value = sdk_response({'topic': 'consumer', 'confidence': .95, 'risk_flags': [], 'facts': []})
    monkeypatch.setattr('nyayasaathi.llm.gemini.genai.Client', Mock(return_value=sdk))
    return AppTest.from_file(APP, default_timeout=10).run(), sdk


def test_production_automatically_uses_live_and_hides_developer_controls(monkeypatch):
    app, sdk = setup(monkeypatch)
    assert not app.exception and not app.chat_input[0].disabled
    assert not any(s.key == 'mode' for s in app.selectbox)
    assert not any(c.key == 'live_consent' for c in app.checkbox)
    assert not any('Application build' in c.value or 'configured-test' in c.value for c in app.caption)
    assert len(app.get('audio_input')) == 1
    sdk.models.generate_content.assert_not_called()
    app.chat_input[0].set_value('online damaged product refund').run()
    assert not app.exception and not app.session_state.case.last_result.error
    app.run()
    sdk.models.generate_content.assert_called_once()


def test_production_missing_credentials_has_no_key_entry_or_fallback(monkeypatch):
    app, sdk = setup(monkeypatch, gemini_api_key=None, groq_api_key=None)
    assert app.chat_input[0].disabled and not app.text_input
    assert any('unavailable' in w.value for w in app.warning)
    assert not any('simulation' in w.value.lower() for w in app.warning)
    sdk.models.generate_content.assert_not_called()


def test_production_rejects_simulation_configuration(monkeypatch):
    app, sdk = setup(monkeypatch, llm_provider='simulation')
    assert app.chat_input[0].disabled
    sdk.models.generate_content.assert_not_called()


def test_corrected_voice_transcript_only_submitted_explicitly(monkeypatch):
    app, sdk = setup(monkeypatch)
    app.session_state.voice = VoiceState(transcript='online refund 450', pending_id='voice-synthetic')
    app.run()
    sdk.models.generate_content.assert_not_called()
    next(t for t in app.text_area if t.label.startswith('Review transcript')).set_value('online refund INR 4500')
    app.button(key='voice_send').click().run()
    assert not app.exception
    assert app.session_state.case.history[0].content == 'online refund INR 4500'
    assert not app.session_state.voice.pending_id
    app.run()
    assert sdk.models.generate_content.call_count == 1
    assert not app.session_state.voice.transcript


def test_audio_consent_and_transcription_do_not_send_to_gemini(monkeypatch):
    app, sdk = setup(monkeypatch)
    service = Mock(return_value='online headphones damaged')
    monkeypatch.setattr('nyayasaathi.speech.GroqSpeech.transcribe', service)
    # AppTest has no microphone driver: inject a recording at the widget boundary.
    from io import BytesIO
    monkeypatch.setattr('streamlit.audio_input', lambda *a, **k: BytesIO(wav()) if not k['disabled'] else None)
    app.checkbox(key='voice_consent').check().run()
    app.button(key='voice_transcribe').click().run()
    assert not app.exception and app.session_state.voice.transcript == 'online headphones damaged'
    sdk.models.generate_content.assert_not_called()
    app.run()
    assert service.call_count == 1


def test_new_case_clears_audio_transcript_and_keeps_text(monkeypatch):
    app, sdk = setup(monkeypatch)
    app.session_state.voice = VoiceState(transcript='pending', pending_id='voice-id')
    app.run()
    next(b for b in app.button if b.label.startswith('New case')).click().run()
    assert 'voice' not in app.session_state and not app.session_state.case.history
    assert not app.chat_input[0].disabled
