# PrivacyChatBoX

![PrivacyChatBoX Logo](assets/logo.png)

## Overview

PrivacyChatBoX is a comprehensive Python-based AI privacy protection platform that provides an intuitive and engaging approach to safeguarding sensitive information across multiple document types and providers. This application offers a privacy-focused environment for AI interactions with multiple model integrations while ensuring user data remains secure.

## Key Features

- **Multi-Provider AI Integration**: Seamlessly switch between OpenAI, Anthropic Claude, Google Gemini, and local LLM models
- **Privacy Scanning**: Automatically scans text for sensitive information before sending to AI models
- **Document Anonymization**: Detects and anonymizes sensitive information in documents
- **Microsoft DLP Integration**: Blocks sensitive files based on Microsoft Sensitivity labels
- **Conversation Management**: Save, export, and manage conversation history
- **Azure AD Authentication**: Enterprise-ready authentication with Microsoft identities
- **Admin Dashboard**: User management, system metrics, and configuration
- **Analytics**: Comprehensive privacy metrics and visualization
- **PDF Export**: Export conversations to well-formatted PDF documents
- **Web Search**: Integrated web search capabilities through SerpAPI

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
│   └── settings.py         # User settings
├── models.py               # Database models
├── database.py             # Database connection utilities
├── ai_providers.py         # AI provider integration
├── privacy_scanner.py      # Privacy scanning functionality
├── ms_dlp.py               # Microsoft DLP integration
├── auth.py                 # Authentication utilities
├── azure_auth.py           # Azure AD authentication
├── utils.py                # General utilities
├── utils_auth.py           # Authentication utilities
├── pdf_export.py           # PDF export functionality
├── shared_sidebar.py       # Shared UI components
├── style.py                # Custom CSS styling
├── assets/                 # Static assets
│   ├── logo.png            # Application logo
│   └── ...                 # Other assets
├── .env                    # Environment variables (not in repo)
├── .streamlit/             # Streamlit configuration
│   └── config.toml         # Streamlit configuration file
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Project metadata
├── migration_add_dlp_columns.py  # Database migration script
├── model_utils.py          # Local LLM model utilities
├── test_local_llm.py       # Testing script for local LLM integration
├── models/                 # Directory for local LLM models
└── docs/                   # Documentation
    ├── Modules.md          # Module documentation
    └── Database.md         # Database documentation
```

## Setup and Installation

### Prerequisites

- Python 3.11 or higher
- PostgreSQL database
- API keys for desired AI providers (OpenAI, Claude, Gemini)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/PrivacyChatBoX.git
   cd PrivacyChatBoX
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
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
   
   # Microsoft DLP Integration (Optional)
   MS_CLIENT_ID=your_ms_client_id
   MS_CLIENT_SECRET=your_ms_client_secret
   MS_TENANT_ID=your_ms_tenant_id
   MS_DLP_ENDPOINT_ID=your_ms_dlp_endpoint_id
   ```

4. Run database migrations:
   ```bash
   python migration_add_dlp_columns.py
   ```

5. Start the application:
   ```bash
   streamlit run app.py
   ```

6. Access the application at `http://localhost:5000`

### Initial Setup

**Important:** On first run, the application automatically creates an admin user:
- Username: **`admin`**
- Password: **`admin`**

This default admin account is created by the `init_auth()` function in `auth.py`, which runs during application startup. The admin user has full access to all features, including user management.

⚠️ **Security Warning:** It's strongly recommended to change this password immediately after your first login by going to the Admin panel > User Management.

## Usage

1. **Login**: Use the login form or Azure AD login if configured
2. **Chat**: Navigate to the chat page to start conversations with AI
3. **Settings**: Configure your AI providers, privacy settings, and more
4. **History**: View your conversation history and analytics
5. **Admin**: Manage users and view system metrics (admin only)

## Environment Variables

Refer to the Settings page > Environment Config tab for a complete list of available environment variables and their descriptions.

## API Keys

This application requires various API keys for full functionality:

- **OpenAI API Key**: Get from [OpenAI Platform](https://platform.openai.com/account/api-keys)
- **Claude API Key**: Get from [Anthropic Console](https://console.anthropic.com/account/keys)
- **Gemini API Key**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
- **SerpAPI Key**: Get from [SerpAPI](https://serpapi.com/)

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

If you encounter database-related errors, especially with missing columns, make sure to run these migration scripts:

```bash
python migration_add_dlp_columns.py
python migration_add_local_llm_columns.py
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

## License

This project is licensed under the MIT License - see the LICENSE file for details.