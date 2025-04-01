import streamlit as st
import hashlib
import os
from datetime import datetime, timedelta
import jwt
from database import get_session
from models import User, Settings
from sqlalchemy.exc import IntegrityError

# Secret key for JWT token generation
JWT_SECRET = os.environ.get("JWT_SECRET", "default_secret_key")
JWT_EXPIRY_DAYS = 30

def init_auth():
    """Initialize authentication system"""
    # Create admin user if it doesn't exist
    session = get_session()
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
        finally:
            session.close()

def hash_password(password):
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate(username, password):
    """Authenticate a user"""
    if not username or not password:
        return False, None, None
    
    session = get_session()
    user = session.query(User).filter(User.username == username).first()
    
    if user and user.password == hash_password(password):
        # Generate JWT token and store in session
        token = generate_jwt_token(user.id, user.username, user.role)
        st.session_state.token = token
        
        return True, user.id, user.role
    
    return False, None, None

def create_user(username, password, role="user"):
    """Create a new user"""
    if not username or not password:
        return False
    
    session = get_session()
    
    # Check if username already exists
    existing_user = session.query(User).filter(User.username == username).first()
    if existing_user:
        session.close()
        return False
    
    # Create new user
    new_user = User(
        username=username,
        password=hash_password(password),
        role=role
    )
    session.add(new_user)
    
    # Create default settings for the user
    default_settings = Settings(
        user=new_user,
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
        return True
    except IntegrityError:
        session.rollback()
        return False
    finally:
        session.close()

def get_users():
    """Get all users"""
    session = get_session()
    users = session.query(User).all()
    session.close()
    return users

def delete_user(user_id):
    """Delete a user"""
    session = get_session()
    user = session.query(User).filter(User.id == user_id).first()
    
    if user:
        session.delete(user)
        session.commit()
        session.close()
        return True
    
    session.close()
    return False

def update_user_role(user_id, new_role):
    """Update a user's role"""
    session = get_session()
    user = session.query(User).filter(User.id == user_id).first()
    
    if user:
        user.role = new_role
        session.commit()
        session.close()
        return True
    
    session.close()
    return False

def generate_jwt_token(user_id, username, role):
    """Generate a JWT token for the user"""
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(days=JWT_EXPIRY_DAYS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_jwt_token(token):
    """Verify a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return True, payload
    except jwt.ExpiredSignatureError:
        return False, "Token expired"
    except jwt.InvalidTokenError:
        return False, "Invalid token"
