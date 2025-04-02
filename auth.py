import streamlit as st
import os
from datetime import datetime, timedelta
from database import get_session, session_scope
from models import User, Settings
from sqlalchemy.exc import IntegrityError
# Import hash_password from utils_auth instead
from utils_auth import hash_password

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
            
        # Create admin user if it doesn't exist
        admin_exists = session.query(User).filter(User.username == "admin").first()
        
        if not admin_exists:
            # Create admin user with default password "admin"
            admin_user = User(
                username="admin",
                password=hash_password("admin"),
                role="admin"
            )
            session.add(admin_user)
            
            # Create default settings for admin
            default_settings = Settings(
                user=admin_user,
                llm_provider="openai",
                ai_character="assistant",
                openai_api_key="",
                openai_model="gpt-4o",
                claude_api_key="",
                claude_model="claude-3-5-sonnet-20241022",
                gemini_api_key="",
                gemini_model="gemini-pro",
                serpapi_key="",
                local_model_path="",
                scan_enabled=True,
                scan_level="standard",
                auto_anonymize=True,
                disable_scan_for_local_model=True,
                custom_patterns=[]
            )
            session.add(default_settings)
            
            try:
                session.commit()
                st.sidebar.success("Admin user created with default password 'admin'")
            except IntegrityError:
                session.rollback()

# hash_password is now imported from utils_auth.py

def authenticate(username, password):
    """Authenticate a user"""
    if not username or not password:
        return False, None, None
    
    try:
        with session_scope() as session:
            user = session.query(User).filter(User.username == username).first()
            
            if user and user.password == hash_password(password):
                # Store user info in session state
                st.session_state.user_info = {
                    "user_id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "exp": (datetime.utcnow() + timedelta(days=30)).isoformat()
                }
                
                return True, user.id, user.role
    except Exception as e:
        print(f"Authentication error: {str(e)}")
    
    return False, None, None

def create_user(username, password, role="user"):
    """Create a new user"""
    if not username or not password:
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
                    session.close()
                    
                    # Import and run the migration
                    from migration_add_dlp_columns import run_migration
                    run_migration()
                
                # Check if local LLM columns exist
                if ('local_model_context_size' not in columns or 
                    'local_model_gpu_layers' not in columns or 
                    'local_model_temperature' not in columns):
                    session.close()
                    
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
                role=role
            )
            session.add(new_user)
            session.flush()  # Flush to get the user ID
            
            # Create settings dictionary with all required fields
            settings_dict = {
                "user_id": new_user.id,
                "llm_provider": "openai",
                "ai_character": "assistant",
                "openai_api_key": "",
                "openai_model": "gpt-4o",
                "claude_api_key": "",
                "claude_model": "claude-3-5-sonnet-20241022",
                "gemini_api_key": "",
                "gemini_model": "gemini-1.5-pro",
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
        
def update_user_password(user_id, new_password):
    """Update a user's password"""
    if not user_id or not new_password:
        return False
    
    with session_scope() as session:
        user = session.query(User).filter(User.id == user_id).first()
        
        if user:
            user.password = hash_password(new_password)
            return True
        
        return False
