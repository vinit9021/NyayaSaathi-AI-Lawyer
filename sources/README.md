# Curated legal-information catalogue

Milestone 2 review: **9 November 2026**. Seven records: four active guidance
sources, one verified original statutory document retained as reference-only,
and two unverified candidates. No rental statutory entitlement is enabled.
This is a narrow source-backed information layer, not a legal opinion or a
complete, continuously updated law database.

| Source ID | Status and approved scope |
| --- | --- |
| `nch_grievance` | Verified active: NCH grievance routing and tracking. No refund guarantee. |
| `nch_online` | Verified active: online-purchase coverage guidance, with eligibility caveats. No commission thresholds, filing deadlines, or portals imported. |
| `nalsa_help` | Verified active: appropriate legal-services authority/qualified-lawyer referral, without guaranteeing free aid. |
| `pib_model_tenancy` | Verified active: model-law adoption context, not an enacted nationwide deposit rule. |
| `ecommerce_original` | Verified document, reference-only: original 2020 e-commerce rules. Consolidated applicability review incomplete; no output claims. |
| `tn_tenancy_candidate` | Unverified: official PDF returned 502; portal timed out. No state-law claims. |
| `indiacode_candidate` | Unverified: PDF and Act page timed out. No statutory language imported. |

Exact URLs, authorities, locators, review notes, concise summaries, jurisdiction,
topic tags, English/Hindi claim text, and limitations are in `catalogue.json`.
See [verification log](VERIFICATION_LOG.md) for research URLs and failed attempts.
Hindi text is our paraphrase, not an official translation or statutory quotation.

## Review and integrity contract

`verification=verified` records that the cited content was opened and read during
curation. It does not certify a person's entitlement, that every passage is
current, or that a live site is always reachable. `usage=active` separately gates
whether curated claims may be returned. A verified but reference-only document
cannot support output. Unverified records must have no claims.

Each record has a SHA-256 of its UTF-8 `summary`, not the entire remote document.
This detects accidental summary edits; it is not a digital signature, independent
proof of source support, or a replacement for reviewing claims. The catalogue is
trusted repository configuration, never user-uploaded data or model output.
Source/claim edits must be reviewed together before committing.

Initial review window: 90 days from checking (through 7 February 2027). This is a
prototype maintenance policy, not a legal deadline. Both retrieval and claim
selection reject expired/future-dated reviews. Recheck earlier before public
release or when legislation changes. Dates are injectable for deterministic
tests; runtime uses the current date. Do not refresh dates without rereading.

To add a source: open the official URL and read the relevant content and
qualifications; document amendment/applicability gaps; create concise paraphrases
and supporting locators; approve English/Hindi text; assign topic/jurisdiction;
update summary hash; add exclusion and support tests. Add a new official host
to the exact host allowlist only after manual verification. HTTPS/host checks
alone do not establish legal support.

## Retrieval and safety integration

`load_catalogue()` returns immutable typed records. Invalid JSON, duplicate IDs,
unapproved URLs, malformed metadata, and summary-hash mismatch fail the whole
load with `CatalogueError`; a caller must show a verification gap, never use a
previous unvalidated result. Empty catalogues are valid but yield no evidence.

`retrieve(catalogue, topic=..., state=..., text=...)` filters active verified
records by topic, review window, and jurisdiction before ranking tag matches.
Ties use source ID, so results are deterministic. A topic match is relevant even
when no optional tag matches. No runtime requests, embeddings, or arbitrary URL
fetching occur. Full state names/common codes are supported, with selected Hindi
aliases; unknown names/cities are not guessed. Generic national rental context
can be returned without state, but `state_required_for_rental_law` and
`rental_statutory_position_unverified` remain explicit gaps.

`assess_request()` is a conservative local screen, not a semantic classifier.
It detects common English/Hindi/Hinglish unsupported/risk/injection indicators.
Risk takes priority over supported words. Mixed supported topics clarify.
Negation is deliberately not resolved: even “no hearing yet” escalates pending
review. Unknown phrasing may evade keyword detection; do not claim exhaustive
protection. Until milestone 3 successfully classifies the complete case context,
`classifier_succeeded=False` keeps drafting blocked. On later turns, orchestration
must preserve earlier risk flags and screen context, not only the latest text.
Oversized input must be bounded without dropping risk evidence.

`require_drafting_allowed()` is a guard for the future drafting module, not a
document generator. Future integration must call it; this milestone does not
implement or test a full conversation-to-draft workflow.

`ground_claims()` renders only a requested claim ID's fixed reviewed text, kind,
stored source URL, locator, date, and limitations. It rechecks eligibility rather
than trusting a caller-supplied source match. Unknown/inapplicable claims reject
the entire batch. Future statutory claims can require confirmed applicability
facts; rental statutory claims additionally require a matching state source,
never a national model-law announcement. Model self-attestation is insufficient.

`validate_proposed_claim()` rejects extra fields and any change to reviewed text,
source ID, or URL. Thus a real citation cannot legitimize an invented deadline,
section, judgment, or legal conclusion. Do not display unrestricted model prose
beside a verified badge. Informational/referral claims are not personalized legal
advice; referral and review caveats must remain visible.

## Current coverage and deliberate gaps

Supported routing: online refunds, defective/damaged products and non-delivery;
rental deposit withholding/disputed deductions with state-law uncertainty.
No refund entitlement, deadline, deposit cap, deduction legality, court outcome,
or case law is approved. Rental facts, neutral drafting, and conversational
follow-ups remain future milestones. No state-specific law is currently active.

Criminal defence, divorce/custody, complex property litigation, representation,
urgent proceedings, physical danger, and other high-risk matters escalate to
qualified help. Business/resale eligibility is conservatively referred rather
than decided. No public deployment or live model evaluation is claimed.

Offline commands (no keys, no external network):

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_retrieval.py tests/test_safety.py -q
.\.venv\Scripts\python.exe -m pytest -q
```

Synthetic state-rule fixtures test filtering only; they are labelled synthetic
and never added to the real catalogue. Tests validate implementation mechanics,
not independent legal review of the content.
