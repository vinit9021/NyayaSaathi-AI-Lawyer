# NyayaSaathi — AI Lawyer for Everyday Legal Problems in India

An Indian legal-information prototype limited to consumer shopping complaints
and rental security-deposit disputes. **Not a licensed lawyer.**

## Current status: Milestone 1 foundation

Implemented: package structure, validated configuration, provider-neutral LLM
request/response/error contracts, injectable provider factory, and offline tests.
`app.py` displays a foundation status message only. Legal retrieval, safety
workflow, case extraction, chat, Gemini calls, speech, and drafting are **not
implemented**. Their modules are explicit placeholders; the source catalogue is
empty. There is no public deployment or live evaluation result yet.

See [requirements](PROJECT_REQUIREMENTS.md), [architecture](ARCHITECTURE.md),
[implementation plan](IMPLEMENTATION_PLAN.md), and [agent instructions](AGENTS.md).

## Windows PowerShell setup

Use Python **3.12** (verified locally with 3.12.10), Git, and PowerShell. No Docker,
WSL, virtual-environment activation, or execution-policy change is needed. From
the repository root:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
```

Runtime direct dependencies are pinned in `requirements.txt`; development adds
Pytest through `requirements-dev.txt`. Transitive dependencies are resolved by
pip, not fully locked. This avoids freezing Windows-only packages into the cloud
runtime requirements. No API key is required for setup or offline tests.

Optional foundation-only preview:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Stop with Ctrl+C. The preview does not construct provider clients or make AI API
requests. It is not the working legal assistant promised for later milestones.

## Private configuration

`.env.example` contains blank key/model placeholders and safe defaults. Do not
paste credentials into chat, commit them, or put them in screenshots/logs.
Local configuration supports environment variables and an explicitly supplied
`.env` path. Loading configuration does not implicitly search parent directories
or mutate the process environment. No `.env` file is needed for this milestone.

| Setting | Default/purpose |
| --- | --- |
| `LLM_PROVIDER` | `gemini`; adapter selection, no production adapter registered yet |
| `GEMINI_MODEL` | Unset; choose an actually available model in milestone 3 |
| `GEMINI_API_KEY` | Unset; required only when Gemini integration is used later |
| `GROQ_API_KEY` | Unset; voice-specific, not a text prerequisite |
| `LLM_TIMEOUT_SECONDS` | 30; accepted range 1–30 |
| `LLM_MAX_RETRIES` | 1; accepted range 0–1 |
| `LLM_MAX_OUTPUT_TOKENS` | 2048; accepted range 1–8192, subject to future model validation |

`load_settings(environ=..., secrets=..., dotenv_path=...)` accepts injectable
mappings for tests. Precedence is environment > Streamlit secrets > explicit
dotenv file > defaults. Blank values override lower-priority values; blank keys
mean unavailable. Dotenv interpolation is disabled. Secrets are omitted from
configuration repr, but never serialize/log the configuration object as a whole.

`load_streamlit_settings()` is the future UI integration boundary. It lazily
reads root-level Streamlit secrets, handles absent secrets, and snapshots the
environment first to preserve precedence. Invalid configuration gets safe errors.
`require_gemini()` and `require_groq()` check readiness independently, allowing
configuration/imports with no credentials. The status preview does not read keys.

For future Community Cloud deployment, choose `app.py`, Python **3.12**, and
install runtime `requirements.txt`. Add root-level settings using the cloud's
Secrets dashboard; local `.streamlit/secrets.toml` is ignored. See the official
[Streamlit secrets guide](https://docs.streamlit.io/develop/concepts/connections/secrets-management).
No Windows paths are embedded in runtime configuration. Deployment itself is
milestone 7 and has not been tested on Community Cloud.

## Provider boundary and offline tests

Business code will depend on `LLMClient.generate(LLMRequest) -> LLMResponse`.
Only plain dataclasses/values cross the boundary. Normalized error codes cover
missing credentials, authentication, quota, timeout, unavailability, and invalid
responses. Adapters must enforce configured bounds and normalize SDK errors.
The foundation defines these contracts; it does not yet implement SDK requests
or retries. A real response is not proof of legal accuracy or grounding.

`create_llm_client(settings, builders=...)` selects an explicitly registered
builder. Tests inject `tests.fakes.FakeLLM`; production has no fake fallback.
Until milestone 3 registers Gemini, the default factory returns a safe
unavailable error. Replacing a vendor requires an adapter and factory
registration; choosing another supported model will be configuration-only.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_config.py tests/test_contracts.py -q
.\.venv\Scripts\python.exe -m pytest -q
```

Tests isolate configuration, use synthetic values, block outbound socket
connections, mock Streamlit secrets/SDK constructors, and cover precedence,
missing/invalid settings, safe errors, contract validation, and factory injection.
They do not prove legal reasoning quality, transcription accuracy, or live
provider availability. Later evaluation will save real synthetic-run outputs
separately; none are invented here.

## Privacy and repository hygiene

Never commit credentials, private legal case data, or assignment PDFs. `.env`,
`.streamlit/secrets.toml`, virtual environments, private-data directories, caches,
and all PDFs are ignored. Only `.env.example` is narrowly exempted. Review changes
and stage exact file paths; ignore rules do not detect secrets inside source.

The planned public free-tier demo is synthetic-only. No real case data should be
submitted until provider terms/privacy controls are reviewed. The app will never
send/file a complaint automatically. Next milestone: curated sources and safety;
it is not part of this foundation implementation.
