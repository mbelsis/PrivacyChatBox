import streamlit as st
from style import apply_custom_css

# Apply custom CSS to hide default menu
apply_custom_css()
import os
import time
from datetime import datetime
import pandas as pd
import json
import re
from typing import List, Optional

# Import custom modules
from database import get_session
from models import Conversation, Message, File, Settings
from privacy_scanner import scan_text, anonymize_text, scan_file_content
from ai_providers import get_ai_response, create_system_prompt, get_user_settings, get_available_models
from page_logic import (
    build_chat_ai_messages,
    build_current_user_content,
    build_file_payloads,
    build_uploaded_file_records,
    get_chat_provider_precheck_error,
)
from utils import (
    create_new_conversation, 
    get_conversation, 
    add_message_to_conversation,
    save_uploaded_file,
    format_conversation_messages
)
# Import shared sidebar
import shared_sidebar

# Web search for the /search command (official SerpApi client)
from web_search import WebSearchError, format_search_results, search_web

# Microsoft Purview DLP (optional integration)
try:
    from ms_dlp import check_prompt_with_purview
except ImportError:  # pragma: no cover - msal not installed
    check_prompt_with_purview = None

def show():
    """Main function to display the chat interface"""
    # Clear sidebar state for fresh creation
    if "sidebar_created" in st.session_state:
        del st.session_state.sidebar_created
    
    # Create sidebar with shared component
    shared_sidebar.create_sidebar("chat_page")
    
    # Page settings
    st.title("💬 AI Chat")
    
    # Get user information
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("You must be logged in to access this page.")
        return
    
    # Get user settings
    settings = get_user_settings(user_id)
    if not settings:
        st.error("User settings not found. Please contact an administrator.")
        return

    if st.session_state.get("must_change_password"):
        st.warning("Your password is temporary. Change it in Settings > Account before using chat.")
        return

    # Create two columns for conversation management
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Create new conversation button
        if st.button("Start New Conversation"):
            # Create new conversation in database
            conversation_id = create_new_conversation(user_id)
            if conversation_id <= 0:
                st.error("Failed to create a new conversation.")
            else:
                st.session_state.current_conversation_id = conversation_id
                st.rerun()
    
    with col2:
        # Dropdown to select existing conversation
        session = get_session()
        if not session:
            st.error("Unable to load conversations.")
            return
        conversations = session.query(Conversation).filter(
            Conversation.user_id == user_id
        ).order_by(Conversation.updated_at.desc()).all()
        session.close()
        
        conversation_options = {}
        for conv in conversations:
            # Format title with date
            formatted_date = conv.created_at.strftime("%m/%d/%Y")
            title = f"{conv.title} ({formatted_date})"
            conversation_options[title] = conv.id
        
        current_conversation_id = st.session_state.get("current_conversation_id")
        current_selection = "Select a conversation"
        for title, conv_id in conversation_options.items():
            if conv_id == current_conversation_id:
                current_selection = title
                break

        # Add placeholder for selecting conversation
        conversation_list = ["Select a conversation"] + list(conversation_options.keys())
        selected_conversation = st.selectbox(
            "Load conversation", 
            conversation_list,
            index=conversation_list.index(current_selection)
        )
        
        if selected_conversation != "Select a conversation":
            selected_id = conversation_options[selected_conversation]
            if st.session_state.get("current_conversation_id") != selected_id:
                st.session_state.current_conversation_id = selected_id
                st.rerun()
    
    # Create main chat interface
    st.markdown("---")
    
    # Check if we have a current conversation
    if "current_conversation_id" not in st.session_state or not st.session_state.current_conversation_id:
        st.info("Start a new conversation or select an existing one from the dropdown.")
        return
    
    # Load the current conversation
    conversation_id = st.session_state.current_conversation_id
    conversation = get_conversation(conversation_id, requesting_user_id=user_id)
    
    if not conversation:
        st.error("Conversation not found. It may have been deleted.")
        st.session_state.current_conversation_id = None
        st.rerun()
        return

    # A pending sensitive-content review belongs to exactly one conversation. If the user
    # switched conversations, drop it so the chat input is not left disabled forever.
    stale_pending = st.session_state.get("pending_chat_submission")
    if stale_pending and stale_pending.get("conversation_id") != conversation_id:
        st.session_state.pop("pending_chat_submission", None)
    
    # More compact layout with selectors and chat in a single continuous view
    st.container().markdown("""
    <style>
    /* Additional CSS for more compact layout */
    section.main > div:first-child {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
    }
    .stSelectbox {
        margin-bottom: 0 !important;
    }
    .stMarkdown h3 {
        margin-bottom: 5px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Title and selector row
    st.subheader(f"Conversation: {conversation['title']}", anchor=False)
    
    # Create a more compact row for all selectors
    compact_col1, compact_col2, compact_col3 = st.columns([1, 1, 1])
    
    with compact_col1:
        # AI Provider selector
        provider_options = ["openai", "claude", "gemini", "local"]
        
        # Create a temporary provider selection for this session only
        if "temp_provider" not in st.session_state:
            st.session_state.temp_provider = settings.llm_provider
            
        # Provider selection dropdown
        selected_provider = st.selectbox(
            "AI Provider",
            provider_options,
            index=provider_options.index(st.session_state.temp_provider) if st.session_state.temp_provider in provider_options else 0,
            label_visibility="visible"
        )
        
        # Update session state
        st.session_state.temp_provider = selected_provider
    
    with compact_col2:
        # Get all available models for the selected provider
        available_models = get_available_models()
        current_provider = st.session_state.temp_provider
        model_options = available_models.get(current_provider, [])
        
        # Get current model from settings
        current_model = ""
        if current_provider == "openai":
            current_model = settings.openai_model
        elif current_provider == "claude":
            current_model = settings.claude_model
        elif current_provider == "gemini":
            current_model = settings.gemini_model
        
        # Create a temporary model selection for this session only
        if "temp_model" not in st.session_state or st.session_state.temp_provider != getattr(st.session_state, "last_provider", ""):
            st.session_state.temp_model = current_model
            st.session_state.last_provider = current_provider
            
        # Model selection dropdown
        selected_model = st.selectbox(
            "AI Model",
            model_options,
            index=model_options.index(st.session_state.temp_model) if st.session_state.temp_model in model_options and model_options else 0,
            label_visibility="visible"
        )
        
        # Update session state
        st.session_state.temp_model = selected_model
    
    with compact_col3:
        character_options = ["assistant", "privacy_expert", "data_analyst", "programmer"]
        
        # Create a temporary character selection for this session only
        if "temp_character" not in st.session_state:
            st.session_state.temp_character = settings.ai_character
            
        # Character selection dropdown
        selected_character = st.selectbox(
            "AI Character",
            character_options,
            index=character_options.index(st.session_state.temp_character) if st.session_state.temp_character in character_options else 0,
            label_visibility="visible"
        )
    
    # Display a very small privacy notice if needed
    if settings.scan_enabled:
        st.markdown('<div style="font-size: 0.7rem; color: #5a9; padding: 1px 5px; border-radius: 3px; background-color: #f0f9f6; margin-bottom: 5px;">🔒 Privacy protection active</div>', unsafe_allow_html=True)
    
    # Custom CSS to make the layout more compact similar to ChatGPT
    st.markdown("""
    <style>
    /* Make the selectors more compact */
    div[data-testid="stVerticalBlock"] > div.element-container:nth-child(2) {
        margin-bottom: 0px !important;
    }
    
    /* Reduce padding around chat messages */
    .stChatMessage {
        padding-top: 10px !important;
        padding-bottom: 10px !important;
    }
    
    /* Give AI responses a slight background color */
    .css-1c7y2kd {  /* This targets the assistant message bubbles */
        background-color: #f8f9fa !important;
    }
    
    /* Ensure chat message content is scrollable */
    .stChatMessageContent, 
    .stChatMessage > div:last-child > div:first-child,
    .stChatMessage p {
        max-height: 400px !important;
        overflow-y: auto !important;
        overflow-x: auto !important;
        white-space: pre-wrap !important;
        word-wrap: break-word !important;
    }
    
    /* Add scrollbar styling */
    .stChatMessageContent::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    .stChatMessageContent::-webkit-scrollbar-thumb {
        background-color: #ccc;
        border-radius: 10px;
    }
    .stChatMessageContent::-webkit-scrollbar-track {
        background-color: transparent;
    }
    
    /* Make file uploader button more compact */
    .stFileUploader > div:first-child {
        background-color: transparent !important;
        padding: 0 !important;
        margin-bottom: 0 !important;
    }
    .stFileUploader > div > small {
        display: none !important;
    }
    
    /* Fix the input area at the bottom */
    .input-area {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background-color: white;
        padding: 10px 0;
        border-top: 1px solid #e0e0e0;
        z-index: 100;
        display: flex;
        align-items: center;
    }
    
    /* Create space for fixed input area */
    .chat-container {
        margin-bottom: 80px;
    }
    
    /* Connect file uploader with the message input box */
    .input-container {
        display: flex;
        align-items: center;
        border: 1px solid #e0e0e0;
        border-radius: 20px;
        padding: 5px;
        background-color: #ffffff;
        width: 100%;
    }
    
    /* Make the file upload button part of the input box */
    .upload-button {
        margin-right: 5px;
    }
    
    /* Style the input box */
    .message-input {
        flex-grow: 1;
    }
    
    /* Integrate drag & drop with the chat input */
    section[data-testid="stFileUploader"] > div:first-child {
        padding: 0 !important;
        border: none !important;
        background-color: transparent !important;
    }
    
    /* Style the drag & drop text */
    section[data-testid="stFileUploader"] > div:first-child > div:first-child > span:first-child {
        font-size: 0.8rem !important;
        color: #666 !important;
        font-style: italic !important;
    }
    
    /* Position the file uploader over the chat input */
    .file-upload-overlay {
        width: 100%;
        position: relative;
        z-index: 10;
    }
    
    /* Position the message input */
    .message-input {
        width: 100%;
        position: relative;
        z-index: 5;
        margin-top: -40px;
    }
    
    /* Style the upload button to look like an icon */
    section[data-testid="stFileUploader"] button[kind="secondary"] {
        border: none !important;
        padding: 0.5rem !important;
        background-color: transparent !important;
        color: #0b5394 !important;
        margin-right: 5px !important;
    }
    
    /* Make the file names appear more compact */
    section[data-testid="stFileUploader"] div[data-testid="stFileUploadDropzoneContentUploadedFile"] {
        padding: 2px 5px !important;
        margin: 2px !important;
        background-color: #f0f6ff !important;
        border-radius: 4px !important;
    }
    
    /* Style the chat input to be more visible */
    div[data-testid="stChatInput"] {
        border: 1px solid #e0e0e0 !important;
        border-radius: 20px !important;
        background-color: #ffffff !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
    }
    
    /* No forced sidebar positioning - let Streamlit handle it */
    </style>
    """, unsafe_allow_html=True)
    
    # Chat message container with padding at bottom for fixed input
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # Display the messages in the conversation, sorted by timestamp
    sorted_messages = sorted(conversation["messages"], key=lambda x: x["timestamp"])
    for message in sorted_messages:
        if message["role"] == "user":
            with st.chat_message("user"):
                # Check if this was a search command
                if message["content"].startswith("/search "):
                    st.write(f"🔍 **Search Query:** {message['content'][8:]}")
                else:
                    st.write(message["content"])
                
                # Display files if they exist
                if "files" in message:
                    for file in message["files"]:
                        st.caption(f"📎 File: {file['original_name']} ({file['mime_type']})")
        else:
            with st.chat_message("assistant"):
                st.write(message["content"])
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Create a chat container to ensure all messages stay together
    chat_container = st.container()
    
    # Create a container for the input area at the bottom
    input_container = st.container()
    
    with input_container:
        st.markdown('<div class="input-area">', unsafe_allow_html=True)
        
        # Create a container for the integrated input
        input_col = st.container()
        
        with input_col:
            st.markdown('<div class="input-container">', unsafe_allow_html=True)
            
            # First add the file uploader that spans the entire width
            st.markdown('<div class="file-upload-overlay">', unsafe_allow_html=True)
            uploaded_files = st.file_uploader(
                "Drag files here or browse",
                accept_multiple_files=True,
                type=["txt", "py", "java", "cpp", "c", "json", "csv", "md", "docx", "xlsx", "pptx", "pdf"],
                label_visibility="visible"
            )
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Now add the chat input below
            st.markdown('<div class="message-input">', unsafe_allow_html=True)
            user_message = st.chat_input(
                "Type your message here or drag files anywhere...",
                disabled=bool(st.session_state.get("pending_chat_submission"))
            )
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # File support info below input container
            supported_files = "TXT, PY, JAVA, CPP, C, JSON, CSV, MD, DOCX, XLSX, PPTX, PDF"
            st.caption(f"💡 Tip: Use /search [query] to search the web • Supported files: {supported_files}")
            
            # Show file count if any are uploaded
            if uploaded_files:
                st.caption(f"📎 {len(uploaded_files)} file(s) ready to send")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Process user message in the chat container
    with chat_container:
        pending_submission = st.session_state.get("pending_chat_submission")

        final_message = None
        file_payloads = []

        if pending_submission:
            # --- Path A: the user is resolving a sensitive-content review ---
            st.warning("Sensitive information was detected in your last submission.")
            st.write("Detected patterns:")
            for pattern_type, matches in pending_submission.get("detected", {}).items():
                st.write(
                    f"- **{pattern_type}**: {', '.join(matches[:3])}"
                    + (f" and {len(matches) - 3} more" if len(matches) > 3 else "")
                )

            pending_col1, pending_col2 = st.columns(2)
            with pending_col1:
                continue_original = st.button("Continue with original text", key="continue_original_sensitive")
            with pending_col2:
                anonymize_pending = st.button("Anonymize sensitive information", key="anonymize_sensitive")

            if not continue_original and not anonymize_pending:
                st.info("Choose how to proceed to continue.")
                st.stop()

            user_message = pending_submission["user_message"]
            file_payloads = pending_submission.get("file_payloads", [])
            final_message = user_message

            if anonymize_pending:
                final_message, _ = anonymize_text(user_id, user_message)
                for file_payload in file_payloads:
                    anonymized_content, _ = anonymize_text(user_id, file_payload["content"])
                    file_payload["content"] = anonymized_content
                    file_payload["content_bytes"] = anonymized_content.encode("utf-8")

                with st.chat_message("user"):
                    st.write("Original message has been anonymized:")
                    st.markdown(f"**Anonymized message:** {final_message}")
                    for file_payload in file_payloads:
                        st.caption(f"File: {file_payload['name']} (anonymized)")
            else:
                with st.chat_message("user"):
                    st.write(user_message)
                    for file_payload in file_payloads:
                        st.caption(f"File: {file_payload['name']}")

            st.session_state.pop("pending_chat_submission", None)

        elif user_message:
            # --- Path B: a brand-new message was submitted ---
            # Create a placeholder for the user message that will be replaced if anonymized
            user_message_container = st.container()
            
            # Display user message (this may be replaced later if anonymized)
            with user_message_container.chat_message("user"):
                st.write(user_message)
                
                # Display files if they exist
                if uploaded_files:
                    for file in uploaded_files:
                        st.caption(f"File: {file.name}")
            
            file_payloads = build_file_payloads(uploaded_files)

            # Scan message for sensitive information
            has_sensitive = False
            detected = {}
            if settings.scan_enabled:
                has_sensitive, detected = scan_text(user_id, user_message)

                for file_payload in file_payloads:
                    file_has_sensitive, file_detected = scan_file_content(user_id, file_payload["content"], file_payload["name"])
                    if file_has_sensitive:
                        for pattern_type, matches in file_detected.items():
                            detected.setdefault(pattern_type, []).extend(matches)
                        has_sensitive = True

                detected = {key: list(dict.fromkeys(value)) for key, value in detected.items()}

            # If sensitive information found, either block for manual review or auto-anonymize
            final_message = user_message
            if has_sensitive:
                # Check if auto-anonymize is enabled in settings
                if settings.auto_anonymize:
                    # Automatically anonymize the message
                    final_message, _ = anonymize_text(user_id, user_message)
                    
                    # Anonymize file contents if any
                    for file_payload in file_payloads:
                        anonymized_content, _ = anonymize_text(user_id, file_payload["content"])
                        file_payload["content"] = anonymized_content
                        file_payload["content_bytes"] = anonymized_content.encode("utf-8")
                    
                    # Clear the original user message and display the anonymized version
                    user_message_container.empty()
                    
                    # Display anonymized message in the same position
                    with user_message_container.chat_message("user"):
                        st.write("Original message has been anonymized automatically:")
                        st.markdown(f"**Anonymized message:** {final_message}")
                        
                        # Display files if they exist
                        for file_payload in file_payloads:
                            st.caption(f"File: {file_payload['name']} (anonymized)")
                    
                    st.success("Message and files automatically anonymized (based on your settings)")
                else:
                    st.session_state.pending_chat_submission = {
                        "conversation_id": conversation_id,
                        "user_message": user_message,
                        "file_payloads": file_payloads,
                        "detected": detected,
                    }
                    st.rerun()
        else:
            # Nothing to do on this run.
            return

        uploaded_file_records = build_uploaded_file_records(file_payloads)

        # Evaluate the prompt against the organisation's Purview DLP policies before it
        # is stored or sent to any model. Uploaded files are evaluated separately when
        # they are attached to the message.
        if check_prompt_with_purview is not None:
            prompt_allowed, purview_message = check_prompt_with_purview(user_id, final_message)
            if not prompt_allowed:
                st.error(f"⛔ {purview_message}")
                st.stop()
            if purview_message:
                st.warning(f"⚠️ {purview_message}")

        # Add message to database
        message_id, dlp_error = add_message_to_conversation(
            conversation_id=conversation_id,
            role="user",
            content=final_message,
            uploaded_files=uploaded_file_records
        )
        
        # Check if any files were blocked by Microsoft DLP
        if dlp_error:
            st.error(f"⚠️ {dlp_error}")
            # Early return if files were blocked
            st.stop()
        
        # Prepare context from files if any are uploaded
        file_context = ""
        if file_payloads:
            file_context = "\n\nThe following files were uploaded:\n\n"
            for file_payload in file_payloads:
                file_context += f"--- BEGIN FILE: {file_payload['name']} ---\n"
                file_context += file_payload["content"]
                file_context += f"\n--- END FILE: {file_payload['name']} ---\n\n"
        
        # Handle web search directive
        search_results = ""
        if final_message.startswith("/search "):
            search_query = final_message[8:].strip()
            response_container = st.empty()
            response_container.info(f"🔍 Searching the web for: {search_query}")
            
            try:
                results = search_web(search_query)
                search_results = format_search_results(search_query, results)
                response_container.success("✅ Search completed")
            except WebSearchError as e:
                search_results = f"\n\nError performing web search: {str(e)}\n\n"
                response_container.warning(f"⚠️ {str(e)}")
        
        # Get the currently selected model and character (from temporary session state)
        selected_model = st.session_state.get("temp_model", "")
        selected_character = st.session_state.get("temp_character", settings.ai_character)
        
        # Check if character has changed
        last_character = st.session_state.get("last_used_character", None)
        character_changed = last_character is not None and last_character != selected_character
        
        # Store the current character for future comparison
        st.session_state["last_used_character"] = selected_character

        # Add system message based on selected character
        system_prompt = create_system_prompt(selected_character)
        
        # Define role name for later use
        role_name = selected_character.replace("_", " ").title()

        current_user_content = build_current_user_content(
            final_message=final_message,
            search_results=search_results,
            file_context=file_context,
        )

        # Reload after persisting the current user turn so the history window stays accurate.
        refreshed_conversation = get_conversation(conversation_id, requesting_user_id=user_id)
        if not refreshed_conversation:
            st.error("Failed to reload the conversation after saving your message.")
            return

        ai_messages = build_chat_ai_messages(
            system_prompt=system_prompt,
            conversation_messages=refreshed_conversation["messages"],
            current_message_id=message_id,
            current_user_content=current_user_content,
            character_changed=character_changed,
            role_name=role_name,
        )
        
        # Get AI response
        with st.chat_message("assistant"):
            # Initialize an empty container for the response
            response_container = st.empty()
            full_response = ""
            
            # Display thinking indicator
            thinking_msg = response_container.text("Thinking...")
            
            # Get the selected provider
            selected_provider = st.session_state.get("temp_provider", settings.llm_provider)
            
            # Check environment variables for API keys
            openai_key = os.environ.get("OPENAI_API_KEY", "")
            claude_key = os.environ.get("ANTHROPIC_API_KEY", "")
            gemini_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
            
            # Check provider settings based on the selected provider
            provider_error = get_chat_provider_precheck_error(
                selected_provider=selected_provider,
                settings=settings,
                openai_key=openai_key,
                claude_key=claude_key,
                gemini_key=gemini_key,
            )
            if provider_error:
                full_response = provider_error
            else:
                # Get streamed response from AI provider
                try:
                    # Override the provider settings temporarily
                    provider_settings = {}
                    if selected_provider != settings.llm_provider:
                        provider_settings["override_provider"] = selected_provider
                    
                    # Pass the selected model and provider as overrides
                    response_stream = get_ai_response(
                        user_id, 
                        ai_messages, 
                        stream=True,
                        override_model=selected_model,
                        input_already_processed=True,
                        **provider_settings
                    )
                    
                    # Check if response is a string (error) or a generator
                    if isinstance(response_stream, str):
                        full_response = response_stream
                    else:
                        # Process stream
                        for chunk in response_stream:
                            full_response += chunk
                            # Update the response container with the new content
                            response_container.markdown(full_response)
                except Exception as e:
                    full_response = f"Error getting AI response: {str(e)}"
                
            # Update the final response
            response_container.markdown(full_response)
        
        if provider_error:
            # A configuration problem is not part of the conversation; keep it out of history.
            st.stop()

        # Save the assistant message to the database
        message_id, _ = add_message_to_conversation(
            conversation_id=conversation_id,
            role="assistant",
            content=full_response,
            uploaded_files=[] # Empty list instead of None
        )
        
        # Update the conversation in session state
        st.rerun()

# If the file is run directly, show the chat interface
if __name__ == "__main__" or "show" not in locals():
    # Check if user is authenticated
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.error("You must be logged in to access this page.")
        st.stop()
    
    show()
