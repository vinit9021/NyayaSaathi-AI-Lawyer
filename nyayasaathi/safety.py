"""Conservative offline screening and constructive claim/citation enforcement.

Keyword screening is not a semantic classifier. Only a later successful semantic
classification may unlock a supported case; local risk flags always override it.
Never display model-authored legal prose directly. Use ground_claims instead.
"""

from collections.abc import Mapping
from datetime import date

from nyayasaathi.models import ClaimDecision, GroundedClaim, LegalSource, SafetyDecision
from nyayasaathi.retrieval import SUPPORTED_TOPICS, contains, eligible, normalize_state

DISCLAIMER = "AI legal-information assistant, not a licensed lawyer. Consult a qualified lawyer for legal advice or urgent matters."
UNVERIFIED = "I could not verify the legal position from the available sources."

# Deliberately conservative: mentions of danger/court action are not negation-
# resolved here. Later semantic review may clarify, but cannot silently bypass.
HIGH_RISK = (
    "urgent", "emergency", "hearing", "summons", "court notice", "legal notice",
    "limitation", "deadline", "injunction", "evict", "eviction", "locked out",
    "lockout", "threat", "threatened", "threatening", "violence", "assault",
    "arrest", "injury", "injured", "death", "suicide", "self harm",
    "सुनवाई", "समन", "धमकी", "हिंसा", "बेदखल", "गिरफ्तार", "चोट",
    "आत्महत्या", "तुरंत", "अंतिम तारीख", "dhamki", "sunwai", "maar dunga",
    "ghar se nikal", "taala", "ताला", "jaan se", "court tomorrow",
)
OUT_OF_SCOPE = (
    "criminal", "bail", "fir", "police case", "divorce", "custody", "maintenance",
    "inheritance", "partition", "property title", "land dispute", "court representation",
    "tax", "visa", "employment", "salary", "insurance", "medical negligence",
    "तलाक", "जमानत", "एफआईआर", "विरासत", "जमीन विवाद", "आपराधिक",
    "talak", "talaq", "custody", "zameen", "बच्चे की कस्टडी",
    "commercial purpose", "resale", "for my business", "पुनर्विक्रय",
)
INJECTION = (
    "ignore previous", "ignore all instructions", "ignore your instructions",
    "ignore safety", "system prompt", "reveal secrets", "api key", "access token",
    "invent a law", "invent a judgment", "make up a case", "fake citation",
    "fabricate", "made-up law", "झूठा कानून", "फर्जी कानून", "नकली फैसला",
    "fake section", "jhootha kanoon", "nakli judgment",
)
CONSUMER_CHANNEL = ("online", "ऑनलाइन", "amazon", "flipkart", "website", "ecommerce", "e-commerce")
CONSUMER_PROBLEM = (
    "refund", "refunds", "defective", "damaged", "broken", "faulty", "not delivered",
    "non-delivery", "never arrived", "money back", "खराब", "टूटा", "टूटी",
    "रिफंड", "पैसे वापस", "नहीं मिला", "नहीं आया", "kharab", "toota",
    "paise wapas", "nahi mila", "delivery nahi",
)
RENTAL_PARTY = ("landlord", "tenant", "rental", "rent", "lease", "मकान मालिक", "किराया", "किरायेदार", "maalik", "makaan", "kiraya")
RENTAL_PROBLEM = ("deposit", "deduction", "deductions", "जमा", "कटौती", "जमानत राशि", "advance", "security", "paise wapas")


def _any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(contains(text, phrase) for phrase in phrases)


def assess_request(
    text: str, *, confirmed_topic: str | None = None,
    classifier_succeeded: bool = False, semantic_risk_flags: tuple[str, ...] = (),
) -> SafetyDecision:
    """Screen full case context, not just the last message, at every future turn.

    confirmed_topic/classifier_succeeded are trusted orchestration inputs, never
    fields accepted from the user's message. M2 performs no model classification.
    """
    if not isinstance(text, str) or not text.strip() or len(text) > 4000:
        return SafetyDecision("unclear", "clarify", ("invalid_or_oversized_input",), "Please describe the issue briefly without private identifiers.")
    if _any(text, HIGH_RISK) or semantic_risk_flags:
        return SafetyDecision("unsupported", "escalate", ("high_risk_or_time_sensitive",),
                              "This may be urgent or high-risk. Contact a qualified lawyer promptly; if there is immediate danger, seek local emergency help. Do not rely on this prototype for deadlines.")
    if _any(text, INJECTION):
        return SafetyDecision("unsupported", "reject", ("unsafe_instruction_or_fabrication_request",),
                              "I cannot invent legal authority, reveal secrets, or bypass source checks.")
    if _any(text, OUT_OF_SCOPE):
        return SafetyDecision("unsupported", "escalate", ("unsupported_category",),
                              "This is outside the two supported dispute types. Please consult a qualified lawyer.")
    consumer = _any(text, CONSUMER_CHANNEL) and _any(text, CONSUMER_PROBLEM)
    rental = _any(text, RENTAL_PARTY) and _any(text, RENTAL_PROBLEM)
    if consumer and rental:
        return SafetyDecision("unclear", "clarify", ("mixed_topics",), "Please separate the shopping and rental-deposit issues.")
    candidate = "consumer" if consumer else "rental_deposit" if rental else "unclear"
    if classifier_succeeded is not True:
        return SafetyDecision(candidate, "clarify", ("semantic_review_required",),
                              "The issue needs scope and risk confirmation before legal options or drafting.")
    if confirmed_topic == "unsupported":
        return SafetyDecision("unsupported", "escalate", ("unsupported_classification",),
                              "This issue is outside the supported scope. Please consult a qualified lawyer.")
    if confirmed_topic not in SUPPORTED_TOPICS:
        return SafetyDecision("unclear", "clarify",
                              ("unsupported_or_unclear_classification",), "Please clarify the issue or consult a qualified lawyer.")
    if candidate != "unclear" and candidate != confirmed_topic:
        return SafetyDecision("unclear", "clarify", ("conflicting_classification",), "Please clarify which dispute you need help with.")
    return SafetyDecision(confirmed_topic, "supported", (),
                          "General legal information only; applicability requires review. " + DISCLAIMER)


def require_drafting_allowed(decision: SafetyDecision) -> None:
    """Guard for milestone 4; this function does not create any document."""
    if not decision.allow_drafting or decision.topic not in SUPPORTED_TOPICS:
        raise ValueError("Drafting is blocked until scope and risk checks pass.")


def ground_claims(
    catalogue: tuple[LegalSource, ...], decision: SafetyDecision,
    claim_ids: tuple[str, ...], *, state: str | None = None,
    language: str = "en", confirmed_facts: frozenset[str] = frozenset(),
    as_of: date | None = None,
) -> ClaimDecision:
    """Select only immutable curated text; reject the whole batch on any gap.

    IDs select claims, never supply prose/URLs. Fact flags must be produced by
    trusted orchestration from confirmed case facts, not model self-attestation.
    """
    if language not in {"en", "hi"}:
        return ClaimDecision((), ("unsupported_output_language",))
    if not decision.allow_drafting or decision.topic not in SUPPORTED_TOPICS:
        return ClaimDecision((), ("safety_gate_blocked",))
    if not isinstance(claim_ids, tuple) or not claim_ids or any(not isinstance(v, str) for v in claim_ids):
        return ClaimDecision((), ("no_valid_claim_selection",))
    today = date.today() if as_of is None else as_of
    available = {}
    for source in catalogue:
        if eligible(source, decision.topic, state, today):
            for claim in source.claims:
                if claim.id in available:
                    return ClaimDecision((), ("ambiguous_claim_id",))
                available[claim.id] = (source, claim)
    approved = []
    gaps = []
    for claim_id in dict.fromkeys(claim_ids):
        if claim_id not in available:
            gaps.append("unsupported_or_inapplicable_claim")
            continue
        source, claim = available[claim_id]
        if claim.kind == "statutory" and decision.topic == "rental_deposit":
            if normalize_state(state) is None or source.jurisdiction == "IN":
                gaps.append("rental_state_law_required")
                continue
        if not set(claim.required_facts) <= confirmed_facts:
            gaps.append("claim_applicability_unconfirmed")
            continue
        approved.append(GroundedClaim(
            claim.id, source.id, claim.kind, getattr(claim, language), source.title, source.url,
            source.jurisdiction, source.locator, source.checked_on, source.limitations,
        ))
    return ClaimDecision(() if gaps else tuple(approved), tuple(dict.fromkeys(gaps)))


def validate_proposed_claim(
    proposal: Mapping[str, object], catalogue: tuple[LegalSource, ...],
    decision: SafetyDecision, **context,
) -> ClaimDecision:
    """Strict compatibility gate for later model output; no fuzzy citation match.

    Adding a section, deadline, extra text, or real-but-unrelated URL fails. The
    recommended interface remains selecting IDs via ground_claims directly.
    """
    if not isinstance(proposal, Mapping) or set(proposal) != {"claim_id", "source_id", "text", "url"}:
        return ClaimDecision((), ("invalid_claim_shape",))
    if any(not isinstance(v, str) for v in proposal.values()):
        return ClaimDecision((), ("invalid_claim_shape",))
    result = ground_claims(catalogue, decision, (proposal["claim_id"],), **context)
    if not result.claims:
        return result
    claim = result.claims[0]
    if proposal != {"claim_id": claim.claim_id, "source_id": claim.source_id, "text": claim.text, "url": claim.url}:
        return ClaimDecision((), ("citation_or_text_mismatch",))
    return result
