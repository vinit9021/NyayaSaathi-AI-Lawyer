"""Provider-neutral transport contracts; legal extraction schemas come later.

These contracts validate transport shape, not legal truth. Response text must
never be displayed as verified legal guidance without later safety validation.
"""

from dataclasses import dataclass, field
from typing import Literal
from datetime import date
from uuid import uuid4
import json


def require_text(value: object, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text.")


def require_int(value: object, label: str, minimum: int, maximum: int) -> None:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{label} must be an integer from {minimum} to {maximum}.")


@dataclass(frozen=True)
class Message:
    role: Literal["user", "assistant"]
    content: str = field(repr=False)

    def __post_init__(self) -> None:
        if self.role not in ("user", "assistant"):
            raise ValueError("Message role must be user or assistant.")
        require_text(self.content, "Message content")


@dataclass(frozen=True)
class LLMRequest:
    system_instruction: str = field(repr=False)
    messages: tuple[Message, ...] = field(repr=False)
    max_output_tokens: int = 2048
    response_format: Literal["json", "text"] = "json"
    response_schema: dict | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        require_text(self.system_instruction, "System instruction")
        if not isinstance(self.messages, tuple) or not self.messages:
            raise ValueError("Messages must be a non-empty tuple.")
        if any(not isinstance(message, Message) for message in self.messages):
            raise ValueError("Messages must contain Message objects only.")
        require_int(self.max_output_tokens, "Output token limit", 1, 8192)
        if self.response_format not in ("json", "text"):
            raise ValueError("Response format must be json or text.")
        if self.response_schema is not None:
            if not isinstance(self.response_schema, dict) or self.response_format != "json":
                raise ValueError("Response schema requires a JSON object and JSON format.")
            json.dumps(self.response_schema, allow_nan=False)


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None

    def __post_init__(self) -> None:
        for value in (self.input_tokens, self.output_tokens):
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("Token counts must be non-negative integers or unknown.")


@dataclass(frozen=True)
class LLMResponse:
    text: str = field(repr=False)
    model: str
    usage: TokenUsage = field(default_factory=TokenUsage)

    def __post_init__(self) -> None:
        require_text(self.text, "Response text")
        require_text(self.model, "Model identifier")
        if not isinstance(self.usage, TokenUsage):
            raise ValueError("Usage must be a TokenUsage object.")


@dataclass(frozen=True)
class CuratedClaim:
    """Authored information, never unrestricted model prose."""

    id: str
    en: str
    hi: str
    kind: Literal["information", "referral", "statutory"]
    required_facts: tuple[str, ...] = ()


@dataclass(frozen=True)
class LegalSource:
    id: str
    title: str
    url: str
    authority: str
    jurisdiction: str
    topics: tuple[str, ...]
    tags: tuple[str, ...]
    scope: str
    locator: str
    summary: str
    summary_sha256: str
    verification: Literal["verified", "unverified"]
    usage: Literal["active", "reference_only"]
    checked_on: date
    review_due: date
    verification_note: str
    limitations: str
    claims: tuple[CuratedClaim, ...]


@dataclass(frozen=True)
class SourceMatch:
    source: LegalSource
    score: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalResult:
    matches: tuple[SourceMatch, ...]
    gaps: tuple[str, ...]


@dataclass(frozen=True)
class SafetyDecision:
    topic: str
    disposition: str
    reasons: tuple[str, ...]
    message: str

    @property
    def allow_drafting(self) -> bool:
        return self.disposition == "supported"


@dataclass(frozen=True)
class GroundedClaim:
    claim_id: str
    source_id: str
    kind: str
    text: str
    title: str
    url: str
    jurisdiction: str
    locator: str
    checked_on: date
    limitations: str


@dataclass(frozen=True)
class ClaimDecision:
    claims: tuple[GroundedClaim, ...]
    gaps: tuple[str, ...]


CASE_FIELDS = (
    "problem", "seller", "city", "state", "amount_paid", "refund_amount",
    "purchase_date", "delivery_date", "evidence", "contact_attempts", "desired_outcome",
    "deposit_paid", "deposit_returned", "move_out_date", "deductions", "agreement",
    "sender_name", "sender_contact", "recipient_contact", "product", "order_reference",
    "landlord", "rental_property", "agreement_date",
)


@dataclass(frozen=True)
class CaseFact:
    name: str
    value: str | None = field(repr=False)
    quote: str = field(repr=False)
    turn: int
    confirmed: bool = False

    def __post_init__(self):
        if self.name not in CASE_FIELDS:
            raise ValueError("Unknown case field.")
        if self.value is not None:
            require_text(self.value, "Fact value")
            if len(self.value) > 500:
                raise ValueError("Fact value is too long.")
        require_text(self.quote, "Fact provenance")
        require_int(self.turn, "Origin turn", 0, 20)
        if type(self.confirmed) is not bool:
            raise ValueError("Confirmation must be explicit.")


@dataclass(frozen=True)
class Extraction:
    topic: str
    confidence: float
    risk_flags: tuple[str, ...]
    facts: tuple[CaseFact, ...]


@dataclass(frozen=True)
class TurnResult:
    message: str
    decision: SafetyDecision
    questions: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()
    evidence_checklist: tuple[str, ...] = ()
    claims: tuple[GroundedClaim, ...] = ()
    gaps: tuple[str, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class CaseState:
    case_id: str = field(default_factory=lambda: uuid4().hex)
    language: str = "en"
    topic: str = "unclear"
    facts: tuple[CaseFact, ...] = field(default=(), repr=False)
    proposals: tuple[CaseFact, ...] = field(default=(), repr=False)
    conflicts: tuple[str, ...] = ()
    history: tuple[Message, ...] = field(default=(), repr=False)
    processed_ids: tuple[str, ...] = ()
    blocked: SafetyDecision | None = None
    last_result: TurnResult | None = field(default=None, repr=False)
    assessment: SafetyDecision | None = None

    def __post_init__(self):
        if self.language not in {"en", "hi"} or self.topic not in {"consumer", "rental_deposit", "unclear", "unsupported"}:
            raise ValueError("Invalid case language or topic.")
        for name in ("facts", "proposals"):
            values = getattr(self, name)
            if not isinstance(values, tuple) or any(not isinstance(v, CaseFact) for v in values):
                raise ValueError("Case facts must be typed tuples.")
            if len({v.name for v in values}) != len(values):
                raise ValueError("Duplicate case field.")
        if any(not f.confirmed for f in self.facts) or any(f.confirmed for f in self.proposals):
            raise ValueError("Confirmed facts and proposals must remain separate.")
        if len(self.history) > 40 or len(self.processed_ids) > 20:
            raise ValueError("Case session limit exceeded.")
