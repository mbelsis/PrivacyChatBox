# PrivacyChatBoX Setup Guide

This guide provides step-by-step instructions for setting up PrivacyChatBoX using the automated setup script.

## Prerequisites

Before running the setup script, make sure you have the following prerequisites installed:

1. **Python 3.10 or higher**: Required to run the application
2. **PostgreSQL** (optional but recommended): Required for the database
3. **git**: Required to clone the repository

## Quick Setup with the Automated Script

PrivacyChatBoX provides an automated setup script that handles the following:

- Creating a Python virtual environment
- Installing required dependencies
- Setting up the PostgreSQL database
- Creating necessary directories
- Running database migrations
- Configuring environment variables

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/PrivacyChatBoX.git
cd PrivacyChatBoX
```

### Step 2: Run the Setup Script

```bash
./setup.sh
```

The script will guide you through the setup process with interactive prompts.

### Step 3: Running the Application

After the setup is complete, you can start the application with:

```bash
# Activate the virtual environment (if not already activated)
source venv/bin/activate

# Start the application
streamlit run app.py
```

The application will be available at http://localhost:5000

### Step 4: Initial Login

Use the default admin credentials to log in for the first time:
- Username: **admin**
- Password: **admin**

**Important:** Change the admin password immediately after your first login by going to the Admin panel > User Management.

## Manual Setup Process

If you prefer to set up the application manually or if the automated script doesn't work for your environment, follow these steps:

### Step 1: Create a Python Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 2: Install Dependencies

```bash
pip install .
```

### Step 3: Create and Configure the Database

Create a PostgreSQL database:

```bash
createdb privacychatbox
```

Set the DATABASE_URL environment variable:

```bash
export DATABASE_URL="postgresql://username:password@localhost:5432/privacychatbox"
```

Or create a `.env` file with this content:

```
DATABASE_URL=postgresql://username:password@localhost:5432/privacychatbox
```

### Step 4: Create Required Directories

Create the following directories if they don't exist:
- `.streamlit`: For Streamlit configuration
- `models`: For local LLM models
- `assets`: For static assets

Create a `.streamlit/config.toml` file with:

```toml
[server]
headless = true
address = "0.0.0.0"
port = 5000
```

### Step 5: Run Database Migrations

Run the database migrations:

```bash
python database_check.py
python migration_add_dlp_columns.py
python migration_add_local_llm_columns.py
```

### Step 6: Start the Application

```bash
streamlit run app.py
```

### Step 7: Initial Login

Use the default admin credentials to log in:
- Username: **admin**
- Password: **admin**

## Environment Variables Configuration

PrivacyChatBoX uses environment variables for configuration. You can set these in a `.env` file or directly in your environment.

### Essential Variables

- `DATABASE_URL`: PostgreSQL connection string (required)

### API Keys (Optional)

- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic Claude API key
- `GOOGLE_API_KEY`: Google Gemini API key
- `SERPAPI_KEY`: SerpAPI key for web search

### Azure AD Authentication (Optional)

- `AZURE_CLIENT_ID`: Azure AD application client ID
- `AZURE_CLIENT_SECRET`: Azure AD application client secret
- `AZURE_TENANT_ID`: Azure AD tenant ID
- `AZURE_REDIRECT_URI`: Redirect URI after authentication

### Microsoft DLP Integration (Optional)

- `MS_CLIENT_ID`: Microsoft application client ID
- `MS_CLIENT_SECRET`: Microsoft application client secret
- `MS_TENANT_ID`: Microsoft tenant ID
- `MS_DLP_ENDPOINT_ID`: Microsoft DLP endpoint ID

## Troubleshooting

### Database Connection Issues

If you're having trouble connecting to the database:

1. Verify that PostgreSQL is running
2. Check that the DATABASE_URL is correct
3. Ensure the database exists and is accessible

### Missing Dependencies

If you encounter errors about missing dependencies:

1. Make sure you've activated the virtual environment
2. Try reinstalling the dependencies:
   ```bash
   pip install --upgrade .
   ```

### Database Schema Issues

If you encounter database schema errors:

1. Run the migration scripts:
   ```bash
   python migration_add_dlp_columns.py
   python migration_add_local_llm_columns.py
   ```

2. Or run the database check script:
   ```bash
   python database_check.py
   ```

### Initial Admin User Issues

If you're unable to log in with the default admin credentials:

1. Check the application logs to see if the admin user was created
2. You may need to manually create the admin user:
   ```python
   from auth import create_user
   create_user("admin", "admin", "admin")
   ```

## Additional Resources

For more detailed information, check out these additional documentation files:

- [Database Documentation](Database.md): Details about the database schema and operations
- [Local LLM Integration](LocalLLM.md): Information about using local language models
- [Troubleshooting Guide](Troubleshooting.md): Solutions for common issues
- [Conversation Data Formatting](ConversationData.md): How conversation data is formatted and handled