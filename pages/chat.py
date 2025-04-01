import streamlit as st
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
from utils import (
    create_new_conversation, 
    get_conversation, 
    add_message_to_conversation,
    save_uploaded_file
)

# Import for web search functionality
from serpapi import GoogleSearch

def show():
    """Main function to display the chat interface"""
    # Page settings
    st.title("💬 AI Chat")
    
    # Get user information
    user_id = st.session_state.user_id
    if not user_id:
        st.error("You must be logged in to access this page.")
        return
    
    # Get user settings
    settings = get_user_settings(user_id)
    if not settings:
        st.error("User settings not found. Please contact an administrator.")
        return
    
    # Create two columns for conversation management
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Create new conversation button
        if st.button("Start New Conversation"):
            # Create new conversation in database
            conversation_id = create_new_conversation(user_id)
            st.session_state.current_conversation_id = conversation_id
            st.rerun()
    
    with col2:
        # Dropdown to select existing conversation
        session = get_session()
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
        
        # Add placeholder for selecting conversation
        conversation_list = ["Select a conversation"] + list(conversation_options.keys())
        selected_conversation = st.selectbox(
            "Load conversation", 
            conversation_list,
            index=0
        )
        
        if selected_conversation != "Select a conversation":
            selected_id = conversation_options[selected_conversation]
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
    conversation = get_conversation(conversation_id)
    
    if not conversation:
        st.error("Conversation not found. It may have been deleted.")
        st.session_state.current_conversation_id = None
        st.rerun()
        return
    
    # Display the conversation title
    st.subheader(f"Conversation: {conversation.title}")
    
    # Create a row for provider/model/character selectors
    selector_col1, selector_col2, selector_col3 = st.columns([1, 1, 1])
    
    with selector_col1:
        # AI Provider selector
        provider_options = ["openai", "claude", "gemini", "local"]
        
        # Create a temporary provider selection for this session only
        if "temp_provider" not in st.session_state:
            st.session_state.temp_provider = settings.llm_provider
            
        # Provider selection dropdown
        selected_provider = st.selectbox(
            "AI Provider",
            provider_options,
            index=provider_options.index(st.session_state.temp_provider) if st.session_state.temp_provider in provider_options else 0
        )
        
        # Update session state
        st.session_state.temp_provider = selected_provider
    
    with selector_col2:
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
            index=model_options.index(st.session_state.temp_model) if st.session_state.temp_model in model_options and model_options else 0
        )
        
        # Update session state
        st.session_state.temp_model = selected_model
    
    with selector_col3:
        character_options = ["assistant", "privacy_expert", "data_analyst", "programmer"]
        
        # Create a temporary character selection for this session only
        if "temp_character" not in st.session_state:
            st.session_state.temp_character = settings.ai_character
            
        # Character selection dropdown
        selected_character = st.selectbox(
            "AI Character",
            character_options,
            index=character_options.index(st.session_state.temp_character) if st.session_state.temp_character in character_options else 0
        )
        
        # Update session state
        st.session_state.temp_character = selected_character
    
    # Display privacy notice if needed
    if settings.scan_enabled:
        st.info("🔒 Privacy scanning is enabled. Sensitive information will be detected and can be anonymized.")
    
    # Custom CSS to create a chat container with fixed input at bottom
    st.markdown("""
    <style>
    .chat-container {
        display: flex;
        flex-direction: column;
        height: calc(100vh - 300px);
        min-height: 400px;
    }
    .messages-container {
        flex: 1;
        overflow-y: auto;
        padding: 10px;
        margin-bottom: 10px;
    }
    .input-container {
        border-top: 1px solid #e0e0e0;
        padding-top: 10px;
        background-color: white;
        position: sticky;
        bottom: 0;
    }
    .stFileUploader > div:first-child {
        background-color: transparent !important;
        padding: 0 !important;
    }
    .stFileUploader > div > small {
        display: none !important;
    }
    .upload-button-container {
        display: flex;
        align-items: center;
        gap: 5px;
    }
    .small-upload-button {
        border-radius: 20px;
        padding: 5px 10px;
        border: 1px solid #e0e0e0;
        background-color: white;
        cursor: pointer;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create container for the entire chat UI
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # Messages container
    st.markdown('<div class="messages-container">', unsafe_allow_html=True)
    for message in conversation.messages:
        if message.role == "user":
            with st.chat_message("user"):
                # Check if this was a search command
                if message.content.startswith("/search "):
                    st.write(f"🔍 **Search Query:** {message.content[8:]}")
                else:
                    st.write(message.content)
                
                # Display files if they exist
                for file in message.files:
                    st.caption(f"📎 File: {file.original_name} ({file.mime_type})")
        else:
            with st.chat_message("assistant"):
                st.write(message.content)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Input area container (fixed at bottom)
    st.markdown('<div class="input-container">', unsafe_allow_html=True)
    
    # Create a row for the input area
    input_col1, input_col2, input_col3 = st.columns([1, 12, 1])
    
    # Upload button on the left side
    with input_col1:
        uploaded_files = st.file_uploader(
            "Files",
            accept_multiple_files=True,
            type=["txt", "py", "java", "cpp", "c", "json", "csv", "md", "docx", "xlsx", "pptx", "pdf"],
            label_visibility="collapsed"
        )
        
    # Message input in the center
    with input_col2:
        # Add tip about search and file types
        supported_files = "TXT, PY, JAVA, CPP, C, JSON, CSV, MD, DOCX, XLSX, PPTX, PDF"
        tip_text = f"💡 Tip: Use /search [query] to search the web • Supported files: {supported_files}"
        st.caption(tip_text)
        
        # Chat input
        user_message = st.chat_input("Type your message here...")
        
        # Show file count if any are uploaded
        if uploaded_files:
            st.caption(f"📎 {len(uploaded_files)} file(s) ready to send")
    
    # Close the input container div
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Close the chat container div
    st.markdown('</div>', unsafe_allow_html=True)
    
    if user_message:
        # Display user message
        with st.chat_message("user"):
            st.write(user_message)
            
            # Display files if they exist
            if uploaded_files:
                for file in uploaded_files:
                    st.caption(f"File: {file.name}")
        
        # Scan message for sensitive information
        has_sensitive, detected = scan_text(user_id, user_message)
        
        # Process files if any are uploaded
        file_contents = []
        if uploaded_files:
            for file in uploaded_files:
                # Read file content
                file_content = file.read().decode("utf-8", errors="ignore")
                
                # Scan file content
                file_has_sensitive, file_detected = scan_file_content(user_id, file_content, file.name)
                
                # Add to detected if sensitive information found
                if file_has_sensitive:
                    for pattern_type, matches in file_detected.items():
                        if pattern_type in detected:
                            detected[pattern_type].extend(matches)
                        else:
                            detected[pattern_type] = matches
                    
                    has_sensitive = True
                
                # Store file content
                file_contents.append({"name": file.name, "content": file_content})
                
                # Reset file pointer for later use
                file.seek(0)
        
        # If sensitive information found, show warning and options
        final_message = user_message
        if has_sensitive and settings.scan_enabled:
            st.warning("🚨 Sensitive information detected in your message or files!")
            
            # Show detected patterns
            st.write("Detected patterns:")
            for pattern_type, matches in detected.items():
                st.write(f"- **{pattern_type}**: {', '.join(matches[:3])}" + 
                         (f" and {len(matches) - 3} more" if len(matches) > 3 else ""))
            
            # Ask user what to do
            st.info("How would you like to proceed?")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Continue with original text"):
                    pass  # Use original message
            
            with col2:
                if st.button("Anonymize sensitive information"):
                    # Anonymize message
                    final_message, _ = anonymize_text(user_id, user_message)
                    
                    # Anonymize file contents if any
                    for i, file_data in enumerate(file_contents):
                        anonymized_content, _ = anonymize_text(user_id, file_data["content"])
                        file_contents[i]["content"] = anonymized_content
                    
                    st.success("Message and files anonymized.")
        
        # Add message to database
        message_id = add_message_to_conversation(
            conversation_id=conversation_id,
            role="user",
            content=final_message,
            uploaded_files=uploaded_files
        )
        
        # Prepare context from files if any are uploaded
        file_context = ""
        if file_contents:
            file_context = "\n\nThe following files were uploaded:\n\n"
            for file_data in file_contents:
                file_context += f"--- BEGIN FILE: {file_data['name']} ---\n"
                file_context += file_data["content"]
                file_context += f"\n--- END FILE: {file_data['name']} ---\n\n"
        
        # Handle web search directive
        search_results = ""
        if final_message.startswith("/search "):
            search_query = final_message[8:].strip()
            response_container = st.empty()
            response_container.info(f"🔍 Searching the web for: {search_query}")
            
            # Check if SerpAPI key is configured
            if not settings.serpapi_key:
                st.warning("⚠️ SerpAPI key not configured. Please add your API key in the settings.")
            else:
                try:
                    # Perform the search
                    search_params = {
                        "q": search_query,
                        "api_key": settings.serpapi_key,
                        "num": 5  # Get top 5 results
                    }
                    
                    search = GoogleSearch(search_params)
                    results = search.get_dict()
                    
                    # Format search results
                    search_results = "\n\nWeb search results for query: " + search_query + "\n\n"
                    
                    if "organic_results" in results:
                        for i, result in enumerate(results["organic_results"][:5], 1):
                            title = result.get("title", "No title")
                            snippet = result.get("snippet", "No description")
                            link = result.get("link", "#")
                            search_results += f"{i}. {title}\n{snippet}\nURL: {link}\n\n"
                    else:
                        search_results = "\n\nNo search results found.\n\n"
                    
                    response_container.success("✅ Search completed")
                except Exception as e:
                    search_results = f"\n\nError performing web search: {str(e)}\n\n"
                    response_container.error(f"Error during search: {str(e)}")
        
        # Get the currently selected model and character (from temporary session state)
        selected_model = st.session_state.get("temp_model", "")
        selected_character = st.session_state.get("temp_character", settings.ai_character)
        
        # Prepare messages for AI
        ai_messages = []
        
        # Add system message based on selected character
        system_prompt = create_system_prompt(selected_character)
        ai_messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history (limit to last 10 messages to avoid token limits)
        for message in conversation.messages[-10:]:
            ai_messages.append({"role": message.role, "content": message.content})
        
        # Modify the last user message to include file context and search results if any
        if (file_context or search_results) and ai_messages and ai_messages[-1]["role"] == "user":
            content = ai_messages[-1]["content"]
            if search_results:
                content += search_results
            if file_context:
                content += file_context
            ai_messages[-1]["content"] = content
        
        # Get AI response
        with st.chat_message("assistant"):
            # Initialize an empty container for the response
            response_container = st.empty()
            full_response = ""
            
            # Display thinking indicator
            thinking_msg = response_container.text("Thinking...")
            
            # Get the selected provider
            selected_provider = st.session_state.get("temp_provider", settings.llm_provider)
            
            # Check provider settings based on the selected provider
            if selected_provider == "openai" and not settings.openai_api_key:
                full_response = "⚠️ OpenAI API key not configured. Please add your API key in the settings."
            elif selected_provider == "claude" and not settings.claude_api_key:
                full_response = "⚠️ Claude API key not configured. Please add your API key in the settings."
            elif selected_provider == "gemini" and not settings.gemini_api_key:
                full_response = "⚠️ Gemini API key not configured. Please add your API key in the settings."
            elif selected_provider == "local" and not settings.local_model_path:
                full_response = "⚠️ Local model path not configured. Please add a model path in the settings."
            else:
                # Get streamed response from AI provider
                try:
                    # Get the selected provider
                    selected_provider = st.session_state.get("temp_provider", settings.llm_provider)
                    
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
        
        # Save the assistant message to the database
        add_message_to_conversation(
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
