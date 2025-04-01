import streamlit as st
import time
from datetime import datetime
import pandas as pd
import json

# Import custom modules
from database import get_session
from models import Conversation, Message, File, Settings
from privacy_scanner import scan_text, anonymize_text, scan_file_content
from ai_providers import get_ai_response, create_system_prompt, get_user_settings
from utils import (
    create_new_conversation, 
    get_conversation, 
    add_message_to_conversation,
    save_uploaded_file
)

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
    
    # Display the messages in the conversation
    message_container = st.container()
    
    with message_container:
        for message in conversation.messages:
            if message.role == "user":
                with st.chat_message("user"):
                    st.write(message.content)
                    
                    # Display files if they exist
                    for file in message.files:
                        st.caption(f"File: {file.original_name} ({file.mime_type})")
            else:
                with st.chat_message("assistant"):
                    st.write(message.content)
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Upload files to include in your message", 
        accept_multiple_files=True,
        type=["txt", "py", "java", "cpp", "c", "json", "csv", "md"]
    )
    
    # Show privacy warning if scanning is enabled
    if settings.scan_enabled:
        st.caption("🔒 Privacy scanning is enabled. Sensitive information will be detected and can be anonymized.")
    
    # Chat input
    user_message = st.chat_input("Type your message here...")
    
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
        
        # Prepare messages for AI
        ai_messages = []
        
        # Add system message
        system_prompt = create_system_prompt(settings.ai_character)
        ai_messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history (limit to last 10 messages to avoid token limits)
        for message in conversation.messages[-10:]:
            ai_messages.append({"role": message.role, "content": message.content})
        
        # Modify the last user message to include file context if any
        if file_context and ai_messages and ai_messages[-1]["role"] == "user":
            ai_messages[-1]["content"] += file_context
        
        # Get AI response
        with st.chat_message("assistant"):
            # Initialize an empty container for the response
            response_container = st.empty()
            full_response = ""
            
            # Display thinking indicator
            thinking_msg = response_container.text("Thinking...")
            
            # Check provider settings
            if settings.llm_provider == "openai" and not settings.openai_api_key:
                full_response = "⚠️ OpenAI API key not configured. Please add your API key in the settings."
            elif settings.llm_provider == "claude" and not settings.claude_api_key:
                full_response = "⚠️ Claude API key not configured. Please add your API key in the settings."
            elif settings.llm_provider == "gemini" and not settings.gemini_api_key:
                full_response = "⚠️ Gemini API key not configured. Please add your API key in the settings."
            elif settings.llm_provider == "local" and not settings.local_model_path:
                full_response = "⚠️ Local model path not configured. Please add a model path in the settings."
            else:
                # Get streamed response from AI provider
                try:
                    response_stream = get_ai_response(user_id, ai_messages, stream=True)
                    
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
            uploaded_files=None
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
