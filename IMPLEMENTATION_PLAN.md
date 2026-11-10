# NyayaSaathi implementation plan

Progress: Milestones 1–5 implemented and offline-tested. Live voice verification,
evaluation artifacts, and public deployment/submission verification remain in progress. Commands below
document the roadmap and executed checks. PROJECT_REQUIREMENTS.md defines scope; ARCHITECTURE.md defines module
boundaries. Complete a narrow vertical slice before polishing the UI.

## Starting point and time budget

Repository: `vinit9021/NyayaSaathi-AI-Lawyer`, public, `main`; initial commit
`181c60e` contains README and .gitignore only. Python 3.12.10, Git, and gh were
verified during setup. Existing README says Python 3.11+; milestone 1 will align
it to the now-locked Python 3.12. Existing `.env.*` ignores `.env.example`;
milestone 1 adds only `!.env.example` after it, with placeholder-only content.

Suggested focused budget: 6–8 engineering hours plus account/deployment waits;
this is an estimate, not the assignment's stated time limit. Timebox curation
and integrations. If time runs short, remove optional polish/video, not safety,
test honesty, supported topics, or the required voice confirmation flow.

## Ordered milestones

### 1. Foundation and contracts (about 45 minutes)

After dependency-install approval, create the package layout, configuration,
typed contracts, fake LLM, requirements files with compatible pinned versions,
and placeholder-only `.env.example`. Runtime packages: Streamlit, current Google
Gen AI SDK, Groq SDK, and python-dotenv; Pytest is a development dependency.
Validate versions against Python 3.12 before pinning. Do not add frameworks.

Acceptance: imports and config tests work without keys; missing settings have
safe errors; fake adapter satisfies the same contract as the future Gemini
adapter; .env remains ignored while .env.example is trackable. No live API call.

Expected PowerShell commands (use the venv executable to avoid activation policy):

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests/test_config.py tests/test_contracts.py -q
git check-ignore .env .streamlit/secrets.toml .venv/pyvenv.cfg
git check-ignore .env.example
```

The final check should return no match (exit 1); do not interpret that expected
exit code as failure. No dependency installation has occurred during planning.

### 2. Curated sources and safety (about 60 minutes)

Create and review a small official-source catalogue and approved claim texts.
Validate National Consumer Helpline guidance, applicable consumer material, and
official legal-help routing. Use the requirements' source links as starting
points, not pre-approved excerpts. Record jurisdiction/review date/locators.
Rental entitlement claims remain disabled without state-specific evidence.

Acceptance: deterministic relevant retrieval; wrong-state/unknown-state/empty
catalogue paths abstain; unknown source IDs and invented sections/URLs are
rejected; unsupported/urgent cases cannot reach drafting. Include English,
Hindi, and Hinglish examples and mixed-risk cases.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_retrieval.py tests/test_safety.py -q
```

### 3. Case intake and grounded text engine (about 75 minutes)

Implement extraction validation, conversation state, merge/correction rules,
missing-fact questions, summary, checklist, and approved practical options.
Use fake responses first, then implement Gemini behind the same contract.
Select/configure the actual available model; never assume free quota.

Acceptance: multi-turn consumer and rental journeys retain facts; Hindi/Hinglish
paraphrases work in fixtures; ambiguity triggers questions; unsupported cases
escalate; failures leave confirmed facts intact. Model-generated legal claims
never bypass the registry. Unseen inputs are not matched to canned case answers.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_extraction.py tests/test_conversation.py tests/test_llm.py -q
```

### 4. Streamlit text UI and editable drafts (about 60 minutes)

Completed: concise chat, expandable reviewed sources, compact case summary,
atomic bulk confirmation/corrections, and two editable neutral request templates.
Drafts use only confirmed statements/placeholders, preserve review notices,
block unsafe/conflicting cases and stale downloads, and export UTF-8 text only.
Offline tests exercise consumer/rental journeys, edits, reruns, isolation, reset,
missing facts/sources, injection, unsupported legal claims, and download contents.
The text-chat foundation was brought forward during Milestone 3 by user request.
Milestone 3 initially used offline/mocked validation. Subsequent authorized live
diagnostics verified gemini-3.5-flash-lite with one consumer workflow. The model
omitted two structured details; verbatim retention fixes were validated offline
against the unchanged response. Broad live evaluation remains Milestone 6 work.

Build chat, preferred language, privacy notice, disclaimer, editable summary,
evidence checklist, source display, and two plain-text draft templates. Add
reset and explicit submissions. Update README with local setup and boundaries.

Acceptance: one end-to-end synthetic journey per topic; edits persist across
reruns; no duplicate API calls; two sessions do not share facts; missing keys
produce setup guidance; drafts contain only confirmed facts/placeholders and
are downloadable but never sent. User can correct date/amount/name before use.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_drafting.py tests/test_ui.py -q
.\.venv\Scripts\python.exe -m streamlit run app.py
```

### 5. Voice and failure handling (about 45 minutes)

Implemented: in-memory bounded PCM WAV validation, Groq SDK transcription without
a language hint, one-time audio consent, editable transcript with explicit send,
recording and submission deduplication, and safe error messages. Production UI
automatically selects the configured live provider; development mode alone exposes
simulation. 432 offline tests passed at this checkpoint. Live Groq and physical
microphone validation remain pending credentials/authorization; do not infer them
from mocks. Text remains independent of voice availability.

Add `st.audio_input`, consent before transcription, Groq Turbo adapter, editable
pending transcript, explicit send confirmation, bounds, and clear error states.

Acceptance: mock transcription tests cover empty/oversized/invalid audio, auth,
quota, timeout, and provider failure; none sends an unconfirmed transcript to
Gemini. Test actual microphone with synthetic English and Hindi/Hinglish audio
when credentials exist. Corrections to names/dates/amounts reach case extraction.
Text works if speech is unavailable; audio is not written to disk by the app.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_speech.py tests/test_ui.py -q
```

### 6. Evaluation and submission evidence (about 60 minutes)

Add an explicit synthetic-only evaluation runner and case fixtures covering all
requirements. Separate offline/mocked tests from opt-in live runs. Keep a small
held-out paraphrase set; no production conversation collection.

Acceptance: full suite passes; real live outputs (including errors) remain
unedited in unique run folders; human review records expected vs actual behavior,
grounding failures, transcript mistakes, latency, and measured provider usage.
No made-up success rates. Missing credentials/quota are recorded as not run or
failed, never passed. A failing implementation must be fixed before its commit.

Proposed commands once the runner exists:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m evaluation.run --mode live --synthetic-only --output evaluation/runs
```

Each run folder should contain UTC timestamp, commit SHA plus dirty flag, exact
model IDs/configuration, catalogue hash, synthetic input IDs/text, raw provider
response text or safe error status, final displayed output, and usage/timing
metadata. Never capture authentication headers. Keep review annotations in a
separate file; do not overwrite earlier outputs on reruns. Only explicitly
reviewed synthetic artifacts may be staged for the public repository.

### 7. Public deployment and solution document (about 45–75 minutes)

With working integrations, deploy `app.py` from `main` to Streamlit Community
Cloud using Python 3.12 and dashboard secrets. Verify hosting/account prerequisites
before promising a URL; obtain approval for any new paid service. Keep demo
synthetic-only under unpaid provider terms. Add the verified URL to README.

Acceptance: external browser opens app; disclaimer and privacy notice visible;
text and confirmed voice paths work; missing-source/unsupported/error paths work;
no secrets exposed; reset works. Run the full suite before the release commit.
Create a maximum two-page solution document using measured evaluation results,
scope, architecture, AI use, cost assumptions, and honest limitations/failures.
If exporting PDF, keep the generated submission outside tracked files because
PDFs are ignored; commit the public Markdown source after review. Optional video
comes last. Do not call the assignment complete until required artifacts exist.

## Evaluation matrix

| Category | Minimum cases/assertions |
| --- | --- |
| Consumer | Refund, defective/damaged goods, non-delivery; clarify missing dates and refund amount. |
| Rental | Withheld deposit and disputed deductions in different/unknown states; no nationwide deposit rule. |
| Language | English, Hindi script, Hinglish, mixed numbers/dates; transcript correction before submit. |
| Context | Multiple turns, correction, conflicting amount, reset, two independent sessions. |
| Boundaries | Criminal/divorce, imminent hearing, eviction threat inside deposit story, unclear mixed topic. |
| Grounding | Invent-a-judgment request, malicious instructions, nonexistent citation, irrelevant real source, no source. |
| Reliability | Missing key, 429/quota, timeout, malformed model JSON, transcription failure, rerun duplicates. |
| Drafts | Unknown details remain placeholders; no invented deadline/amount; user edits survive rerun. |

Offline tests assert properties of the workflow, not exact LLM prose. Live runs
need manual review of source support and language quality; no untested claim of
universal unseen-case accuracy. Tests are planned here, not executed yet.

## Prerequisites, decisions, and blockers

- No architecture decision blocks offline implementation. Use dataclasses,
  explicit validation, tag retrieval, templates, and one production LLM adapter.
- User must securely configure Gemini/Groq keys; account model access, quota,
  billing, and data terms remain unverified. Never request keys in chat.
- Verify an available stable Gemini model at milestone 3. Keep its ID configurable;
  don't silently substitute a different provider or chargeable model.
- Source excerpts and state applicability require curation before legal claims
  ship. Lack of rental state law limits entitlement advice, not neutral drafting.
- Streamlit account/access and hosted Python/runtime availability block public
  release only. Dependency installation needs approval when implementation begins.
- Real private legal-case use needs a separate provider/privacy decision; default
  synthetic assignment evaluation can proceed without it.

## Git and milestone completion

For each implementation milestone: review diff, run targeted tests and the full
available suite before commit, inspect tracked/staged files for secrets/private
data, stage exact paths, and create a meaningful Conventional Commit. Push to
existing `origin/main` after passing checks under the user's standing authority;
request any required environment approval. Do not force-push or bypass hooks.
Verify local/remote commit identity and clean status. Stop if unrelated changes,
remote divergence, or uncertain artifacts would be overwritten/published.

This planning task stages exactly PROJECT_REQUIREMENTS.md, ARCHITECTURE.md,
IMPLEMENTATION_PLAN.md, and AGENTS.md; checks documentation consistency and
`git diff --check`; creates one `docs:` commit; pushes and verifies it. No
application tests exist yet, so do not claim Pytest ran for this task.
