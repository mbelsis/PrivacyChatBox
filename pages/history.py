import streamlit as st
from style import apply_custom_css

# Apply custom CSS to hide default menu
apply_custom_css()
import pandas as pd
import json
from datetime import datetime

# Import custom modules
from database import get_session
from models import Conversation, Message, File, User
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
    user_role = st.session_state.get("role", "user")
    is_admin = user_role == "admin"
    
    if not user_id:
        st.error("You must be logged in to access this page.")
        return
    
    # Create tabs for History and Analytics
    history_tab, analytics_tab = st.tabs(["📜 History", "📊 Analytics"])
    
    with history_tab:
        # Get conversations based on user role
        session = get_session()
        
        if is_admin:
            # For admins, show all conversations with user information
            st.subheader("All User Conversations")
            
            # Get users for mapping
            users = {user.id: user.username for user in session.query(User).all()}
            
            # Get all conversations
            conversations = session.query(Conversation).order_by(
                Conversation.updated_at.desc()
            ).all()
            
            # Add filtering options for admins
            st.write("Filter conversations:")
            filter_col1, filter_col2 = st.columns(2)
            
            with filter_col1:
                # Create a list of all usernames with IDs
                user_options = {"All Users": None}
                user_options.update({username: uid for uid, username in users.items()})
                
                selected_user = st.selectbox(
                    "User",
                    options=list(user_options.keys()),
                    index=0
                )
                
                # Apply user filter if selected
                selected_user_id = user_options.get(selected_user)
                if selected_user_id is not None:
                    conversations = [c for c in conversations if c.user_id == selected_user_id]
            
            with filter_col2:
                # Date range filter
                date_options = ["All Time", "Today", "Past Week", "Past Month"]
                selected_date_range = st.selectbox(
                    "Date Range",
                    options=date_options,
                    index=0
                )
                
                # Apply date filter if selected
                if selected_date_range != "All Time":
                    now = datetime.now()
                    if selected_date_range == "Today":
                        date_threshold = datetime(now.year, now.month, now.day)
                    elif selected_date_range == "Past Week":
                        date_threshold = now - timedelta(days=7)
                    elif selected_date_range == "Past Month":
                        date_threshold = now - timedelta(days=30)
                    
                    conversations = [c for c in conversations if c.created_at >= date_threshold]
        else:
            # For regular users, show only their conversations
            conversations = session.query(Conversation).filter(
                Conversation.user_id == user_id
            ).order_by(Conversation.updated_at.desc()).all()
            
            if not conversations:
                st.info("You don't have any conversations yet. Start chatting to create one!")
            else:
                # Display conversations in a table
                st.subheader("Your Conversations")
        
        # Close session
        session.close()
    
    with analytics_tab:
        # Load analytics data
        from models import DetectionEvent
        from sqlalchemy.sql import func
        from privacy_scanner import get_detection_events
        import plotly.express as px
        from datetime import datetime, timedelta
        
        # Set title based on user role
        if is_admin:
            st.subheader("System-wide Analytics")
            
            # Add user filtering for admins
            session = get_session()
            users = {user.id: user.username for user in session.query(User).all()}
            session.close()
            
            # Add filtering options
            filter_col1, filter_col2 = st.columns(2)
            
            with filter_col1:
                # User filter for admins
                user_options = {"All Users": None}
                user_options.update({username: uid for uid, username in users.items()})
                
                selected_user = st.selectbox(
                    "User Analytics",
                    options=list(user_options.keys()),
                    index=0,
                    key="analytics_user_filter"
                )
                
                # Set analysis user ID based on filter
                analysis_user_id = user_options.get(selected_user)
                if analysis_user_id is None:
                    # All users mode - admin only
                    analysis_user_id = None
                    user_filter = True
                else:
                    # Specific user mode
                    user_filter = DetectionEvent.user_id == analysis_user_id
            
            with filter_col2:
                # Date range filter
                date_options = ["All Time", "Today", "Past Week", "Past Month"]
                selected_date_range = st.selectbox(
                    "Date Range",
                    options=date_options,
                    index=0,
                    key="analytics_date_filter"
                )
                
                # Set date range
                now = datetime.now()
                if selected_date_range == "Today":
                    date_threshold = datetime(now.year, now.month, now.day)
                    date_filter = DetectionEvent.timestamp >= date_threshold
                elif selected_date_range == "Past Week":
                    date_threshold = now - timedelta(days=7)
                    date_filter = DetectionEvent.timestamp >= date_threshold
                elif selected_date_range == "Past Month":
                    date_threshold = now - timedelta(days=30)
                    date_filter = DetectionEvent.timestamp >= date_threshold
                else:
                    # All time
                    date_filter = True
        else:
            st.subheader("Your Usage Analytics")
            analysis_user_id = user_id
            # Regular users can only see their own data
            user_filter = DetectionEvent.user_id == user_id
            date_filter = True
        
        # Initialize analytics metrics
        total_conversations = 0
        total_messages = 0
        total_detection_events = 0
        total_dlp_blocks = 0
        detection_by_severity = {"low": 0, "medium": 0, "high": 0}
        detection_by_action = {"scan": 0, "anonymize": 0, "block_sensitive_file": 0}
        conversations_by_date = {}
        users_by_conversation_count = {}
        
        try:
            # Calculate metrics with error handling
            with get_session() as session:
                if session:
                    # Create base queries for conversations
                    if analysis_user_id is not None:
                        # Single user queries
                        conversation_base_query = session.query(Conversation).filter(Conversation.user_id == analysis_user_id)
                        detection_base_query = session.query(DetectionEvent).filter(DetectionEvent.user_id == analysis_user_id)
                    else:
                        # All users queries (admin only)
                        conversation_base_query = session.query(Conversation)
                        detection_base_query = session.query(DetectionEvent)
                    
                    # Count conversations
                    total_conversations = conversation_base_query.count()
                    
                    # Count messages
                    if analysis_user_id is not None:
                        # For a specific user
                        total_messages = session.query(Message).join(
                            Conversation, Message.conversation_id == Conversation.id
                        ).filter(Conversation.user_id == analysis_user_id).count()
                    else:
                        # For all users
                        total_messages = session.query(Message).count()
                    
                    # Count detection events
                    total_detection_events = detection_base_query.count()
                    
                    # Get severity breakdown - safely handle different cases
                    severity_query = session.query(
                        DetectionEvent.severity, 
                        func.count(DetectionEvent.id)
                    )
                    
                    if analysis_user_id is not None:
                        severity_query = severity_query.filter(DetectionEvent.user_id == analysis_user_id)
                        
                    severity_counts = severity_query.group_by(DetectionEvent.severity).all()
                    
                    # Convert to dictionary format safely
                    for severity, count in severity_counts:
                        if severity in detection_by_severity:
                            detection_by_severity[severity] = count
                    
                    # Get action type breakdown
                    action_query = session.query(
                        DetectionEvent.action, 
                        func.count(DetectionEvent.id)
                    )
                    
                    if analysis_user_id is not None:
                        action_query = action_query.filter(DetectionEvent.user_id == analysis_user_id)
                        
                    action_counts = action_query.group_by(DetectionEvent.action).all()
                    
                    # Convert to dictionary format safely
                    for action, count in action_counts:
                        if action in detection_by_action:
                            detection_by_action[action] = count
                    
                    # Count DLP blocks specifically
                    total_dlp_blocks = detection_by_action.get("block_sensitive_file", 0)
                    
                    # Get counts by date for the past 30 days
                    thirty_days_ago = datetime.now() - timedelta(days=30)
                    
                    date_query = session.query(
                        func.date(Conversation.created_at),
                        func.count(Conversation.id)
                    )
                    
                    if analysis_user_id is not None:
                        date_query = date_query.filter(Conversation.user_id == analysis_user_id)
                        
                    conversations_by_date_query = date_query.filter(
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
                    
                    # For admin view, get conversation counts by user
                    if is_admin and analysis_user_id is None:
                        user_conversation_counts = session.query(
                            Conversation.user_id,
                            func.count(Conversation.id)
                        ).group_by(Conversation.user_id).all()
                        
                        for user_id_val, count in user_conversation_counts:
                            user_name = users.get(user_id_val, f"User {user_id_val}")
                            users_by_conversation_count[user_name] = count
        except Exception as e:
            st.error(f"Error loading analytics data: {str(e)}")
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Conversations", total_conversations)
        
        with col2:
            st.metric("Total Messages", total_messages)
        
        with col3:
            st.metric("Privacy Events", total_detection_events)
            
        with col4:
            st.metric("Blocked Sensitive Files", total_dlp_blocks)
        
        # Create data for charts
        st.subheader("Privacy Detection Analysis")
        severity_df = pd.DataFrame({
            "Severity": list(detection_by_severity.keys()),
            "Count": list(detection_by_severity.values())
        })
        
        # Create columns for side-by-side charts
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
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
                    hole=0.4,
                    title="By Severity"
                )
                fig.update_layout(margin=dict(t=30, b=0, l=0, r=0))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No privacy detection events recorded yet.")
        
        with chart_col2:
            # Create action type chart
            action_df = pd.DataFrame({
                "Action": [
                    "Content Scan", 
                    "Content Anonymization",
                    "Blocked Sensitive Files"
                ],
                "Count": [
                    detection_by_action.get("scan", 0),
                    detection_by_action.get("anonymize", 0),
                    detection_by_action.get("block_sensitive_file", 0)
                ]
            })
            
            if action_df["Count"].sum() > 0:
                action_fig = px.pie(
                    action_df,
                    values="Count",
                    names="Action",
                    color="Action",
                    color_discrete_map={
                        "Content Scan": "#42A5F5",  # Blue
                        "Content Anonymization": "#AB47BC",  # Purple
                        "Blocked Sensitive Files": "#F44336"  # Red
                    },
                    hole=0.4,
                    title="By Action Type"
                )
                action_fig.update_layout(margin=dict(t=30, b=0, l=0, r=0))
                st.plotly_chart(action_fig, use_container_width=True)
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
        
        # For admin view, show user distribution chart
        if is_admin and analysis_user_id is None and users_by_conversation_count:
            st.subheader("Conversation Distribution by User")
            user_df = pd.DataFrame({
                "User": list(users_by_conversation_count.keys()),
                "Conversations": list(users_by_conversation_count.values())
            })
            
            # Sort by conversation count
            user_df = user_df.sort_values("Conversations", ascending=False)
            
            # Create bar chart
            user_fig = px.bar(
                user_df,
                x="User",
                y="Conversations",
                color="Conversations",
                color_continuous_scale="Viridis",
                title="Users by Conversation Count"
            )
            user_fig.update_layout(margin=dict(t=50, b=50, l=20, r=20))
            st.plotly_chart(user_fig, use_container_width=True)
    
    # Create a dataframe from the conversations
    conversation_data = []
    
    # Get usernames for admin view
    if is_admin:
        session = get_session()
        users = {user.id: user.username for user in session.query(User).all()}
        session.close()
    
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
        
        # Create conversation data dict
        conv_data = {
            "ID": conv.id,
            "Title": conv.title,
            "Created": created_date,
            "Last Updated": updated_date,
            "Messages": message_count,
            "User Msgs": user_messages,
            "AI Msgs": ai_messages
        }
        
        # Add username for admin view
        if is_admin:
            username = users.get(conv.user_id, f"User {conv.user_id}")
            conv_data["Username"] = username
        
        # Add to data
        conversation_data.append(conv_data)
    
    # Create dataframe
    df = pd.DataFrame(conversation_data)
    
    # Display the table with column configuration based on user role
    column_config = {
        "ID": st.column_config.Column("ID", width="small"),
        "Title": st.column_config.Column("Title", width="medium"),
        "Created": st.column_config.Column("Created", width="medium"),
        "Last Updated": st.column_config.Column("Last Updated", width="medium"),
        "Messages": st.column_config.Column("Messages", width="small"),
        "User Msgs": st.column_config.Column("User Msgs", width="small"),
        "AI Msgs": st.column_config.Column("AI Msgs", width="small")
    }
    
    # Add Username column for admin view
    if is_admin:
        column_config["Username"] = st.column_config.Column("Username", width="medium")
    
    # Display dataframe with configured columns
    st.dataframe(
        df,
        column_config=column_config,
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
