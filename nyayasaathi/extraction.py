"""Strict intake parsing, explicit confirmation, and conflict-preserving merges."""

from dataclasses import replace
from datetime import date
import json
import math
import re
import unicodedata
from decimal import Decimal

from nyayasaathi.models import CASE_FIELDS, CaseFact, CaseState, Extraction, FactIssue, Message
from nyayasaathi.retrieval import normalize_state
from nyayasaathi.safety import assess_request

TOPICS = ("consumer", "rental_deposit", "unclear", "unsupported")
RISKS = ("danger", "urgent", "court_proceedings", "criminal", "complex_property", "family", "other_high_risk")
INTAKE_VERSION = "2"
EXTRACTION_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["topic", "confidence", "risk_flags"],
    "properties": {
        "topic": {"type": "string", "enum": list(TOPICS)},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "risk_flags": {"type": "array", "items": {"type": "string", "enum": list(RISKS)}},
        "facts": {"type": "array", "maxItems": len(CASE_FIELDS), "items": {
            "type": "object", "additionalProperties": False,
            "required": ["name", "value", "quote"],
            "properties": {
                "name": {"type": "string", "enum": list(CASE_FIELDS)},
                "value": {"type": ["string", "null"], "minLength": 1, "maxLength": 500},
                "quote": {"type": "string", "minLength": 1, "maxLength": 4000},
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


class ExtractionError(ValueError):
    """Static diagnostic category only; never retain model output or user text."""

    def __init__(self, code: str):
        self.code = code
        super().__init__("The intake response was invalid; confirmed facts were preserved.")


def parse_extraction(text: str, user_text: str, turn: int) -> Extraction:
    """Validate safety envelope atomically, then quarantine individual bad fields."""
    try:
        if not isinstance(text, str) or len(text) > 24000:
            raise ValueError
        data = json.loads(text, object_pairs_hook=_unique_object)
        required = {"topic", "confidence", "risk_flags"}
        if not isinstance(data, dict) or not required <= set(data) or set(data) - required - {"facts"}:
            raise ValueError
        if data["topic"] not in TOPICS:
            raise ValueError
        confidence = data["confidence"]
        if type(confidence) not in (float, int) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError
        if not isinstance(data["risk_flags"], list) or any(r not in RISKS for r in data["risk_flags"]):
            raise ValueError
        rows = data.get("facts", [])
        if not isinstance(rows, list) or len(rows) > len(CASE_FIELDS):
            raise ValueError
    except (ValueError, TypeError, KeyError, RecursionError):
        raise ExtractionError("intake_shape") from None
    facts = {}
    issues = []
    seen = {}
    rejected = set()
    for row in rows:
        name = row.get("name") if isinstance(row, dict) else None
        name = name if isinstance(name, str) and name in CASE_FIELDS else None
        if name is not None and name in seen:
            if row == seen[name]:  # Identical copies carry no additional evidence.
                continue
            # Lists of evidence/communications may legitimately be emitted as
            # separate rows. Combine only independently validated, exact quotes
            # into their ORIGINAL contiguous user passage, never model prose.
            if name in {"evidence", "contact_attempts"} and name in facts and name not in rejected:
                try:
                    additional = _parse_fact(row, user_text, turn)
                    previous = facts[name]
                    start = min(user_text.index(previous.quote), user_text.index(additional.quote))
                    end = max(user_text.index(previous.quote) + len(previous.quote),
                              user_text.index(additional.quote) + len(additional.quote))
                    passage = user_text[start:end]
                    if len(passage) <= 500:
                        facts[name] = CaseFact(name, passage, passage, turn)
                        continue
                except (ExtractionError, ValueError):
                    pass
            facts.pop(name, None)
            rejected.add(name)
            issues.append(FactIssue(name, "fact_conflict"))
            continue
        if name is not None:
            seen[name] = row
        try:
            fact = _parse_fact(row, user_text, turn)
            if fact.name not in rejected:
                facts[fact.name] = fact
        except ExtractionError as error:
            issues.append(FactIssue(name, error.code))
    return Extraction(data["topic"], float(confidence), tuple(data["risk_flags"]),
                      tuple(facts.values()), tuple(dict.fromkeys(issues)))


MONEY_FIELDS = {"amount_paid", "refund_amount", "deposit_paid", "deposit_returned"}
NARRATIVE_FIELDS = {"problem", "evidence", "contact_attempts", "desired_outcome", "deductions", "agreement"}
# Do not strip arbitrary commas: only valid Indian/Western grouping is harmless.
_NUMBER = r"(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]{1,2}(?:,[0-9]{2})*,[0-9]{3}|[0-9]+)(?:\.[0-9]{1,2})?"
_MONEY = rf"(?:(?:INR|Rs\.?|₹)\s*)?{_NUMBER}"


def _money_value(value: str) -> Decimal | None:
    if not re.fullmatch(_MONEY, value, re.I):
        return None
    return Decimal(re.sub(r"^(?:INR|Rs\.?|₹)\s*", "", value, flags=re.I).replace(",", ""))


def _literal_span(value: str, text: str) -> str | None:
    """Whitespace-only equivalence, returning ORIGINAL user characters.

    No case folding, translation, punctuation removal, fuzzy matching or numeric
    substring matches. Word boundaries avoid 'paid' inside 'unpaid'.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    pattern = r"\s+".join(re.escape(part) for part in value.split())
    def wordish(character):
        return character == '_' or unicodedata.category(character)[0] in {'L', 'M', 'N'}
    for found in re.finditer(pattern, text):
        if ((found.start() == 0 or not wordish(text[found.start() - 1]))
                and (found.end() == len(text) or not wordish(text[found.end()]))):
            return found.group()
    return None


def _parse_fact(row: object, user_text: str, turn: int) -> CaseFact:
    if (not isinstance(row, dict) or set(row) != {"name", "value", "quote"}
            or not isinstance(row["name"], str) or row["name"] not in CASE_FIELDS):
        raise ExtractionError("fact_shape")
    name, value, quote = row["name"], row["value"], row["quote"]
    if value is None:
        # A model-null is not proof the user said 'unknown'. Keep it unanswered;
        # the user can explicitly mark unknown in the review form.
        raise ExtractionError("fact_absent")
    if name in MONEY_FIELDS and type(value) is int and 0 <= value <= 10**15:
        value = str(value)  # Accept only when an equal, unambiguous user token exists.
    if (not isinstance(value, str) or not value.strip() or len(value) > 500
            or not isinstance(quote, str) or not quote.strip() or len(quote) > 4000):
        raise ExtractionError("fact_shape")
    quote = _literal_span(quote, user_text)
    if quote is None:
        raise ExtractionError("fact_provenance")
    literal = _literal_span(value, quote)
    if name in MONEY_FIELDS:
        numeric = _money_value(value.strip())
        tokens = re.findall(r"(?<![\w.,+/:\-])" + _MONEY + r"(?![\w,/:\-]|\.[0-9])", quote, re.I)
        # A quote containing two sums/dates is ambiguous; ask for a narrow quote.
        if (numeric is None or len(tokens) != 1 or _money_value(tokens[0]) != numeric
                or re.search(r"\b(?:USD|EUR|GBP|dollars?|euros?|pounds?)\b|[$€£]", quote, re.I)):
            raise ExtractionError("fact_provenance")
        value = tokens[0]  # Original formatting; confirmation remains explicit.
    elif name in NARRATIVE_FIELDS and literal is None and len(quote) <= 500:
        value = quote  # Discard model paraphrase and preserve the user's assertion.
    elif literal is not None:
        value = literal
    else:
        raise ExtractionError("fact_provenance")
    if name == "state" and normalize_state(value) is None:
        raise ExtractionError("fact_provenance")
    if name.endswith("_date") and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            date.fromisoformat(value)
        except ValueError:
            raise ExtractionError("fact_provenance") from None
    try:
        return CaseFact(name, value, quote, turn)
    except (ValueError, TypeError):
        raise ExtractionError("fact_shape") from None


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


def preserve_intake_details(state: CaseState, facts: tuple[CaseFact, ...], text: str, turn: int) -> tuple[CaseFact, ...]:
    """Keep short initial narratives and omitted communication statements verbatim.

    This is loss prevention, not semantic fact invention. Every supplement is
    an unconfirmed user assertion with an exact quote, still subject to review.
    Long narratives remain in chat history instead of being silently truncated.
    """
    values = {f.name: f for f in facts}
    existing = {f.name for f in state.facts + state.proposals}
    if "problem" not in existing and len(text) <= 500:
        values["problem"] = CaseFact("problem", text, text, turn)
    if "contact_attempts" not in existing and "contact_attempts" not in values:
        sentences = re.split(r"(?<=[.!?।])\s+|\n+", text)
        pattern = r"\b(?:refused|declined|contacted|emailed|replied|responded)\b|मना|संपर्क|जवाब|\bmana kiya\b"
        matches = [s.strip() for s in sentences if re.search(pattern, s, re.I)]
        if len(matches) == 1 and len(matches[0]) <= 500:
            quote = matches[0]
            values["contact_attempts"] = CaseFact("contact_attempts", quote, quote, turn)
    return tuple(values.values())


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


def confirm_facts(state: CaseState, values: dict[str, str | None]) -> CaseState:
    """Atomic bulk review: validate everything before committing any correction."""
    for name, value in values.items():
        validate_confirmed_value(name, value)
    result = state
    for name, value in values.items():
        result = confirm_fact(result, name, value)
        if result.blocked:
            return replace(state, blocked=result.blocked, last_result=None)
    return result
