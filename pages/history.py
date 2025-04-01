import streamlit as st
import pandas as pd
import json
from datetime import datetime

# Import custom modules
from database import get_session
from models import Conversation, Message, File
from utils import delete_conversation
from pdf_export import export_conversation_to_pdf

def show():
    """Main function to display the chat history interface"""
    # Page settings
    st.title("📜 Conversation History")
    
    # Get user information
    user_id = st.session_state.user_id
    if not user_id:
        st.error("You must be logged in to access this page.")
        return
    
    # Get all user conversations
    session = get_session()
    conversations = session.query(Conversation).filter(
        Conversation.user_id == user_id
    ).order_by(Conversation.updated_at.desc()).all()
    
    # Close session
    session.close()
    
    if not conversations:
        st.info("You don't have any conversations yet. Start chatting to create one!")
        return
    
    # Display conversations in a table
    st.subheader("Your Conversations")
    
    # Create a dataframe from the conversations
    conversation_data = []
    
    for conv in conversations:
        # Count messages
        message_count = len(conv.messages)
        user_messages = sum(1 for msg in conv.messages if msg.role == "user")
        ai_messages = sum(1 for msg in conv.messages if msg.role == "assistant")
        
        # Get date in readable format
        created_date = conv.created_at.strftime("%Y-%m-%d %H:%M")
        updated_date = conv.updated_at.strftime("%Y-%m-%d %H:%M")
        
        # Add to data
        conversation_data.append({
            "ID": conv.id,
            "Title": conv.title,
            "Created": created_date,
            "Last Updated": updated_date,
            "Messages": message_count,
            "User": user_messages,
            "AI": ai_messages
        })
    
    # Create dataframe
    df = pd.DataFrame(conversation_data)
    
    # Display the table
    st.dataframe(
        df,
        column_config={
            "ID": st.column_config.Column("ID", width="small"),
            "Title": st.column_config.Column("Title", width="medium"),
            "Created": st.column_config.Column("Created", width="medium"),
            "Last Updated": st.column_config.Column("Last Updated", width="medium"),
            "Messages": st.column_config.Column("Messages", width="small"),
            "User": st.column_config.Column("User Msgs", width="small"),
            "AI": st.column_config.Column("AI Msgs", width="small")
        },
        hide_index=True,
        use_container_width=True
    )
    
    # Conversation selection and actions
    st.subheader("Conversation Actions")
    
    # Let user select a conversation
    conversation_options = {conv.title: conv.id for conv in conversations}
    selected_title = st.selectbox("Select a conversation", list(conversation_options.keys()))
    selected_id = conversation_options[selected_title]
    
    # Get the selected conversation details
    selected_conversation = next((c for c in conversations if c.id == selected_id), None)
    
    if selected_conversation:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Open Conversation", key="open_btn"):
                st.session_state.current_conversation_id = selected_id
                st.switch_page("pages/chat.py")
        
        with col2:
            if st.button("Export to PDF", key="pdf_btn"):
                try:
                    # Generate PDF
                    with st.spinner("Generating PDF..."):
                        pdf_path = export_conversation_to_pdf(selected_id)
                    
                    # Provide download link
                    with open(pdf_path, "rb") as pdf_file:
                        pdf_bytes = pdf_file.read()
                    
                    st.download_button(
                        label="Download PDF",
                        data=pdf_bytes,
                        file_name=f"conversation_{selected_id}.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"Error generating PDF: {str(e)}")
        
        with col3:
            # Delete conversation with confirmation
            if st.button("Delete Conversation", key="delete_btn"):
                st.warning(f"Are you sure you want to delete '{selected_conversation.title}'? This action cannot be undone.")
                
                confirm_col1, confirm_col2 = st.columns(2)
                
                with confirm_col1:
                    if st.button("Yes, delete it", key="confirm_delete"):
                        # Delete the conversation
                        success = delete_conversation(selected_id)
                        
                        if success:
                            st.success("Conversation deleted successfully.")
                            # Clear current conversation if it was the deleted one
                            if st.session_state.get("current_conversation_id") == selected_id:
                                st.session_state.current_conversation_id = None
                            st.rerun()
                        else:
                            st.error("Failed to delete conversation.")
                
                with confirm_col2:
                    if st.button("Cancel", key="cancel_delete"):
                        st.rerun()
        
        # Display conversation preview
        st.subheader("Conversation Preview")
        
        # Display messages (limited to 5 for preview)
        message_limit = 5
        messages_to_show = selected_conversation.messages[:message_limit]
        
        for msg in messages_to_show:
            if msg.role == "user":
                with st.chat_message("user"):
                    # Truncate long messages
                    content = msg.content
                    if len(content) > 300:
                        content = content[:300] + "..."
                    
                    st.write(content)
                    
                    # Show files if any
                    if msg.files:
                        for file in msg.files:
                            st.caption(f"File: {file.original_name}")
            else:
                with st.chat_message("assistant"):
                    # Truncate long messages
                    content = msg.content
                    if len(content) > 300:
                        content = content[:300] + "..."
                    
                    st.write(content)
        
        # Show a message if there are more messages
        if len(selected_conversation.messages) > message_limit:
            st.info(f"Showing {message_limit} of {len(selected_conversation.messages)} messages. Open the conversation to see all.")

# If the file is run directly, show the history interface
if __name__ == "__main__" or "show" not in locals():
    # Check if user is authenticated
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.error("You must be logged in to access this page.")
        st.stop()
    
    show()
