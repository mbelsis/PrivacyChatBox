import streamlit as st
from style import apply_custom_css

# Apply custom CSS to hide default menu
apply_custom_css()
import pandas as pd
import json
from datetime import datetime

# Import custom modules
from database import get_session
from models import Conversation, Message, File
from utils import delete_conversation, get_conversation
from pdf_export import export_conversation_to_pdf
import shared_sidebar

def show():
    """Main function to display the chat history interface"""
    # Clear sidebar state for fresh creation
    if "sidebar_created" in st.session_state:
        del st.session_state.sidebar_created
    
    # Create sidebar with shared component
    shared_sidebar.create_sidebar("history_page")
    
    # Page settings
    st.title("📜 Conversation History & Analytics")
    
    # Get user information
    user_id = st.session_state.user_id
    if not user_id:
        st.error("You must be logged in to access this page.")
        return
    
    # Create tabs for History and Analytics
    history_tab, analytics_tab = st.tabs(["📜 History", "📊 Analytics"])
    
    with history_tab:
        # Get all user conversations
        session = get_session()
        conversations = session.query(Conversation).filter(
            Conversation.user_id == user_id
        ).order_by(Conversation.updated_at.desc()).all()
        
        # Close session
        session.close()
        
        if not conversations:
            st.info("You don't have any conversations yet. Start chatting to create one!")
        else:
            # Display conversations in a table
            st.subheader("Your Conversations")
    
    with analytics_tab:
        st.subheader("Your Usage Analytics")
        
        # Load user-specific analytics data
        from models import Message, DetectionEvent, User
        from sqlalchemy.sql import func
        from privacy_scanner import get_detection_events
        import plotly.express as px
        from datetime import datetime, timedelta
        
        # Initialize analytics metrics
        total_conversations = 0
        total_messages = 0
        total_detection_events = 0
        detection_by_severity = {"low": 0, "medium": 0, "high": 0}
        conversations_by_date = {}
        
        try:
            # Get detection events for this user
            detection_events = get_detection_events(user_id)
            formatted_events = []
            
            # Calculate metrics with error handling
            with get_session() as session:
                if session:
                    # Count conversations
                    total_conversations = session.query(Conversation).filter(
                        Conversation.user_id == user_id
                    ).count()
                    
                    # Count messages
                    total_messages = session.query(Message).join(
                        Conversation, Message.conversation_id == Conversation.id
                    ).filter(Conversation.user_id == user_id).count()
                    
                    # Count detection events
                    total_detection_events = session.query(DetectionEvent).filter(
                        DetectionEvent.user_id == user_id
                    ).count()
                    
                    # Get severity breakdown - safely handle different cases
                    severity_counts = session.query(
                        DetectionEvent.severity, 
                        func.count(DetectionEvent.id)
                    ).filter(
                        DetectionEvent.user_id == user_id
                    ).group_by(DetectionEvent.severity).all()
                    
                    # Convert to dictionary format safely
                    for severity, count in severity_counts:
                        if severity in detection_by_severity:
                            detection_by_severity[severity] = count
                    
                    # Get counts by date for the past 30 days
                    thirty_days_ago = datetime.now() - timedelta(days=30)
                    conversations_by_date_query = session.query(
                        func.date(Conversation.created_at),
                        func.count(Conversation.id)
                    ).filter(
                        Conversation.user_id == user_id,
                        Conversation.created_at >= thirty_days_ago
                    ).group_by(func.date(Conversation.created_at)).all()
                    
                    # Create date dictionary with all days in the past 30 days
                    for i in range(30):
                        date_key = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                        conversations_by_date[date_key] = 0
                    
                    # Fill in actual counts
                    for date_str, count in conversations_by_date_query:
                        if isinstance(date_str, str):
                            date_key = date_str
                        else:
                            date_key = date_str.strftime('%Y-%m-%d')
                        conversations_by_date[date_key] = count
        except Exception as e:
            st.error(f"Error loading analytics data: {str(e)}")
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Conversations", total_conversations)
        
        with col2:
            st.metric("Total Messages", total_messages)
        
        with col3:
            st.metric("Privacy Events", total_detection_events)
        
        # Create data for charts
        st.subheader("Privacy Detection by Severity")
        severity_df = pd.DataFrame({
            "Severity": list(detection_by_severity.keys()),
            "Count": list(detection_by_severity.values())
        })
        
        if severity_df["Count"].sum() > 0:
            # Create severity chart
            fig = px.pie(
                severity_df, 
                values="Count", 
                names="Severity", 
                color="Severity",
                color_discrete_map={
                    "low": "#66BB6A",  # Green
                    "medium": "#FFA726",  # Orange
                    "high": "#EF5350"  # Red
                },
                hole=0.4
            )
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No privacy detection events recorded yet.")
        
        # Activity over time chart
        st.subheader("Conversation Activity (Past 30 Days)")
        activity_df = pd.DataFrame({
            "Date": list(conversations_by_date.keys()),
            "Conversations": list(conversations_by_date.values())
        })
        activity_df["Date"] = pd.to_datetime(activity_df["Date"])
        activity_df = activity_df.sort_values("Date")
        
        if activity_df["Conversations"].sum() > 0:
            activity_fig = px.line(
                activity_df, 
                x="Date", 
                y="Conversations",
                markers=True,
            )
            activity_fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(activity_fig, use_container_width=True)
        else:
            st.info("No conversation activity in the past 30 days.")
    
    # Create a dataframe from the conversations
    conversation_data = []
    
    for conv in conversations:
        # Initialize message counters safely
        try:
            # For detached objects, we need to ensure messages are loaded
            if hasattr(conv, 'messages') and conv.messages is not None:
                message_count = len(conv.messages)
                user_messages = sum(1 for msg in conv.messages if msg.role == "user")
                ai_messages = sum(1 for msg in conv.messages if msg.role == "assistant")
            else:
                # If messages aren't loaded, get a fresh conversation object
                fresh_conv = get_conversation(conv.id)
                message_count = len(fresh_conv.messages) if fresh_conv and hasattr(fresh_conv, 'messages') else 0
                user_messages = sum(1 for msg in fresh_conv.messages if msg.role == "user") if fresh_conv and hasattr(fresh_conv, 'messages') else 0
                ai_messages = sum(1 for msg in fresh_conv.messages if msg.role == "assistant") if fresh_conv and hasattr(fresh_conv, 'messages') else 0
        except Exception as e:
            # Fallback to safe values if any error occurs
            message_count = 0
            user_messages = 0
            ai_messages = 0
        
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
        
        try:
            # Get a fresh conversation with eagerly loaded messages and files
            fresh_conversation = get_conversation(selected_id)
            
            if fresh_conversation and hasattr(fresh_conversation, 'messages') and fresh_conversation.messages:
                # Display messages (limited to 5 for preview)
                message_limit = 5
                messages_to_show = fresh_conversation.messages[:message_limit]
                
                for msg in messages_to_show:
                    if msg.role == "user":
                        with st.chat_message("user"):
                            # Truncate long messages
                            content = msg.content
                            if len(content) > 300:
                                content = content[:300] + "..."
                            
                            st.write(content)
                            
                            # Show files if any
                            if hasattr(msg, 'files') and msg.files:
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
                if len(fresh_conversation.messages) > message_limit:
                    st.info(f"Showing {message_limit} of {len(fresh_conversation.messages)} messages. Open the conversation to see all.")
            else:
                st.info("No messages in this conversation. Open it to start chatting.")
        except Exception as e:
            st.error(f"Error loading conversation preview: {str(e)}")
            st.info("Try opening the conversation to view messages.")

# If the file is run directly, show the history interface
if __name__ == "__main__" or "show" not in locals():
    # Check if user is authenticated
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.error("You must be logged in to access this page.")
        st.stop()
    
    show()
