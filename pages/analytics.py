import streamlit as st

def show():
    """Minimalist analytics page to ensure it loads without errors"""
    st.title("Analytics Dashboard")
    
    # Simple message about maintenance
    st.info("The analytics page is currently under maintenance to fix technical issues.")
    
    # Add some placeholder content
    st.write("We're working to resolve issues with database access on this page.")
    
    # Add a navigation button to go back to the home page
    if st.button("Return to Home Page"):
        st.switch_page("app.py")