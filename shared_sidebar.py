import streamlit as st

def create_sidebar(page_name=""):
    """
    Create a consistent sidebar for all pages
    
    Args:
        page_name: Optional identifier for the current page to create unique button keys
    """
    # Fixed width CSS to prevent sidebar trembling
    fixed_width_css = """
    <style>
    section[data-testid="stSidebar"] {
        width: 18rem !important;
        min-width: 18rem !important;
        max-width: 18rem !important;
        transition: none !important;
    }
    </style>
    """
    st.markdown(fixed_width_css, unsafe_allow_html=True)
    
    # Create a container for the sidebar with fixed width styling
    with st.sidebar:
        # Only show logo in sidebar for authenticated users to avoid duplication
        if st.session_state.get("authenticated", False):
            # Apply button styles
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
                transition: none !important;
            }
            div[data-testid="stVerticalBlock"] div.stButton > button:hover {
                background-color: #e1f5fe;
                border-left: 4px solid #1e88e5;
            }
            .sidebar-content {
                padding-top: 1rem;
                padding-bottom: 1rem;
            }
            </style>
            """
            st.markdown(button_style, unsafe_allow_html=True)
            
            # Center the logo horizontally and make it bigger
            col1, col2, col3 = st.columns([1, 3, 1])
            with col2:
                st.image("assets/logo.png", width=160)
            # Title already included in the logo
            st.markdown(f"<div style='text-align:center; margin-bottom:10px;'>Welcome, <b>{st.session_state.username}</b> ({st.session_state.role})</div>", unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Create a container with a colored background and rounded corners for the navigation menu
            # Use a specific height to prevent content shifting
            menu_container = st.container()
            with menu_container:
                # Add menu buttons with prominent icons and colored backgrounds
                menu_options = {
                    "chat": {"icon": "💬", "label": "Chat", "path": "pages/chat.py", "color": "#e3f2fd"},
                    "history": {"icon": "📜", "label": "History", "path": "pages/history.py", "color": "#e8f5e9"},
                    "settings": {"icon": "⚙️", "label": "Settings", "path": "pages/settings.py", "color": "#fafafa"},
                    "models": {"icon": "🤖", "label": "Model Manager", "path": "pages/model_manager.py", "color": "#ede7f6"},
                    "home": {"icon": "🏠", "label": "Home", "path": "app.py", "color": "#e0f7fa"}
                }
                
                # Admin-only options
                if st.session_state.get("role", "") == "admin":
                    menu_options["admin"] = {"icon": "👑", "label": "Admin Panel", "path": "pages/admin.py", "color": "#f3e5f5"}
                else:
                    # Remove Model Manager option for non-admin users
                    if "models" in menu_options:
                        del menu_options["models"]
                
                # Create buttons for each menu option - with consistent widths
                for key, option in menu_options.items():
                    # Use unique keys for each page to ensure they don't conflict
                    button_key = f"btn_{key}_{page_name}"
                    col1, col2 = st.columns([1, 5])
                    with col1:
                        st.markdown(f'<div style="font-size:24px; text-align:center">{option["icon"]}</div>', unsafe_allow_html=True)
                    with col2:
                        if st.button(option["label"], key=button_key, use_container_width=True):
                            st.switch_page(option["path"])
            
            # Use a fixed height spacer instead of variable <br> tags
            st.markdown('<div style="height:100px"></div>', unsafe_allow_html=True)
            
            # Add theme toggle and logout buttons at the bottom with improved styling
            st.markdown('<div style="position:fixed; bottom:30px; width:16rem;">', unsafe_allow_html=True)
            theme_col, logout_col = st.columns(2)
            
            with theme_col:
                theme_key = f"theme_toggle_{page_name}"
                # Choose icon based on current theme
                icon = "☀️" if st.session_state.get("dark_mode", False) else "🌙"
                button_text = f"{icon} Theme"
                tooltip = "Switch to Light Mode" if st.session_state.get("dark_mode", False) else "Switch to Dark Mode"
                
                if st.button(button_text, key=theme_key, help=tooltip):
                    try:
                        # Import toggle_dark_mode function from app.py
                        from app import toggle_dark_mode
                        toggle_dark_mode()
                    except:
                        st.session_state.dark_mode = not st.session_state.get("dark_mode", False)
                        st.rerun()
            
            with logout_col:
                logout_key = f"logout_button_{page_name}"
                if st.button("🚪 Logout", key=logout_key, help="Log out"):
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)