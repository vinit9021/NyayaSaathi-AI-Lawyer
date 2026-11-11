
# ⚖️ NyayaSaathi — AI Legal Assistant for Everyday Problems in India

### An AI-powered, multilingual legal-information assistant built for the KukuFM AI Generalist Take-Home Assignment

NyayaSaathi helps people understand common legal problems in simple language, organize relevant facts, explore practical next steps, and prepare editable complaint drafts.

The application supports **English, Hindi, and Hinglish** through text and voice input. It uses Google Gemini for conversational AI, Groq Whisper for speech recognition, and a curated collection of official Indian legal-information sources to ground its responses.

> **Disclaimer:** NyayaSaathi is an AI legal-information prototype, not a licensed lawyer. It does not provide legal representation or guarantee legal outcomes. The public demonstration is intended for fictional cases only. Do not submit real personal or sensitive legal information.

---

## 🌐 Live Application

### [🚀 Try NyayaSaathi — AI Lawyer](https://nyayasaathi-ai-lawyer.onrender.com)

**Deployed URL:** https://nyayasaathi-ai-lawyer.onrender.com

**GitHub Repository:** https://github.com/vinit9021/NyayaSaathi-AI-Lawyer

The application is deployed on **Render** and can be accessed directly through a web browser.

No installation, account creation, or personal API key is required to use the deployed prototype.

**Note:** The application uses Render's free hosting tier, so its first request after a period of inactivity may take longer while the service starts.

---

## 📌 Project Overview

Legal information is often difficult for ordinary people to understand because of complex terminology, language barriers, fragmented resources, and uncertainty about the appropriate next steps.

Many people face everyday disputes involving defective products, online shopping refunds, and rental security deposits but may not know how to organize their complaints or identify the right resources.

**NyayaSaathi aims to make initial legal-information assistance more accessible.**

Instead of acting as a general-purpose lawyer covering all Indian laws, the application focuses on two common problem categories and handles them through a structured conversational workflow.

The system helps users:

- Describe a legal problem in everyday language.
- Communicate in English, Hindi, or Hinglish.
- Record spoken queries using a microphone.
- Answer relevant follow-up questions.
- Review and correct extracted case information.
- Identify missing facts and supporting evidence.
- Access source-grounded legal information.
- Generate editable complaint or repayment-request drafts.
- Recognize when professional legal assistance is necessary.

The goal is to create a useful, transparent, and narrowly scoped AI-powered legal assistant rather than an unrestricted legal chatbot.

---

## 🎯 Supported Use Cases

NyayaSaathi intentionally focuses on **two categories of everyday legal problems in India**.

### 1. Consumer Complaints

The application supports common consumer disputes involving online purchases.

**Examples:**

- A defective product delivered after an online purchase.
- A damaged item received from an online seller.
- A seller refusing a requested refund.
- Non-delivery of an ordered product.
- Problems communicating with a seller or shopping platform.

**Example Query:**

> I purchased headphones online for ₹4,500. They arrived damaged, and the seller is refusing my refund. I have the invoice and photographs. I live in Delhi. What should I do?

**How NyayaSaathi helps:**

1. Recognizes the issue as a consumer complaint.
2. Extracts the purchase amount, problem, seller information, and available evidence.
3. Requests important missing details.
4. Presents relevant information from approved consumer-help resources.
5. Suggests practical, non-guaranteed complaint options.
6. Helps prepare an editable complaint or refund-request letter.

### 2. Rental Security Deposit Disputes

The application supports disputes involving landlords withholding or disputing the repayment of rental security deposits.

**Examples:**

- A landlord refusing to return a security deposit.
- Disputed deductions from a rental deposit.
- Delayed repayment after a tenant vacates a property.
- Disagreements involving rental agreements and payment records.

**Example Query:**

> Maine Chandigarh mein ek room rent par liya tha aur landlord ko ₹20,000 security deposit diya tha. Maine room khaali kar diya, lekin landlord paise wapas nahi kar raha. Mere paas rent agreement aur UPI payment proof hai.

**How NyayaSaathi helps:**

1. Identifies the rental-deposit dispute.
2. Collects the deposit amount, location, tenancy details, and available evidence.
3. Asks for missing information such as the move-out date or landlord's explanation.
4. Organizes the user's statements into a structured case summary.
5. Explains relevant options while acknowledging jurisdiction-specific uncertainty.
6. Generates an editable deposit-repayment request.

**Important:** Rental regulations can differ between Indian states and Union Territories. The application does not assume that a particular state law applies throughout India or promise a statutory repayment deadline without verified support.

---

## 🚫 Out of Scope

NyayaSaathi is **not designed to cover all of Indian law**.

The following are outside the current prototype's scope:

- Criminal defence and criminal litigation.
- Divorce, child custody, and complex family-law matters.
- Complex property ownership and title disputes.
- Court representation or preparation of litigation strategy.
- Emergency legal proceedings.
- Complex commercial disputes.
- Guaranteed legal opinions or predictions of case outcomes.
- Automatic submission of complaints, notices, or court documents.

For unsupported, urgent, or high-risk issues, the application directs users toward qualified legal assistance.

---

## ✨ Key Features

### 💬 Conversational Legal Assistance

Users describe their problems through a chat interface.

Google Gemini processes the conversation and helps identify the nature of the dispute, collect missing information, and provide relevant responses.

The assistant maintains case context throughout the current session and asks focused follow-up questions.

### 🎙️ Multilingual Voice Input

NyayaSaathi supports browser-based microphone recording.

The audio is processed using **Groq Whisper Large V3 Turbo**, which converts speech into text.

Supported input scenarios include:

- English speech.
- Hindi speech.
- Hindi-English mixed speech (Hinglish).

The user can review and edit the transcription before submitting it to the legal assistant.

Voice transcription is not assumed to be perfectly accurate. Names, amounts, dates, and other important details should be checked before confirmation.

### 🌐 Multilingual Interaction

Users can communicate using English, Hindi, or Hinglish.

The application includes English and Hindi response-language preferences.

### 🧾 Structured Case Intake

The assistant collects and organizes information such as:

- Problem description.
- Purchase or deposit amount.
- Relevant dates.
- Seller or landlord details.
- Indian state or location.
- Previous communication attempts.
- Supporting evidence.
- Desired resolution.

Extracted facts remain subject to user review.

### ✅ Fact Confirmation and Correction

The application distinguishes user-provided statements from independently established facts.

Users can confirm or correct extracted details.

Conflicting information is handled conservatively rather than silently overwriting previously confirmed facts.

### 📚 Source-Grounded Legal Information

NyayaSaathi uses a curated legal-information catalogue instead of relying entirely on the language model's internal knowledge.

The system provides references to approved sources and avoids presenting unsupported legal provisions as verified facts.

### 📋 Evidence Checklist

The application helps users identify potentially relevant supporting documents.

For consumer complaints, examples include invoices, receipts, delivery records, photographs, and seller communications.

For rental disputes, examples include rental agreements, deposit-payment records, move-out communications, and landlord correspondence.

### 📝 Editable Legal Document Drafts

NyayaSaathi can prepare:

1. Consumer complaint and refund-request drafts.
2. Rental security deposit repayment-request drafts.

Generated documents can be reviewed, edited, and downloaded as UTF-8 text files.

Missing information remains visible rather than being invented.

**Documents are never automatically sent, filed, or submitted.**

### 🛡️ Legal Safety and Error Handling

The application includes safeguards for:

- Unsupported legal problems.
- High-risk requests.
- Unverified legal claims.
- Fabricated or irrelevant citations.
- Missing case information.
- Conflicting user statements.
- Invalid AI-generated structured data.
- API timeouts and temporary provider failures.

If live AI services are unavailable, the application displays an error instead of silently substituting simulated responses.

---

## 🏗️ Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| Programming language | Python 3.12 target | Application implementation |
| Frontend | Streamlit | Interactive web interface |
| Conversational AI | Google Gemini | Case understanding, extraction, and conversational responses |
| LLM integration | Google GenAI SDK | Gemini API communication |
| Speech recognition | Groq Whisper Large V3 Turbo | Multilingual speech-to-text |
| Voice API | Groq Python SDK | Audio transcription |
| Case management | Python models and Streamlit Session State | Structured facts and conversation context |
| Legal information | Curated JSON source catalogue | Source-grounded legal responses |
| Document drafting | Python templates | Editable complaint and repayment requests |
| Configuration | Environment variables and python-dotenv | Secure configuration loading |
| Testing | Pytest and Streamlit AppTest | Automated and UI validation |
| Version control | Git and GitHub | Source management |
| Deployment | Render | Public web application hosting |

**Configured Gemini model during development:** `gemini-3.5-flash-lite`

The model identifier is configurable and can be changed without redesigning the application's legal workflow.

---

## ⚙️ System Architecture

NyayaSaathi separates conversational understanding from deterministic validation and legal-source handling.

```text
                    USER
                     |
             Text Input / Voice
                     |
         +-----------+-----------+
         |                       |
      Text Chat             Audio Recording
         |                       |
         |                Groq Whisper API
         |                       |
         |               Editable Transcript
         |                       |
         +-----------+-----------+
                     |
              Streamlit UI
                     |
             Conversation Engine
                     |
          Scope and Safety Screening
                     |
               Gemini LLM
                     |
            Structured Extraction
                     |
          Fact / Provenance Validation
                     |
           Case State and Follow-ups
                     |
          Curated Legal Source Retrieval
                     |
           Grounded Legal Information
                     |
             Case Review and Drafting
                     |
             Editable Document
                     |
               User Download
```

### AI Responsibilities

The language model is used for:

- Understanding natural-language questions.
- Interpreting English, Hindi, and Hinglish inputs.
- Identifying the likely dispute category.
- Proposing structured case information.
- Supporting conversational follow-up questions.

### Deterministic Code Responsibilities

Application code handles:

- Validating extracted case facts.
- Tracking confirmed information.
- Checking supported scope.
- Enforcing citation restrictions.
- Retrieving approved legal-source records.
- Preserving session state.
- Controlling document-generation eligibility.
- Handling external API failures.
- Preventing duplicate submissions.

This separation reduces dependence on unrestricted model-generated legal assertions.

---

## 📚 Legal Information Sources

The curated source catalogue includes reviewed material from:

- **National Consumer Helpline (NCH)** — Consumer grievance guidance and selected consumer information.
- **National Legal Services Authority (NALSA)** — Legal-aid and referral information.
- **Government of India tenancy-related resources** — Limited contextual information about tenancy frameworks.
- **Selected consumer-regulation references** — Used only within their verified applicability and catalogue restrictions.

Official websites:

- National Consumer Helpline: https://consumerhelpline.gov.in/
- National Legal Services Authority: https://nalsa.gov.in/
- India Code: https://www.indiacode.nic.in/
- Department of Consumer Affairs: https://consumeraffairs.nic.in/

These websites are reference resources. Their inclusion does not imply that every page or provision is active in the application's verified catalogue.

See `sources/catalogue.json` and `sources/README.md` for the project's source records, verification information, and limitations.

---

## 🚀 Run the Project Locally

### Prerequisites

Install the following:

- Python 3.12 (recommended for the project's tested local environment).
- Git.
- A code editor such as Visual Studio Code.
- A valid Gemini API key.
- A Groq API key for voice transcription.
- An internet connection for live AI requests.

### Step 1 — Clone the GitHub Repository

Open PowerShell or a terminal and execute:

```bash
git clone https://github.com/vinit9021/NyayaSaathi-AI-Lawyer.git
cd NyayaSaathi-AI-Lawyer
```

### Step 2 — Create a Virtual Environment

On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
```

On Linux or macOS with Python 3.12 installed:

```bash
python3.12 -m venv .venv
```

### Step 3 — Activate the Virtual Environment

**Windows PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

**Linux/macOS:**

```bash
source .venv/bin/activate
```

If PowerShell blocks the activation script, use the virtual environment's Python executable directly instead of changing system-wide execution settings.

### Step 4 — Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### Step 5 — Configure API Keys

Create a local `.env` file in the project root.

Add the following configuration:

```dotenv
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.5-flash-lite

GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=whisper-large-v3-turbo

APP_MODE=production
LLM_PROVIDER=gemini
```

Replace the placeholder key values with your own credentials.

**Gemini API key:** https://aistudio.google.com/api-keys

**Groq API key:** https://console.groq.com/keys

The `.env` file must remain private and must never be committed to GitHub.

The API key must have access to the configured model. Model availability and quota limits can vary across accounts.

### Step 6 — Launch the Application

From the project root:

```bash
streamlit run app.py
```

If Streamlit is not found as a command, run:

```bash
python -m streamlit run app.py
```

### Step 7 — Open the Application

Visit:

http://localhost:8501

You should see the NyayaSaathi chat interface.

There is no requirement to choose between Gemini and Offline Simulation. The application automatically uses the configured live Gemini provider.

---

## 🧑‍💻 How to Use NyayaSaathi

### Text Conversation

1. Open the application.
2. Select the preferred response language if necessary.
3. Describe a fictional legal problem.
4. Submit the message.
5. Review the AI-generated follow-up questions.
6. Provide missing details.
7. Review and confirm the case facts.
8. Explore relevant source-backed information.
9. Generate an editable document when appropriate.

### Voice Conversation

1. Expand **Speak your problem / अपनी समस्या बोलें**.
2. Allow microphone access in your browser.
3. Record your fictional problem.
4. Submit the recording for transcription with the required permission.
5. Review the generated transcript.
6. Correct mistakes in names, amounts, dates, or locations.
7. Confirm and submit the transcript.
8. Continue the same conversational legal-assistance workflow.

### Document Generation

1. Complete the relevant case-intake questions.
2. Review and confirm the extracted details.
3. Open the drafting section.
4. Generate the supported document.
5. Edit the text if required.
6. Review the final draft and acknowledge its limitations.
7. Download the document.

The application does not automatically contact sellers, landlords, lawyers, or government portals.

---

## 🧪 Testing and Evaluation

NyayaSaathi includes automated tests for the application components and end-to-end workflow behavior.

### Run All Tests

From the project root:

```bash
python -m pytest -q
```

### Run Evaluation-Specific Tests

```bash
python -m pytest tests/test_evaluation.py -v
```

### Python Compilation Check

```bash
python -m compileall -q app.py nyayasaathi tests
```

### Dependency Consistency Check

```bash
python -m pip check
```

### Recorded Development Verification

During Render deployment preparation, the automated test suite reported:

**437 tests passed**

This result reflects the repository state at that checkpoint and may change as tests are added or updated.

The suite includes tests for:

- Consumer and rental case handling.
- Multi-turn conversations.
- Fact extraction and corrections.
- English, Hindi, and Hinglish inputs.
- Unsupported legal requests.
- Citation enforcement.
- Invalid structured responses.
- Missing or contradictory information.
- Document drafting and downloads.
- Voice transcription integration.
- API failures and duplicate-request prevention.
- Streamlit UI behavior.
- Deployment configuration.

### Live Model Evaluation

The application was also evaluated using controlled synthetic scenarios with the real Gemini and Groq APIs.

Observed results included:

- Successful multi-turn consumer conversations.
- Successful rental-dispute conversations.
- Preservation of case context across turns.
- Rejection of unsupported model-generated facts.
- Successful English speech transcription.
- Hinglish transcription with some pronunciation and transcription errors requiring user correction.

Some extracted facts required additional clarification, and not every model response was fully reliable.

These are genuine limitations of the prototype and are not hidden by the automated test results.

### Raw Evaluation Outputs

Evaluation code and recorded output artifacts are organized under:

```text
evaluation/
├── test_cases/
├── raw_outputs/
├── run.py
└── run_speech.py
```

The raw-output records distinguish:

- Live Gemini tests.
- Live Groq transcription tests.
- Offline simulated tests.

Only genuine executed test outputs should be presented as actual results. Mocked or simulated output must not be represented as live model behavior.

The availability of these records in the public repository depends on whether the reviewed evaluation artifacts have been committed.

---

## 🔐 Privacy and Security

NyayaSaathi uses external AI providers to process user-submitted content.

Important safeguards include:

- API keys loaded from server-side environment variables.
- No API credentials required from reviewers.
- No API keys hardcoded into application source files.
- Session-only case state rather than permanent application-side case storage by default.
- Transcript confirmation before legal processing.
- No permanent audio recording storage by default.
- Input-size and request controls.
- Restricted legal-information coverage.
- Validation of extracted case facts.
- Conservative handling of uncertain legal claims.
- No automatic filing or delivery of generated documents.

The model providers' own data-processing and retention policies still apply.

**The deployed prototype is intended for fictional examples only. Users should not submit real names, addresses, identity documents, or sensitive legal records.**

---

## ☁️ Deployment

### Production Platform: Render

NyayaSaathi is deployed as a Python web service on Render.

**Live application:**

https://nyayasaathi-ai-lawyer.onrender.com

### Render Configuration

| Setting | Configuration |
|---|---|
| Service type | Web Service |
| Runtime | Python 3 |
| Branch | `main` |
| Build command | `pip install -r requirements.txt` |
| Root directory | Repository root |
| Health check path | `/_stcore/health` |
| Production provider | Gemini |
| Hosting | Render free-tier web service |

**Start Command:**

```bash
streamlit run app.py --server.address=0.0.0.0 --server.port=$PORT --server.headless=true
```

### Required Render Environment Variables

Configure these in the Render dashboard:

```dotenv
GEMINI_API_KEY=your_actual_gemini_key
GEMINI_MODEL=gemini-3.5-flash-lite

GROQ_API_KEY=your_actual_groq_key
GROQ_MODEL=whisper-large-v3-turbo

APP_MODE=production
LLM_PROVIDER=gemini
```

The values of `GEMINI_API_KEY` and `GROQ_API_KEY` must remain private.

Render deploys changes from the connected GitHub repository. With automatic deployment enabled, new commits to the configured branch can trigger a redeployment.

### Free-Tier Limitations

- The application may take time to start after inactivity.
- Available memory and compute resources are limited.
- Gemini and Groq have independent API quotas.
- Free-tier availability can change.
- Performance may vary with provider traffic and hosting conditions.
- API failures can temporarily prevent live conversations or transcription.

The application does not silently replace failed live AI requests with simulated answers.

---

## 📁 Project Structure

```text
NyayaSaathi-AI-Lawyer/
│
├── app.py                     # Streamlit application entry point
├── nyayasaathi/
│   ├── config.py              # Application configuration
│   ├── models.py              # Case and response models
│   ├── conversation.py        # Conversation workflow
│   ├── extraction.py          # Fact extraction and validation
│   ├── retrieval.py           # Legal-source retrieval
│   ├── safety.py              # Scope and safety checks
│   ├── drafting.py            # Editable document generation
│   ├── speech.py              # Groq speech transcription
│   └── llm/                   # Provider-independent LLM integration
│
├── sources/
│   ├── catalogue.json         # Curated source records
│   └── README.md              # Source documentation
│
├── evaluation/
│   ├── test_cases/            # Fictional test scenarios
│   ├── raw_outputs/           # Recorded evaluation outputs
│   ├── run.py                 # Evaluation runner
│   └── run_speech.py          # Speech evaluation runner
│
├── tests/                     # Automated test suite
├── scripts/                   # Supporting development scripts
├── deployment/                # Additional deployment documentation
├── .streamlit/                # Streamlit configuration
├── requirements.txt           # Application dependencies
├── requirements-dev.txt       # Development dependencies
├── pyproject.toml             # Python project configuration
├── render.yaml                # Render deployment configuration
├── Dockerfile                 # Optional Docker deployment support
├── .dockerignore              # Docker build exclusions
├── .gitignore                 # Git exclusions
├── .env.example               # Environment-variable template
├── ARCHITECTURE.md            # Technical architecture
├── PROJECT_REQUIREMENTS.md    # Requirements and MVP scope
├── IMPLEMENTATION_PLAN.md     # Implementation roadmap
├── AGENTS.md                  # Development-agent instructions
└── README.md
```

---

## ⚠️ Known Limitations

NyayaSaathi is a working prototype, not a production-grade legal-advice service.

Current limitations include:

1. **Restricted legal coverage:** Only consumer complaints and rental security-deposit disputes are supported.

2. **AI extraction uncertainty:** Gemini can occasionally omit, paraphrase, or incorrectly structure case facts. The application validates proposed facts and asks for clarification when needed.

3. **Source coverage:** The curated catalogue is limited and does not represent a complete or continuously updated Indian-law database.

4. **State-specific rental laws:** Detailed statutory entitlements cannot be assumed without verified jurisdiction-specific sources.

5. **Speech recognition errors:** Hindi and Hinglish transcription may contain mistakes, making transcript review essential.

6. **Session persistence:** Case context is maintained primarily within the current Streamlit session and may be lost after a refresh or reset.

7. **Document format:** The supported download workflow focuses on editable text documents rather than automatically filed legal notices.

8. **External dependencies:** Gemini, Groq, and Render availability affect application performance.

9. **Legal reliability:** Retrieved information, extracted facts, and generated drafts must be reviewed. The system cannot guarantee legal correctness, eligibility, remedies, or outcomes.

---

## 🔮 Future Improvements

Possible future developments include:

- Broader coverage of verified Indian legal resources.
- Improved state-specific legal retrieval.
- More robust Hindi and Hinglish transcription.
- Multilingual legal-document drafting.
- Downloadable PDF documents.
- Secure case-saving functionality with appropriate privacy controls.
- Improved source-refresh and verification mechanisms.
- Expanded evaluation datasets.
- Human-lawyer referral workflows.
- Accessibility improvements for users with limited legal or digital literacy.

These features are not represented as implemented functionality in the current prototype.

---

## 🧠 Development Approach

NyayaSaathi was built with the assistance of AI coding tools, including **ChatGPT Codex**, for implementation, debugging, testing, and documentation.

The project emphasizes:

- A narrowly defined and achievable MVP.
- Separation of AI reasoning from deterministic checks.
- Transparent legal-source grounding.
- Explicit fact validation.
- User control over generated documents.
- Genuine testing with synthetic cases.
- Honest reporting of failures and limitations.
- Replaceable AI model integration.

A notable development challenge involved Gemini returning paraphrased or malformed structured facts. Early versions sometimes rejected an entire response because one proposed fact failed provenance validation.

The extraction pipeline was improved to validate facts independently, retain supported information, quarantine invalid fields, and request clarification instead of accepting unsupported details or discarding an otherwise useful response.

This experience informed the project's conservative legal-assistance design.

---

## 📄 Assignment Context

**Company:** KukuFM
**Role:** AI Generalist
**Selected Problem:** Problem 2 — Build an AI Lawyer
**Project:** NyayaSaathi

The submission focuses on demonstrating a practical AI-powered solution with clearly defined coverage, grounded information, multilingual access, editable outputs, testing evidence, and transparent limitations.

---

## 🔗 Important Links

| Resource | Link |
|---|---|
| **Live Application** | https://nyayasaathi-ai-lawyer.onrender.com |
| **GitHub Repository** | https://github.com/vinit9021/NyayaSaathi-AI-Lawyer |
| **Google AI Studio** | https://aistudio.google.com/ |
| **Groq Console** | https://console.groq.com/ |
| **Render** | https://render.com/ |
| **Streamlit** | https://streamlit.io/ |
| **National Consumer Helpline** | https://consumerhelpline.gov.in/ |
| **NALSA** | https://nalsa.gov.in/ |

---

## ⚖️ Final Disclaimer

NyayaSaathi provides AI-generated legal information and drafting assistance for a restricted set of everyday disputes in India.

It is not a substitute for a licensed legal professional and does not establish an advocate-client relationship.

The system does not guarantee the accuracy of every AI response, the applicability of every legal resource, or any particular legal outcome.

For urgent, complex, or consequential legal matters, consult a qualified lawyer or the appropriate legal-services authority.

---

**NyayaSaathi — Making everyday legal information easier to understand, one conversation at a time.**
