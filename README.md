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

On first run, an admin user will be created with:
- Username: `admin`
- Password: `admin`

It's recommended to change this password immediately after first login.

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

## License

This project is licensed under the MIT License - see the LICENSE file for details.