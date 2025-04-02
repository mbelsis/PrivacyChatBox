import streamlit as st

# Set up page configuration - must be the first Streamlit command
st.set_page_config(
    page_title="PrivacyChatBoX",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
        # Enhanced Login/Register form styling
        st.markdown("""
        <style>
        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px;
            background-color: #f8f9fa;
            border-radius: 10px 10px 0 0;
            padding: 10px 10px 0 10px;
        }
        
        body.dark .stTabs [data-baseweb="tab-list"] {
            background-color: #2d3035;
        }
        
        .stTabs [data-baseweb="tab"] {
            border-radius: 5px 5px 0 0;
            border: none;
            padding: 10px 16px;
            background-color: transparent;
            font-weight: 500;
            font-size: 14px;
            color: #555;
        }
        
        body.dark .stTabs [data-baseweb="tab"] {
            color: #ccc;
        }
        
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            background-color: white;
            color: #1E88E5;
            border-bottom: 2px solid #1E88E5;
        }
        
        body.dark .stTabs [data-baseweb="tab"][aria-selected="true"] {
            background-color: #3d4045;
            color: #81D4FA;
            border-bottom: 2px solid #81D4FA;
        }
        
        /* Tab content area */
        .stTabs [data-baseweb="tab-panel"] {
            background-color: white;
            border-radius: 0 0 10px 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        body.dark .stTabs [data-baseweb="tab-panel"] {
            background-color: #3d4045;
        }
        
        /* Form fields */
        .login-form-container .stTextInput > div > div {
            background-color: #f5f7f9;
            border-radius: 8px;
            border: 1px solid #dfe3e7;
        }
        
        body.dark .login-form-container .stTextInput > div > div {
            background-color: #40444b;
            border: 1px solid #4e5359;
        }
        
        /* Submit buttons */
        .login-form-container .stButton > button {
            background-color: #1E88E5;
            color: white;
            border-radius: 20px;
            padding: 8px 24px;
            font-weight: 500;
            border: none;
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
        }
        
        .login-form-container .stButton > button:hover {
            background-color: #1565C0;
            transform: none;
            border-left: none;
        }
        
        /* Register form button */
        #register_button {
            background-color: #66BB6A;
        }
        
        #register_button:hover {
            background-color: #43A047;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Login and register tabs styled
        login_tab, register_tab = st.tabs(["🔑 Login", "✏️ Register"])
        
        with login_tab:
            st.markdown("<div class='login-form-container'>", unsafe_allow_html=True)
            st.subheader("Welcome Back!")
            st.markdown("Enter your credentials to access your account.")
            
            login_username = st.text_input("Username", key="login_username", 
                                          placeholder="Enter your username")
            login_password = st.text_input("Password", type="password", key="login_password",
                                         placeholder="Enter your password")
            
            if st.button("🔐 Sign In", key="login_button"):
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
            st.markdown("</div>", unsafe_allow_html=True)
        
        with register_tab:
            st.markdown("<div class='login-form-container'>", unsafe_allow_html=True)
            st.subheader("Create an Account")
            st.markdown("Join PrivacyChatBoX to access all features.")
            
            reg_username = st.text_input("Choose a Username", key="reg_username",
                                       placeholder="Enter a unique username")
            reg_password = st.text_input("Create Password", type="password", key="reg_password",
                                       placeholder="Create a secure password")
            reg_password_confirm = st.text_input("Confirm Password", type="password", key="reg_password_confirm",
                                               placeholder="Confirm your password")
            
            if st.button("✅ Create Account", key="register_button"):
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
            st.markdown("</div>", unsafe_allow_html=True)
    
    # Show navigation menu if authenticated
    else:
        # Create an app-like interface with completely new layout
        st.markdown("""
        <style>
        /* New modern sidebar style */
        section.main div.block-container {
            padding-top: 1rem;
        }
        
        [data-testid="stSidebar"] {
            padding-top: 0;
            background-color: #f8f9fa;
        }
        
        .dark-mode [data-testid="stSidebar"] {
            background-color: #1e1e2e;
        }
        
        /* Custom navigation menu */
        .nav-container {
            margin: -1rem -1rem 0 -1rem;
            background-color: #4285F4;
            color: white;
            padding: 1.5rem 1rem 1rem 1rem;
            border-radius: 0 0 20px 20px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }
        
        .dark-mode .nav-container {
            background-color: #3949ab;
        }
        
        .logo-area {
            display: flex;
            align-items: center;
            margin-bottom: 1.2rem;
        }
        
        .app-logo {
            font-size: 22px;
            font-weight: 700;
            margin-left: 10px;
        }
        
        .app-version {
            font-size: 12px;
            opacity: 0.7;
            margin-left: 5px;
        }
        
        .user-area {
            display: flex;
            align-items: center;
            background-color: rgba(255, 255, 255, 0.15);
            padding: 10px;
            border-radius: 12px;
            margin-bottom: 1.5rem;
        }
        
        .user-avatar {
            width: 42px;
            height: 42px;
            background-color: white;
            color: #4285F4;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 18px;
            margin-right: 12px;
        }
        
        .dark-mode .user-avatar {
            color: #3949ab;
        }
        
        .user-details {
            flex-grow: 1;
        }
        
        .user-name {
            font-weight: 600;
            font-size: 16px;
            margin-bottom: 2px;
        }
        
        .user-role {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            opacity: 0.8;
        }
        
        /* New menu buttons style */
        .menu-section {
            margin: 0 -1rem;
            padding: 0 1rem;
        }
        
        .menu-title {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #555;
            margin: 20px 0 10px 15px;
            font-weight: 600;
        }
        
        .dark-mode .menu-title {
            color: #a0a0a0;
        }
        
        .menu-button {
            display: block; /* Not flex, block worked better with Streamlit structure */
            background-color: transparent;
            color: #333;
            border: none;
            padding: 14px 15px;
            margin-bottom: 5px;
            border-radius: 10px;
            transition: all 0.2s ease;
            text-decoration: none;
            cursor: pointer;
            text-align: left;
            width: 100%;
        }
        
        .dark-mode .menu-button {
            color: #e5e5e5;
        }
        
        .menu-button:hover {
            background-color: rgba(66, 133, 244, 0.1);
        }
        
        .dark-mode .menu-button:hover {
            background-color: rgba(97, 130, 237, 0.2);
        }
        
        .menu-button.active {
            background-color: rgba(66, 133, 244, 0.15);
            color: #4285F4;
            font-weight: 500;
        }
        
        .dark-mode .menu-button.active {
            background-color: rgba(97, 130, 237, 0.25);
            color: #8ab4f8;
        }
        
        .menu-icon {
            display: inline-block;
            width: 24px;
            text-align: center;
            margin-right: 12px;
        }
        
        /* Adjusting regular buttons to use the new style */
        .menu-section button {
            width: 100%;
            border: none;
            background-color: transparent;
            text-align: left;
            margin-bottom: 5px;
            border-radius: 10px;
            transition: all 0.2s ease;
            padding: 14px 15px;
            font-weight: normal;
            display: flex;
            align-items: center;
        }
        
        .menu-section button span {
            margin-left: 12px;
        }
        
        .menu-section button:hover {
            background-color: rgba(66, 133, 244, 0.1);
        }
        
        .dark-mode .menu-section button:hover {
            background-color: rgba(97, 130, 237, 0.2);
        }
        
        /* Admin section styling */
        .admin-section {
            margin-top: 20px;
        }
        
        .admin-section .menu-title {
            color: #9333ea;
        }
        
        .dark-mode .admin-section .menu-title {
            color: #c084fc;
        }
        
        .admin-button {
            background: linear-gradient(135deg, rgba(147, 51, 234, 0.05), rgba(192, 132, 252, 0.05));
        }
        
        .admin-button:hover {
            background: linear-gradient(135deg, rgba(147, 51, 234, 0.1), rgba(192, 132, 252, 0.1));
        }
        
        /* Special button styling for theme toggle and logout */
        .footer-section {
            position: absolute;
            bottom: 20px;
            left: 0;
            width: 100%;
            padding: 0 1rem;
        }
        
        .footer-button {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background-color: #f0f2f5;
            color: #555;
            border: none;
            border-radius: 10px;
            padding: 10px 15px;
            width: 48%;
            margin: 0 1% 0 0;
            transition: all 0.2s ease;
            cursor: pointer;
        }
        
        .dark-mode .footer-button {
            background-color: #2d3035;
            color: #d0d0d0;
        }
        
        .footer-button:hover {
            background-color: #e5e7eb;
        }
        
        .dark-mode .footer-button:hover {
            background-color: #3d4045;
        }
        
        .footer-button.danger {
            color: #ef4444;
        }
        
        .footer-button.danger:hover {
            background-color: rgba(239, 68, 68, 0.1);
        }
        
        .dark-mode .footer-button.danger:hover {
            background-color: rgba(239, 68, 68, 0.15);
        }
        
        </style>
        """, unsafe_allow_html=True)
        
        # New Top Menu Bar with user profile
        st.markdown("""
        <div class="nav-container">
            <div class="logo-area">
                <span style="font-size: 24px;">🔒</span>
                <span class="app-logo">PrivacyChatBoX</span>
                <span class="app-version">v2.0</span>
            </div>
        """, unsafe_allow_html=True)
        
        # User profile in the header
        user_initial = st.session_state.username[0].upper() if st.session_state.username else "U"
        role_display = "Administrator" if st.session_state.role == "admin" else "User"
        
        st.markdown(f"""
            <div class="user-area">
                <div class="user-avatar">{user_initial}</div>
                <div class="user-details">
                    <div class="user-name">{st.session_state.username}</div>
                    <div class="user-role">{role_display}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Main navigation section
        st.markdown("""
        <div class="menu-section">
            <div class="menu-title">Main Navigation</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Use custom styling for buttons with icons in spans
        chat_button = st.button("💬 Chat", key="chat_btn", use_container_width=True)
        if chat_button:
            st.switch_page("pages/chat.py")
        
        history_button = st.button("📜 History", key="history_btn", use_container_width=True)
        if history_button:
            st.switch_page("pages/history.py")
        
        settings_button = st.button("⚙️ Settings", key="settings_btn", use_container_width=True)
        if settings_button:
            st.switch_page("pages/settings.py")
            
        # Admin section with special styling
        if st.session_state.role == "admin":
            st.markdown("""
            <div class="admin-section">
                <div class="menu-title">Admin Tools</div>
            </div>
            """, unsafe_allow_html=True)
            
            admin_button = st.button("👑 Admin Panel", key="admin_btn", use_container_width=True)
            if admin_button:
                st.switch_page("pages/admin.py")
            
            analytics_button = st.button("📊 Analytics", key="analytics_btn", use_container_width=True) 
            if analytics_button:
                st.switch_page("pages/analytics.py")
        
        # Footer with theme and logout buttons using native Streamlit
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🌙 Toggle Theme", key="theme_btn"):
                toggle_dark_mode()
                
        with col2:
            if st.button("🚪 Logout", key="logout_btn"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
                
        # Add CSS to style these buttons
        st.markdown("""
        <style>
        /* Style the footer buttons */
        [data-testid="stHorizontalBlock"] button {
            background-color: #f0f2f5;
            color: #555;
            border: none;
            border-radius: 10px;
            transition: all 0.2s ease;
            margin-top: 30px;
        }
        
        [data-testid="stHorizontalBlock"] button:hover {
            background-color: #e5e7eb;
        }
        
        [data-testid="stHorizontalBlock"] [data-baseweb="column"]:nth-child(2) button {
            color: #ef4444;
        }
        
        [data-testid="stHorizontalBlock"] [data-baseweb="column"]:nth-child(2) button:hover {
            background-color: rgba(239, 68, 68, 0.1);
        }
        
        body.dark [data-testid="stHorizontalBlock"] button {
            background-color: #2d3035;
            color: #d0d0d0;
        }
        
        body.dark [data-testid="stHorizontalBlock"] button:hover {
            background-color: #3d4045;
        }
        
        body.dark [data-testid="stHorizontalBlock"] [data-baseweb="column"]:nth-child(2) button {
            color: #ff6b6b;
        }
        
        body.dark [data-testid="stHorizontalBlock"] [data-baseweb="column"]:nth-child(2) button:hover {
            background-color: rgba(239, 68, 68, 0.15);
        }
        </style>
        """, unsafe_allow_html=True)

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
    # Redirect to the chat page by switching pages
    st.switch_page("pages/chat.py")

# Footer
st.markdown("---")
st.markdown("PrivacyChatBoX © 2025 | Secure AI Communication")
