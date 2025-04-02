import streamlit as st

def apply_custom_css():
    """Apply custom CSS styling to hide the default Streamlit menu and apply other styling"""
    
    st.markdown("""
    <style>
        /* Hide hamburger menu */
        button[kind="header"] {
            display: none !important;
        }
        
        /* Hide header decoration */
        .stApp > header {
            background-color: transparent;
            display: none !important;
        }
        
        /* Remove top padding from sidebar */
        section[data-testid="stSidebar"] > div.css-1oe6ov4.e1fqkh3o3 {
            padding-top: 0.5rem;
        }
        
        /* Hide only the default Streamlit navigation, not the sidebar itself */
        div[data-testid="stSidebarNav"] {
            display: none !important;
        }
    </style>
    """, unsafe_allow_html=True)