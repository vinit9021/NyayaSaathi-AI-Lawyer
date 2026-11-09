"""Offline replay of an unchanged real response to an explicitly fictional case."""

from pathlib import Path
import json

import pytest

from nyayasaathi.conversation import process_turn, follow_up_questions
from nyayasaathi.extraction import confirm_fact, preserve_intake_details
from nyayasaathi.models import CaseState, CaseFact, LLMResponse
from nyayasaathi.retrieval import load_catalogue, retrieve
from nyayasaathi.safety import ground_claims
from tests.fakes import FakeLLM
from datetime import date

pytestmark = pytest.mark.offline


def test_real_response_omissions_preserved_without_another_model_call():
    record = json.loads((Path(__file__).parent / 'fixtures/gemini_consumer_live.json').read_text(encoding='utf-8'))
    client = FakeLLM(LLMResponse(record['raw_response'], record['model']))
    text = record['synthetic_input']
    catalogue = load_catalogue()
    initial = CaseState()
    state = process_turn(initial, text, 'one', client, catalogue, as_of=date(2026, 11, 10))
    values = {f.name: f.value for f in state.proposals}
    assert state.topic == 'consumer' and not state.facts
    assert 'mixer grinder' in values['problem'] and 'damaged' in values['problem']
    assert values['seller'] == 'FictionalShop' and values['amount_paid'] == 'INR 3500'
    assert values['evidence'] == 'invoice and photos' and values['state'] == 'Maharashtra'
    assert values['contact_attempts'] == 'The seller refused a refund.'
    assert values['desired_outcome'] == 'money back'
    assert all(f.quote in text and f.value in f.quote and not f.confirmed for f in state.proposals)
    selected = tuple(m.source for m in retrieve(catalogue, topic=state.topic, text=text, as_of=date(2026, 11, 10)).matches)
    result = state.last_result
    assert ground_claims(selected, result.decision, tuple(c.claim_id for c in result.claims), as_of=date(2026, 11, 10)).claims == result.claims
    assert all(c.kind != 'statutory' for c in result.claims)
    assert process_turn(state, text, 'one', client, catalogue) is state
    assert len(client.requests) == 1
    confirmed = confirm_fact(state, 'amount_paid', values['amount_paid'])
    assert confirmed.facts[0].confirmed and confirmed.facts[0].value == 'INR 3500'
    assert state.proposals and not state.facts  # Original snapshot unchanged.
    assert not any('contacted' in q for q in follow_up_questions(confirmed))
    assert confirmed.history[0].content == text and confirmed.case_id == initial.case_id


@pytest.mark.parametrize('text', [
    'My fictional toaster broke. I emailed the shop yesterday.',
    'The seller declined my request.',
    'विक्रेता ने मना किया।',
])
def test_verbatim_supplements_generalize(text):
    facts = preserve_intake_details(CaseState(), (), text, 1)
    assert {f.name for f in facts} == {'problem', 'contact_attempts'}
    assert all(f.value == f.quote and f.quote in text and not f.confirmed for f in facts)


def test_supplements_do_not_overwrite_or_truncate():
    prior = confirm_fact(CaseState(), 'problem', 'Previous problem')
    fact = CaseFact('contact_attempts', 'replied', 'replied', 2)
    assert preserve_intake_details(prior, (fact,), 'They replied.', 2) == (fact,)
    assert not preserve_intake_details(CaseState(), (), 'x' * 501, 1)
    assert len(preserve_intake_details(CaseState(), (), 'I emailed. They replied.', 1)) == 1
