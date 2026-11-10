from dataclasses import replace
import json

import pytest

from nyayasaathi.extraction import confirm_fact, merge_proposals, parse_extraction
from nyayasaathi.models import CaseFact, CaseState

pytestmark = pytest.mark.offline


def payload(**updates):
    return json.dumps({"topic": "consumer", "confidence": 0.95, "risk_flags": [], "facts": [], **updates})


def test_exact_quote_proposals_not_confirmed():
    result = parse_extraction(payload(facts=[{"name": "amount_paid", "value": "5000", "quote": "I paid 5000"}]), "I paid 5000", 1)
    assert result.facts[0].value == "5000"
    assert not result.facts[0].confirmed
    assert result.facts[0].turn == 1


@pytest.mark.parametrize("updates", [
    {"confidence": True}, {"confidence": -1}, {"confidence": float("nan")},
    {"topic": "criminal_law"}, {"risk_flags": ["made_up"]}, {"facts": {}},
    {"answer": "Section 999 guarantees a refund"},
    {"facts": [{"name": "amount_paid", "value": "9000", "quote": "5000"}]},
    {"facts": [{"name": "amount_paid", "value": "5000", "quote": "I paid 5000"}]},
    {"facts": [{"name": "law", "value": "5000", "quote": "5000"}]},
    {"facts": [{"name": "amount_paid", "value": "5000", "quote": "5000", "confirmed": True}]},
])
def test_untrusted_shape_and_hallucinations_rejected(updates):
    if isinstance(updates.get('facts'), list):
        result = parse_extraction(payload(**updates), "5000", 1)
        assert not result.facts and result.issues
    else:
        with pytest.raises(ValueError, match="confirmed facts were preserved"):
            parse_extraction(payload(**updates), "5000", 1)


@pytest.mark.parametrize("raw", ["not JSON", '[]', '{"topic":"consumer","topic":"unsupported"}', "x" * 24001])
def test_bad_json_rejected(raw):
    with pytest.raises(ValueError):
        parse_extraction(raw, "hello", 1)


def test_conflicting_proposal_preserves_old_fact_until_user_confirms():
    state = confirm_fact(CaseState(topic="consumer"), "amount_paid", "5000")
    changed = merge_proposals(state, (CaseFact("amount_paid", "7000", "7000", 1),))
    assert changed.facts[0].value == "5000"
    assert changed.proposals[0].value == "7000"
    assert changed.conflicts == ("amount_paid",)
    corrected = confirm_fact(changed, "amount_paid", "7000")
    assert corrected.facts[0].value == "7000"
    assert not corrected.proposals and not corrected.conflicts
    assert state.facts[0].value == "5000"  # Transactional immutable input.


@pytest.mark.parametrize("name,value", [
    ("amount_paid", "5k"), ("amount_paid", "5000 or 7000"), ("amount_paid", "-1"),
    ("purchase_date", "01/02/26"), ("purchase_date", "2026-02-30"),
    ("state", "Chennai"), ("state", "California"), ("seller", ""),
])
def test_ambiguous_values_require_user_correction(name, value):
    with pytest.raises(ValueError):
        confirm_fact(CaseState(), name, value)


def test_user_can_mark_unknown_without_inventing_value():
    state = confirm_fact(CaseState(), "purchase_date", None)
    assert state.facts[0].value is None and state.facts[0].confirmed


def test_edits_cannot_bypass_risk_screen():
    state = confirm_fact(CaseState(), "problem", "urgent hearing")
    assert state.blocked
    with pytest.raises(ValueError):
        confirm_fact(state, "seller", "DemoShop")


def test_case_models_reject_invalid_states():
    with pytest.raises(ValueError):
        CaseState(language="xx")
    with pytest.raises(ValueError):
        CaseState(facts=(CaseFact("seller", "DemoShop", "DemoShop", 1),))
    with pytest.raises(ValueError):
        replace(CaseState(), processed_ids=tuple(str(i) for i in range(21)))
