import streamlit as st

def apply_custom_css():
    """Apply custom CSS styling to hide the default Streamlit menu and apply other styling"""
    
    st.markdown("""
    <style>
        /* Hide only default menu elements, not the entire sidebar */
        div[data-testid="stSidebarNav"] {
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
        
        /* Remove top padding from sidebar but don't hide it */
        section[data-testid="stSidebar"] > div {
            padding-top: 0.5rem;
        }
        
        /* Hide default navigation while keeping the sidebar itself visible */
        .stApp ul.css-eczf16,
        .stApp button[kind="icon"] {
            display: none !important;
        }
        
        /* Ensure menu items in sidebar have proper top margin */
        section[data-testid="stSidebar"] div.block-container {
            padding-top: 1rem !important;
        }
        
        /* Make sure sidebar is always visible */
        section[data-testid="stSidebar"] {
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
            height: auto !important;
            width: auto !important;
            transform: none !important;
        }
    </style>
    """, unsafe_allow_html=True)