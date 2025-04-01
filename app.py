import streamlit as st
from datetime import datetime
import os
import uuid
import pandas as pd
import importlib

# Import custom modules
from auth import authenticate, create_user, get_users, init_auth
from database import init_db, get_session
from models import User, Settings, DetectionEvent, Conversation, Message, File
from privacy_scanner import scan_text, anonymize_text
from ai_providers import get_ai_response, get_available_models
from utils import save_uploaded_file

# Initialize the database
init_db()

# Set up page configuration
st.set_page_config(
    page_title="PrivacyChatBoX",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state variables if they don't exist
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "role" not in st.session_state:
    st.session_state.role = None
if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None
if "conversations" not in st.session_state:
    st.session_state.conversations = []
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

# Initialize authentication
init_auth()

# Define function to toggle dark mode
def toggle_dark_mode():
    st.session_state.dark_mode = not st.session_state.dark_mode
    # Use st.rerun() to apply changes
    st.rerun()

# Sidebar for navigation and authentication
with st.sidebar:
    st.title("🔒 PrivacyChatBoX")
    st.caption("AI-powered privacy protection")
    
    # Show login form if not authenticated
    if not st.session_state.authenticated:
        login_tab, register_tab = st.tabs(["Login", "Register"])
        
        with login_tab:
            st.subheader("Login")
            login_username = st.text_input("Username", key="login_username")
            login_password = st.text_input("Password", type="password", key="login_password")
            
            if st.button("Login", key="login_button"):
                success, user_id, role = authenticate(login_username, login_password)
                if success:
                    st.session_state.authenticated = True
                    st.session_state.username = login_username
                    st.session_state.user_id = user_id
                    st.session_state.role = role
                    st.success(f"Welcome back, {login_username}!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        
        with register_tab:
            st.subheader("Register")
            reg_username = st.text_input("Username", key="reg_username")
            reg_password = st.text_input("Password", type="password", key="reg_password")
            reg_password_confirm = st.text_input("Confirm Password", type="password", key="reg_password_confirm")
            
            if st.button("Register", key="register_button"):
                if not reg_username or not reg_password:
                    st.error("Username and password are required")
                elif reg_password != reg_password_confirm:
                    st.error("Passwords do not match")
                else:
                    success = create_user(reg_username, reg_password, role="user")
                    if success:
                        st.success("Registration successful! You can now login.")
                    else:
                        st.error("Username already exists")
    
    # Show navigation menu if authenticated
    else:
        st.write(f"Logged in as: **{st.session_state.username}**")
        
        st.markdown("### Navigation")
        
        if st.button("💬 Chat", use_container_width=True):
            st.switch_page("pages/chat.py")
            
        if st.button("📜 History", use_container_width=True):
            st.switch_page("pages/history.py")
            
        if st.button("⚙️ Settings", use_container_width=True):
            st.switch_page("pages/settings.py")
            
        # Only show admin panel for admin users
        if st.session_state.role == "admin":
            if st.button("👑 Admin Panel", use_container_width=True):
                st.switch_page("pages/admin.py")
        
        if st.button("Toggle Dark/Light Mode"):
            toggle_dark_mode()
            
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

# Main content area
if not st.session_state.authenticated:
    # Landing page for non-authenticated users
    st.title("Welcome to PrivacyChatBoX")
    st.write("### AI-powered privacy protection platform")
    
    st.markdown("""
    PrivacyChatBoX is an intelligent privacy protection platform that safeguards your sensitive information 
    when interacting with AI models. Our platform scans and anonymizes confidential data before sending it to AI services.

    ### Key Features:
    - 🔒 Privacy scanning for sensitive information
    - 🔄 Automatic anonymization 
    - 🤖 Multiple AI model integrations (OpenAI, Claude, Gemini)
    - 📁 Support for multiple file formats
    - 📊 Comprehensive logging
    - 📑 PDF export capabilities

    Please log in or register to get started.
    """)
    
    # Show feature columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.header("🔍 Privacy Scanning")
        st.write("Detect sensitive information like credit card numbers, SSNs, and more using advanced pattern matching.")
    
    with col2:
        st.header("🤖 Multiple AI Models")
        st.write("Use your preferred AI model from OpenAI, Anthropic Claude, Google Gemini, or local LLMs.")
    
    with col3:
        st.header("🔄 Anonymization")
        st.write("Automatically replace or mask detected sensitive information before sending to AI models.")

else:
    # Try to import chat dynamically to avoid import errors
    try:
        # Import the pages.chat module dynamically
        chat_module = importlib.import_module("pages.chat")
        chat_module.show()
    except Exception as e:
        st.error(f"Error loading chat module: {str(e)}")
        st.info("Please navigate to chat using the sidebar.")

# Footer
st.markdown("---")
st.markdown("PrivacyChatBoX © 2025 | Secure AI Communication")
