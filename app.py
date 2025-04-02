import streamlit as st

# Set up page configuration - must be the first Streamlit command
st.set_page_config(
    page_title="PrivacyChatBoX",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Import and apply custom CSS
from style import apply_custom_css
apply_custom_css()

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
        # Add a nice logo/icon at the top
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image("https://img.icons8.com/fluency/96/privacy.png", width=80)
            st.title("PrivacyChatBoX")
            st.caption("Secure AI Assistant with Privacy Protection")
            
        # Create fancy tabs with icons
        st.markdown("""
        <style>
        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0;
            background-color: #f0f8ff;
            border-radius: 10px 10px 0 0;
            padding: 5px;
        }
        
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px 8px 0 0;
            border: none;
            padding: 10px 16px;
            font-weight: 600;
            font-size: 15px;
            background-color: transparent;
            color: #555;
        }
        
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            background-color: white;
            border-bottom: 3px solid #1E88E5;
            color: #1E88E5;
        }
        
        /* Tab content area */
        .stTabs [data-baseweb="tab-panel"] {
            background-color: white;
            border-radius: 0 0 10px 10px;
            padding: 20px;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
        }
        
        /* Fancy login button */
        button[kind="primaryFormSubmit"] {
            width: 100%;
            height: 50px;
            font-size: 16px;
            font-weight: 600;
            border-radius: 8px;
            background: linear-gradient(90deg, #1E88E5 0%, #42a5f5 100%);
            border: none;
            margin-top: 10px;
            transition: all 0.3s ease;
        }
        
        button[kind="primaryFormSubmit"]:hover {
            background: linear-gradient(90deg, #1565C0 0%, #1E88E5 100%);
            box-shadow: 0 5px 15px rgba(30, 136, 229, 0.3);
            transform: translateY(-2px);
        }
        
        /* Register button */
        #register_button {
            background: linear-gradient(90deg, #66BB6A 0%, #81c784 100%);
        }
        
        #register_button:hover {
            background: linear-gradient(90deg, #43A047 0%, #66BB6A 100%);
            box-shadow: 0 5px 15px rgba(102, 187, 106, 0.3);
        }
        
        /* Form fields */
        [data-testid="stTextInput"] > div:first-child {
            background-color: #f8fafe;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
            padding: 5px;
            box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Create tabs with emoji icons
        login_tab, register_tab = st.tabs(["👤 Login", "📝 Register"])
        
        with login_tab:
            login_container = st.container()
            with login_container:
                st.header("Welcome Back!")
                st.write("Sign in to access your secure AI assistant")
                
                login_username = st.text_input(
                    "Username", 
                    key="login_username",
                    placeholder="Enter your username"
                )
                
                login_password = st.text_input(
                    "Password", 
                    type="password", 
                    key="login_password",
                    placeholder="Enter your password"
                )
                
                login_button = st.button(
                    "🔐 Sign In", 
                    key="login_button",
                    use_container_width=True
                )
                
                if login_button:
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
            register_container = st.container()
            with register_container:
                st.header("Create Account")
                st.write("Join PrivacyChatBoX to access all privacy-focused AI features")
                
                reg_username = st.text_input(
                    "Choose a Username", 
                    key="reg_username",
                    placeholder="Enter a unique username"
                )
                
                reg_password = st.text_input(
                    "Create Password", 
                    type="password", 
                    key="reg_password",
                    placeholder="Create a secure password"
                )
                
                reg_password_confirm = st.text_input(
                    "Confirm Password", 
                    type="password", 
                    key="reg_password_confirm",
                    placeholder="Confirm your password"
                )
                
                register_button = st.button(
                    "✅ Create Account", 
                    key="register_button",
                    use_container_width=True
                )
                
                if register_button:
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
        st.image("https://img.icons8.com/fluency/96/privacy.png", width=60)
        st.title("PrivacyChatBoX")
        st.caption(f"Welcome, **{st.session_state.username}** ({st.session_state.role})")
        
        st.markdown("---")
        
        # Create a container with a colored background and rounded corners for the navigation menu
        menu_container = st.container()
        with menu_container:
            # Create a grid layout for the menu items
            button_style = """
            <style>
            div[data-testid="stVerticalBlock"] div.stButton > button {
                width: 100%;
                border: none;
                padding: 15px 15px; 
                text-align: left;
                font-size: 16px;
                font-weight: 500;
                border-radius: 10px;
                margin-bottom: 8px;
                display: flex;
                align-items: center;
                background-color: #f0f8ff;
            }
            div[data-testid="stVerticalBlock"] div.stButton > button:hover {
                background-color: #e1f5fe;
                border-left: 4px solid #1e88e5;
            }
            </style>
            """
            st.markdown(button_style, unsafe_allow_html=True)
            
            # Add menu buttons with prominent icons and colored backgrounds
            menu_options = {
                "chat": {"icon": "💬", "label": "Chat", "path": "pages/chat.py", "color": "#e3f2fd"},
                "history": {"icon": "📜", "label": "History", "path": "pages/history.py", "color": "#e8f5e9"},
                "settings": {"icon": "⚙️", "label": "Settings", "path": "pages/settings.py", "color": "#fafafa"}
            }
            
            # Admin-only options
            if st.session_state.role == "admin":
                menu_options["admin"] = {"icon": "👑", "label": "Admin Panel", "path": "pages/admin.py", "color": "#f3e5f5"}
                menu_options["analytics"] = {"icon": "📊", "label": "Analytics", "path": "pages/analytics.py", "color": "#fff3e0"}
            
            # Create buttons for each menu option
            for key, option in menu_options.items():
                col1, col2 = st.columns([1, 5])
                with col1:
                    st.markdown(f'<div style="font-size:24px; text-align:center">{option["icon"]}</div>', unsafe_allow_html=True)
                with col2:
                    if st.button(option["label"], key=f"btn_{key}", use_container_width=True):
                        st.switch_page(option["path"])
        
        # Add spacer
        st.markdown("<br>" * 3, unsafe_allow_html=True)
        
        # Add theme toggle and logout buttons at the bottom
        theme_col, logout_col = st.columns(2)
        
        with theme_col:
            if st.button("🌙 Theme", key="theme_toggle", help="Toggle dark/light mode"):
                toggle_dark_mode()
        
        with logout_col:
            if st.button("🚪 Logout", key="logout_button", help="Log out"):
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
    # Welcome dashboard for authenticated users
    st.title(f"Welcome back, {st.session_state.username}!")
    st.write("### Please select an option from the sidebar menu")
    
    st.info("👈 Use the sidebar navigation on the left to access different features.")
    
    # Quick access cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("💬 **Chat**")
        st.write("Start a new conversation with AI")
        if st.button("Open Chat", key="home_chat_btn"):
            st.switch_page("pages/chat.py")
    
    with col2:
        st.info("📜 **History**") 
        st.write("View your past conversations")
        if st.button("Open History", key="home_history_btn"):
            st.switch_page("pages/history.py")
    
    with col3:
        st.info("⚙️ **Settings**")
        st.write("Configure your AI and privacy settings")
        if st.button("Open Settings", key="home_settings_btn"):
            st.switch_page("pages/settings.py")

# Footer
st.markdown("---")
st.markdown("PrivacyChatBoX © 2025 | Secure AI Communication")
