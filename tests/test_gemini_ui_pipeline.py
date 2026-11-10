"""Exercise the real UI/factory/adapter/parser; only the SDK transport is mocked."""
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from google.genai import types
from streamlit.testing.v1 import AppTest

from nyayasaathi.config import Settings

pytestmark = pytest.mark.offline
APP = str(Path(__file__).resolve().parents[1] / 'app.py')
CASES = (
    ('I bought headphones for INR 4500 online. They arrived damaged and the seller refused a refund.', 'consumer', 'amount_paid', 'INR 4500'),
    ('My landlord has not returned my INR 20000 security deposit after I moved out.', 'rental_deposit', 'deposit_paid', 'INR 20000'),
    ('Maine landlord ko 20000 security deposit diya tha. Room khaali kar diya, lekin paise wapas nahi mile.', 'rental_deposit', 'deposit_paid', '20000'),
)


def sdk_response(payload, finish='STOP'):
    return types.GenerateContentResponse(candidates=[types.Candidate(
        content=types.Content(role='model', parts=[types.Part(text=json.dumps(payload))]), finish_reason=finish)],
        usage_metadata=types.GenerateContentResponseUsageMetadata(prompt_token_count=10, candidates_token_count=30))


def run_ui(monkeypatch, response, text):
    sdk = Mock()
    sdk.models.generate_content.return_value = response
    monkeypatch.setattr('nyayasaathi.llm.gemini.genai.Client', Mock(return_value=sdk))
    monkeypatch.setattr('nyayasaathi.config.load_streamlit_settings', lambda **_: Settings(
        app_mode='development',
        gemini_api_key='synthetic-only', gemini_model='configured-test-model', llm_max_retries=0))
    app = AppTest.from_file(APP, default_timeout=10).run()
    app.chat_input[0].set_value(text).run()
    return app, sdk


@pytest.mark.parametrize('text,topic,name,value', CASES)
def test_real_gemini_ui_contract_with_mocked_transport(monkeypatch, text, topic, name, value):
    payload = {'topic': topic, 'confidence': .95, 'risk_flags': [],
               'facts': [{'name': name, 'value': value, 'quote': value}]}
    app, sdk = run_ui(monkeypatch, sdk_response(payload), text)
    assert not app.exception
    state = app.session_state.case
    assert not state.last_result.error and state.topic == topic
    assert any(f.name == name and f.value == value for f in state.proposals)
    assert state.last_result.claims and state.last_result.questions
    assert len(state.history) == 2
    app.run()
    sdk.models.generate_content.assert_called_once()
    assert sdk.models.generate_content.call_args.kwargs['config'].response_mime_type == 'application/json'


def test_empty_null_placeholder_is_omitted_without_losing_valid_facts(monkeypatch):
    text, topic, name, value = CASES[0]
    payload = {'topic': topic, 'confidence': .95, 'risk_flags': [], 'facts': [
        {'name': name, 'value': value, 'quote': value},
        {'name': 'purchase_date', 'value': None, 'quote': ''}]}
    app, _ = run_ui(monkeypatch, sdk_response(payload), text)
    state = app.session_state.case
    assert not state.last_result.error
    assert any(f.name == name and f.value == value for f in state.proposals)
    assert not any(f.name == 'purchase_date' for f in state.proposals)
    assert 'purchase_date' in state.last_result.missing_fields


@pytest.mark.parametrize('row', [
    {'name': 'purchase_date', 'value': 'yesterday', 'quote': ''},
    {'name': 'purchase_date', 'value': None, 'quote': 'invented quotation'},
    {'name': 'made_up_field', 'value': None, 'quote': ''},
    {'name': 'amount_paid', 'value': '9000', 'quote': 'INR 4500'},
])
def test_invalid_facts_remain_rejected_and_confirmed_state_survives(monkeypatch, row):
    from nyayasaathi.extraction import confirm_fact
    text, topic, name, value = CASES[0]
    payload = {'topic': topic, 'confidence': .95, 'risk_flags': [], 'facts': []}
    app, sdk = run_ui(monkeypatch, sdk_response(payload), text)
    confirmed = confirm_fact(app.session_state.case, name, value)
    app.session_state.case = confirmed
    payload['facts'] = [row]
    sdk.models.generate_content.return_value = sdk_response(payload)
    app.chat_input[0].set_value(text).run()
    assert not app.exception
    assert not app.session_state.case.last_result.error
    assert app.session_state.case.last_result.issues
    assert app.session_state.case.facts == confirmed.facts
    assert app.session_state.case.proposals == confirmed.proposals


def test_duplicate_placeholder_cannot_hide_a_duplicate_fact():
    from nyayasaathi.extraction import parse_extraction
    payload = {'topic': 'consumer', 'confidence': .95, 'risk_flags': [], 'facts': [
        {'name': 'amount_paid', 'value': None, 'quote': ''},
        {'name': 'amount_paid', 'value': '4500', 'quote': '4500'}]}
    result = parse_extraction(json.dumps(payload), '4500', 1)
    assert not result.facts
    assert any(i.code == 'fact_conflict' for i in result.issues)


def test_paraphrased_problem_recovers_only_exact_user_quote(monkeypatch):
    text, topic, name, value = CASES[1]
    payload = {'topic': topic, 'confidence': .9, 'risk_flags': [], 'facts': [
        {'name': name, 'value': value, 'quote': value},
        {'name': 'problem', 'value': 'landlord has not returned security deposit after move out', 'quote': text}]}
    app, sdk = run_ui(monkeypatch, sdk_response(payload), text)
    state = app.session_state.case
    assert not app.exception and not state.last_result.error
    assert state.topic == topic
    assert any(f.name == name and f.value == value for f in state.proposals)
    problem = next(f for f in state.proposals if f.name == 'problem')
    assert problem.value == problem.quote == text
    assert not problem.confirmed and not state.facts
    assert state.last_result.claims and state.last_result.questions
    assert 'rental_statutory_position_unverified' in state.last_result.gaps
    assert all(c.kind != 'statutory' for c in state.last_result.claims)
    app.run()
    assert app.session_state.case == state
    sdk.models.generate_content.assert_called_once()


@pytest.mark.parametrize('quote', ['invented evidence', '', 'x' * 501])
def test_problem_recovery_cannot_invent_or_expand_evidence(quote):
    from nyayasaathi.extraction import parse_extraction
    payload = {'topic': 'consumer', 'confidence': .95, 'risk_flags': [], 'facts': [
        {'name': 'problem', 'value': 'summary', 'quote': quote}]}
    result = parse_extraction(json.dumps(payload), CASES[0][0], 1)
    assert not result.facts and result.issues
