import streamlit as st
from style import apply_custom_css
import os
import json

# Apply custom CSS to hide default menu
apply_custom_css()

# Import custom modules
from database import get_session
from models import Settings
from ai_providers import get_available_models
from utils import update_user_settings
from privacy_scanner import STANDARD_PATTERNS, STRICT_PATTERNS, DEFAULT_PATTERNS
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
    ai_tab, privacy_tab, custom_tab, config_tab = st.tabs([
        "AI Models", 
        "Privacy Settings", 
        "Custom Patterns",
        "Environment Config"
    ])
    
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
            
            # Use environment variable if available, otherwise show as empty
            env_openai_key = os.environ.get("OPENAI_API_KEY", "")
            openai_key_status = "Set in environment" if env_openai_key else "Not set"
            
            st.info(f"OpenAI API Key status: **{openai_key_status}**")
            st.markdown("""
            API keys are now stored in environment variables for enhanced security. 
            To set your API key, add it to your environment variables or .env file:
            ```
            OPENAI_API_KEY=your_key_here
            ```
            """)
            
            # Pass empty string to maintain compatibility with existing code
            openai_api_key = ""
            
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
            
            # Use environment variable if available, otherwise show as empty
            env_claude_key = os.environ.get("ANTHROPIC_API_KEY", "")
            claude_key_status = "Set in environment" if env_claude_key else "Not set"
            
            st.info(f"Claude API Key status: **{claude_key_status}**")
            st.markdown("""
            API keys are now stored in environment variables for enhanced security. 
            To set your API key, add it to your environment variables or .env file:
            ```
            ANTHROPIC_API_KEY=your_key_here
            ```
            """)
            
            # Pass empty string to maintain compatibility with existing code
            claude_api_key = ""
            
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
            
            # Use environment variable if available, otherwise show as empty
            env_gemini_key = os.environ.get("GOOGLE_API_KEY", "")
            gemini_key_status = "Set in environment" if env_gemini_key else "Not set"
            
            st.info(f"Gemini API Key status: **{gemini_key_status}**")
            st.markdown("""
            API keys are now stored in environment variables for enhanced security. 
            To set your API key, add it to your environment variables or .env file:
            ```
            GOOGLE_API_KEY=your_key_here
            ```
            """)
            
            # Pass empty string to maintain compatibility with existing code
            gemini_api_key = ""
            
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
            
            # Information about local model support
            st.info("""
            Local Model support allows you to use your own language models stored on this server.
            
            **Supported formats:**
            - GGUF format models (e.g., models downloaded from HuggingFace)
            
            **Recommended models:**
            - Llama-2-7b-chat.gguf
            - Mistral-7B-Instruct-v0.2.gguf
            - Phi-2.gguf  
            - Any other GGUF format model
            
            **Note:** The model file must be accessible from this server. For large models,
            ensure there is enough RAM and CPU/GPU resources available.
            """)
            
            local_model_path = st.text_input(
                "Local Model Path", 
                value=settings.local_model_path,
                help="Full path to your local GGUF model file"
            )
            
            # Additional settings
            col1, col2 = st.columns(2)
            
            with col1:
                st.checkbox(
                    "Disable privacy scanning for local model",
                    value=settings.disable_scan_for_local_model,
                    help="When enabled, privacy scanning is bypassed for queries to local models",
                    key="disable_scan_local"
                )
            
            with col2:
                st.checkbox(
                    "Auto-download model if not found",
                    value=False,
                    disabled=True,  # Placeholder for future functionality
                    help="Coming soon: Auto-download recommended models if not found",
                    key="auto_download"
                )
            
            # Help information for getting models
            with st.expander("How to get local models"):
                st.markdown("""
                ### Getting Started with Local Models
                
                1. **Download a GGUF model** from [HuggingFace](https://huggingface.co/models?pipeline_tag=text-generation&sort=downloads&search=gguf)
                
                2. **Copy the model file to this server** in a directory that's accessible to this application
                
                3. **Enter the full path to the model file** in the "Local Model Path" field above
                
                Popular models:
                - [Llama-2-7B-Chat-GGUF](https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF)
                - [Mistral-7B-Instruct-v0.2-GGUF](https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF)
                - [Phi-2-GGUF](https://huggingface.co/TheBloke/phi-2-GGUF)
                
                Remember to use the "q4_K_M" or "q5_K_M" quantization levels for a good balance of quality and performance.
                """)
            
            # Update settings if Save button is clicked
            if st.button("Save Local Model Settings"):
                success = update_user_settings(
                    user_id,
                    {
                        "llm_provider": selected_provider,
                        "ai_character": selected_character,
                        "local_model_path": local_model_path,
                        "disable_scan_for_local_model": st.session_state.disable_scan_local
                    }
                )
                
                if success:
                    st.success("Local model settings saved.")
                else:
                    st.error("Failed to save settings.")
        
        # Search API settings
        st.subheader("Search API Settings (Optional)")
        
        # Use environment variable if available, otherwise show as empty
        env_serpapi_key = os.environ.get("SERPAPI_KEY", "")
        serpapi_key_status = "Set in environment" if env_serpapi_key else "Not set"
        
        st.info(f"SerpAPI Key status: **{serpapi_key_status}**")
        st.markdown("""
        API keys are now stored in environment variables for enhanced security. 
        To set your API key, add it to your environment variables or .env file:
        ```
        SERPAPI_KEY=your_key_here
        ```
        """)
        
        # Pass empty string to maintain compatibility with existing code
        serpapi_key = ""
        
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
            pattern_set = STANDARD_PATTERNS
            st.info("Standard patterns include: " + ", ".join(pattern_set.keys()))
        else:
            pattern_set = STRICT_PATTERNS
            st.info("Strict patterns include: " + ", ".join(pattern_set.keys()))
            
        # Show pattern details in an expander
        with st.expander("View All Available Detection Patterns"):
            # Create a table with pattern details
            st.markdown("### All Available Patterns")
            st.markdown("These are the system-defined patterns that detect sensitive information:")
            
            # Group patterns by category and level
            categories = {
                "Basic identifiers": ["credit_card", "ssn", "email", "phone_number", "msisdn", "ip_address", "date_of_birth", "address"],
                "Credentials": ["password", "api_key", "jwt"],
                "Cloud provider tokens": ["aws_access_key", "aws_secret_key", "google_api_key"],
                "Financial information": ["iban", "bank_account"],
                "Personal information": ["name", "passport", "uk_nino", "greek_amka", "greek_tax_id"],
                "Classification terms": ["classification"],
                "Private keys": ["private_key"],
                "Other": ["url", "uuid"]
            }
            
            # Create a mapping of pattern names to their levels
            pattern_levels = {pattern["name"]: pattern["level"] for pattern in DEFAULT_PATTERNS}
            
            # For each category, show the available patterns with their levels
            for category, pattern_keys in categories.items():
                st.markdown(f"#### {category}")
                for key in pattern_keys:
                    if key in pattern_set:
                        level = pattern_levels.get(key, "standard")
                        level_badge = f"<span style='background-color:#E8F5E9;padding:2px 6px;border-radius:3px;font-size:0.8em;'>STANDARD</span>" if level == "standard" else f"<span style='background-color:#FFEBEE;padding:2px 6px;border-radius:3px;font-size:0.8em;'>STRICT</span>"
                        st.markdown(f"**{key}** {level_badge}", unsafe_allow_html=True)
                        st.code(f"{pattern_set[key]}")
                st.markdown("---")
        
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
            st.session_state.custom_patterns.append({"name": "", "pattern": "", "level": "standard"})
        
        # Function to remove a pattern
        def remove_pattern(index):
            del st.session_state.custom_patterns[index]
        
        # Display existing patterns
        for i, pattern in enumerate(st.session_state.custom_patterns):
            # Ensure pattern has a level attribute (backward compatibility)
            if "level" not in pattern:
                st.session_state.custom_patterns[i]["level"] = "standard"
                
            col1, col2, col3, col4 = st.columns([3, 5, 2, 1])
            
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
                st.session_state.custom_patterns[i]["level"] = st.selectbox(
                    "Scan Level",
                    options=["standard", "strict"],
                    index=0 if pattern["level"] == "standard" else 1,
                    key=f"level_{i}",
                    help="Standard (baseline) patterns are included in all scans. Strict patterns are only used in strict mode."
                )
            
            with col4:
                st.button("🗑️", key=f"remove_{i}", on_click=remove_pattern, args=(i,))
        
        # Add new pattern button
        st.button("Add Pattern", on_click=add_pattern)
        
        # Example patterns
        with st.expander("Example Advanced Patterns"):
            st.markdown("### Example Advanced Patterns")
            st.markdown("Here are some example regex patterns you can use in your custom patterns:")
            
            example_patterns = [
                ("UK National Insurance Number (NINO)", "\\b(?!BG|GB|NK|KN|TN|NT|ZZ)([A-CEGHJ-PR-TW-Z]{2})\\d{6}[A-D]\\b"),
                ("Greek Tax ID (AFM)", "\\b\\d{9}\\b"),
                ("IBAN (International Bank Account Number)", "\\b[A-Z]{2}\\d{2}(?:[ ]?[0-9A-Z]){11,30}\\b"),
                ("Private API Key Format", "\\b(?:api_key|apikey|access_token|token|secret|bearer)[\"']?\\s*[:=]\\s*[\"']?[A-Za-z0-9\\-_]{16,64}[\"']?\\b"),
                ("Classification Terms", "\\b(confidential|strictly confidential|secret|internal use only|proprietary|classified)\\b"),
                ("JWT (JSON Web Token)", "\\beyJ[A-Za-z0-9\\-_]+?\\.eyJ[A-Za-z0-9\\-_]+?\\.[A-Za-z0-9\\-_]+\\b")
            ]
            
            # Display example patterns in a more readable format
            for name, pattern in example_patterns:
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.markdown(f"**{name}:**")
                with col2:
                    st.code(pattern, language="text")
                
            st.markdown("---")
            st.markdown("For more examples, check the 'View All Available Detection Patterns' section under Privacy Settings.")
        
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
    
    # Environment Config tab
    with config_tab:
        st.subheader("Environment Configuration")
        
        # Check if user is admin
        is_admin = st.session_state.get("role", "") == "admin"
        
        if not is_admin:
            st.warning("Only administrators can view and configure these settings.")
            st.info("Contact your administrator to update these configuration settings.")
        else:
            st.info("""
            This tab allows administrators to view and configure environment variables needed 
            for Microsoft DLP and Azure AD integrations. The values you enter here are for
            information purposes only - you'll need to set these as environment variables
            in your deployment environment.
            """)
            
            # Microsoft DLP Environment Variables
            st.subheader("Microsoft DLP Integration Configuration")
            
            st.markdown("""
            ### Required Environment Variables for Microsoft DLP
            
            To enable Microsoft DLP integration, set the following environment variables:
            """)
            
            ms_dlp_variables = {
                "MS_CLIENT_ID": "Microsoft App client ID for DLP integration",
                "MS_CLIENT_SECRET": "Client secret for the Microsoft app",
                "MS_TENANT_ID": "Your Microsoft tenant ID",
                "MS_DLP_ENDPOINT_ID": "The endpoint ID for Microsoft DLP services"
            }
            
            # Display the required environment variables
            for var_name, description in ms_dlp_variables.items():
                current_value = os.environ.get(var_name, "")
                masked_value = "••••••••" if current_value else "(Not set)"
                
                st.markdown(f"#### {var_name}")
                st.markdown(f"*{description}*")
                st.code(f"{var_name}={masked_value}")
            
            # Azure AD Environment Variables
            st.subheader("Azure AD Integration Configuration")
            
            st.markdown("""
            ### Required Environment Variables for Azure AD
            
            To enable Azure AD authentication, set the following environment variables:
            """)
            
            azure_ad_variables = {
                "AZURE_CLIENT_ID": "Azure AD app client ID",
                "AZURE_CLIENT_SECRET": "Client secret for the Azure AD app",
                "AZURE_TENANT_ID": "Your Azure tenant ID",
                "AZURE_REDIRECT_URI": "The redirect URI for authentication callbacks (e.g., http://localhost:5000/)"
            }
            
            # Display the required environment variables
            for var_name, description in azure_ad_variables.items():
                current_value = os.environ.get(var_name, "")
                masked_value = "••••••••" if current_value else "(Not set)"
                
                st.markdown(f"#### {var_name}")
                st.markdown(f"*{description}*")
                st.code(f"{var_name}={masked_value}")
            
            st.info("""
            ### How to Set Environment Variables
            
            These environment variables should be set in your deployment environment. Do not hardcode these values in the application code for security reasons.
            
            **For local development:**
            - Create a `.env` file in the project root directory
            - Add these variables in the format: `VARIABLE_NAME=value`
            - Use the `python-dotenv` package to load them
            
            **For production deployment:**
            - Set these as environment variables in your hosting platform
            - Many platforms offer secure ways to store and manage secrets
            """)

# If the file is run directly, show the settings interface
if __name__ == "__main__" or "show" not in locals():
    # Check if user is authenticated
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.error("You must be logged in to access this page.")
        st.stop()
    
    show()
