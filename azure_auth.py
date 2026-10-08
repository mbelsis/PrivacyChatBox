import os
import json
import time
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any
import msal
import requests
from jose import jwt
import uuid
import html
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

# How long an OAuth ``state`` value stays valid.
AUTH_STATE_MAX_AGE_SECONDS = 600


def _state_signing_key() -> bytes:
    """Key used to sign the OAuth ``state`` parameter.

    A dedicated secret can be provided through ``AZURE_STATE_SECRET``; otherwise the
    client secret (which Azure login requires anyway) is used.
    """
    return (os.environ.get("AZURE_STATE_SECRET") or AZURE_CLIENT_SECRET or "").encode("utf-8")


def generate_auth_state(now: Optional[float] = None) -> str:
    """Create a self-validating, HMAC-signed CSRF ``state`` value.

    Streamlit allocates a fresh session (and therefore fresh ``session_state``) when the
    browser returns from the Microsoft login redirect, so a state stored only in
    ``session_state`` can never be matched. Signing the state makes it verifiable
    without server-side storage while still preventing CSRF/login-fixation.
    """
    timestamp = str(int(now if now is not None else time.time()))
    nonce = uuid.uuid4().hex
    payload = f"{timestamp}.{nonce}"
    signature = hmac.new(_state_signing_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def verify_auth_state(state: Optional[str], now: Optional[float] = None, max_age: int = AUTH_STATE_MAX_AGE_SECONDS) -> bool:
    """Validate a ``state`` produced by :func:`generate_auth_state`."""
    if not state:
        return False
    parts = state.split(".")
    if len(parts) != 3:
        return False
    timestamp, nonce, signature = parts
    payload = f"{timestamp}.{nonce}"
    expected = hmac.new(_state_signing_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return False
    try:
        issued_at = int(timestamp)
    except ValueError:
        return False
    current = now if now is not None else time.time()
    return 0 <= current - issued_at <= max_age


def init_azure_auth():
    """Initialize the Azure AD authentication"""
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
        state=generate_auth_state(),
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
    # Verify the signed state to prevent CSRF / login fixation
    if not verify_auth_state(state):
        print("Azure AD login rejected: invalid or expired state parameter")
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
    response = requests.get(ENDPOINT, headers=headers, timeout=15)
    
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
    created_user_id, _ = create_or_get_azure_user(email, name, user_id)
    
    return created_user_id > 0

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
            
            # Set authentication in session state (outside the with block to avoid detached instance errors)
            if user_id > 0:
                st.session_state.authenticated = True
                st.session_state.username = email
                st.session_state.user_id = user_id
                st.session_state.role = user_role
                st.session_state.azure_user = True
                st.session_state.must_change_password = False
                # Mirror the local login flow so session expiry applies to Azure users too.
                st.session_state.user_info = {
                    "user_id": user_id,
                    "username": email,
                    "role": user_role,
                    "exp": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                    "must_change_password": False,
                }
    
    except Exception as e:
        st.error(f"Error creating or getting Azure user: {e}")
        return -1, ""
    
    return user_id, user_role

def check_azure_auth_params():
    """Check if Azure AD auth parameters are set in URL"""
    query_params = st.query_params

    def get_query_param(name: str) -> Optional[str]:
        value = query_params.get(name)
        if isinstance(value, list):
            return value[0] if value else None
        return value

    code = get_query_param("code")
    state = get_query_param("state")
    
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
    safe_auth_url = html.escape(auth_url, quote=True)
    
    st.markdown(
        f"""
        <div style="margin-top: 20px; text-align: center;">
            <a href="{safe_auth_url}" target="_self" style="display: inline-block; padding: 12px 20px; background-color: #0078d4; color: white; text-decoration: none; border-radius: 4px; font-weight: 600;">
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
