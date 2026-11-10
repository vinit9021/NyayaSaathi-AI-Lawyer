# NyayaSaathi architecture

Status: Milestones 1–4 implemented; voice/evaluation/deployment remain planned.
See PROJECT_REQUIREMENTS.md for scope and acceptance requirements.
One Python 3.12 Streamlit application, small pure-Python business modules, and
two external providers. No database, background workers, or vector index.

## Components and proposed layout

| Path | Responsibility |
| --- | --- |
| `app.py` | Thin Streamlit entry point, controls, rendering, session-state ownership, explicit submission and reset. |
| `nyayasaathi/config.py` | Validated environment/secrets configuration; provider factory inputs, limits, no secret logging. |
| `nyayasaathi/models.py` | Provider-neutral typed case, source, extraction, response, and error contracts. Prefer dataclasses and explicit validation. |
| `nyayasaathi/conversation.py` | Turn orchestration, state transitions, fact merging, questions, bounded context, safe failure fallback. |
| `nyayasaathi/llm/base.py` | `LLMClient.generate(request) -> response` protocol and normalized failure types. |
| `nyayasaathi/llm/gemini.py` | Gemini SDK mapping, structured output request, timeout and error normalization. |
| `nyayasaathi/speech.py` | In-memory audio validation and Groq transcription; no conversation logic. |
| `nyayasaathi/extraction.py` | Validate model-extracted facts, nulls, conflicts, amounts/dates, and user-confirmed corrections. |
| `nyayasaathi/retrieval.py` | Deterministic topic/state/tag selection over reviewed catalogue entries. |
| `nyayasaathi/safety.py` | Risk/scope gate, instruction-injection boundaries, evidence/claim validation and safe fallback. |
| `nyayasaathi/drafting.py` | Two plain-text draft templates using confirmed facts; no autonomous legal notice or filing. |
| `sources/catalogue.json` | Public reviewed source records and approved claim text; never private case data. |
| `tests/` | Offline unit/integration tests and fake adapters; synthetic fixtures only. |
| `evaluation/` | Synthetic evaluation runner, inputs, and explicitly captured immutable raw runs. |

Paths are a proposal for implementation, not files created in this planning task.

## Data flow and trust boundaries

```text
Browser text ---------------------------> explicit submit
Browser microphone -> consent -> Groq -> editable transcript -> explicit confirm
                                                   |
                                                   v
Streamlit session -> scope/risk gate -> Gemini extraction/classification
                                     -> validate facts and merge case state
                                     -> source retrieval (topic + state + tags)
                                     -> select approved options/claims
                                     -> validate claim/source applicability
                                     -> questions + summary + cited options
Confirmed case -----------------------> deterministic editable draft -> user download
```

Run local obvious-risk checks before any model call, and validate semantic scope
and risk after extraction. Ambiguous cases clarify; urgent/high-risk cases stop
substantive advice and drafting. Rule matching alone is insufficient for Hindi,
negation, or mixed issues. If the classifier fails, never default to “supported.”

Target one bounded structured Gemini call per submitted turn for language,
classification, facts, and candidate questions. Retrieval then operates on the
validated case. Legal text comes from approved catalogue claims/templates, not
unrestricted model prose. This reduces calls and makes grounding inspectable.
Natural-language acknowledgements must not introduce independent legal advice.
Any future second synthesis call must obey the same claim allowlist and tests.

## Contracts and state

`CaseState`: case ID (session-local), topic, preferred language, risk flags,
confirmed/proposed facts, timeline, evidence descriptions, contact attempts,
desired resolution, missing fields, conflict markers, and bounded chat history.
Each fact records originating user turn and confirmation status. LLM-inferred
facts are proposals, not confirmed evidence. Explicit structured-summary edits
are user corrections; unknown dates and currency amounts remain null or literal
unconfirmed text, never guessed. Preserve exact user amounts pending validation.

`TurnResult`: scope/risk decision, follow-up questions, case summary, evidence
checklist, approved practical options, source references, verification gaps, and
safe error status. `LLMRequest/Response` contain plain values only; no Gemini
types cross the adapter boundary. Reject malformed fields and unexpected claims.

UI state owns pending transcript and editable draft separately from committed
case facts. Reruns must not duplicate turns or provider calls: use submission IDs
and explicit buttons. Commit case changes only after validation; a timeout or
invalid response preserves prior confirmed state. A new-case button clears all
user data and widget references. Do not use global mutable case objects or
`st.cache_data` for personal content; a public immutable catalogue may be cached.

## Model interchangeability and failure behavior

`LLM_PROVIDER=gemini` and `GEMINI_MODEL` configure a factory that returns the
protocol implementation. Only Gemini is a required production adapter; tests
inject a fake implementing the same contract. Changing Gemini models is config
only; adding another vendor requires a new adapter/factory registration, not
changes to UI, extraction, retrieval, safety, or drafting. Do not claim arbitrary
vendors work without an adapter and contract tests.

Normalize missing credentials, auth failure, quota exhaustion, timeout,
unavailability, and invalid response into safe errors. Default timeout: 30 seconds,
configurable up to 90 following live diagnostics; at most one transient retry
with exponential backoff and jitter. Respect provider delay guidance; waits over
30 seconds stop rather than retry early. Retry 429 only with retry guidance and
no detected daily/zero/spend/unknown quota violation. Never retry authentication
or invalid requests. SDK retries remain disabled. Never hide a provider outage behind a fake AI answer.
Fallback may offer static scope information or show existing facts, clearly
labelled. Missing Groq credentials disable voice but not text; missing Gemini
credentials leave the UI usable with an explicit setup message.

Intake validation has two boundaries. The topic/confidence/risk envelope must
validate in full; malformed JSON, duplicate JSON keys, extra root fields, invalid
safety metadata and truncated/filtered SDK completions fail closed. `facts` may
be omitted. A present facts container must be a bounded list. Individual bad
rows are quarantined with allowlisted field/code diagnostics; supported rows
remain unconfirmed proposals. No raw diagnostic logging is added.

Quote matching permits whitespace differences but stores the original user
span. Narrative paraphrases are discarded in favor of short exact user quotes.
Amounts may differ only by validated INR grouping/prefix/decimal formatting;
acceptance requires one numerically equal user token, stored in its original
form. No inferred dates, locations, zero repayment, translated quotes or fuzzy
matches. Nulls remain absent until explicit user review. Identical rows dedupe;
conflicting single-valued fields are withheld. Separately supported evidence or
communication rows may combine into a bounded original user passage. Rejected
updates to existing facts preserve the prior value but require review and block
stale drafting. Clarifications prioritize rejected fields. One local complete
JSON-fence/BOM cleanup is allowed; partial JSON is never reconstructed and no
extra model repair request is made.

Initial limits: 4,000 characters per turn, 20 recent turns plus validated case
facts, bounded output tokens, 60-second/5 MB audio, and one in-flight submission
per session. Reject or explain limits rather than silently dropping important
facts. Configure actual model token limits at integration. Session rate guards
and provider spending limits reduce exposure but do not stop distributed abuse.

## Source grounding

Start with roughly 4–8 small records from official primary sources; fewer are
acceptable if they honestly cover only the claims shown. Each record contains
stable ID, title, exact URL, authority, document/section locator, short supporting
excerpt or faithful summary, reviewed date, jurisdiction, topic/tags, approved
claim IDs, applicability restrictions, and approved English/Hindi wording.
Separate checked source text from our interpretation. Record URL and excerpt
hash/version for evaluation provenance. Public legal snippets may be committed;
assignment PDFs and private documents may not.

Retrieval is auditable: normalize language/topic tags, filter jurisdiction first,
then rank matching tags and return a few records with match reasons. A national
source is eligible only for its documented national scope. Unknown state never
matches a state-specific entitlement. No runtime web search, user-URL fetching,
or model-generated links. Curation verifies content, not just HTTP success.

MVP claim enforcement is constructive: render legal propositions only from the
reviewed claim registry, with source IDs mapped to stored URLs. Reject unknown
IDs and inapplicable claims. A citation validator cannot prove semantic support
for arbitrary prose; therefore do not render unrestricted model legal prose.
No case-law generation. Missing evidence yields “I could not verify the legal
position from the available sources,” with safe fact-gathering/negotiation steps
and a lawyer referral. Recheck sources before release; show review date and
avoid “current law verified” claims based solely on an old snapshot.

The Model Tenancy Act is not assumed universally enacted. Until actual state
law is reviewed, rental output uses agreement/evidence questions, neutral request
wording, and qualified-help routing. Consumer referral information must come from
verified official pages. Never imply that an informal complaint guarantees a
refund, that all users qualify for legal aid, or that a requested response date
is a statutory deadline.

## Security and document boundaries

User text, transcripts, catalogue excerpts, and model outputs are data, never
instructions to execute code, change policy, fetch URLs, or reveal secrets.
Providers receive no credentials other than their own authentication headers.
Do not render untrusted HTML or expose exception bodies. Keep contacts/addresses
optional; use local placeholders in drafts where possible.

Audio exists only in memory for transcription; discard application references
after success/reset, while acknowledging that Python/browser/provider memory
erasure cannot be guaranteed. Do not log request bodies or raw SDK errors.
Synthetic evaluation capture is an explicit separate runner, never attached to
real user sessions. Hosted secrets stay server-side; `.env.example` has no keys.

Drafts use confirmed facts and placeholders, are marked “Draft — review before
use,” and remain editable. No invented allegations, legal citations, penalties,
or deadlines. Edited draft text is not silently merged back into case facts.
Consumer drafts address seller/platform or contain a grievance narrative; rental
drafts request repayment/itemized deductions. No court-ready pleadings promised.

Milestone 4 retains the latest scope/risk assessment separately from transient
display results so bulk confirmation cannot accidentally discard the safety gate.
The drafting module rechecks risk/history and conflicts at generation and export.
Drafts carry a case fingerprint: new submissions, fact changes or a different case
require explicit regeneration. User text edits require renewed acknowledgement;
export always prefixes the review disclaimer. Source details live in a UI expander,
with current jurisdiction and catalogue eligibility rechecked on reruns.

## Test seams and known limits

Inject adapter, catalogue, and transcription client to run offline tests without
network/secrets. Test orchestration independently of Streamlit; use Streamlit
AppTest where supported and browser/manual checks for microphone/permission
behavior. Test session separation, duplicate-submit handling, reset, and draft
edits. Keep a small held-out synthetic paraphrase set for live evaluation.

Keyword retrieval is intentionally narrow, model extraction can err, Hindi
legal phrasing needs review, and classifiers cannot guarantee detection of every
urgent issue. The public prototype is not a confidential legal service. Document
observed failures instead of implying exhaustive legal or security assurance.
