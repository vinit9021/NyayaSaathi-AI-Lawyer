from dataclasses import replace
from datetime import date
import json

import pytest

from nyayasaathi.models import CuratedClaim
from nyayasaathi.retrieval import (
    CATALOGUE_PATH, CatalogueError, load_catalogue, normalize_state, query_tags, retrieve,
)

pytestmark = pytest.mark.offline
REVIEW_DATE = date(2026, 11, 9)


@pytest.fixture
def catalogue():
    return load_catalogue()


def test_catalogue_review_status_and_provenance(catalogue):
    assert len(catalogue) == 7
    assert sum(s.verification == "verified" for s in catalogue) == 5
    assert sum(s.usage == "active" for s in catalogue) == 4
    for source in catalogue:
        assert source.checked_on == REVIEW_DATE
        assert source.locator and source.limitations and source.verification_note
        assert len(source.summary_sha256) == 64
        if source.verification != "verified" or source.usage != "active":
            assert not source.claims


@pytest.mark.parametrize("text,tag", [
    ("online refund", "refund"), ("ऑनलाइन सामान खराब है", "defect"),
    ("online paise wapas chahiye", "refund"), ("damaged parcel", "damage"),
    ("online सामान नहीं मिला", "non_delivery"), ("landlord कटौती", "deduction"),
])
def test_multilingual_tag_normalization(text, tag):
    assert tag in query_tags(text)


@pytest.mark.parametrize("text", [
    "online refund", "online defective product", "online damaged parcel",
    "online not delivered", "ऑनलाइन पैसे वापस", "online kharab phone",
])
def test_consumer_retrieval_is_relevant_and_repeatable(catalogue, text):
    result = retrieve(catalogue, topic="consumer", text=text, as_of=REVIEW_DATE)
    assert result == retrieve(tuple(reversed(catalogue)), topic="consumer", text=text, as_of=REVIEW_DATE)
    assert {m.source.id for m in result.matches} == {"nch_grievance", "nch_online", "nalsa_help"}
    assert all("consumer" in m.source.topics for m in result.matches)
    assert all(m.reasons for m in result.matches)
    assert not result.gaps


def test_rental_returns_context_not_entitlements(catalogue):
    result = retrieve(catalogue, topic="rental_deposit", state="Maharashtra", as_of=REVIEW_DATE)
    assert {m.source.id for m in result.matches} == {"nalsa_help", "pib_model_tenancy"}
    assert "rental_statutory_position_unverified" in result.gaps
    assert all(c.kind != "statutory" for m in result.matches for c in m.source.claims)


@pytest.mark.parametrize("state", [None, "", "unknown", "Chennai", "India", "California"])
def test_unknown_state_never_infers_state_law(catalogue, state):
    result = retrieve(catalogue, topic="rental_deposit", state=state, as_of=REVIEW_DATE)
    assert "state_required_for_rental_law" in result.gaps
    assert all(m.source.jurisdiction == "IN" for m in result.matches)


@pytest.mark.parametrize("state", ["Tamil Nadu", "tn", "IN-TN", " तमिलनाडु "])
def test_state_normalization(state):
    assert normalize_state(state) == "IN-TN"


def test_state_filter_before_ranking(catalogue):
    # Synthetic source tests mechanics only; this is NOT a real Tamil Nadu rule.
    synthetic = replace(catalogue[0], id="synthetic_state", jurisdiction="IN-TN",
                        topics=("rental_deposit",), tags=("deposit",),
                        claims=(CuratedClaim("synthetic", "Synthetic test", "परीक्षण", "statutory"),))
    assert retrieve((synthetic,), topic="rental_deposit", state="TN", as_of=REVIEW_DATE).matches
    for state in (None, "MH", "unknown"):
        result = retrieve((synthetic,), topic="rental_deposit", state=state, text="deposit", as_of=REVIEW_DATE)
        assert not result.matches
        assert "no_verified_applicable_sources" in result.gaps


@pytest.mark.parametrize("topic", ["criminal", "unsupported", "unclear", "", "rental"])
def test_unsupported_topics_abstain(catalogue, topic):
    assert not retrieve(catalogue, topic=topic, as_of=REVIEW_DATE).matches


def test_empty_and_stale_catalogues_abstain(catalogue):
    assert not retrieve((), topic="consumer", as_of=REVIEW_DATE).matches
    assert not retrieve(catalogue, topic="consumer", as_of=date(2030, 1, 1)).matches
    assert not retrieve(catalogue, topic="consumer", as_of=date(2020, 1, 1)).matches


def test_unverified_and_reference_only_never_retrieved(catalogue):
    excluded = tuple(s for s in catalogue if s.usage == "reference_only")
    for topic in ("consumer", "rental_deposit"):
        assert not retrieve(excluded, topic=topic, state="TN", as_of=REVIEW_DATE).matches


@pytest.mark.parametrize("limit", [0, -1, 11, True])
def test_invalid_limit_rejected(catalogue, limit):
    with pytest.raises(ValueError):
        retrieve(catalogue, topic="consumer", limit=limit)


@pytest.mark.parametrize("mutation", [
    lambda rows: rows[0].update(url="https://consumerhelpline.gov.in.evil.example/"),
    lambda rows: rows[0].update(url="https://user:password@consumerhelpline.gov.in/"),
    lambda rows: rows[0].update(url="http://consumerhelpline.gov.in/"),
    lambda rows: rows[0].update(summary="Changed without hash update"),
    lambda rows: rows[0].update(checked_on="not-a-date"),
    lambda rows: rows[0].update(review_due="2020-01-01"),
    lambda rows: rows[0].update(verification="unverified"),
    lambda rows: rows[0].update(jurisdiction="everywhere"),
    lambda rows: rows[0].update(topics=["criminal"]),
    lambda rows: rows[0].update(tags="refund"),
    lambda rows: rows[0].update(extra="field"),
    lambda rows: rows[0]["claims"][0].update(en="Visit https://invented.example"),
    lambda rows: rows[1].update(id=rows[0]["id"]),
    lambda rows: rows[1]["claims"][0].update(id=rows[0]["claims"][0]["id"]),
])
def test_corrupt_catalogue_fails_closed(tmp_path, mutation):
    rows = json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))
    mutation(rows)
    path = tmp_path / "catalogue.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    with pytest.raises(CatalogueError, match="no claims may be verified"):
        load_catalogue(path)


def test_missing_and_invalid_json_are_safe(tmp_path):
    path = tmp_path / "missing.json"
    with pytest.raises(CatalogueError):
        load_catalogue(path)
    path.write_text("not json synthetic-private-content", encoding="utf-8")
    with pytest.raises(CatalogueError) as error:
        load_catalogue(path)
    assert "synthetic-private-content" not in str(error.value)
