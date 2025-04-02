import streamlit as st

def apply_custom_css():
    """Apply custom CSS styling to hide the default Streamlit menu and apply other styling"""
    
    # Apply basic styles that hide default Streamlit UI elements
    base_styles = """
    <style>
        /* Hide hamburger menu more aggressively */
        button[kind="header"],
        .stApp header button,
        header button[data-testid="stApp"] {
            display: none !important;
            opacity: 0 !important;
            visibility: hidden !important;
        }
        
        /* Hide header decoration */
        .stApp > header,
        header[data-testid="stHeader"] {
            background-color: transparent !important;
            display: none !important;
            height: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        
        /* Remove top padding from sidebar */
        section[data-testid="stSidebar"] > div {
            padding-top: 0.5rem !important;
        }
        
        /* Hide default Streamlit navigation menu */
        div[data-testid="stSidebarNav"],
        [data-testid="stSidebarNav"] {
            display: none !important;
            opacity: 0 !important;
            visibility: hidden !important;
            height: 0 !important;
            width: 0 !important;
            position: absolute !important;
            overflow: hidden !important;
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
    """
    
    st.markdown(base_styles, unsafe_allow_html=True)
    
    # Apply dark mode styles if enabled in session state
    if st.session_state.get("dark_mode", False):
        dark_mode_styles = """
        <style>
            /* Dark mode colors */
            .stApp {
                background-color: #121212 !important;
                color: #f5f5f5 !important;
            }
            
            /* Sidebar background */
            [data-testid="stSidebar"] {
                background-color: #1e1e1e !important;
                border-right: 1px solid #333 !important;
            }
            
            /* Headings */
            h1, h2, h3, h4, h5, h6 {
                color: #e0e0e0 !important;
            }
            
            /* Sidebar buttons */
            div[data-testid="stVerticalBlock"] div.stButton > button {
                background-color: #2d2d2d !important;
                color: #e0e0e0 !important;
            }
            
            div[data-testid="stVerticalBlock"] div.stButton > button:hover {
                background-color: #3d3d3d !important;
                border-left: 4px solid #64b5f6 !important;
            }
            
            /* Text inputs */
            .stTextInput > div > div > input {
                background-color: #2d2d2d !important;
                color: #e0e0e0 !important;
                border: 1px solid #444 !important;
            }
            
            /* Text area */
            .stTextArea > div > div > textarea {
                background-color: #2d2d2d !important;
                color: #e0e0e0 !important;
                border: 1px solid #444 !important;
            }
            
            /* Selectbox */
            .stSelectbox > div > div {
                background-color: #2d2d2d !important;
                color: #e0e0e0 !important;
                border: 1px solid #444 !important;
            }
            
            /* Cards and containers */
            [data-testid="stExpander"] {
                background-color: #1e1e1e !important;
                border: 1px solid #333 !important;
            }
            
            /* Info boxes */
            .element-container .stAlert {
                background-color: #1e1e1e !important;
                color: #e0e0e0 !important;
                border: 1px solid #444 !important;
            }
            
            /* Success boxes */
            .element-container .stAlert.success {
                background-color: rgba(76, 175, 80, 0.1) !important;
                border-left-color: #4CAF50 !important;
            }
            
            /* Info boxes */
            .element-container .stAlert.info {
                background-color: rgba(33, 150, 243, 0.1) !important;
                border-left-color: #2196F3 !important;
            }
            
            /* Warning boxes */
            .element-container .stAlert.warning {
                background-color: rgba(255, 152, 0, 0.1) !important;
                border-left-color: #FF9800 !important;
            }
            
            /* Error boxes */
            .element-container .stAlert.error {
                background-color: rgba(244, 67, 54, 0.1) !important;
                border-left-color: #F44336 !important;
            }
            
            /* Tabs */
            .stTabs [data-baseweb="tab-list"] {
                background-color: #1e1e1e !important;
            }
            
            .stTabs [data-baseweb="tab"] {
                color: #e0e0e0 !important;
            }
            
            .stTabs [data-baseweb="tab"][aria-selected="true"] {
                background-color: #2d2d2d !important;
                color: #64b5f6 !important;
            }
            
            .stTabs [data-baseweb="tab-panel"] {
                background-color: #1e1e1e !important;
            }
            
            /* Dataframes */
            .stDataFrame {
                background-color: #1e1e1e !important;
            }
            
            .stDataFrame [data-testid="stTable"] {
                background-color: #2d2d2d !important;
                color: #e0e0e0 !important;
            }
            
            /* Code blocks */
            .stCodeBlock {
                background-color: #2d2d2d !important;
            }
            
            /* Caption text */
            .caption {
                color: #bdbdbd !important;
            }
        </style>
        """
        st.markdown(dark_mode_styles, unsafe_allow_html=True)