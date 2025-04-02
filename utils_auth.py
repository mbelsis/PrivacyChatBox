import hashlib
import streamlit as st
from typing import Optional, Dict, Any

def hash_password(password):
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_session() -> Optional[Dict[str, Any]]:
    """
    Check if a user is logged in and return their info
    
    Returns:
        Dict with user info if authenticated, None otherwise
    """
    if not st.session_state.get("authenticated", False):
        return None
    
    # Return user info
    return {
        "id": st.session_state.get("user_id"),
        "username": st.session_state.get("username"),
        "role": st.session_state.get("role")
    }