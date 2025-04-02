import streamlit as st
from style import apply_custom_css

# Apply custom CSS to hide default menu
apply_custom_css()
import json

# Import custom modules
from database import get_session
from models import Settings
from ai_providers import get_available_models
from utils import update_user_settings
from privacy_scanner import STANDARD_PATTERNS, STRICT_PATTERNS
import shared_sidebar

def show():
    """Main function to display the settings interface"""
    # Clear sidebar state for fresh creation
    if "sidebar_created" in st.session_state:
        del st.session_state.sidebar_created
    
    # Create sidebar with shared component
    shared_sidebar.create_sidebar("settings_page")
    
    # Page settings
    st.title("⚙️ Settings")
    
    # Get user information
    user_id = st.session_state.user_id
    if not user_id:
        st.error("You must be logged in to access this page.")
        return
    
    # Get user settings
    session = get_session()
    settings = session.query(Settings).filter(Settings.user_id == user_id).first()
    session.close()
    
    if not settings:
        st.error("User settings not found. Please contact an administrator.")
        return
    
    # Create tabs for different settings categories
    ai_tab, privacy_tab, custom_tab = st.tabs(["AI Models", "Privacy Settings", "Custom Patterns"])
    
    # AI Models tab
    with ai_tab:
        st.subheader("AI Model Settings")
        
        # Select AI provider
        provider_options = {
            "openai": "OpenAI",
            "claude": "Anthropic Claude",
            "gemini": "Google Gemini",
            "local": "Local Model"
        }
        
        selected_provider = st.selectbox(
            "AI Provider",
            options=list(provider_options.keys()),
            format_func=lambda x: provider_options[x],
            index=list(provider_options.keys()).index(settings.llm_provider)
        )
        
        # Get available models for the selected provider
        available_models = get_available_models()
        
        # Select AI character
        character_options = {
            "assistant": "General Assistant",
            "privacy_expert": "Privacy Expert",
            "data_analyst": "Data Analyst",
            "programmer": "Programming Assistant"
        }
        
        selected_character = st.selectbox(
            "AI Character",
            options=list(character_options.keys()),
            format_func=lambda x: character_options[x],
            index=list(character_options.keys()).index(settings.ai_character) if settings.ai_character in character_options else 0
        )
        
        # Provider-specific settings
        if selected_provider == "openai":
            st.subheader("OpenAI Settings")
            
            openai_api_key = st.text_input(
                "OpenAI API Key", 
                value=settings.openai_api_key,
                type="password",
                help="Your OpenAI API key. Get one at https://platform.openai.com/account/api-keys"
            )
            
            openai_model = st.selectbox(
                "OpenAI Model",
                options=available_models["openai"],
                index=available_models["openai"].index(settings.openai_model) if settings.openai_model in available_models["openai"] else 0
            )
            
            # Update settings if Save button is clicked
            if st.button("Save OpenAI Settings"):
                success = update_user_settings(
                    user_id,
                    {
                        "llm_provider": selected_provider,
                        "ai_character": selected_character,
                        "openai_api_key": openai_api_key,
                        "openai_model": openai_model
                    }
                )
                
                if success:
                    st.success("OpenAI settings saved.")
                else:
                    st.error("Failed to save settings.")
        
        elif selected_provider == "claude":
            st.subheader("Claude Settings")
            
            claude_api_key = st.text_input(
                "Claude API Key", 
                value=settings.claude_api_key,
                type="password",
                help="Your Anthropic Claude API key. Get one at https://console.anthropic.com/account/keys"
            )
            
            claude_model = st.selectbox(
                "Claude Model",
                options=available_models["claude"],
                index=available_models["claude"].index(settings.claude_model) if settings.claude_model in available_models["claude"] else 0
            )
            
            # Update settings if Save button is clicked
            if st.button("Save Claude Settings"):
                success = update_user_settings(
                    user_id,
                    {
                        "llm_provider": selected_provider,
                        "ai_character": selected_character,
                        "claude_api_key": claude_api_key,
                        "claude_model": claude_model
                    }
                )
                
                if success:
                    st.success("Claude settings saved.")
                else:
                    st.error("Failed to save settings.")
        
        elif selected_provider == "gemini":
            st.subheader("Gemini Settings")
            
            gemini_api_key = st.text_input(
                "Gemini API Key", 
                value=settings.gemini_api_key,
                type="password",
                help="Your Google AI Studio API key. Get one at https://makersuite.google.com/app/apikey"
            )
            
            gemini_model = st.selectbox(
                "Gemini Model",
                options=available_models["gemini"],
                index=available_models["gemini"].index(settings.gemini_model) if settings.gemini_model in available_models["gemini"] else 0
            )
            
            # Update settings if Save button is clicked
            if st.button("Save Gemini Settings"):
                success = update_user_settings(
                    user_id,
                    {
                        "llm_provider": selected_provider,
                        "ai_character": selected_character,
                        "gemini_api_key": gemini_api_key,
                        "gemini_model": gemini_model
                    }
                )
                
                if success:
                    st.success("Gemini settings saved.")
                else:
                    st.error("Failed to save settings.")
        
        elif selected_provider == "local":
            st.subheader("Local Model Settings")
            
            local_model_path = st.text_input(
                "Local Model Path", 
                value=settings.local_model_path,
                help="Path to your local model or API endpoint"
            )
            
            # Update settings if Save button is clicked
            if st.button("Save Local Model Settings"):
                success = update_user_settings(
                    user_id,
                    {
                        "llm_provider": selected_provider,
                        "ai_character": selected_character,
                        "local_model_path": local_model_path
                    }
                )
                
                if success:
                    st.success("Local model settings saved.")
                else:
                    st.error("Failed to save settings.")
        
        # Search API settings
        st.subheader("Search API Settings (Optional)")
        
        serpapi_key = st.text_input(
            "SerpAPI Key", 
            value=settings.serpapi_key,
            type="password",
            help="Your SerpAPI key for web search capabilities"
        )
        
        if st.button("Save Search API Settings"):
            success = update_user_settings(
                user_id,
                {
                    "serpapi_key": serpapi_key
                }
            )
            
            if success:
                st.success("Search API settings saved.")
            else:
                st.error("Failed to save settings.")
    
    # Privacy Settings tab
    with privacy_tab:
        st.subheader("Privacy Settings")
        
        # Enable/disable scanning
        scan_enabled = st.toggle(
            "Enable Privacy Scanning", 
            value=settings.scan_enabled,
            help="Scan text for sensitive information before sending to AI models"
        )
        
        # Set scan level
        scan_level_options = {
            "standard": "Standard (Basic patterns)",
            "strict": "Strict (More comprehensive patterns)"
        }
        
        scan_level = st.selectbox(
            "Scan Level",
            options=list(scan_level_options.keys()),
            format_func=lambda x: scan_level_options[x],
            index=list(scan_level_options.keys()).index(settings.scan_level) if settings.scan_level in scan_level_options else 0,
            help="Select the thoroughness of the privacy scan"
        )
        
        # Show patterns included in each level
        if scan_level == "standard":
            st.info("Standard patterns include: " + ", ".join(STANDARD_PATTERNS.keys()))
        else:
            st.info("Strict patterns include: " + ", ".join(STRICT_PATTERNS.keys()))
        
        # Auto-anonymize option
        auto_anonymize = st.toggle(
            "Auto-Anonymize Detected Information", 
            value=settings.auto_anonymize,
            help="Automatically anonymize detected sensitive information"
        )
        
        # Disable scan for local models
        disable_scan_for_local_model = st.toggle(
            "Disable Scanning for Local Models", 
            value=settings.disable_scan_for_local_model,
            help="Skip privacy scanning when using local LLMs (data doesn't leave your machine)"
        )
        
        # Update settings if Save button is clicked
        if st.button("Save Privacy Settings"):
            success = update_user_settings(
                user_id,
                {
                    "scan_enabled": scan_enabled,
                    "scan_level": scan_level,
                    "auto_anonymize": auto_anonymize,
                    "disable_scan_for_local_model": disable_scan_for_local_model
                }
            )
            
            if success:
                st.success("Privacy settings saved.")
            else:
                st.error("Failed to save settings.")
    
    # Custom Patterns tab
    with custom_tab:
        st.subheader("Custom Regex Patterns")
        st.write("""
        Define custom regex patterns to detect sensitive information specific to your needs.
        Each pattern needs a name and a valid regex pattern.
        """)
        
        # Get existing custom patterns
        custom_patterns = settings.get_custom_patterns()
        
        # Initialize session state for patterns if it doesn't exist
        if "custom_patterns" not in st.session_state:
            st.session_state.custom_patterns = custom_patterns.copy() if custom_patterns else []
        
        # Function to add a new pattern
        def add_pattern():
            st.session_state.custom_patterns.append({"name": "", "pattern": ""})
        
        # Function to remove a pattern
        def remove_pattern(index):
            del st.session_state.custom_patterns[index]
        
        # Display existing patterns
        for i, pattern in enumerate(st.session_state.custom_patterns):
            col1, col2, col3 = st.columns([3, 6, 1])
            
            with col1:
                st.session_state.custom_patterns[i]["name"] = st.text_input(
                    "Pattern Name",
                    value=pattern["name"],
                    key=f"name_{i}"
                )
            
            with col2:
                st.session_state.custom_patterns[i]["pattern"] = st.text_input(
                    "Regex Pattern",
                    value=pattern["pattern"],
                    key=f"pattern_{i}"
                )
            
            with col3:
                st.button("🗑️", key=f"remove_{i}", on_click=remove_pattern, args=(i,))
        
        # Add new pattern button
        st.button("Add Pattern", on_click=add_pattern)
        
        # Example patterns
        with st.expander("Example Patterns"):
            st.write("""
            Here are some example regex patterns you can use:
            
            - Credit Card: `\\b(?:\\d{4}[ -]?){3}\\d{4}\\b`
            - SSN: `\\b\\d{3}[-]?\\d{2}[-]?\\d{4}\\b`
            - Email: `\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b`
            - Phone Number: `\\b(?:\\+\\d{1,3}[-\\.\\s]?)?\\(?\\d{3}\\)?[-\\.\\s]?\\d{3}[-\\.\\s]?\\d{4}\\b`
            - IP Address: `\\b\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\b`
            """)
        
        # Update settings if Save button is clicked
        if st.button("Save Custom Patterns"):
            # Validate patterns
            valid_patterns = []
            for pattern in st.session_state.custom_patterns:
                if pattern["name"] and pattern["pattern"]:
                    valid_patterns.append(pattern)
            
            success = update_user_settings(
                user_id,
                {
                    "custom_patterns": valid_patterns
                }
            )
            
            if success:
                st.success("Custom patterns saved.")
            else:
                st.error("Failed to save custom patterns.")

# If the file is run directly, show the settings interface
if __name__ == "__main__" or "show" not in locals():
    # Check if user is authenticated
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.error("You must be logged in to access this page.")
        st.stop()
    
    show()
