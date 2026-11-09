from pathlib import Path
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from nyayasaathi.config import Settings

pytestmark = pytest.mark.offline
APP = str(Path(__file__).resolve().parents[1] / "app.py")


def start_simulation(language="English"):
    app = AppTest.from_file(APP).run()
    app.selectbox(key="language").select(language).run()
    app.selectbox(key="mode").select("Offline simulation").run()
    assert not app.exception
    return app


def button(app, label):
    return next(b for b in app.button if b.label == label)


def test_simulated_chat_rerun_does_not_duplicate_turn():
    app = start_simulation()
    assert any("SIMULATION" in item.value for item in app.warning)
    app.chat_input[0].set_value("online refund; seller: FictionalShop; amount_paid: INR 5000; state: Maharashtra").run()
    assert not app.exception
    assert app.session_state.case.topic == "consumer"
    assert app.session_state.case.last_result.claims
    assert len(app.session_state.case.processed_ids) == 1
    app.run()
    assert len(app.session_state.case.processed_ids) == 1
    assert any("consumerhelpline.gov.in" in m.value for m in app.markdown)


def test_confirm_correction_and_reset():
    app = start_simulation()
    app.chat_input[0].set_value("online refund; amount_paid: 5000").run()
    app.selectbox(key="fact_field").select("amount_paid").run()
    app.text_area[0].set_value("6000").run()
    button(app, "Confirm detail / पुष्टि करें").click().run()
    assert not app.exception
    assert next(f for f in app.session_state.case.facts if f.name == "amount_paid").value == "6000"
    old_id = app.session_state.case.case_id
    button(app, "New case / नया मामला").click().run()
    assert app.session_state.case.case_id != old_id
    assert not app.session_state.case.history and not app.session_state.case.facts
    assert len(app.chat_message) == 0


def test_hindi_rental_flow_and_evidence():
    app = start_simulation("हिन्दी")
    app.chat_input[0].set_value("मकान मालिक जमा पैसे वापस नहीं दे रहा; state: Maharashtra").run()
    assert not app.exception
    assert app.session_state.case.topic == "rental_deposit"
    assert "जानकारी" in app.session_state.case.last_result.message
    assert "rental_statutory_position_unverified" in app.session_state.case.last_result.gaps


def test_missing_credentials_friendly_no_fake_fallback(monkeypatch):
    monkeypatch.setattr("nyayasaathi.config.load_streamlit_settings", lambda **_: Settings())
    app = AppTest.from_file(APP).run()
    app.selectbox(key="mode").select("Gemini").run()
    assert not app.exception and app.chat_input[0].disabled
    assert any("GEMINI_API_KEY" in item.value for item in app.warning)
    assert not any("OFFLINE SIMULATION" in item.value for item in app.warning)


def test_configured_gemini_still_requires_consent(monkeypatch):
    monkeypatch.setattr("nyayasaathi.config.load_streamlit_settings", lambda **_: Settings(gemini_api_key="synthetic", gemini_model="test"))
    forbidden = Mock(side_effect=AssertionError("must not construct SDK"))
    monkeypatch.setattr("nyayasaathi.llm.gemini.genai.Client", forbidden)
    app = AppTest.from_file(APP).run()
    app.selectbox(key="mode").select("Gemini").run()
    assert app.chat_input[0].disabled
    assert not app.warning
    forbidden.assert_not_called()


def test_high_risk_disables_chat():
    app = start_simulation()
    app.chat_input[0].set_value("landlord eviction threat deposit").run()
    assert app.session_state.case.blocked
    assert app.chat_input[0].disabled
    assert not app.session_state.case.last_result.claims


def test_two_ui_sessions_do_not_share_data():
    first = start_simulation()
    first.chat_input[0].set_value("online refund; seller: FictionalShop").run()
    second = start_simulation()
    assert second.session_state.case.case_id != first.session_state.case.case_id
    assert not second.session_state.case.history


def test_switching_modes_clears_case_context(monkeypatch):
    monkeypatch.setattr("nyayasaathi.config.load_streamlit_settings", lambda **_: Settings())
    app = start_simulation()
    app.chat_input[0].set_value("online refund").run()
    app.selectbox(key="mode").select("Gemini").run()
    assert not app.session_state.case.history
