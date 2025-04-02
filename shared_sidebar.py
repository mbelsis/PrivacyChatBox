import streamlit as st

def create_sidebar(page_name=""):
    """
    Create a consistent sidebar for all pages
    
    Args:
        page_name: Optional identifier for the current page to create unique button keys
    """
    # Simplified approach - always recreate the sidebar when requested
    # This avoids potential issues with session state management
    
    # Use a unique key for each page to avoid conflicts
    sidebar_key = f"sidebar_created_{page_name}_{st.session_state.get('username', 'guest')}"
    st.session_state[sidebar_key] = True
    with st.sidebar:
        st.image("assets/logo.png", width=120)
        # Title already included in the logo
        
        if st.session_state.authenticated:
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
                
                # Add home option
                menu_options["home"] = {"icon": "🏠", "label": "Home", "path": "app.py", "color": "#e0f7fa"}
                
                # Admin-only options
                if st.session_state.role == "admin":
                    menu_options["admin"] = {"icon": "👑", "label": "Admin Panel", "path": "pages/admin.py", "color": "#f3e5f5"}
                    # Temporarily display analytics as disabled
                    with st.sidebar:
                        st.markdown("📊 Analytics (Maintenance)")
                    # Removed problematic analytics page from navigation
                
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
                    try:
                        # Import toggle_dark_mode function from app.py
                        from app import toggle_dark_mode
                        toggle_dark_mode()
                    except:
                        st.session_state.dark_mode = not st.session_state.dark_mode
                        st.rerun()
            
            with logout_col:
                if st.button("🚪 Logout", key="logout_button", help="Log out"):
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()