# PrivacyChatBoX

![PrivacyChatBoX Logo](assets/logo.png)

> **IMPORTANT NOTICE**: This project is still a work in progress. Some features may be incomplete or subject to change.

## Overview

PrivacyChatBoX is a comprehensive Python-based AI privacy protection platform that provides an intuitive and engaging approach to safeguarding sensitive information across multiple document types and providers. 

This application offers a privacy-focused environment for AI interactions with multiple model integrations while ensuring user data remains secure.

## Key Features

- **Multi-Provider AI Integration**: Seamlessly switch between OpenAI, Anthropic Claude, Google Gemini, and local LLM models
- **Privacy Scanning**: Automatically scans text for sensitive information before sending to AI models
- **Document Anonymization**: Detects and anonymizes sensitive information in documents
- **Privacy Alerts**: Visual indicators (⚠️) for conversations with detected sensitive information
- **Role-Based Access Control**: Admin and regular user roles with appropriate permissions
- **Privacy-Focused Administration**: Admins can see metadata and privacy alerts but not conversation content
- **Microsoft Purview DLP Integration**: Enforces Microsoft sensitivity labels on uploads and evaluates prompts against your Purview DLP policies
- **Conversation Management**: Save, export, and manage conversation history
- **Azure AD Authentication**: Enterprise-ready authentication with Microsoft identities
- **Admin Dashboard**: User management, system metrics, and configuration
- **Analytics**: Comprehensive privacy metrics and visualization
- **PDF Export**: Export conversations to well-formatted PDF documents
- **Web Search**: Integrated web search capabilities through SerpAPI
- **Docker Deployment**: Containerized deployment for easy installation and scaling

> **Security Notice**: Conversation titles, message content and file names are encrypted at rest when `DATA_ENCRYPTION_KEY` is set (see [Encryption at Rest](#encryption-at-rest)). Without a key they are stored in plaintext and the Admin panel shows a warning. Privacy logs store masked previews of detected values, and uploaded files are not retained after their DLP checks.

## Architecture

The application is built using the following technologies:

- **Frontend & Backend**: Streamlit (Python web application framework)
- **Database**: PostgreSQL
- **AI Providers**: OpenAI API, Anthropic Claude API, Google Gemini API
- **Authentication**: Local authentication with password hashing, Azure AD integration
- **Privacy Analysis**: Custom regex patterns and Microsoft DLP integration

## Folder Structure

```
PrivacyChatBoX/
├── app.py                  # Main application entry point
├── pages/                  # Streamlit pages
│   ├── admin.py            # Admin dashboard
│   ├── chat.py             # Main chat interface
│   ├── history.py          # Conversation history and analytics
│   ├── model_manager.py    # Local LLM model management (admin only)
│   └── settings.py         # User settings
├── models.py               # Database models
├── database.py             # Database connection utilities
├── database_check.py       # Database schema validation
├── ai_providers.py         # AI provider integration
├── privacy_scanner.py      # Privacy scanning functionality
├── ms_dlp.py               # Microsoft Purview DLP / sensitivity label integration
├── model_catalog.py        # Supported AI model IDs (single source of truth)
├── web_search.py           # /search command via the official serpapi client
├── data_protection.py      # Encryption at rest and audit-log masking
├── migration_secure_existing_data.py # Encrypt legacy rows, rotate keys, mask old logs
├── auth.py                 # Authentication utilities
├── azure_auth.py           # Azure AD authentication
├── utils.py                # General utilities
├── utils_auth.py           # Authentication utilities
├── pdf_export.py           # PDF export functionality
├── shared_sidebar.py       # Shared UI components (with role-based visibility)
├── style.py                # Custom CSS styling
├── assets/                 # Static assets
│   ├── logo.png            # Application logo
│   └── ...                 # Other assets
├── .env                    # Environment variables (not in repo)
├── .streamlit/             # Streamlit configuration
│   └── config.toml         # Streamlit configuration file
├── pyproject.toml          # Project metadata and Python dependencies
├── migration_add_dlp_columns.py      # Microsoft DLP integration migration
├── migration_add_local_llm_columns.py # Local LLM settings migration
├── migration_pattern_levels.py       # Privacy pattern levels migration
├── model_utils.py          # Local LLM model utilities
├── test_local_llm.py       # Testing script for local LLM integration
├── setup.sh                # Automated installation script
├── models/                 # Directory for local LLM models
└── docs/                   # Documentation
    ├── Modules.md          # Module documentation
    ├── Database.md         # Database documentation
    ├── Setup_Guide.md      # Detailed setup instructions
    ├── Troubleshooting.md  # Solutions for common issues
    ├── ConversationData.md # Conversation data formatting guide
    ├── LocalLLM.md         # Local LLM integration guide
    └── Optimization_Guide.md # Performance optimization techniques
```

## Setup and Installation

### Prerequisites

- Python 3.11 or higher
- PostgreSQL database (recommended)
- API keys for desired AI providers (OpenAI, Claude, Gemini) - optional

### Automated Setup (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/PrivacyChatBoX.git
   cd PrivacyChatBoX
   ```

2. Run the setup script:
   ```bash
   ./setup.sh
   ```
   
   This script will:
   - Create a Python virtual environment
   - Install required dependencies
   - Set up the PostgreSQL database
   - Create necessary directories
   - Configure environment variables
   - Run database migrations

3. Start the application:
   ```bash
   source venv/bin/activate
   streamlit run app.py
   ```

4. Access the application at `http://localhost:5000`

For detailed setup instructions, troubleshooting, and manual setup options, see [Setup Guide](docs/Setup_Guide.md).

### Manual Installation

If you prefer a manual setup:

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/PrivacyChatBoX.git
   cd PrivacyChatBoX
   ```

2. Install dependencies:
   ```bash
   pip install .
   ```

3. Configure environment variables by creating a `.env` file:
   ```bash
   # Database Configuration
   DATABASE_URL=postgresql://username:password@localhost/privacychatbox
   
   # OpenAI API (Optional)
   OPENAI_API_KEY=your_openai_api_key
   
   # Anthropic API (Optional)
   ANTHROPIC_API_KEY=your_anthropic_api_key
   
   # Google Gemini API (Optional)
   GOOGLE_API_KEY=your_gemini_api_key
   
   # SerpAPI for web search (Optional)
   SERPAPI_KEY=your_serpapi_key
   
   # Azure AD Authentication (Optional)
   AZURE_CLIENT_ID=your_azure_client_id
   AZURE_CLIENT_SECRET=your_azure_client_secret
   AZURE_TENANT_ID=your_azure_tenant_id
   AZURE_REDIRECT_URI=http://localhost:5000/
   
   # Microsoft Purview DLP Integration (Optional)
   MS_CLIENT_ID=your_ms_client_id
   MS_CLIENT_SECRET=your_ms_client_secret
   MS_TENANT_ID=your_ms_tenant_id

   # Encryption at rest (strongly recommended)
   DATA_ENCRYPTION_KEY=your_fernet_key
   ```

4. Create Streamlit configuration:
   ```bash
   mkdir -p .streamlit
   echo "[server]" > .streamlit/config.toml
   echo "headless = true" >> .streamlit/config.toml
   echo "address = \"0.0.0.0\"" >> .streamlit/config.toml
   echo "port = 5000" >> .streamlit/config.toml
   ```

5. Run database migrations:
   ```bash
   python database_check.py
   ```

6. Start the application:
   ```bash
   streamlit run app.py
   ```

7. Access the application at `http://localhost:5000`



### Docker Deployment

The application can be easily deployed using Docker and Docker Compose:

### Quick Docker Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/PrivacyChatBoX.git
   cd PrivacyChatBoX
   ```

2. Start the application:
   ```bash
   docker-compose up -d
   ```

3. Access the application at `http://localhost:5000`

For a complete step-by-step guide on Docker deployment, configuration, and troubleshooting, see:
- [Docker Setup Guide](docs/docker-setup.md) - Comprehensive instructions for Docker deployment
- [Docker Guide](docs/Docker_Guide.md) - Detailed reference and advanced configurations

## Testing

Run the automated test suite locally with:

```bash
python -m pytest tests -q
```

The current test suite focuses on the highest-risk application logic, including:

- authentication and session expiry
- conversation access control and deletion
- privacy scanning and anonymization behavior
- provider privacy-scan bypass logic
- PDF export escaping and authorization
- migration commit behavior
- history, analytics, and page-level data-shaping helpers

A lightweight GitHub Actions workflow is included at [`.github/workflows/tests.yml`](.github/workflows/tests.yml) so the same command runs automatically on pushes and pull requests.

### Initial Setup

On first run, `init_auth()` in `auth.py` creates a bootstrap admin account:
- Username: **`admin`** (override with `DEFAULT_ADMIN_USERNAME`)
- Password: a **random temporary password printed once in the server log** (`docker-compose logs app` for Docker). Set `DEFAULT_ADMIN_PASSWORD` to choose it yourself; weak values such as `admin` are rejected and a random password is generated instead.

The bootstrap password is temporary: the admin must change it at first login before using chat. Passwords that an administrator sets for other users are also temporary. Existing installations whose admin still uses the old `admin`/`admin` default are forced to change it at next login.


## User Roles and Permissions

The application supports two types of user roles with different permissions:

### Regular Users
- Can access Chat, History, and Settings pages
- Can only see and manage their own conversations
- Can configure their own AI provider settings and privacy preferences
- Cannot access Admin Panel or Model Manager pages

### Administrators
- Have full access to all pages including Admin Panel and Model Manager
- Can manage users (create, delete, change roles and passwords)
- Can view metadata about all users' conversations (titles, timestamps, file attachments, privacy alerts)
- Can see which conversations contain privacy alerts (⚠️ indicator)
- **Cannot view the actual content of other users' conversations**, only metadata
- Can manage system-wide settings and local LLM models

> **Security Note**: With `DATA_ENCRYPTION_KEY` set, conversation content is encrypted at rest, so database dumps and backups do not expose it. Anyone holding both the database and the key (including the application host) can still decrypt it.

## Usage

1. **Login**: Use the login form or Azure AD login if configured
2. **Chat**: Navigate to the chat page to start conversations with AI
3. **Settings**: Configure your AI providers, privacy settings, and more
4. **History**: View your conversation history and analytics
5. **Admin**: Manage users and view system metrics (admin only)
6. **Model Manager**: Download and configure local LLM models (admin only)


## Environment Variables and Security

This application uses environment variables to store sensitive configuration like API keys and database credentials. This approach enhances security by keeping secrets out of your code repository.

### Environment Setup

1. **Create your .env file**:
   - Copy the provided `.env.example` file:
     ```bash
     cp .env.example .env
     ```
   - Edit the `.env` file with your actual credentials

2. **Security measures in place**:
   - The `.gitignore` file is configured to exclude the `.env` file from git
   - Environment variables are loaded at runtime and never stored in the database
   - API keys are accessed only when needed for specific operations

3. **Available variables**:
   - Database connection: `DATABASE_URL`
   - API keys: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY` (or `GEMINI_API_KEY`), `SERPAPI_KEY`
   - Model lists: `OPENAI_MODELS`, `CLAUDE_MODELS`, `GEMINI_MODELS` (optional overrides)
   - Azure authentication: `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, etc.
   - Microsoft Purview DLP: `MS_CLIENT_ID`, `MS_CLIENT_SECRET`, `MS_TENANT_ID`, optional `MS_PURVIEW_*` / `MS_DLP_*`
   - Encryption at rest: `DATA_ENCRYPTION_KEY`
   - Bootstrap admin: `DEFAULT_ADMIN_USERNAME`, `DEFAULT_ADMIN_PASSWORD`

You can also refer to the Settings page > Environment Config tab for a complete list of available environment variables and additional descriptions.

### ⚠️ Important Security Notes

- **NEVER commit your `.env` file** to version control
- Double-check your `.gitignore` file includes `.env` entries
- Regularly rotate your API keys for production deployments
- Use separate API keys for development and production environments

## API Keys

This application requires various API keys for full functionality:

- **OpenAI API Key**: Get from [OpenAI Platform](https://platform.openai.com/account/api-keys)
- **Claude API Key**: Get from [Anthropic Console](https://console.anthropic.com/account/keys)
- **Gemini API Key**: Get from [Google AI Studio](https://aistudio.google.com/apikey)
- **SerpAPI Key**: Get from [SerpAPI](https://serpapi.com/)

## Supported AI Models

Model IDs live in one place, [`model_catalog.py`](model_catalog.py). The first entry is the default for new users.

| Provider | Models offered | SDK |
|---|---|---|
| OpenAI | `gpt-5.6-terra` (default), `gpt-6.1-sol`, `gpt-6-luna`, `gpt-5.5`, `gpt-5.4-mini`, `gpt-5.4-nano` | `openai` |
| Anthropic | `claude-sonnet-5-5` (default), `claude-opus-5-5`, `claude-fable-5-1`, `claude-haiku-5-5` | `anthropic` |
| Google | `gemini-3.8-flash` (default), `gemini-3.5-flash-lite`, `gemini-3.1-pro-preview` (preview) | `google-genai` |

- Settings saved with a retired model (for example `gpt-4o` or `claude-3-5-sonnet-20241022`) are resolved to the provider default automatically.
- Model lists go stale quickly. Replace a provider's list without a code change with `OPENAI_MODELS`, `CLAUDE_MODELS` or `GEMINI_MODELS` (comma-separated).
- OpenAI GPT-5 and later are reasoning models, so requests use `max_completion_tokens` and the default temperature.
- Gemini uses the `google-genai` SDK; the previous `google-generativeai` package has reached end of life.

## Web Search

The `/search <query>` chat command uses SerpApi's officially maintained [`serpapi`](https://pypi.org/project/serpapi/) client. It replaces the legacy `google-search-results` package, which is no longer developed and fails to build on recent Python versions. Both install a module named `serpapi`, so when upgrading run:

```bash
pip uninstall -y google-search-results && pip install serpapi
```

The query is sent after privacy scanning and anonymization, so detected sensitive values are not forwarded to the search provider when auto-anonymize is on.

## Microsoft Purview DLP

The integration uses documented Microsoft APIs:

1. **Sensitivity labels on uploads.** Labels are read locally from the file's own metadata (`MSIP_Label_*` properties in Office files, PDFs and e-mails), so files are not uploaded to Microsoft just to learn their label. Label IDs are resolved to names with Microsoft Graph `GET /beta/security/informationProtection/sensitivityLabels`. Files labelled at or above the user's threshold are blocked.
2. **Purview DLP policies on prompts and file text.** Content is evaluated with Microsoft Graph v1.0 `POST /users/{id}/dataSecurityAndGovernance/processContent`. Content is blocked when Purview returns `restrictAccess` with `block`. Blocked uploads are recorded in Purview audit with `contentActivities`.

**Setup:** register an Entra application, grant the Microsoft Graph application permissions `InformationProtectionPolicy.Read.All`, `Content.Process.User` and `ContentActivity.Write` with admin consent, and set `MS_CLIENT_ID`, `MS_CLIENT_SECRET` and `MS_TENANT_ID`. Then create a Purview DLP policy that targets the application. Without one, `processContent` allows everything. The Admin panel's **Microsoft DLP** tab has a connection test that lists your tenant's labels.

**Coverage:** label enforcement applies to every user. Purview policy evaluation needs a Microsoft Entra identity, so it applies to users who sign in with Azure AD.

**Optional settings:** `MS_DLP_LABEL_LEVELS` maps label names or IDs to levels (JSON). `MS_DLP_UNKNOWN_LABEL_LEVEL` sets the level for unrecognised labels and defaults to `confidential`, so unknown labels fail safe. `MS_PURVIEW_FAIL_CLOSED=true` blocks content when Purview cannot be reached. `MS_DLP_ENDPOINT_ID` from earlier versions is no longer used.

## Encryption at Rest

Set `DATA_ENCRYPTION_KEY` to a Fernet key to encrypt conversation titles, message content and uploaded file names in the database:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

- `setup.sh` generates a key automatically if none exists.
- Run `python migration_secure_existing_data.py` once to encrypt existing plaintext rows. The Docker entrypoint runs it on every start, and it is idempotent.
- **Key rotation:** prepend a new key (`DATA_ENCRYPTION_KEY=new_key,old_key`), run the migration, then remove the old key.
- **Back up the key securely.** Data encrypted with a lost key cannot be recovered.

## Performance Optimizations

PrivacyChatBoX includes several performance optimizations to improve scanning speed and memory efficiency:

- **Pre-compiled Regex Patterns**: All privacy patterns are pre-compiled at startup for faster matching
- **Confidence Scoring**: Each pattern has a confidence score to reduce false positives
- **Chunked File Processing**: Large files are processed in manageable chunks to prevent memory issues
- **Parallel Processing**: Multi-threading support for faster document scanning
- **Adaptive Loading**: Document processing libraries are loaded conditionally as needed

For detailed information on performance optimizations, see [Optimization Guide](docs/Optimization_Guide.md).


## Local LLM Integration

PrivacyChatBoX supports running local language models without requiring an internet connection or API keys, which enhances privacy and reduces operational costs.

### Local Model Support

The application supports GGUF format models through the llama-cpp-python library. Popular models include:

- **Llama 2**: Meta's Llama 2 models in various sizes
- **Mistral**: Mistral AI's efficient models
- **Phi-2**: Microsoft's compact but capable models
- **Any GGUF format model**: Compatible with the llama-cpp-python library

### Model Manager

The Model Manager page provides a user-friendly interface for:

- Downloading pre-configured models directly within the application
- Customizing model parameters like context length and temperature
- Testing models before deploying them in the chat interface

### Privacy Features with Local Models

- **Offline Operation**: Process all requests entirely on your own hardware
- **Bypass Privacy Scanning**: Option to disable privacy scanning for local models (since data never leaves your system)
- **Hardware Acceleration**: GPU acceleration support for faster inference

## Troubleshooting

### Database Migrations

This application uses several database migration scripts to handle schema updates:

- **migration_add_dlp_columns.py**: Adds Microsoft DLP integration columns to the Settings table
- **migration_add_local_llm_columns.py**: Adds local LLM configuration columns to the Settings table
- **migration_pattern_levels.py**: Adds 'level' attribute to custom patterns in Settings table, enabling categorization of patterns into standard and strict modes

If you encounter database-related errors, especially with missing columns, make sure to run these migration scripts:

```bash
python migration_add_dlp_columns.py
python migration_add_local_llm_columns.py
python migration_pattern_levels.py
```

The application includes auto-migration checks that will attempt to detect and apply necessary migrations when features are accessed.

### Common Issues and Solutions

1. **Missing Database Columns Error**:
   - Error: `column settings.enable_ms_dlp does not exist` or similar
   - Solution: Run the appropriate migration script as mentioned above

2. **Detached Instance Errors**:
   - Error: `Instance <User at 0x...> is not bound to a Session`
   - Solution: The application uses the session_scope context manager to properly handle database sessions. 
               Check that all database operations are performed within a session_scope block.

3. **Conversation Display Issues**:
   - Problem: Conversations not displaying correctly or errors when accessing message properties
   - Solution: The application uses a robust message formatting function that handles both model objects and dictionaries.
               Make sure to use the format_conversation_messages function when working with conversation data.

## Future Development

The following features and improvements are planned for future versions of PrivacyChatBoX:

1. **Key Management Integration**: Load `DATA_ENCRYPTION_KEY` from a managed key store (Azure Key Vault, AWS KMS, HashiCorp Vault) instead of an environment variable.

2. **Chat Interface Optimization**: Improve the chat interface performance and responsiveness, including faster message rendering and reduced latency for long conversations.

3. **Multi-modal AI Support**: Expand capabilities to handle image, audio, and video inputs/outputs with privacy-preserving processing for all media types.

4. **Advanced RAG Implementation**: Add Retrieval-Augmented Generation capabilities with local vector databases for organizational knowledge bases, with privacy-aware embedding generation.

5. **Federated Learning Integration**: Implement privacy-preserving model fine-tuning using federated learning techniques to improve AI responses without compromising user data.

6. **Enterprise SSO Integration**: Expand authentication options to support additional enterprise SSO providers beyond Azure AD, including Okta, Auth0, and Google Workspace.

7. **Compliance Reporting**: Implement automated compliance reporting for privacy regulations like GDPR, HIPAA, and CCPA with audit trails for all AI interactions.

## Application Screenshots

Here are some screenshots showing the various interfaces of the PrivacyChatBoX application:

### Login and Main Screen
![Main Screen](attached_assets/MainScreen.png)
*The welcome screen with login form and key features overview*

### Chat Interface with Anonymization
![Chat Interface](attached_assets/Anonymisation.png)
*The chat interface showing privacy protection in action with anonymized phone number*

### Settings Panel
![Settings Panel](attached_assets/Settings.png)
*AI model configuration settings with API key management*

### Custom Privacy Patterns
![Privacy Patterns](attached_assets/Privacy-Patterns.png)
*Custom regex pattern configuration for privacy scanning*

### Conversation History with Privacy Alerts
![Conversation History](attached_assets/Chat-History.png)
*Conversation history with privacy alert indicators*

## License

This project is licensed under a dual-license model:

### Non-Commercial Use
- **Free** for personal, educational, research, and non-profit use
- Permission to use, modify, and redistribute for non-commercial purposes
- Must include original copyright notice and license terms
- Contributions back to the project welcome under same license terms

### Commercial Use
- Requires a paid commercial license for any business or revenue-generating applications
- Contact the copyright holders for commercial licensing options and pricing
- Enterprise support and customization available under commercial agreements

The full license terms are available in the [LICENSE.md](LICENSE.md) file, which includes all conditions, disclaimers, and limitations. This dual-licensing approach helps maintain the project's sustainable development while providing free access for non-commercial users.

**DISCLAIMER:** This software is provided "AS IS" without warranty of any kind. Use at your own risk. The developers assume no liability for any damages or losses resulting from the use of this software.
