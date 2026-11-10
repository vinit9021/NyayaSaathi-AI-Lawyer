# NyayaSaathi — AI Lawyer for Everyday Legal Problems in India

Legal-information prototype for online shopping complaints and rental security-deposit disputes. **Not a licensed lawyer. Fictional cases only.**

## Milestone 4 status

Implemented: text chat, English/Hindi responses, English/Hindi/Hinglish intake through structured extraction, session context, bulk fact review, short follow-ups, evidence checklists, expandable source-backed information, and two editable text-document workflows. No voice or public deployment is claimed. One synthetic live consumer workflow was exercised before Milestone 4; this is not a broad model-quality evaluation. Milestone 4 testing is entirely offline; no new live API calls or dependencies were needed.

Gemini returns classification and proposed facts, never unrestricted legal prose. Extracted values must appear in verbatim current-message quotes. Users explicitly confirm or correct proposals; confirmation records an assertion, not independent proof. Conflicting details preserve prior confirmed values until reviewed. Missing details remain unknown.

All legal output is fixed reviewed catalogue text selected from actually retrieved eligible sources, with stored URLs, locators, review dates, and caveats. Four active guidance sources cover NCH routing/online shopping, NALSA referrals, and PIB model-tenancy context. No statutory entitlement, refund deadline, deposit cap, judgment, or guaranteed outcome is enabled. See [source coverage](sources/README.md) and [verification log](sources/VERIFICATION_LOG.md).

## Windows PowerShell setup

Use Python **3.12**, Git, and PowerShell. No Docker, WSL, activation, or execution-policy change. From the repository root, for a fresh environment:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m streamlit run app.py
```

For the existing installed environment, run only the final command. Open the local URL printed by Streamlit; stop with Ctrl+C. Select a language, then type or record a fictional supported issue. The app uses the configured live Gemini provider automatically; opening the app sends no API request.

## Hugging Face Docker Space deployment

The production container is defined in [Dockerfile](Dockerfile), binds
Streamlit to `0.0.0.0:7860` for Hugging Face, and includes the reviewed catalogue under
[`sources/`](sources/). Space metadata and the separate Space-repository
copy workflow are documented in [deployment/README.md](deployment/README.md);
the root GitHub README remains the project documentation.

## Render native Python web service

Render should use a **Web Service** with the native Python runtime, not the
Dockerfile. The checked-in [render.yaml](render.yaml) contains the equivalent
configuration:

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `streamlit run app.py --server.address=0.0.0.0 --server.port=$PORT --server.headless=true`

The start command uses Render's platform-provided `PORT`; the shared
[Streamlit config](.streamlit/config.toml) intentionally does not hardcode a
port. The Dockerfile's `7860` remains isolated to Hugging Face Docker Spaces
and is not used by this native Render service.

In the Render service's environment settings, add these variables without
committing their values:

| Variable | Required value |
| --- | --- |
| `GEMINI_API_KEY` | Google AI Studio API key |
| `GEMINI_MODEL` | An account-available structured-output Gemini model |
| `GROQ_API_KEY` | Groq API key for browser microphone transcription |
| `GROQ_MODEL` | `whisper-large-v3-turbo` |
| `APP_MODE` | `production` |
| `LLM_PROVIDER` | `gemini` |

Render does not need Streamlit secrets or a committed `.env`. The application
automatically uses Gemini in production, with no simulation/mode selector.
Text, voice transcription with confirmation, curated legal grounding, case
summaries, editable drafts, and safety boundaries remain unchanged. Do not
deploy or make live provider calls as part of configuration verification.

### Offline test fixtures

Offline simulation is available only through test fixtures and mocks; it is not a user-facing application mode and is never used as a live-provider fallback. Tests need no keys or network. The deterministic fixture recognizes limited topic words and optional field labels:

```text
online refund; seller: FictionalShop; amount_paid: 5000; state: Maharashtra
```

Then `purchase_date: 2026-10-01; desired_outcome: refund`. Open **Review all details**, edit the fields together, and click **Confirm entered details** once. Dates require YYYY-MM-DD; INR amounts require digits without commas. Use the field's **Unknown** checkbox to explicitly clear a value. Blank untouched fields stay absent. Rental example: `landlord deposit; deposit_paid: 20000; state: Maharashtra`.

Simulation language understanding is limited. Natural-language Hindi/Hinglish fixtures exercise the engine, but do not establish real Gemini quality. No provider error silently switches to simulation.

### Review and download a draft

1. Describe a fictional supported case. Chat asks at most two follow-ups at a time; detailed claims and citations are under **Legal information and sources**.
2. Review the compact case summary. **Missing** means absent/unknown; **Awaiting confirmation** means information was supplied but not yet approved by you. Resolve conflicts in the bulk form; prior confirmed values remain protected until you submit corrections.
3. Confirm the details to use. Optional name/contact, seller or landlord, product/order reference, rental property and agreement date can be entered in the same form. Do not use real private identifiers in this prototype.
4. Click **Generate / regenerate draft**. Choose the dispute by describing it in chat; the correct template follows the assessed case topic. Consumer drafts address the seller/platform and request a refund/resolution. Rental drafts request deposit repayment or a written, itemized explanation.
5. Review important missing fields and all `[Please provide: ...]` placeholders. Partial drafts can be downloaded, but must be completed and checked before use. Unconfirmed information is never silently promoted into the letter.
6. Edit the draft, open **Preview**, acknowledge review, and click **Download text**. Downloads are UTF-8 `.txt`; no PDF dependency, automatic sending, filing, or emailing. A non-removable export notice identifies unverified statements and user responsibility.

Edits stay in the current session and do not alter confirmed facts. Editing requires fresh review; changing the case disables the old download until you explicitly regenerate. Regeneration replaces draft edits. New cases clear both facts and drafts. Separate sessions do not share them. Draft templates are in English with bilingual field labels; your statements retain their original language. Full Hindi document composition is not claimed.

Drafting requires a successful scope/safety assessment. Unsupported/urgent matters, unresolved conflicts, injection attempts and detected legal claims are blocked. The conservative text screen may also reject ordinary wording such as a fixed number of days or risk-related words; it cannot certify every possible user edit. No statute, deadline, judgment, guarantee, legal threat or state-specific entitlement is generated. Missing legal sources still permit neutral factual requests, not verified legal advice. Confirmation means the user affirmed a statement, not that evidence or legal rights were independently verified.

### Live Gemini provider

Securely configure `GEMINI_API_KEY` and `GEMINI_MODEL` through environment variables, an ignored repository-root `.env`, or root-level Streamlit secrets. `.env.example` contains placeholders only. Never paste keys into chat, screenshots, or Git. Select an account-available model supporting structured JSON output; no model ID is baked in or silently substituted.

The application automatically uses Gemini for submitted fictional text and case context. Missing configuration disables chat and shows guidance; it never switches to simulation. Account model availability, quota, billing, and provider privacy terms require verification. `gemini-3.5-flash-lite` succeeded in a minimal test and a synthetic workflow on 9–10 November 2026 (India time); it is the locally configured model. Other accounts must verify their own access. The adapter uses the [official Google Gen AI SDK](https://googleapis.github.io/python-genai/).

| Setting | Default/purpose |
| --- | --- |
| `LLM_PROVIDER` | `gemini`; required for the application |
| `GEMINI_MODEL` | Unset; configure an available structured-output model |
| `GEMINI_API_KEY` | Unset; real Gemini only |
| `GROQ_API_KEY` | Unset; unused until voice implementation |
| `LLM_TIMEOUT_SECONDS` | 30 per attempt by default; range 1–90; local verified configuration uses 90 |
| `LLM_MAX_RETRIES` | 1; range 0–1; transient timeout/network/server failures only |
| `LLM_MAX_OUTPUT_TOKENS` | 2048; range 1–8192; also capped by request |

Precedence: environment > Streamlit secrets > explicit root `.env` > defaults. Blank values override lower priorities; dotenv interpolation is disabled. Safe errors cover missing/invalid credentials, quota, timeouts, network failures and malformed output; confirmed facts remain intact. At most one transient retry uses exponential backoff with jitter. HTTP 429 is retried only with provider retry guidance and no detected daily, zero, spending, or unknown quota violation. Authentication, invalid requests, and ambiguous quota failures are not retried. Retry-After seconds/HTTP dates and Google RetryInfo are respected; waits over 30 seconds stop instead of retrying too early. SDK retries are disabled to prevent multiplication. With a 90-second timeout and one retry, a turn can take approximately 210 seconds; HTTP transport timeouts are not a strict overall wall-clock deadline. Retries may incur charges; no free quota is assumed. Model selection is explicit configuration, never automatic cross-model or simulated fallback.

Live repair evidence: 3.8 Flash returned HTTP 504 after 59.331 seconds; 3.5 Flash-Lite returned the minimal expected text in 1.804 seconds. Its single consumer workflow took 7.139 seconds (304 input / 121 output tokens). The model omitted product and seller refusal from structured fields. An offline replay of its unchanged response now verifies verbatim narrative retention and recovery of a single omitted communication sentence. Those supplements remain unconfirmed assertions, not independently verified facts. Multiple/long communication statements remain for review; this limited rule is not a universal semantic extractor. No additional live call was made after that fix. Original unedited diagnostic records remain in ignored `tmp/`; the synthetic response used for regression is in `tests/fixtures/gemini_consumer_live.json`.

Future Community Cloud deployment uses `app.py`, Python **3.12**, runtime `requirements.txt`, and dashboard Secrets. See [Streamlit secrets documentation](https://docs.streamlit.io/develop/concepts/connections/secrets-management). Deployment remains Milestone 7 and is untested.

## Architecture and safeguards

`app.py` owns session-local immutable `CaseState`. `conversation.py` orchestrates screening, extraction, merging, follow-ups, retrieval and grounding. `extraction.py` validates provenance, conflicts and confirmation. Business logic uses `LLMClient.generate(LLMRequest) -> LLMResponse`; SDK types stay in the Gemini adapter. A replacement provider needs an adapter/factory registration; Gemini model changes use configuration.

Deterministic screening precedes the model and remains the final boundary. Structured semantic assessment supplements it; confidence below 0.8 triggers clarification. Self-reported confidence is not calibrated. High-risk decisions persist until reset. Criminal/family cases, complex property litigation, court representation, urgent proceedings, danger and unsupported requests escalate. Conservative keyword rules can produce false positives (including negation) and miss novel wording.

Only confirmed state informs jurisdiction-specific retrieval; conflicting state is treated as unknown. No rental statutory rule is active even with a known state. Missing, stale or unverified sources disable claims and show uncertainty. No arbitrary model prose, citation, statute or judgment is rendered as a legal explanation. This prevents model-invented citations from reaching legal output; it does not guarantee legal accuracy or semantic classification. Catalogue expiry dates require actual source re-review.

Memory is session-only: at most 20 submissions and 40 retained messages, plus facts and persistent risk flags. Refresh may lose it. New case and mode changes clear context. No database, application chat logging, shared user-state cache, audio retention, private evidence upload, or automatic filing exists. External provider policies still apply.

## Offline verification

### Structured intake reliability (current behavior)

The parser now validates safety metadata separately from optional fact rows.
One invalid row no longer discards valid sibling facts. The application keeps
only facts supported by the current user message, never auto-confirms them,
and asks concise clarifications for rejected fields. A rejected update to an
existing fact preserves its old value and requires review before drafting.

| Variation | Behavior |
| --- | --- |
| Missing fact list or optional fact, model null | Remains absent; no guessed value or automatic “unknown” answer |
| Bad row shape/type, extra row properties, invented value/quote | Drop that row; keep independent valid facts; show static check codes |
| Whitespace differences | Find and retain the original user span; no fuzzy matching |
| INR 4500 versus ₹4,500 | Accept only an equal, unambiguous amount token; retain user formatting for review |
| Translated/inferred locations or reformatted dates | Require literal support; otherwise clarify rather than infer |
| Narrative paraphrase | Retain only its exact short user quote, never the model's paraphrase |
| Duplicate fields | Dedupe identical rows; quarantine conflicting single-value rows; combine supported evidence/communications only as an exact user passage |
| Invalid safety envelope, extra root claims/citations, truncated/filtered output | Reject the response without changing facts; never bypass safety |
| Complete JSON fence/BOM | One local cleanup; no additional API request |

Dates and amounts still require explicit review before draft use. Original
comma-formatted amounts must be entered without commas in the confirmation form.
Schema compliance is not proof of semantic truth; Google's
[structured-output documentation](https://ai.google.dev/gemini-api/docs/structured-output)
also requires application-side validation. No schema can prove arbitrary legal
claims; the separate catalogue-only legal rendering remains unchanged.

The interface shows an application build and intake-contract version, plus a
notice when a retained session sees changed application files. Restart Streamlit
and use New case for a fresh reviewer test; no evidence establishes that a stale
session caused the observed provider-output failures. The app was restarted on
`http://127.0.0.1:8501` during verification. Existing case data is session-only.

Four newly authorized real requests tested two two-turn Streamlit conversations
with `gemini-3.5-flash-lite` (2,048 output-token cap, 90-second timeout, zero retries):

| Conversation | Turn 1 latency | Turn 2 latency | Observed result |
| --- | --- | --- | --- |
| English consumer | 2.936 s | 2.245 s | Both turns responded; confirmed INR 4500 preserved and INR 4600 correction flagged; repeated evidence rows were withheld |
| Hinglish/Hindi rental | 1.790 s | 2.267 s | Both turns responded with clarifications; deposit/state/evidence model fields failed provenance and were withheld; user-reviewed deposit survived turn 2 |

All four outputs used only catalogue guidance, retained case state on reruns,
and made no duplicate request. This verifies real two-turn operation, **not
complete extraction or broad live reliability**. The later multi-item evidence
combination and additional boundary hardening were tested offline only; no
extra live requests were made. The final offline regression suite passed
403 tests; compilation and dependency checks passed.
Shape/code/timing diagnostics (no raw content)
are in ignored `tmp/intake-stability-20261110T062131Z/diagnostics.json`.
Previously captured synthetic records below remain unchanged.

Remaining failures are explicit: ambiguous money/dates, translated or unsupported
quotes, rejected optional rows, unknown state names, invalid safety metadata,
truncation, and provider errors may require user correction or resubmission.
Provenance establishes textual support, not correctness of the model's field
assignment, legal accuracy, or independent proof of a user's allegation.

Live intake diagnostic (10 November 2026): the real Streamlit Gemini path
intermittently rejected valid JSON when the model paraphrased a `problem` value
despite providing an exact user quote. The parser previously rejected the whole
turn, including valid amounts. Simulation emitted literal values and did not
exercise this mismatch. The parser now discards the problem paraphrase and uses
only its exact, short current-message quote as an **unconfirmed** assertion.
Other fields still require literal provenance; invented quotes remain rejected.
Empty null placeholders are omitted, never marked as answered. The requested
schema now specifies nonempty quotes and the existing 500-character value limit.
No SDK, model, API key, or legal-source enforcement was changed.

Validation failures display only static diagnostic codes (`intake_shape`,
`fact_shape`, `fact_provenance`, or `intake_internal`), never raw provider errors
or private content. Recovery is local and makes no additional model requests.
Use New case when retesting after a restart. To restart the local app, stop its
PowerShell process with Ctrl+C, then run
`.\.venv\Scripts\python.exe -m streamlit run app.py` from the repository root.
Select Gemini and consent to synthetic testing; simulation is a separate mode.

The six authorized diagnostic calls used `gemini-3.5-flash-lite`, 2,048 maximum
output tokens, a 90-second timeout and zero retries. Initial A/B/C UI tests all
passed; the English rental rerun reproduced the provenance failure. Raw fictional
outputs remain unchanged in ignored `tmp/gemini-ui-*` directories. Offline UI
regressions exercise the actual factory and Gemini adapter with only the SDK
transport mocked; they do not prove final live verification.

After the provenance fix, one separately approved seventh request succeeded
through Streamlit's real Gemini path in 3.664 seconds (342 input / 150 output
tokens). It extracted the INR 20000 deposit, asked for the missing state, and
rendered only approved catalogue claims with rental-law uncertainty. State
survived a UI rerun without another request. The full offline suite passed
313 tests. This is narrow synthetic verification, not a guarantee for all inputs.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_extraction.py tests/test_conversation.py tests/test_llm.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_ui.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_drafting.py tests/test_ui.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q app.py nyayasaathi tests
.\.venv\Scripts\python.exe -m pip check
```

Tests block outbound sockets and inject synthetic responses, including an unchanged real response to a fictional case. They cover context, multilingual intake, contradictions/corrections, missing facts/sources, risks/injection, fabricated citations, provider errors/retries, UI confirmation/reset, consent and separate sessions, plus all Milestone 1/2 regressions. They do not prove broad live model quality, legal accuracy or cloud operation. The full evaluation runner remains Milestone 6 work.

Runtime direct dependencies remain pinned; Pytest is in `requirements-dev.txt`. Transitive dependencies are not fully locked. No new dependencies were needed for Milestone 3.

## Repository and next milestone

Never commit credentials, private cases, evidence, audio or assignment PDFs. Secrets, virtual environments, private-data directories, caches and PDFs remain ignored; only `.env.example` is exempted. Stage exact paths.

See [requirements](PROJECT_REQUIREMENTS.md), [architecture](ARCHITECTURE.md), [plan](IMPLEMENTATION_PLAN.md), and [agent instructions](AGENTS.md). Next: **Milestone 5 — Voice and failure handling**. It has not started.
