# Troubleshooting Guide

This document provides solutions for common issues encountered when running PrivacyChatBoX.

## Database Issues

### Missing Columns Errors

**Error:** `column settings.enable_ms_dlp does not exist` or similar errors related to missing database columns.

**Cause:** The database schema is missing required columns that have been added to the application models.

**Solution:**
1. Run the migration scripts to add the missing columns:
   ```bash
   python migration_add_dlp_columns.py
   python migration_add_local_llm_columns.py
   ```

2. The application also includes automatic migration detection. When new features are accessed, it will attempt to detect and fix schema issues.

### Detached Instance Errors

**Error:** `Instance <User at 0x...> is not bound to a Session; attribute refresh operation cannot proceed`

**Cause:** Trying to access SQLAlchemy model objects outside of an active database session.

**Solution:**
1. Always use the `session_scope` context manager for database operations:
   ```python
   from database import session_scope
   
   with session_scope() as session:
       # Perform database operations here
       user = session.query(User).filter(User.id == user_id).first()
       # Do something with user within this context
   
   # Don't access user attributes outside the context!
   ```

2. If you need to use model data outside a session, convert to dictionaries:
   ```python
   with session_scope() as session:
       user = session.query(User).filter(User.id == user_id).first()
       user_dict = {
           "id": user.id,
           "username": user.username,
           # ...other attributes
       }
   
   # Now you can use user_dict safely
   ```

3. Use the provided utility functions for common operations:
   - `utils.format_conversation_messages()` for conversation messages
   - `auth.get_users()` for user lists
   - `privacy_scanner.get_detection_events()` for detection events

## Conversation Display Issues

**Error:** `AttributeError: 'dict' object has no attribute 'title'` or `'dict' object has no attribute 'content'`

**Cause:** The code is trying to access dictionary objects using attribute notation instead of dictionary key notation.

**Solution:**
1. Use dictionary access notation when working with formatted data:
   ```python
   # Incorrect:
   conversation.title
   message.content
   
   # Correct:
   conversation["title"]
   message["content"]
   ```

2. Always use the `utils.format_conversation_messages()` function to process conversation messages. This function correctly handles both SQLAlchemy model objects and dictionaries.

3. Check the object type before accessing:
   ```python
   if isinstance(message, dict):
       content = message.get("content", "")
   else:
       content = getattr(message, "content", "")
   ```

## Microsoft DLP Integration Issues

**Error:** Issues related to Microsoft DLP integration or missing DLP columns.

**Solution:**
1. Make sure you've set the required environment variables:
   - `MS_CLIENT_ID`
   - `MS_CLIENT_SECRET`
   - `MS_TENANT_ID`
   - `MS_DLP_ENDPOINT_ID`

2. Run the DLP migration script:
   ```bash
   python migration_add_dlp_columns.py
   ```

3. The application includes the auto-migration function in `ms_dlp.py`, which will automatically check for and run necessary migrations.

## Local LLM Issues

**Error:** Missing columns for local LLM configuration.

**Solution:**
1. Run the local LLM migration script:
   ```bash
   python migration_add_local_llm_columns.py
   ```

2. Make sure you have the required dependencies installed:
   ```bash
   pip install llama-cpp-python
   ```

3. Download a compatible model from the Model Manager page.

## General Troubleshooting Tips

1. **Check Environment Variables:** Ensure all required environment variables are correctly set.

2. **Restart the Application:** Sometimes, a simple restart resolves temporary issues.

3. **Check Logs:** Look for error messages in the application logs.

4. **Update Dependencies:** Ensure all dependencies are up to date.

5. **Use Session Context Managers:** Always use `session_scope()` when working with database operations.

6. **Error Handling:** Wrap critical operations in try-except blocks to catch and handle errors gracefully.

7. **Format Database Objects:** Convert database objects to dictionaries when they need to be used outside of a database session.