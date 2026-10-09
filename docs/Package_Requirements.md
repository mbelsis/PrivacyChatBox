# PrivacyChatBoX Package Requirements

Dependencies are declared in [`pyproject.toml`](../pyproject.toml), which is the single source of truth
(the Dockerfile installs from it as well). Install them with:

```bash
pip install .
```

Python 3.11 or newer is required.

## Notable dependencies

| Purpose | Package | Notes |
|---|---|---|
| Web UI | `streamlit` | |
| Database | `sqlalchemy`, `psycopg2-binary` | PostgreSQL in production; SQLite works for tests |
| OpenAI | `openai>=3.26` | GPT-5+/6 reasoning models |
| Anthropic | `anthropic>=1.12` | Claude 5.x models |
| Google Gemini | `google-genai>=2.29` | Replaces the end-of-life `google-generativeai` |
| Web search | `serpapi>=1.1.2` | Replaces the legacy `google-search-results`; uninstall that package first |
| Microsoft Entra / Graph | `msal`, `requests` | Azure AD login and Purview DLP |
| Encryption at rest | `cryptography` | Fernet field encryption |
| Documents | `pdfminer.six`, `python-docx`, `openpyxl` | Text extraction for scanning |
| PDF export | `reportlab` | |
| Local LLMs | `llama-cpp-python` | Builds from source; may need a C++ toolchain |

## Removed dependencies

These were declared but never used, or conflicted with each other: `jose` (conflicts with `python-jose`
and targets Python 2), `python-jose`, `pyjwt`, `msgraph-core`, `azure-storage-blob`, `concurrent-log-handler`.

## Upgrading an existing environment

```bash
pip uninstall -y google-search-results google-generativeai jose
pip install --upgrade .
```
