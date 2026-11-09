# NyayaSaathi-AI-Lawyer

Initial project setup for a Python-based AI lawyer application.
Application implementation has not started.

## Development environment

- Windows PowerShell
- Python 3.11 or newer (use the `python` command)
- Git and GitHub CLI

## Repository hygiene

Never commit credentials, API keys, private legal case data, or assignment PDFs.
Keep local environment settings in `.env` and Streamlit secrets in
`.streamlit/secrets.toml`; both are ignored by Git. Store private inputs and
generated private data in ignored directories such as `data/` or `private_data/`.
All PDFs are ignored as a precaution.

Review each change and stage explicit file paths. Ignore rules are a safeguard,
not a substitute for reviewing staged content for secrets and private data.
After implementation and relevant tests pass, use meaningful Conventional
Commits and push to `main`, obtaining approval where required.
