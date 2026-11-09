"""Offline catalogue validation and deterministic topic/jurisdiction retrieval.

No URLs are fetched here. A verified flag is a curator's recorded review, not
proof supplied by a model. Only trusted repository catalogue files may be loaded.
"""

from datetime import date
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit

from nyayasaathi.models import CuratedClaim, LegalSource, RetrievalResult, SourceMatch

CATALOGUE_PATH = Path(__file__).resolve().parents[1] / "sources" / "catalogue.json"
SUPPORTED_TOPICS = frozenset({"consumer", "rental_deposit"})
OFFICIAL_HOSTS = frozenset({
    "consumerhelpline.gov.in", "consumeraffairs.gov.in", "www.indiacode.nic.in",
    "www.tenancy.tn.gov.in", "www.pib.gov.in", "nalsa.gov.in",
})
STATES = {
    "andhra pradesh": "AP", "arunachal pradesh": "AR", "assam": "AS",
    "bihar": "BR", "chhattisgarh": "CG", "goa": "GA", "gujarat": "GJ",
    "haryana": "HR", "himachal pradesh": "HP", "jharkhand": "JH",
    "karnataka": "KA", "kerala": "KL", "madhya pradesh": "MP",
    "maharashtra": "MH", "manipur": "MN", "meghalaya": "ML", "mizoram": "MZ",
    "nagaland": "NL", "odisha": "OD", "punjab": "PB", "rajasthan": "RJ",
    "sikkim": "SK", "tamil nadu": "TN", "telangana": "TS", "tripura": "TR",
    "uttar pradesh": "UP", "uttarakhand": "UK", "west bengal": "WB",
    "andaman and nicobar islands": "AN", "chandigarh": "CH",
    "dadra and nagar haveli and daman and diu": "DH", "delhi": "DL",
    "jammu and kashmir": "JK", "ladakh": "LA", "lakshadweep": "LD",
    "puducherry": "PY", "तमिलनाडु": "TN", "महाराष्ट्र": "MH",
    "कर्नाटक": "KA", "दिल्ली": "DL", "उत्तर प्रदेश": "UP",
}
TAG_ALIASES = {
    "refund": ("refund", "refunds", "money back", "paise wapas", "पैसे वापस", "रिफंड"),
    "defect": ("defect", "defective", "faulty", "kharab", "खराब"),
    "damage": ("damage", "damaged", "broken", "toota", "टूटा", "टूटी"),
    "non_delivery": ("non-delivery", "not delivered", "delivery nahi", "नहीं मिला", "नहीं आया"),
    "deposit": ("deposit", "security deposit", "जमा", "जमानत राशि"),
    "deduction": ("deduction", "deductions", "कटौती", "kaat"),
    "legal_help": ("lawyer", "legal aid", "वकील", "vakil"),
}


class CatalogueError(ValueError):
    """Safe validation failure, with no raw catalogue/user content."""


def normalize(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def contains(text: str, phrase: str) -> bool:
    # Unicode word boundaries prevent 'bail' matching 'bailiff' accidentally.
    return re.search(r"(?<!\w)" + re.escape(normalize(phrase)) + r"(?!\w)", normalize(text)) is not None


def normalize_state(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = normalize(value)
    if normalized in STATES:
        return "IN-" + STATES[normalized]
    code = normalized.upper().removeprefix("IN-")
    return "IN-" + code if code in STATES.values() else None


def query_tags(text: str) -> tuple[str, ...]:
    return tuple(tag for tag, aliases in TAG_ALIASES.items()
                 if any(contains(text, alias) for alias in aliases))


def load_catalogue(path: str | Path = CATALOGUE_PATH) -> tuple[LegalSource, ...]:
    """Reject malformed, ambiguous, or tampered records as one failed load."""
    try:
        rows = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            raise ValueError
        sources = []
        source_ids: set[str] = set()
        claim_ids: set[str] = set()
        fields = set(LegalSource.__dataclass_fields__)
        for row in rows:
            if not isinstance(row, dict) or set(row) != fields:
                raise ValueError
            string_fields = fields - {"topics", "tags", "claims"}
            if any(not isinstance(row[k], str) or not row[k].strip() for k in string_fields):
                raise ValueError
            url = urlsplit(row["url"])
            if (url.scheme != "https" or url.hostname not in OFFICIAL_HOSTS
                    or url.username or url.password or url.port not in (None, 443)):
                raise ValueError
            if row["id"] in source_ids or not re.fullmatch(r"[a-z0-9_]+", row["id"]):
                raise ValueError
            source_ids.add(row["id"])
            if row["jurisdiction"] != "IN" and normalize_state(row["jurisdiction"]) != row["jurisdiction"]:
                raise ValueError
            for name in ("topics", "tags"):
                if not isinstance(row[name], list) or not row[name] or any(
                    not isinstance(v, str) or not v.strip() for v in row[name]
                ):
                    raise ValueError
            if not set(row["topics"]) <= SUPPORTED_TOPICS:
                raise ValueError
            if row["verification"] not in {"verified", "unverified"} or row["usage"] not in {"active", "reference_only"}:
                raise ValueError
            checked, due = date.fromisoformat(row["checked_on"]), date.fromisoformat(row["review_due"])
            if due < checked:
                raise ValueError
            if hashlib.sha256(row["summary"].encode("utf-8")).hexdigest() != row["summary_sha256"]:
                raise ValueError
            if not isinstance(row["claims"], list):
                raise ValueError
            claims = []
            for claim in row["claims"]:
                if not isinstance(claim, dict) or set(claim) != set(CuratedClaim.__dataclass_fields__):
                    raise ValueError
                if any(not isinstance(claim[k], str) or not claim[k].strip() for k in ("id", "en", "hi", "kind")):
                    raise ValueError
                if claim["id"] in claim_ids or not re.fullmatch(r"[a-z0-9_]+", claim["id"]):
                    raise ValueError
                claim_ids.add(claim["id"])
                if claim["kind"] not in {"information", "referral", "statutory"}:
                    raise ValueError
                if not isinstance(claim["required_facts"], list) or any(
                    not isinstance(v, str) or not v for v in claim["required_facts"]
                ):
                    raise ValueError
                # URLs belong only to source metadata, never translated prose.
                if any(re.search(r"https?://|www\.", claim[k], re.I) for k in ("en", "hi")):
                    raise ValueError
                claims.append(CuratedClaim(**{**claim, "required_facts": tuple(claim["required_facts"])}))
            if row["verification"] != "verified" and claims:
                raise ValueError
            if row["usage"] == "active" and not claims:
                raise ValueError
            sources.append(LegalSource(**{
                **row, "topics": tuple(row["topics"]), "tags": tuple(row["tags"]),
                "claims": tuple(claims), "checked_on": checked, "review_due": due,
            }))
        return tuple(sources)
    except (OSError, ValueError, TypeError, KeyError):
        raise CatalogueError("Legal source catalogue is unavailable or invalid; no claims may be verified.") from None


def eligible(source: LegalSource, topic: str, state: str | None, as_of: date) -> bool:
    return (
        source.verification == "verified" and source.usage == "active"
        and source.checked_on <= as_of <= source.review_due
        and topic in source.topics
        and (source.jurisdiction == "IN" or source.jurisdiction == normalize_state(state))
    )


def retrieve(
    catalogue: tuple[LegalSource, ...], *, topic: str, state: str | None = None,
    text: str = "", as_of: date | None = None, limit: int = 3,
) -> RetrievalResult:
    """Topic is an explicit input, not inferred by retrieval. No match is valid."""
    if type(limit) is not int or not 1 <= limit <= 10:
        raise ValueError("Retrieval limit must be an integer from 1 to 10.")
    if topic not in SUPPORTED_TOPICS:
        return RetrievalResult((), ("unsupported_or_unclear_topic",))
    today = date.today() if as_of is None else as_of
    tags = set(query_tags(text))
    matches = []
    for source in catalogue:
        if not eligible(source, topic, state, today):
            continue
        matched = tuple(sorted(tags.intersection(source.tags)))
        # Topic is already a relevance filter; tag matches only order that set.
        matches.append(SourceMatch(source, len(matched), ("topic:" + topic, "jurisdiction:" + source.jurisdiction)
                                   + tuple("tag:" + tag for tag in matched)))
    matches.sort(key=lambda match: (-match.score, match.source.id))
    gaps = []
    if topic == "rental_deposit":
        if normalize_state(state) is None:
            gaps.append("state_required_for_rental_law")
        state_law = any(m.source.jurisdiction != "IN" and any(c.kind == "statutory" for c in m.source.claims)
                        for m in matches)
        if not state_law:
            gaps.append("rental_statutory_position_unverified")
    if not matches:
        gaps.append("no_verified_applicable_sources")
    return RetrievalResult(tuple(matches[:limit]), tuple(gaps))
