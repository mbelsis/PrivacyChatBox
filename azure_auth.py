import os
import json
import time
from typing import Dict, Optional, Tuple, Any
import msal
import requests
from jose import jwt
import uuid
import streamlit as st
from database import get_session, session_scope
from models import User, Settings
from utils_auth import hash_password

# Azure AD configuration
AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "")
AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID", "")
AZURE_REDIRECT_URI = os.environ.get("AZURE_REDIRECT_URI", "http://localhost:5000/")

# App endpoints
AUTHORITY = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}"
ENDPOINT = "https://graph.microsoft.com/v1.0/me"

def init_azure_auth():
    """Initialize the Azure AD authentication"""
    # Initialize session state
    if "azure_auth_state" not in st.session_state:
        st.session_state.azure_auth_state = str(uuid.uuid4())
    
    if "azure_token_cache" not in st.session_state:
        st.session_state.azure_token_cache = None

def get_msal_app():
    """Get MSAL application instance"""
    return msal.ConfidentialClientApplication(
        AZURE_CLIENT_ID,
        authority=AUTHORITY,
        client_credential=AZURE_CLIENT_SECRET,
        token_cache=st.session_state.azure_token_cache
    )

def get_auth_url() -> str:
    """Get the Azure AD authorization URL"""
    app = get_msal_app()
    return app.get_authorization_request_url(
        ["User.Read"],
        state=st.session_state.azure_auth_state,
        redirect_uri=AZURE_REDIRECT_URI
    )

def process_auth_code(code: str, state: str) -> bool:
    """
    Process Azure AD authorization code
    
    Args:
        code: Authorization code from Azure AD
        state: State parameter to verify
        
    Returns:
        Boolean indicating success
    """
    # Verify state to prevent CSRF
    if state != st.session_state.azure_auth_state:
        return False
    
    app = get_msal_app()
    result = app.acquire_token_by_authorization_code(
        code,
        scopes=["User.Read"],
        redirect_uri=AZURE_REDIRECT_URI
    )
    
    if "error" in result:
        print(f"Error acquiring token: {result['error']}")
        return False
    
    # Save the token cache
    st.session_state.azure_token_cache = app.token_cache
    
    # Get user info
    return process_azure_user(result)

def process_azure_user(token_data: Dict[str, Any]) -> bool:
    """
    Process Azure AD user information and ensure they exist in our system
    
    Args:
        token_data: Token data with access token
        
    Returns:
        Boolean indicating success
    """
    access_token = token_data.get("access_token")
    if not access_token:
        return False
    
    # Get user profile from Microsoft Graph
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(ENDPOINT, headers=headers)
    
    if response.status_code != 200:
        print(f"Error getting user profile: {response.status_code}")
        print(response.text)
        return False
    
    user_data = response.json()
    
    # Extract user information
    email = user_data.get("userPrincipalName", "")
    name = user_data.get("displayName", "")
    user_id = user_data.get("id", "")
    
    if not email or not user_id:
        return False
    
    # Create or get user in our database
    create_or_get_azure_user(email, name, user_id)
    
    return True

def create_or_get_azure_user(email: str, display_name: str, azure_id: str) -> Tuple[int, str]:
    """
    Create or get a user in our database based on Azure AD information
    
    Args:
        email: User email from Azure AD
        display_name: Display name from Azure AD
        azure_id: Azure AD user ID
        
    Returns:
        Tuple with user ID and role
    """
    # Use session_scope for better transaction management
    user_id = -1
    user_role = ""
    
    # Add columns if they don't exist
    from sqlalchemy import Column, String
    if not hasattr(User, 'azure_id'):
        User.azure_id = Column(String, unique=True, index=True, nullable=True)
    if not hasattr(User, 'azure_name'):
        User.azure_name = Column(String, nullable=True)
    
    try:
        with session_scope() as session:
            if not session:
                st.error("Unable to connect to database. Please try again later.")
                return -1, ""
                
            # Try to find user by Azure ID
            user = session.query(User).filter(User.azure_id == azure_id).first()
            
            if user:
                # User exists
                user_id = user.id
                user_role = user.role
            else:
                # Check if user exists by email used as username
                user = session.query(User).filter(User.username == email).first()
                
                if user:
                    # User exists but doesn't have Azure ID, update it
                    user.azure_id = azure_id
                    user.azure_name = display_name
                    user_id = user.id
                    user_role = user.role
                else:
                    # Create new user
                    # Generate a random password for the user
                    temp_password = str(uuid.uuid4())
                    
                    user = User(
                        username=email,
                        password=hash_password(temp_password),
                        role="user",  # Default role for Azure AD users
                        azure_id=azure_id,
                        azure_name=display_name
                    )
                    
                    session.add(user)
                    session.flush()  # Flush to get the ID without committing yet
                    
                    # Create default settings for the user
                    settings = Settings(user_id=user.id)
                    session.add(settings)
                    
                    user_id = user.id
                    user_role = user.role
            
            # Commit changes
            session.commit()
            
            # Set authentication in session state (outside the with block to avoid detached instance errors)
            if user_id > 0:
                st.session_state.authenticated = True
                st.session_state.username = email
                st.session_state.user_id = user_id
                st.session_state.role = user_role
                st.session_state.azure_user = True
    
    except Exception as e:
        st.error(f"Error creating or getting Azure user: {e}")
        return -1, ""
    
    return user_id, user_role

def check_azure_auth_params():
    """Check if Azure AD auth parameters are set in URL"""
    query_params = st.query_params
    
    code = query_params.get("code", [None])[0]
    state = query_params.get("state", [None])[0]
    
    if code and state:
        success = process_auth_code(code, state)
        
        # Clear URL parameters
        st.query_params.clear()
        
        return success
    
    return False

def show_azure_login_button():
    """Display Azure AD login button"""
    if not all([AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID]):
        st.info("Azure AD integration is configured but missing credentials. Please contact your administrator.")
        return
    
    auth_url = get_auth_url()
    
    st.markdown(
        f"""
        <div style="margin-top: 20px; text-align: center;">
            <a href="{auth_url}" target="_self" style="display: inline-block; padding: 12px 20px; background-color: #0078d4; color: white; text-decoration: none; border-radius: 4px; font-weight: 600;">
                <img src="https://learn.microsoft.com/en-us/azure/active-directory/develop/media/common/microsoft-logo.png" style="height: 20px; vertical-align: middle; margin-right: 10px;" />
                Sign in with Microsoft
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )

def add_azure_id_column():
    """Add Azure ID column to User table if it doesn't exist"""
    # This functionality has been moved to create_or_get_azure_user
    # to ensure proper transaction handling
    pass