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
        # Add custom CSS for beautiful sidebar design
        st.markdown("""
        <style>
        /* Sidebar menu styling */
        .menu-container {
            background-color: #f8f9fa;
            border-radius: 10px;
            padding: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .dark-mode .menu-container {
            background-color: #2d3035;
            color: #ffffff;
        }
        
        .menu-header {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
            background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
            padding: 10px;
            border-radius: 8px;
            color: white;
        }
        
        .nav-button {
            display: flex;
            align-items: center;
            background-color: #ffffff;
            padding: 10px 15px;
            border-radius: 8px;
            margin-bottom: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            transition: all 0.2s ease;
            color: #333;
            text-decoration: none;
            border-left: 4px solid transparent;
        }
        
        .dark-mode .nav-button {
            background-color: #40444b;
            color: #ffffff;
        }
        
        .nav-button:hover {
            transform: translateX(5px);
            border-left: 4px solid #4285F4;
            background-color: #f0f5ff;
        }
        
        .dark-mode .nav-button:hover {
            background-color: #4e5359;
        }
        
        .nav-icon {
            font-size: 18px;
            margin-right: 10px;
            width: 24px;
            text-align: center;
        }
        
        .nav-text {
            font-size: 16px;
            font-weight: 500;
        }
        
        .active-nav {
            background-color: #e8f0fe;
            border-left: 4px solid #4285F4;
        }
        
        .dark-mode .active-nav {
            background-color: #4e5359;
            border-left: 4px solid #4285F4;
        }
        
        .user-profile {
            display: flex;
            align-items: center;
            background-color: #f0f2f5;
            padding: 10px;
            border-radius: 8px;
            margin: 15px 0;
        }
        
        .dark-mode .user-profile {
            background-color: #40444b;
        }
        
        .user-avatar {
            background-color: #4285F4;
            color: white;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            margin-right: 10px;
        }
        
        .user-info {
            display: flex;
            flex-direction: column;
        }
        
        .user-name {
            font-weight: bold;
            color: #333;
        }
        
        .dark-mode .user-name {
            color: #ffffff;
        }
        
        .user-role {
            font-size: 12px;
            color: #666;
        }
        
        .dark-mode .user-role {
            color: #cccccc;
        }
        
        .footer-button {
            background-color: transparent;
            border: 1px solid #ddd;
            padding: 8px 15px;
            border-radius: 20px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            margin-right: 8px;
            color: #555;
            transition: all 0.2s ease;
        }
        
        .dark-mode .footer-button {
            border-color: #555;
            color: #ccc;
        }
        
        .footer-button:hover {
            background-color: #f5f5f5;
            color: #333;
        }
        
        .dark-mode .footer-button:hover {
            background-color: #444;
            color: #fff;
        }
        
        .logout-button {
            background-color: #ff4b4b;
            color: white;
            border: none;
        }
        
        .dark-mode .logout-button {
            background-color: #d32f2f;
        }
        
        .logout-button:hover {
            background-color: #d32f2f;
            color: white;
        }

        .admin-section {
            border-top: 1px solid #eee;
            margin-top: 10px;
            padding-top: 10px;
        }
        
        .dark-mode .admin-section {
            border-top-color: #444;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # User profile section
        user_initial = st.session_state.username[0].upper() if st.session_state.username else "U"
        role_display = "Administrator" if st.session_state.role == "admin" else "User"
        
        st.markdown(f"""
        <div class="user-profile">
            <div class="user-avatar">{user_initial}</div>
            <div class="user-info">
                <span class="user-name">{st.session_state.username}</span>
                <span class="user-role">{role_display}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Navigation menu container
        st.markdown("""
        <div class="menu-container">
            <div class="menu-header">
                <span style="margin-right: 10px;">📱</span>
                <span>Main Navigation</span>
            </div>
        """, unsafe_allow_html=True)
        
        # Custom styles for the navigation buttons to make them look modern
        st.markdown("""
        <style>
        /* Override default Streamlit button styling */
        .stButton > button {
            width: 100%;
            border: none;
            background-color: white;
            color: #333;
            text-align: left;
            padding: 10px 15px;
            margin-bottom: 8px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            transition: all 0.2s ease;
            border-left: 4px solid transparent;
            font-weight: 500;
        }
        
        .stButton > button:hover {
            transform: translateX(5px);
            border-left: 4px solid #4285F4;
            background-color: #f0f5ff;
        }
        
        /* Dark mode button styles */
        body.dark .stButton > button {
            background-color: #40444b;
            color: #ffffff;
        }
        
        body.dark .stButton > button:hover {
            background-color: #4e5359;
        }
        
        /* Admin section styling */
        .admin-section-header {
            margin-top: 20px;
            margin-bottom: 10px;
            padding: 10px;
            background: linear-gradient(90deg, #6a3093 0%, #a044ff 100%);
            border-radius: 8px;
            color: white;
            font-weight: 500;
            display: flex;
            align-items: center;
        }
        
        /* Footer button styling */
        .footer-buttons .stButton > button {
            background-color: transparent;
            border: 1px solid #ddd;
            border-radius: 20px;
            color: #555;
            margin-right: 5px;
            width: auto;
            font-size: 14px;
            display: inline-flex;
            justify-content: center;
        }
        
        body.dark .footer-buttons .stButton > button {
            border-color: #555;
            color: #ccc;
        }
        
        .footer-buttons .stButton > button:hover {
            background-color: #f5f5f5;
            color: #333;
            transform: none;
            border-left: 1px solid #ddd;
        }
        
        body.dark .footer-buttons .stButton > button:hover {
            background-color: #444;
            color: #fff;
        }
        
        /* Logout button special styling */
        .logout-button .stButton > button {
            color: #ff4b4b;
            border-color: #ff4b4b;
        }
        
        .logout-button .stButton > button:hover {
            background-color: #ff4b4b;
            color: white;
        }
        
        body.dark .logout-button .stButton > button {
            color: #ff6b6b;
            border-color: #ff6b6b;
        }
        
        body.dark .logout-button .stButton > button:hover {
            background-color: #d32f2f;
            color: white;
        }
        
        /* Icon styling for buttons */
        .nav-label {
            display: flex;
            align-items: center;
            width: 100%;
        }
        
        .icon-wrapper {
            margin-right: 10px;
            width: 24px;
            text-align: center;
            font-size: 16px;
        }
        
        .label-text {
            flex-grow: 1;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Main Navigation Buttons
        if st.button(
            "💬 Chat", 
            key="chat_button",
            help="Go to chat interface"
        ):
            st.switch_page("pages/chat.py")
            
        if st.button(
            "📜 History", 
            key="history_button",
            help="View conversation history"
        ):
            st.switch_page("pages/history.py")
            
        if st.button(
            "⚙️ Settings", 
            key="settings_button",
            help="Configure application settings"
        ):
            st.switch_page("pages/settings.py")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Admin section for admin users
        if st.session_state.role == "admin":
            st.markdown("""
            <div class="admin-section-header">
                <span style="margin-right: 10px;">👑</span>
                <span>Admin Tools</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Admin navigation
            if st.button(
                "🔧 Admin Panel", 
                key="admin_button",
                help="Administrative controls"
            ):
                st.switch_page("pages/admin.py")
                
            if st.button(
                "📊 Analytics Dashboard", 
                key="analytics_button",
                help="View usage statistics and trends"
            ):
                st.switch_page("pages/analytics.py")
                
        # Footer buttons styled differently
        st.markdown("<div class='footer-buttons'>", unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("🌙 Theme", key="theme_toggle", help="Toggle between dark and light mode"):
                toggle_dark_mode()
        
        with col2:
            st.markdown("<div class='logout-button'>", unsafe_allow_html=True)
            if st.button("🚪 Logout", key="logout_button", help="Log out of your account"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True)

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
