import streamlit as st

def create_sidebar(page_name=""):
    """
    Create a consistent sidebar for all pages
    
    Args:
        page_name: Optional identifier for the current page to create unique button keys
    """
    # Create a container for the sidebar with fixed width styling
    with st.sidebar:
        # Only show logo in sidebar for authenticated users to avoid duplication
        if st.session_state.get("authenticated", False):
            # Center the logo horizontally and make it bigger
            col1, col2, col3 = st.columns([1, 3, 1])
            with col2:
                st.image("assets/logo.png", width=160)
            # Title already included in the logo
            st.caption(f"Welcome, **{st.session_state.username}** ({st.session_state.role})")
            
            st.markdown("---")
            
            # Create a container with a colored background and rounded corners for the navigation menu
            menu_container = st.container()
            with menu_container:
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
                    transition: all 0.2s ease-in-out;
                    transform: translateZ(0);
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
                    "settings": {"icon": "⚙️", "label": "Settings", "path": "pages/settings.py", "color": "#fafafa"},
                    "home": {"icon": "🏠", "label": "Home", "path": "app.py", "color": "#e0f7fa"}
                }
                
                # Admin-only options
                if st.session_state.get("role", "") == "admin":
                    menu_options["admin"] = {"icon": "👑", "label": "Admin Panel", "path": "pages/admin.py", "color": "#f3e5f5"}
                
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
            
            # Add spacer
            st.markdown("<br>" * 3, unsafe_allow_html=True)
            
            # Add theme toggle and logout buttons at the bottom
            theme_col, logout_col = st.columns(2)
            
            with theme_col:
                theme_key = f"theme_toggle_{page_name}"
                if st.button("🌙 Theme", key=theme_key, help="Toggle dark/light mode"):
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