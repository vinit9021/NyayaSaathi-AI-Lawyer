"""Strict intake parsing, explicit confirmation, and conflict-preserving merges."""

from dataclasses import replace
from datetime import date
import json
import math
import re

from nyayasaathi.models import CASE_FIELDS, CaseFact, CaseState, Extraction, Message
from nyayasaathi.retrieval import normalize_state
from nyayasaathi.safety import assess_request

TOPICS = ("consumer", "rental_deposit", "unclear", "unsupported")
RISKS = ("danger", "urgent", "court_proceedings", "criminal", "complex_property", "family", "other_high_risk")
EXTRACTION_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["topic", "confidence", "risk_flags", "facts"],
    "properties": {
        "topic": {"type": "string", "enum": list(TOPICS)},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "risk_flags": {"type": "array", "items": {"type": "string", "enum": list(RISKS)}},
        "facts": {"type": "array", "maxItems": len(CASE_FIELDS), "items": {
            "type": "object", "additionalProperties": False,
            "required": ["name", "value", "quote"],
            "properties": {
                "name": {"type": "string", "enum": list(CASE_FIELDS)},
                "value": {"type": ["string", "null"]},
                "quote": {"type": "string"},
            },
        }},
    },
}


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field.")
        result[key] = value
    return result


def parse_extraction(text: str, user_text: str, turn: int) -> Extraction:
    """No prose, citations, or unquoted model inventions cross this boundary."""
    try:
        if not isinstance(text, str) or len(text) > 24000:
            raise ValueError
        data = json.loads(text, object_pairs_hook=_unique_object)
        if not isinstance(data, dict) or set(data) != {"topic", "confidence", "risk_flags", "facts"}:
            raise ValueError
        if data["topic"] not in TOPICS:
            raise ValueError
        confidence = data["confidence"]
        if type(confidence) not in (float, int) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError
        if not isinstance(data["risk_flags"], list) or any(r not in RISKS for r in data["risk_flags"]):
            raise ValueError
        if not isinstance(data["facts"], list) or len(data["facts"]) > len(CASE_FIELDS):
            raise ValueError
        facts = []
        names = set()
        for row in data["facts"]:
            if not isinstance(row, dict) or set(row) != {"name", "value", "quote"}:
                raise ValueError
            fact = CaseFact(**row, turn=turn)
            if fact.name in names or fact.quote not in user_text:
                raise ValueError
            if fact.value is not None and fact.value not in fact.quote:
                raise ValueError
            names.add(fact.name)
            facts.append(fact)
        return Extraction(data["topic"], float(confidence), tuple(data["risk_flags"]), tuple(facts))
    except (ValueError, TypeError, KeyError, RecursionError):
        raise ValueError("The intake response was invalid; confirmed facts were preserved.") from None


def merge_proposals(state: CaseState, facts: tuple[CaseFact, ...]) -> CaseState:
    confirmed = {f.name: f for f in state.facts}
    proposed = {f.name: f for f in state.proposals}
    conflicts = set(state.conflicts)
    for fact in facts:
        existing = confirmed.get(fact.name)
        if existing is not None and existing.value == fact.value:
            continue
        if existing is not None:
            conflicts.add(fact.name)
        proposed[fact.name] = fact
    return replace(state, proposals=tuple(proposed.values()), conflicts=tuple(sorted(conflicts)))


def validate_confirmed_value(name: str, value: str | None) -> None:
    if name not in CASE_FIELDS:
        raise ValueError("Unknown case field.")
    if value is None:
        return  # Explicitly unavailable is not invented, zero, or an empty answer.
    if not isinstance(value, str) or not value.strip() or len(value) > 500:
        raise ValueError("Enter a short value or mark it unknown.")
    if name == "state" and normalize_state(value) is None:
        raise ValueError("Use a recognized Indian state/UT name or code, or mark it unknown.")
    if name.endswith("_date"):
        try:
            date.fromisoformat(value)
        except ValueError:
            raise ValueError("Confirm dates as YYYY-MM-DD, or mark them unknown.") from None
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("Confirm dates as YYYY-MM-DD.")
    if name in {"amount_paid", "refund_amount", "deposit_paid", "deposit_returned"}:
        if not re.fullmatch(r"(?:(?:INR|Rs\.?|₹)\s*)?\d+(?:\.\d{1,2})?", value, re.I):
            raise ValueError("Confirm INR amounts as digits without commas (for example INR 5000), or mark unknown.")


def confirm_fact(state: CaseState, name: str, value: str | None) -> CaseState:
    """Explicit user confirmation/correction, never called from model output."""
    validate_confirmed_value(name, value)
    if state.blocked:
        raise ValueError("This case is blocked; consult qualified help or start a new case.")
    text = value if value is not None else "unknown"
    local = assess_request(text)
    if local.disposition in {"escalate", "reject"}:
        return replace(state, blocked=local, last_result=None)
    facts = {f.name: f for f in state.facts}
    facts[name] = CaseFact(name, value, text, len(state.processed_ids), confirmed=True)
    return replace(
        state, facts=tuple(facts.values()), proposals=tuple(f for f in state.proposals if f.name != name),
        conflicts=tuple(f for f in state.conflicts if f != name), last_result=None,
        history=(state.history + (Message("user", f"User-confirmed {name}: {text}"),))[-40:],
    )
