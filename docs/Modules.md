# PrivacyChatBoX Modules Documentation

This document provides an overview of the key modules in the PrivacyChatBoX application and their functionalities.

## Core Modules

### `app.py`

The main entry point of the application. It initializes the Streamlit interface, sets up authentication, and manages the main navigation flow.

**Key Functions:**
- `toggle_dark_mode()`: Toggles between light and dark themes

### `database.py`

Handles database connections and session management using SQLAlchemy.

**Key Functions:**
- `init_db()`: Initializes the database connection
- `get_session()`: Creates and returns a new database session
- `session_scope()`: Context manager for automatic session handling

### `models.py`

Defines the SQLAlchemy ORM models for the application's database schema.

**Key Models:**
- `User`: Stores user information and credentials
- `Settings`: User-specific settings for AI providers and privacy
- `Conversation`: Represents a chat conversation
- `Message`: Individual messages within a conversation
- `File`: Uploaded files linked to messages
- `DetectionEvent`: Privacy detection events

## AI Integration

### `ai_providers.py`

Integrates multiple AI providers (OpenAI, Claude, Gemini, local LLMs) with unified interfaces.

**Key Functions:**
- `get_available_models()`: Returns available models for each provider
- `get_user_settings(user_id)`: Retrieves user-specific AI settings
- `create_system_prompt(ai_character)`: Creates appropriate system prompts
- `get_ai_response(user_id, messages, stream, override_model, override_provider)`: Main function to get AI responses
- `get_openai_response(settings, messages, stream)`: OpenAI-specific implementation
- `get_claude_response(settings, messages, stream)`: Claude-specific implementation
- `get_gemini_response(settings, messages, stream)`: Gemini-specific implementation
- `get_local_response(settings, messages, stream)`: Local LLM implementation

## Privacy & Security

### `privacy_scanner.py`

Provides functionality to scan text and files for sensitive information.

**Key Functions:**
- `scan_text(user_id, text)`: Scans text for sensitive information
- `scan_file_content(user_id, file_content, file_name)`: Scans file content
- `anonymize_text(user_id, text)`: Anonymizes sensitive information
- `get_detection_events(user_id, limit)`: Gets recent detection events

**Pattern Collections:**
- `STANDARD_PATTERNS`: Basic patterns for sensitive information
- `STRICT_PATTERNS`: More comprehensive patterns

### `ms_dlp.py`

Microsoft Data Loss Prevention (DLP) integration for enhanced file sensitivity detection.

**Key Functions:**
- `get_ms_settings()`: Gets Microsoft settings from environment variables
- `get_ms_graph_token()`: Gets a Microsoft Graph API token
- `check_sensitivity_label(file_path, file_mime)`: Checks files for sensitivity labels
- `report_dlp_violation(user_id, file_path, file_name, sensitivity_info)`: Reports DLP violations
- `scan_file_for_sensitivity(user_id, file_path, file_name, file_mime)`: Main scan function
- `is_dlp_integration_enabled(user_id)`: Checks if DLP is enabled for a user

## Authentication

### `auth.py`

Handles local user authentication (username/password).

**Key Functions:**
- `init_auth()`: Initializes authentication system
- `authenticate(username, password)`: Authenticates a user
- `create_user(username, password, role)`: Creates a new user
- `get_users()`: Gets all users
- `delete_user(user_id)`: Deletes a user
- `update_user_role(user_id, new_role)`: Updates a user's role

### `azure_auth.py`

Integrates Azure Active Directory authentication for enterprise users.

**Key Functions:**
- `init_azure_auth()`: Initializes Azure AD authentication
- `get_auth_url()`: Gets the Azure AD authorization URL
- `process_auth_code(code, state)`: Processes Azure AD authorization code
- `process_azure_user(token_data)`: Processes Azure AD user information
- `create_or_get_azure_user(email, display_name, azure_id)`: Creates or gets a user
- `check_azure_auth_params()`: Checks for Azure AD auth parameters in URL
- `show_azure_login_button()`: Displays Azure AD login button

### `utils_auth.py`

Helper functions for authentication.

**Key Functions:**
- `hash_password(password)`: Hashes a password using SHA-256

## UI and Presentation

### `style.py`

Custom CSS styling for the application.

**Key Functions:**
- `apply_custom_css()`: Applies custom CSS styling

### `shared_sidebar.py`

Creates a consistent sidebar for all pages.

**Key Functions:**
- `create_sidebar(page_name)`: Creates a sidebar with navigation

### `pdf_export.py`

Functionality for exporting conversations to PDF.

**Key Functions:**
- `export_conversation_to_pdf(conversation_id)`: Exports a conversation to PDF

## General Utilities

### `utils.py`

General utility functions used across the application.

**Key Functions:**
- `generate_unique_id()`: Generates a unique ID
- `save_uploaded_file(uploaded_file)`: Saves an uploaded file
- `create_new_conversation(user_id, title)`: Creates a new conversation
- `get_conversations(user_id)`: Gets conversations for a user
- `get_conversation(conversation_id)`: Gets a specific conversation
- `add_message_to_conversation(conversation_id, role, content, uploaded_files)`: Adds a message
- `delete_conversation(conversation_id)`: Deletes a conversation
- `update_user_settings(user_id, settings_data)`: Updates user settings
- `format_detection_events(events)`: Formats detection events for display
- `format_conversation_messages(messages)`: Formats conversation messages

## Page Modules

### `pages/chat.py`

The main chat interface with AI. Handles message sending/receiving, file uploads, and conversation management.

### `pages/settings.py`

User settings interface with tabs for AI Models, Privacy Settings, Microsoft DLP, Custom Patterns, and Environment Config.

### `pages/history.py`

Displays conversation history and analytics about privacy detections.

### `pages/admin.py`

Admin dashboard for user management and system metrics.

## Local LLM Integration

### `model_utils.py`

Utility functions for managing local LLM models, including downloading, verifying, and testing.

**Key Functions:**
- `ensure_models_directory()`: Creates and returns the path to the models directory
- `get_model_info(model_filename)`: Gets information about a pre-configured model
- `download_model(model_filename, force)`: Downloads a model from Hugging Face
- `list_available_models()`: Lists all available models with their download status
- `show_model_download_ui()`: Displays a Streamlit UI for downloading and managing models

### `test_local_llm.py`

Testing script for local LLM integration without running the full application.

**Key Functions:**
- `test_local_model(model_path, prompt, n_ctx, n_gpu_layers)`: Tests a local model with a given prompt

### `pages/model_manager.py`

The Model Manager page for downloading, configuring, and testing local language models.

**Key Features:**
- Download pre-configured GGUF models from Hugging Face
- Upload custom models
- Test local models with customizable parameters
- Configure default settings for local model integration

## Migration Scripts

### `migration_add_dlp_columns.py`

Adds Microsoft DLP integration columns to the Settings table.

**Key Functions:**
- `run_migration()`: Adds necessary columns to the database schema

### `migration_add_local_llm_columns.py`

Adds local LLM configuration columns to the Settings table.

**Key Functions:**
- `run_migration()`: Adds necessary columns for local LLM support