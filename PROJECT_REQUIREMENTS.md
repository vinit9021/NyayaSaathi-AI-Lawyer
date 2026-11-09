# NyayaSaathi — project requirements

Planning baseline: 9 November 2026. This document specifies future work; it does
not claim that application features, live tests, or deployment already exist.

## Purpose and scope

Build a small, honest KukuFM Problem 2 prototype: an accessible Indian
legal-information assistant for ordinary people. Product name: NyayaSaathi — AI
Lawyer for Everyday Legal Problems in India. Despite the name, it is not a
licensed lawyer and must say so clearly.

Supported issues only:

1. Consumer complaints about online shopping refunds, defective products,
   damaged goods, and non-delivery.
2. Rental security deposits withheld by landlords or disputed deductions.

Exclude criminal defence, divorce/custody, complex property litigation, court
representation, urgent proceedings, and other high-risk matters. Mixed or unclear
cases require clarification; risk takes precedence over a supported topic.
Do not expand into a general Indian-law chatbot.

## Locked technology and constraints

- Python 3.12; native Windows PowerShell development, no Docker or WSL.
- Streamlit UI and session state; no separate frontend/backend deployment.
- Gemini API through a provider-independent conversational adapter.
- Groq `whisper-large-v3-turbo` for speech transcription.
- Small manually reviewed source catalogue and transparent keyword/tag retrieval.
- Pytest, GitHub, and Streamlit Community Cloud.
- No vector database, agent framework, accounts, persistent case database, OCR,
  evidence uploads, automatic filing, messaging, payments, or text-to-speech.
  Evidence is described by the user and listed in a checklist.

## Functional acceptance requirements

| ID | Requirement and observable acceptance |
| --- | --- |
| F01 | Text chat accepts English, Hindi, and Hinglish; a response-language selector allows English or Hindi, with everyday Hinglish understood. No claims of perfect translation. |
| F02 | Built-in `st.audio_input` records audio. A separate transcribe action sends it to Groq after notice/consent; the editable transcript is never submitted to Gemini until the user explicitly confirms it. |
| F03 | Scope classification returns consumer, rental deposit, unclear, or unsupported, plus risk flags. Unsupported/high-risk cases receive a clear boundary and qualified-help recommendation. |
| F04 | Multi-turn intake captures events, dates, city/state, amounts, evidence, prior contact, and desired outcome. Ask at most three focused questions per turn; unknowns stay unknown. |
| F05 | Maintain facts and conversation within the current session. Corrections replace prior facts explicitly; conflicts and ambiguous dates/amounts trigger confirmation. Reset clears case, draft, transcript, and audio references. |
| F06 | Show a structured, editable case summary, missing information, and topic-specific evidence checklist. Separate user allegations from established facts and legal information. |
| F07 | Retrieve only curated, reviewed source records relevant to the topic and jurisdiction. Show supporting URLs beside legal claims and source review dates. |
| F08 | Never invent sections, judgments, deadlines, quotations, or URLs. A real URL alone is not proof of support. Missing or inapplicable sources produce an explicit verification gap. |
| F09 | Provide practical steps in simple language. Distinguish optional requests/negotiation from legally required deadlines or guaranteed remedies. Avoid predictions of success. |
| F10 | Create editable consumer complaint or landlord repayment-request text using confirmed facts and visible placeholders. Require user review; offer text download/copy only, with no send/file integration. |
| F11 | Missing keys, unavailable model, malformed model responses, quota errors, timeouts, and transcription failures produce safe, actionable messages without exposing internals or losing confirmed facts. Text remains available when speech fails. |
| F12 | Display: “AI legal-information assistant, not a licensed lawyer. Information may be incomplete or outdated. Review drafts and consult a qualified lawyer for legal advice or urgent matters.” Provide an equivalent Hindi message when selected. |

Consumer facts include seller/platform, purchase and delivery dates, order
reference (optional), amount paid/refund sought, defect/non-delivery, and support
responses. Rental facts include city/state, deposit paid/returned, agreement terms
as reported, move-out/key-handover dates, claimed deductions, inspection/evidence,
and requests already made. Never demand identity documents or bank details.

## Minimum viable assignment version

Prioritize one complete text journey for each topic, source-backed safe options,
summary, follow-up questions, and two editable draft templates. Then add voice
with transcript confirmation, failure handling, and deployment. English/Hindi/
Hinglish support and safety are core, not polish. The submitted version must
include the voice path; an earlier text-only checkpoint is not full completion.

Rental coverage initially means fact gathering, evidence organization, a neutral
repayment request, and qualified-help routing. State-specific legal entitlements
are omitted unless a reviewed source establishes applicability. This keeps the
agreed topic while honestly limiting legal depth. Unseen cases must use the same
workflow, not scripted responses keyed to demo examples.

Defer broad legal coverage, case-law search, formal court pleadings, rich exports,
cross-session history, analytics, and optional video until the core works. The
assignment's exact recommended duration was not provided; implementation time
estimates are engineering estimates, not quoted assignment requirements.

## Privacy and operational requirements

- Never hardcode, print, stage, or commit keys, private case data, or assignment
  PDFs. `.env.example` contains placeholder names/values only.
- Local configuration uses environment variables, optionally loaded from ignored
  `.env`; deployment uses Streamlit secrets. Environment values take precedence.
- No raw conversation/audio logs, persistent audio, shared user-state caches, or
  production-chat evaluation capture. Session memory is temporary, not encrypted
  archival storage; refresh/restart may lose it.
- Explain before sending that audio goes to Groq and confirmed text/context goes
  to Google. App-side non-retention does not guarantee provider non-retention.
- Default public assignment demo: synthetic cases only. Gemini unpaid terms
  prohibit sensitive/confidential/personal submissions. Real private-case use is
  blocked pending suitable provider terms, configuration, and privacy review.
  A consent checkbox alone does not override provider terms.
- Bound inputs, audio size, request counts, context length, and retries; no
  automatic paid-tier upgrade. Public rate limits are not a complete abuse barrier.

## Quality and deliverables

Offline tests must cover both topics, unseen paraphrases, Hindi/Hinglish, missing
facts, corrections, unsupported/mixed-risk cases, fabricated-law requests, prompt
injection, absent/wrong-state sources, invented citations, model failures, and
speech failures. Include transcript confirmation and session-isolation checks.

Use separate live synthetic runs to validate actual provider behavior. Preserve
unedited outputs and failures, configuration/model identifiers, timestamps, source
catalogue version, and commands. Label mocked tests separately; do not fabricate
results, hide failures, or call offline tests proof of live quality.

Deliver a working public Streamlit link, GitHub repository with reproducible
setup, synthetic test cases and raw outputs, and an up-to-two-page solution
document covering design, assumptions, AI use, costs, tests, limitations, and
failures. An up-to-three-minute walkthrough is optional. No deployment URL,
latency, accuracy score, or cost is claimed before measurement.

## External prerequisites and evidence

References checked during planning on 9 November 2026; recheck before integration.

| Dependency | Prerequisite/restriction | Implementation consequence |
| --- | --- | --- |
| Gemini | Google AI Studio/API project and `GEMINI_API_KEY`; model access and quotas vary by project/tier. [Rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) | Select an available low-cost stable text model at integration; configure `GEMINI_MODEL` rather than assume a model ID or fixed free allowance. |
| Gemini privacy/cost | [Terms](https://ai.google.dev/gemini-api/terms?authuser=00) restrict personal/sensitive input to unpaid services; [pricing](https://ai.google.dev/gemini-api/docs/pricing) must be rechecked before spending. | Synthetic demo by default; record actual tier and usage. Pricing page could not be fully fetched in planning, so no numeric price is asserted. |
| Groq | Groq account and `GROQ_API_KEY`; [speech docs](https://console.groq.com/docs/speech-to-text) list multilingual transcription and a 25 MB free-tier upload ceiling. [Limits](https://console.groq.com/docs/rate-limits) vary by plan/model. | Use transcription, not English-only translation. App limit: 60 seconds/5 MB, checked before API call; verify Hindi/Hinglish empirically. |
| Groq privacy | Review [data controls](https://console.groq.com/docs/your-data) for the actual account. | No universal zero-retention promise; use synthetic recordings in evaluation. |
| Streamlit | Account with repository access; cloud secrets and Python 3.12 deployment setting. [Secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management), [limitations](https://docs.streamlit.io/deploy/streamlit-community-cloud/status), [Python](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/upgrade-python). | Verify deployment availability/resources; do not promise SLA or persistent sessions. Microphone needs browser permission and HTTPS/localhost. |

No key, billing tier, available Gemini model, or Streamlit account has been
verified. These block live integration/deployment, not offline implementation.
Never ask the user to paste keys into chat. Guide them to local secret files or
the hosting secrets UI when needed. Installation and any paid service activation
require approval. GitHub authentication will be rechecked before this docs push.

Planning sources for legal curation: [National Consumer Helpline](https://consumerhelpline.gov.in/public/)
describes its grievance route; [NALSA](https://nalsa.gov.in/) provides official
legal-services information; [PIB's Model Tenancy Act announcement](https://www.pib.gov.in/PressReleaseIframePage.aspx?PRID=1723636&lang=2&reg=48)
states circulation to states/UTs for adoption. These are starting points, not a
completed legal corpus. The MoHUA tenancy page returned no substantive text
during planning. No nationwide rental-deposit cap or statutory refund deadline
is approved by this specification.
