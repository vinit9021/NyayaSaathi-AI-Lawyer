"""Adversarial structured variations, not fixed answers to a demo prompt."""
import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from nyayasaathi.extraction import parse_extraction, confirm_fact, EXTRACTION_SCHEMA
from nyayasaathi.models import CaseState, LLMResponse, LLMRequest, Message
from nyayasaathi.conversation import process_turn
from nyayasaathi.retrieval import load_catalogue
from nyayasaathi.llm.gemini import GeminiLLM
from nyayasaathi.llm.base import LLMError
from nyayasaathi.config import Settings
from nyayasaathi.drafting import require_safe_case
from tests.fakes import FakeLLM
from tests.test_gemini_ui_pipeline import run_ui, sdk_response, CASES

pytestmark = pytest.mark.offline


def envelope(facts=(), **extra):
    return {'topic': 'consumer', 'confidence': .95, 'risk_flags': [], 'facts': list(facts), **extra}


def row(name, value, quote=None):
    return {'name': name, 'value': value, 'quote': value if quote is None else quote}


def parse(rows, text='Online damaged headphones cost INR 4500. I have photos.'):
    return parse_extraction(json.dumps(envelope(rows), ensure_ascii=False), text, 1)


@pytest.mark.parametrize('bad', [None, [], 'fact', {}, {'name': 'seller'},
    row('seller', [], 'photos'), row('seller', True, 'photos'), row('seller', 123, 'photos'),
    row('seller', 'FictionalShop', None), row('seller', 'invented', 'invented'),
    row('amount_paid', '450', 'INR 4500'), row('state', 'Maharashtra', 'photos'),
    row('evidence', 'photos', ['photos']), row('evidence', {'a': 1}, 'photos'),
    {**row('evidence', 'photos'), 'confirmed': True},
    row(['seller'], 'photos', 'photos'), row('citations', 'section 999', 'photos')])
def test_bad_optional_row_does_not_discard_good_amount(bad):
    result = parse([row('amount_paid', 'INR 4500'), bad])
    # Same-field ambiguity is discarded, not first/last-wins.
    if isinstance(bad, dict) and bad.get('name') == 'amount_paid':
        assert not result.facts
    else:
        assert result.facts[0].value == 'INR 4500'
    assert result.issues
    assert all(i.field is None or isinstance(i.field, str) for i in result.issues)
    assert 'invented' not in repr(result.issues)


@pytest.mark.parametrize('value,quote', [('INR 4500', '₹4,500'), (4500, '₹4,500'),
    ('4500.00', 'INR 4,500'), ('INR 100000', '₹1,00,000'), ('4500', 'I paid INR 4500.')])
def test_equivalent_money_preserves_original_user_token(value, quote):
    result = parse([row('amount_paid', value, quote)], quote)
    assert len(result.facts) == 1 and not result.issues
    assert result.facts[0].value in quote and result.facts[0].quote == quote
    assert not result.facts[0].confirmed


@pytest.mark.parametrize('value,quote', [('4500', 'USD 4500'), ('4500', 'INR 45000'),
    ('4500', '₹45,00'), ('4500', '-4500'), ('4500', '4500 or 5500'),
    (True, '1'), (4500.0, '4500'), ('4500', '4.5k'), ('4500', '4,500.50'),
    ('2026', '2026-01-01'), ('2026', '2026/01/01')])
def test_money_meaning_is_never_guessed(value, quote):
    result = parse([row('amount_paid', value, quote)], quote)
    assert not result.facts and result.issues


@pytest.mark.parametrize('name,value,quote', [
    ('purchase_date', '2026-02-01', '01/02/2026'),
    ('purchase_date', '2026-02-30', '2026-02-30'),
    ('state', 'Maharashtra', 'Mumbai'), ('city', 'Mumbai', 'Pune'),
    ('seller', 'paid', 'unpaid'), ('order_reference', '123', '1234'),
    ('sender_name', 'राम', 'रामू')])
def test_dates_locations_and_identifiers_not_inferred(name, value, quote):
    assert not parse([row(name, value, quote)], quote).facts


@pytest.mark.parametrize('quote', ['I have photos', 'मेरे पास फोटो हैं', 'mere paas photos hain'])
@pytest.mark.parametrize('field', ['problem', 'evidence', 'contact_attempts'])
def test_narrative_paraphrase_uses_only_original_quote(field, quote):
    result = parse([row(field, 'model paraphrase', quote)], quote)
    assert result.facts[0].value == result.facts[0].quote == quote


def test_whitespace_recovery_keeps_exact_provenance():
    result = parse([row('seller', 'Fictional Shop', 'Fictional Shop')], 'Fictional\nShop')
    assert result.facts[0].value == result.facts[0].quote == 'Fictional\nShop'


def test_optional_absence_does_not_answer_a_question():
    data = envelope()
    del data['facts']
    assert not parse_extraction(json.dumps(data), 'online refund', 1).facts
    result = parse([row('purchase_date', None, ''), {'name': 'seller', 'quote': 'photos'}])
    assert not result.facts and len(result.issues) == 2
    assert 'facts' not in EXTRACTION_SCHEMA['required']


@pytest.mark.parametrize('extra', [{'confidence': '0.95'}, {'risk_flags': None},
    {'risk_flags': ['unknown_risk']}, {'facts': None}, {'facts': {}},
    {'citations': ['https://invented.invalid']}, {'answer': 'Section 999'}, {'topic': []}])
def test_safety_envelope_still_fails_closed(extra):
    with pytest.raises(ValueError):
        parse_extraction(json.dumps({**envelope(), **extra}), 'online refund', 1)


@pytest.mark.parametrize('raw', ['{"topic":', '{} trailing', '[]',
    '{"topic":"consumer","topic":"unsupported"}', '{"confidence":NaN}'])
def test_malformed_envelope_never_partially_salvaged(raw):
    with pytest.raises(ValueError):
        parse_extraction(raw, 'online refund', 1)


def test_duplicate_conflicts_do_not_pick_a_winner():
    result = parse([row('amount_paid', '4500'), row('amount_paid', '5500'), row('evidence', 'photos')],
                   '4500 or 5500; photos')
    assert [f.name for f in result.facts] == ['evidence']
    assert result.issues[0].code == 'fact_conflict'
    same = row('amount_paid', '4500')
    assert len(parse([same, same], '4500').facts) == 1


@pytest.mark.parametrize('field,text,parts', [
    ('evidence', 'I have an invoice and photos.', ('invoice', 'photos')),
    ('evidence', 'मेरे पास रसीद और फोटो हैं।', ('रसीद', 'फोटो')),
    ('contact_attempts', 'I emailed and called the seller.', ('emailed', 'called'))])
def test_multivalued_rows_combine_only_original_passage(field, text, parts):
    result = parse([row(field, p) for p in parts], text)
    assert not result.issues and len(result.facts) == 1
    fact = result.facts[0]
    assert fact.value == fact.quote and fact.quote in text
    assert all(p in fact.value for p in parts)
    assert not fact.confirmed


def test_repeated_evidence_never_salvages_an_invented_quote():
    result = parse([row('evidence', 'photos'), row('evidence', 'invented')])
    assert not result.facts and result.issues


def test_partial_output_keeps_semantic_risk_flags():
    data = envelope([row('amount_paid', '4500'), {'name': 'seller'}], risk_flags=['urgent'])
    after = process_turn(CaseState(), 'online refund 4500', '1',
                         FakeLLM(LLMResponse(json.dumps(data), 'test')), load_catalogue())
    assert after.blocked and not after.proposals and not after.last_result.claims


def test_rejected_update_preserves_confirmed_facts_and_blocks_stale_draft():
    before = confirm_fact(CaseState(topic='consumer'), 'amount_paid', '4500')
    data = envelope([row('amount_paid', '9000', 'photos'), row('evidence', 'photos')])
    client = FakeLLM(LLMResponse(json.dumps(data), 'test'))
    after = process_turn(before, 'online refund; photos', '1', client, load_catalogue())
    assert after.facts == before.facts and 'amount_paid' in after.conflicts
    assert any(f.name == 'evidence' for f in after.proposals)
    assert any('pay' in q for q in after.last_result.questions)
    with pytest.raises(ValueError):
        require_safe_case(after)
    corrected = confirm_fact(after, 'amount_paid', '5500')
    assert not corrected.conflicts


@pytest.mark.parametrize('text,topic,name,value', CASES + (
    ('ऑनलाइन सामान खराब आया। मैंने ₹4500 दिए।', 'consumer', 'amount_paid', '₹4500'),))
@pytest.mark.parametrize('variation', ['missing', 'wrong_type', 'paraphrase'])
def test_two_turn_ui_variations_preserve_state_and_use_catalogue(monkeypatch, text, topic, name, value, variation):
    bad = {'name': 'seller'} if variation == 'missing' else row('seller', [], 'bad')
    if variation == 'paraphrase':
        bad = row('problem', 'summary', text)
    app, sdk = run_ui(monkeypatch, sdk_response(envelope([row(name, value), bad], topic=topic)), text)
    first = app.session_state.case
    assert not app.exception and not first.last_result.error
    assert any(f.name == name and f.value == value for f in first.proposals)
    confirmed = confirm_fact(first, name, value)
    app.session_state.case = confirmed
    sdk.models.generate_content.return_value = sdk_response(envelope([
        row('evidence', 'photos'), row('purchase_date', '2026-02-01', 'photos')], topic=topic))
    app.chat_input[0].set_value('I have photos').run()
    after = app.session_state.case
    assert not app.exception and not after.last_result.error and after.facts == confirmed.facts
    assert any(f.name == 'evidence' for f in after.proposals)
    assert not any(f.name == 'purchase_date' for f in after.proposals)
    assert after.last_result.questions and len(after.last_result.questions) <= 2
    if topic == 'rental_deposit':
        assert 'could not verify the legal position' in after.last_result.message
    for c in after.last_result.claims:
        assert any(s.id == c.source_id and s.url == c.url and any(x.id == c.claim_id and x.en == c.text for x in s.claims)
                   for s in load_catalogue())
    app.run()
    assert app.session_state.case == after and sdk.models.generate_content.call_count == 2
    context = json.loads(sdk.models.generate_content.call_args.kwargs['contents'][0].parts[0].text)
    assert context['case']['confirmed_facts'][0]['value'] == value and context['history']


@pytest.mark.parametrize('finish', ['MAX_TOKENS', 'SAFETY', 'RECITATION'])
def test_even_valid_json_with_incomplete_finish_is_rejected(finish):
    sdk = Mock()
    sdk.models.generate_content.return_value = sdk_response(envelope(), finish=finish)
    provider = GeminiLLM(Settings(gemini_api_key='synthetic', gemini_model='test'), sdk_client=sdk)
    with pytest.raises(LLMError):
        provider.generate(LLMRequest('extract', (Message('user', 'online refund'),)))
    assert sdk.models.generate_content.call_count == 1


@pytest.mark.parametrize('wrapper', ['```json\n{}\n```', '\ufeff{}', '```\n{}\n```'])
def test_bounded_formatting_repair_never_calls_model_twice(wrapper):
    sdk = Mock()
    sdk.models.generate_content.return_value = SimpleNamespace(text=wrapper, usage_metadata=None)
    provider = GeminiLLM(Settings(gemini_api_key='synthetic', gemini_model='test'), sdk_client=sdk)
    assert provider.generate(LLMRequest('extract', (Message('user', 'online refund'),))).text == '{}'
    assert sdk.models.generate_content.call_count == 1


def test_stale_build_notice_preserves_case(monkeypatch):
    text, topic, name, value = CASES[0]
    app, sdk = run_ui(monkeypatch, sdk_response(envelope([row(name, value)])), text)
    before = app.session_state.case
    app.session_state.app_build = 'previous-build'
    app.run()
    assert any('Application updated' in w.value for w in app.warning)
    assert app.session_state.case == before and sdk.models.generate_content.call_count == 1
