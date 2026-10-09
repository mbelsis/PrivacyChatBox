import streamlit as st
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from dotenv import load_dotenv
from database import get_session, session_scope
from models import User, Settings
from sqlalchemy.exc import IntegrityError
from utils_auth import hash_password, verify_password, is_legacy_sha256_hash
from model_catalog import DEFAULT_OPENAI_MODEL, DEFAULT_CLAUDE_MODEL, DEFAULT_GEMINI_MODEL

load_dotenv()

DEFAULT_BOOTSTRAP_ADMIN_USERNAME = os.environ.get("DEFAULT_ADMIN_USERNAME", "admin").strip() or "admin"
# Optional. When unset or weak, a random bootstrap password is generated instead.
CONFIGURED_BOOTSTRAP_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD", "").strip()
# Passwords that earlier versions shipped as defaults; accounts still using them are
# forced to change password even though new installs never create them.
KNOWN_DEFAULT_PASSWORDS = {"admin"}
ALLOW_SELF_REGISTRATION = os.environ.get("ALLOW_SELF_REGISTRATION", "false").strip().lower() in {"1", "true", "yes", "on"}


def is_bootstrap_account(username: str) -> bool:
    """Return True when the username matches the bootstrap admin account."""
    return username == DEFAULT_BOOTSTRAP_ADMIN_USERNAME


def is_using_bootstrap_password(user: User) -> bool:
    """Return True when the bootstrap account still uses a configured or legacy default password."""
    if not is_bootstrap_account(user.username):
        return False
    candidates = set(KNOWN_DEFAULT_PASSWORDS)
    if CONFIGURED_BOOTSTRAP_ADMIN_PASSWORD:
        candidates.add(CONFIGURED_BOOTSTRAP_ADMIN_PASSWORD)
    return any(verify_password(candidate, user.password) for candidate in candidates)


def requires_password_change(user: User) -> bool:
    return bool(getattr(user, "must_change_password", False)) or is_using_bootstrap_password(user)


def validate_password_strength(password: str) -> Optional[str]:
    """Return an error message when a password is too weak."""
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if password.lower() in KNOWN_DEFAULT_PASSWORDS:
        return "This password is a well-known default and cannot be used."
    return None


def resolve_bootstrap_password() -> Tuple[str, bool]:
    """
    Password for a newly created bootstrap admin.

    Returns ``(password, generated)``. The configured ``DEFAULT_ADMIN_PASSWORD`` is used
    only when it passes the password policy; otherwise a random one is generated so a
    fresh install never exposes a guessable admin account.
    """
    configured = CONFIGURED_BOOTSTRAP_ADMIN_PASSWORD
    if configured and validate_password_strength(configured) is None:
        return configured, False
    if configured:
        print("WARNING: DEFAULT_ADMIN_PASSWORD is too weak; generating a random bootstrap password instead.", flush=True)
    return secrets.token_urlsafe(18), True

def init_auth():
    """Initialize authentication system"""
    # Import azure_auth here to avoid circular import issues
    import azure_auth
    
    # Initialize Azure AD authentication
    azure_auth.init_azure_auth()
    
    # Check if we have Azure authentication in the URL
    azure_auth.check_azure_auth_params()
    
    # Use session_scope for better transaction management
    with session_scope() as session:
        if not session:
            st.error("Unable to connect to database. Please try again later.")
            return
            
        # Create the bootstrap admin user if it doesn't exist.
        admin_exists = session.query(User).filter(User.username == DEFAULT_BOOTSTRAP_ADMIN_USERNAME).first()
        
        if not admin_exists:
            bootstrap_password, generated = resolve_bootstrap_password()
            # The bootstrap password is always temporary.
            admin_user = User(
                username=DEFAULT_BOOTSTRAP_ADMIN_USERNAME,
                password=hash_password(bootstrap_password),
                role="admin",
                must_change_password=True,
            )
            session.add(admin_user)
            
            # Create default settings for admin
            default_settings = Settings(
                user=admin_user,
                llm_provider="openai",
                ai_character="assistant",
                openai_api_key="",
                openai_model=DEFAULT_OPENAI_MODEL,
                claude_api_key="",
                claude_model=DEFAULT_CLAUDE_MODEL,
                gemini_api_key="",
                gemini_model=DEFAULT_GEMINI_MODEL,
                serpapi_key="",
                local_model_path="",
                scan_enabled=True,
                scan_level="standard",
                auto_anonymize=True,
                disable_scan_for_local_model=True,
                custom_patterns=[]
            )
            session.add(default_settings)
            
            if generated:
                # Server log only: this code runs before login, so nothing secret may be
                # rendered in the page.
                print(
                    "\n" + "=" * 72
                    + f"\nBootstrap admin account created: {DEFAULT_BOOTSTRAP_ADMIN_USERNAME}"
                    + f"\nTemporary password: {bootstrap_password}"
                    + "\nYou will be asked to change it after the first login."
                    + "\n" + "=" * 72 + "\n",
                    flush=True,
                )
            st.sidebar.warning(
                f"Bootstrap admin '{DEFAULT_BOOTSTRAP_ADMIN_USERNAME}' created. "
                "Its temporary password is in the server log (or DEFAULT_ADMIN_PASSWORD)."
            )

# hash_password is now imported from utils_auth.py

def authenticate(username, password):
    """Authenticate a user"""
    if not username or not password:
        return False, None, None
    
    try:
        with session_scope() as session:
            user = session.query(User).filter(User.username == username).first()
            
            if not user:
                return False, None, None
                
            if verify_password(password, user.password):
                if is_legacy_sha256_hash(user.password):
                    user.password = hash_password(password)

                # Store user info in session state
                st.session_state.user_info = {
                    "user_id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "exp": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                    "must_change_password": requires_password_change(user)
                }
                
                return True, user.id, user.role
    except Exception as e:
        print(f"Authentication error: {str(e)}")
    
    return False, None, None

def create_user(username, password, role="user", allow_when_registration_disabled: bool = False, must_change_password: bool = False):
    """Create a new user"""
    if not username or not password:
        return False

    if role == "user" and not ALLOW_SELF_REGISTRATION and not allow_when_registration_disabled:
        return False

    password_error = validate_password_strength(password)
    if password_error:
        return False
    
    # First, check if MS DLP columns exist in the database
    # If not, run the migration script
    try:
        # Check if DLP columns exist
        with session_scope() as session:
            import sqlalchemy as sa
            from sqlalchemy import inspect
            
            # Get the table inspector
            inspector = inspect(session.bind)
            
            # Check if Settings table exists
            if 'settings' in inspector.get_table_names():
                # Get column names
                columns = [column['name'] for column in inspector.get_columns('settings')]
                
                # If DLP columns don't exist, run the migration
                if 'enable_ms_dlp' not in columns or 'ms_dlp_sensitivity_threshold' not in columns:
                    # Import and run the migration
                    from migration_add_dlp_columns import run_migration
                    run_migration()
                
                # Check if local LLM columns exist
                if ('local_model_context_size' not in columns or 
                    'local_model_gpu_layers' not in columns or 
                    'local_model_temperature' not in columns):
                    # Import and run the migration
                    from migration_add_local_llm_columns import run_migration
                    run_migration()
    except Exception as e:
        print(f"Error checking/running migrations: {str(e)}")
        # Continue anyway, as we'll catch any remaining issues in the user creation step
    
    # Now create the user
    try:
        with session_scope() as session:
            # Check if user already exists
            existing_user = session.query(User).filter(User.username == username).first()
            if existing_user:
                return False
            
            # Create new user
            new_user = User(
                username=username,
                password=hash_password(password),
                role=role,
                must_change_password=must_change_password,
            )
            session.add(new_user)
            session.flush()  # Flush to get the user ID
            
            # Create settings dictionary with all required fields
            settings_dict = {
                "llm_provider": "openai",
                "ai_character": "assistant",
                "openai_api_key": "",
                "openai_model": DEFAULT_OPENAI_MODEL,
                "claude_api_key": "",
                "claude_model": DEFAULT_CLAUDE_MODEL,
                "gemini_api_key": "",
                "gemini_model": DEFAULT_GEMINI_MODEL,
                "serpapi_key": "",
                "local_model_path": "",
                "scan_enabled": True,
                "scan_level": "standard",
                "auto_anonymize": True,
                "disable_scan_for_local_model": True,
                "custom_patterns": []
            }
            
            # Add MS DLP settings if columns exist
            try:
                inspector = inspect(session.bind)
                columns = [column['name'] for column in inspector.get_columns('settings')]
                
                if 'enable_ms_dlp' in columns:
                    settings_dict["enable_ms_dlp"] = True
                    
                if 'ms_dlp_sensitivity_threshold' in columns:
                    settings_dict["ms_dlp_sensitivity_threshold"] = "confidential"
                    
                if 'local_model_context_size' in columns:
                    settings_dict["local_model_context_size"] = 2048
                    
                if 'local_model_gpu_layers' in columns:
                    settings_dict["local_model_gpu_layers"] = -1
                    
                if 'local_model_temperature' in columns:
                    settings_dict["local_model_temperature"] = 0.7
            except Exception as e:
                print(f"Error checking columns for Settings: {str(e)}")
                # Continue anyway, we'll use what we have
            
            # Create and add settings
            default_settings = Settings(**settings_dict)
            new_user.settings = default_settings
            session.add(default_settings)
            
            return True
    except IntegrityError:
        # Log error but don't need to rollback as session_scope handles it
        print("Error creating user: Username already exists or other integrity error")
        return False
    except Exception as e:
        print(f"Error creating user: {str(e)}")
        return False

def get_users():
    """Get all users"""
    try:
        with session_scope() as session:
            users = session.query(User).all()
            
            # Create list of dictionaries with user data to avoid detached instance errors
            user_list = []
            for user in users:
                user_dict = {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "created_at": user.created_at,
                    "azure_id": user.azure_id if hasattr(user, 'azure_id') else None,
                    "azure_name": user.azure_name if hasattr(user, 'azure_name') else None
                }
                user_list.append(user_dict)
            
            return user_list
    except Exception as e:
        print(f"Error retrieving users: {str(e)}")
        return []

def delete_user(user_id):
    """Delete a user"""
    with session_scope() as session:
        user = session.query(User).filter(User.id == user_id).first()
        
        if user:
            session.delete(user)
            return True
        
        return False

def update_user_role(user_id, new_role):
    """Update a user's role"""
    with session_scope() as session:
        user = session.query(User).filter(User.id == user_id).first()
        
        if user:
            user.role = new_role
            return True
        
        return False
        
def update_user_password(user_id, new_password, require_change: bool = False):
    """Update a user's password.

    ``require_change`` marks the new password as temporary (an administrator reset),
    so the user must choose their own at next login.
    """
    if not user_id or not new_password:
        return False

    password_error = validate_password_strength(new_password)
    if password_error:
        return False
    
    with session_scope() as session:
        user = session.query(User).filter(User.id == user_id).first()
        
        if user:
            user.password = hash_password(new_password)
            user.must_change_password = require_change
            return True
        
        return False
