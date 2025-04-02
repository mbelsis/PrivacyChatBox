import streamlit as st

def apply_custom_css():
    """Apply custom CSS styling to hide the default Streamlit menu and apply other styling"""
    
    st.markdown("""
    <style>
        /* Hide default menu */
        section[data-testid="stSidebar"] > div.css-1oe6ov4.e1fqkh3o3 > div.css-1adrfps.e1fqkh3o2 > div.css-1qrvfrg.e1fqkh3o1 {
            display: none !important;
        }
        
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
        
        /* Hide default navigation items with fallback selectors */
        .stApp div[data-testid="stSidebarNav"], 
        .stApp ul.css-eczf16,
        .stApp button[kind="icon"],
        .stApp [data-testid="collapsedControl"] {
            display: none !important;
        }
        
        /* Ensure menu items in sidebar have proper top margin */
        section[data-testid="stSidebar"] div.block-container {
            padding-top: 1rem !important;
        }
    </style>
    """, unsafe_allow_html=True)