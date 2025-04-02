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
        
        /* Fix sidebar width to prevent trembling */
        section[data-testid="stSidebar"] {
            width: 280px !important;
            min-width: 280px !important;
            max-width: 280px !important;
        }
        
        /* Ensure the sidebar content doesn't cause width fluctuations */
        section[data-testid="stSidebar"] > div {
            width: 280px !important;
        }
        
        /* Make sidebar buttons more stable */
        div.stButton > button {
            transition: background-color 0.3s, border-left 0.3s !important;
            transform: translateZ(0);
            backface-visibility: hidden;
        }
    </style>
    """, unsafe_allow_html=True)