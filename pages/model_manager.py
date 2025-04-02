"""
Local LLM Model Management Page
This page allows users to download, upload, and manage local language models
"""

import os
import streamlit as st
from typing import Dict, Any, Optional, Tuple

import database
from models import User, Settings
import model_utils
import test_local_llm
from shared_sidebar import create_sidebar
from utils_auth import check_session

def show():
    """Main function to display the model manager interface"""
    # Apply custom styling and sidebar
    create_sidebar("model_manager")
    
    # Check authentication
    user_info = check_session()
    if not user_info:
        st.warning("Please log in to access this page.")
        return
    
    user_id = user_info["id"]
    
    # Get user settings
    user_settings = None
    with database.session_scope() as session:
        user = session.query(User).filter(User.id == user_id).first()
        if user and user.settings:
            user_settings = user.settings
    
    # Main content
    st.title("Model Manager")
    
    # Tabs for different sections
    tab1, tab2, tab3 = st.tabs(["Download & Manage Models", "Model Testing", "Configuration"])
    
    # Tab 1: Model download and management
    with tab1:
        selected_model = model_utils.show_model_download_ui()
        
        # If a model was selected, update settings
        if selected_model:
            with database.session_scope() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if user and user.settings:
                    user.settings.local_model_path = selected_model
                    st.success(f"Local model path updated to: {selected_model}")
                else:
                    st.error("Could not update settings. Please try again.")
    
    # Tab 2: Model testing
    with tab2:
        st.header("Test Local Model")
        
        if not user_settings or not user_settings.local_model_path:
            st.warning("No local model configured. Please select a model in the Download & Manage Models tab.")
        else:
            model_path = user_settings.local_model_path
            if not os.path.exists(model_path):
                st.error(f"Model file not found at {model_path}. Please select a valid model.")
            else:
                st.write(f"Currently configured model: **{os.path.basename(model_path)}**")
                
                # Test form
                with st.form("test_model_form"):
                    prompt = st.text_area("Enter prompt for testing", 
                                          value="Tell me about privacy in AI systems", 
                                          height=100)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        context_size = st.number_input("Context size", 
                                                      min_value=512, 
                                                      max_value=16384,
                                                      value=user_settings.local_model_context_size if user_settings.local_model_context_size else 2048,
                                                      step=512)
                    
                    with col2:
                        gpu_layers = st.number_input("GPU layers (-1 for all)", 
                                                   min_value=-1, 
                                                   max_value=100,
                                                   value=user_settings.local_model_gpu_layers if user_settings.local_model_gpu_layers else -1,
                                                   step=1)
                    
                    submit = st.form_submit_button("Test Model")
                
                if submit:
                    with st.spinner("Running model test - this might take a minute..."):
                        try:
                            result = test_local_llm.test_local_model(
                                model_path=model_path,
                                prompt=prompt,
                                n_ctx=context_size,
                                n_gpu_layers=gpu_layers
                            )
                            
                            if result:
                                st.success("Model test completed successfully!")
                                st.subheader("Generated Output:")
                                st.markdown(result)
                            else:
                                st.error("Model test failed. Check the logs for details.")
                        except Exception as e:
                            st.error(f"Error testing model: {str(e)}")
    
    # Tab 3: Configuration
    with tab3:
        st.header("Local LLM Configuration")
        
        if not user_settings:
            st.warning("User settings not found. Please log out and log back in.")
        else:
            with st.form("llm_config_form"):
                context_size = st.number_input("Default context window size", 
                                             min_value=512, 
                                             max_value=16384,
                                             value=user_settings.local_model_context_size if user_settings.local_model_context_size else 2048,
                                             step=512,
                                             help="Larger values allow processing more text but use more memory")
                
                gpu_layers = st.number_input("GPU layers to offload", 
                                          min_value=-1, 
                                          max_value=100,
                                          value=user_settings.local_model_gpu_layers if user_settings.local_model_gpu_layers else -1,
                                          step=1,
                                          help="-1 means use all available GPU layers")
                
                temperature = st.slider("Temperature", 
                                      min_value=0.0, 
                                      max_value=2.0,
                                      value=user_settings.local_model_temperature if user_settings.local_model_temperature else 0.7,
                                      step=0.05,
                                      help="Higher values make output more random, lower values more deterministic")
                
                bypass_privacy = st.checkbox("Bypass privacy scanning for local models", 
                                         value=user_settings.disable_scan_for_local_model if user_settings.disable_scan_for_local_model is not None else True,
                                         help="Since local models process data entirely on your device, you may choose to bypass privacy scanning")
                
                submit_config = st.form_submit_button("Save Configuration")
            
            if submit_config:
                with database.session_scope() as session:
                    user = session.query(User).filter(User.id == user_id).first()
                    if user and user.settings:
                        user.settings.local_model_context_size = context_size
                        user.settings.local_model_gpu_layers = gpu_layers
                        user.settings.local_model_temperature = temperature
                        user.settings.disable_scan_for_local_model = bypass_privacy
                        
                        st.success("Local LLM configuration saved successfully!")
                    else:
                        st.error("Could not update settings. Please try again.")