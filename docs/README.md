# PrivacyChatBoX Documentation

Welcome to the PrivacyChatBoX documentation. This section contains comprehensive information about the application's architecture, components, and setup instructions.

## Table of Contents

1. [Overview](../README.md) - High-level description of the application
2. [Module Documentation](Modules.md) - Detailed information about each module and its functionality
3. [Database Documentation](Database.md) - Database schema, relationships, and setup instructions
4. [Package Requirements](Package_Requirements.md) - List of required Python packages

## Additional Resources

### Environment Variables

The application uses the following environment variables:

```
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

### Application Structure

The application follows a modular structure:

- **Core**: `app.py`, `database.py`, `models.py`
- **Pages**: `pages/chat.py`, `pages/settings.py`, `pages/history.py`, `pages/admin.py`
- **AI Integration**: `ai_providers.py`
- **Privacy**: `privacy_scanner.py`, `ms_dlp.py`
- **Authentication**: `auth.py`, `azure_auth.py`, `utils_auth.py`
- **UI Components**: `shared_sidebar.py`, `style.py`
- **Utilities**: `utils.py`, `pdf_export.py`

### User Roles

The application supports two user roles:

1. **User** - Regular users who can:
   - Chat with AI models
   - Manage their own settings
   - View their conversation history
   - Export conversations to PDF

2. **Admin** - Administrators who can additionally:
   - Manage other users
   - View system metrics
   - Access the admin dashboard

### Privacy Features

PrivacyChatBoX includes several privacy features:

1. **Privacy Scanning** - Scans text for sensitive information
2. **Anonymization** - Anonymizes sensitive information
3. **Microsoft DLP Integration** - Blocks sensitive files using Microsoft DLP
4. **Detection Event Logging** - Logs privacy detection events for auditing

### Extensions and Customization

The application can be extended with:

1. **Custom Privacy Patterns** - Add custom regex patterns for privacy scanning
2. **Additional AI Providers** - Implement support for other AI providers
3. **New AI Characters** - Create custom AI characters with specialized system prompts

## Deployment

For deployment instructions, refer to the [main README](../README.md#setup-and-installation).

## Contributing

To contribute to the project, please follow these steps:

1. Fork the repository
2. Create a new branch for your feature
3. Add your changes
4. Submit a pull request

## License

This project is licensed under the MIT License.