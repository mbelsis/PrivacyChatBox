import streamlit as st
from style import apply_custom_css

# Apply custom CSS to hide default menu
apply_custom_css()
import pandas as pd
import json
from datetime import datetime, timedelta

# Import custom modules
from database import get_session
from models import Conversation, Message, File, User, DetectionEvent
from utils import delete_conversation, get_conversation
from pdf_export import export_conversation_to_pdf
import shared_sidebar
from page_logic import (
    build_history_conversation_rows,
    build_privacy_alert_index,
    conversation_has_privacy_alert,
)

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
    conversations = []
    users = {}
    
    with history_tab:
        # Get conversations based on user role
        session = get_session()
        if not session:
            st.error("Unable to connect to database. Please try again later.")
            return
        
        if is_admin:
            # For admins, show all conversations with user information
            st.subheader("All User Conversations")
            
            # Get users for mapping
            users = {user.id: user.username for user in session.query(User).all()}
            
            # Get all conversations
            conversation_rows = session.query(Conversation).order_by(
                Conversation.updated_at.desc()
            ).all()
            conversations = [
                {
                    "id": conv.id,
                    "user_id": conv.user_id,
                    "title": conv.title,
                    "created_at": conv.created_at,
                    "updated_at": conv.updated_at,
                }
                for conv in conversation_rows
            ]
            
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
                    conversations = [c for c in conversations if c["user_id"] == selected_user_id]
            
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
                    
                    conversations = [c for c in conversations if c["created_at"] >= date_threshold]
        else:
            # For regular users, show only their conversations
            conversation_rows = session.query(Conversation).filter(
                Conversation.user_id == user_id
            ).order_by(Conversation.updated_at.desc()).all()
            conversations = [
                {
                    "id": conv.id,
                    "user_id": conv.user_id,
                    "title": conv.title,
                    "created_at": conv.created_at,
                    "updated_at": conv.updated_at,
                }
                for conv in conversation_rows
            ]
            
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
            if not session:
                st.error("Unable to connect to database. Please try again later.")
                return
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
                    detection_date_filter = DetectionEvent.timestamp >= date_threshold
                    conversation_date_filter = Conversation.created_at >= date_threshold
                elif selected_date_range == "Past Week":
                    date_threshold = now - timedelta(days=7)
                    detection_date_filter = DetectionEvent.timestamp >= date_threshold
                    conversation_date_filter = Conversation.created_at >= date_threshold
                elif selected_date_range == "Past Month":
                    date_threshold = now - timedelta(days=30)
                    detection_date_filter = DetectionEvent.timestamp >= date_threshold
                    conversation_date_filter = Conversation.created_at >= date_threshold
                else:
                    # All time
                    detection_date_filter = True
                    conversation_date_filter = True
        else:
            st.subheader("Your Usage Analytics")
            analysis_user_id = user_id
            # Regular users can only see their own data
            user_filter = DetectionEvent.user_id == user_id
            detection_date_filter = True
            conversation_date_filter = True
        
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
            session = get_session()
            if not session:
                st.error("Unable to connect to database. Please try again later.")
                return
            try:
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
                    
                    if conversation_date_filter is not True:
                        conversation_base_query = conversation_base_query.filter(conversation_date_filter)
                    if detection_date_filter is not True:
                        detection_base_query = detection_base_query.filter(detection_date_filter)

                    # Count conversations
                    total_conversations = conversation_base_query.count()
                    
                    # Count messages
                    if analysis_user_id is not None:
                        # For a specific user
                        total_messages_query = session.query(Message).join(
                            Conversation, Message.conversation_id == Conversation.id
                        ).filter(Conversation.user_id == analysis_user_id)
                    else:
                        # For all users
                        total_messages_query = session.query(Message).join(
                            Conversation, Message.conversation_id == Conversation.id
                        )
                    if conversation_date_filter is not True:
                        total_messages_query = total_messages_query.filter(conversation_date_filter)
                    total_messages = total_messages_query.count()

                    # Count detection events
                    total_detection_events = detection_base_query.count()
                    
                    # Get severity breakdown - safely handle different cases
                    severity_query = session.query(
                        DetectionEvent.severity, 
                        func.count(DetectionEvent.id)
                    )
                    
                    if analysis_user_id is not None:
                        severity_query = severity_query.filter(DetectionEvent.user_id == analysis_user_id)
                    if detection_date_filter is not True:
                        severity_query = severity_query.filter(detection_date_filter)
                        
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
                    if detection_date_filter is not True:
                        action_query = action_query.filter(detection_date_filter)
                        
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
                    if conversation_date_filter is not True:
                        date_query = date_query.filter(conversation_date_filter)
                        
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
            finally:
                session.close()
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
    
    # Nothing to list: stop before building the table/select box. Indexing the select box
    # result on an empty option list used to raise ``KeyError: None``.
    if not conversations:
        if is_admin:
            st.info("No conversations match the selected filters.")
        return

    # Create a dataframe from the conversations
    conversation_data = []
    
    # Check for privacy alerts in conversations
    # First, get relevant detection events to find which conversations have privacy issues
    detection_events = []
    if conversations:
        conversation_user_ids = list({conv["user_id"] for conv in conversations})
        conversation_updated_times = [conv["updated_at"] for conv in conversations if conv.get("updated_at")]
        earliest_update = min(conversation_updated_times) - timedelta(minutes=15) if conversation_updated_times else None
        latest_update = max(conversation_updated_times) + timedelta(minutes=15) if conversation_updated_times else None

        session = get_session()
        if session:
            try:
                event_query = session.query(DetectionEvent)
                if not is_admin:
                    event_query = event_query.filter(DetectionEvent.user_id == user_id)
                elif conversation_user_ids:
                    event_query = event_query.filter(DetectionEvent.user_id.in_(conversation_user_ids))

                if earliest_update and latest_update:
                    event_query = event_query.filter(
                        DetectionEvent.timestamp >= earliest_update,
                        DetectionEvent.timestamp <= latest_update
                    )

                detection_events = [
                    {"user_id": event.user_id, "timestamp": event.timestamp}
                    for event in event_query.order_by(DetectionEvent.timestamp.desc()).all()
                ]
            finally:
                session.close()
    
    # Create a quick lookup dictionary to check if a message/conversation has associated privacy events
    # We'll assume a privacy event is associated with a conversation 
    # if it happened around the same time as the conversation was updated
    privacy_alerts = build_privacy_alert_index(detection_events)
    
    message_counts = {}
    conversation_ids = [conv["id"] for conv in conversations]
    if conversation_ids:
        session = get_session()
        if session:
            try:
                from sqlalchemy.sql import func
                count_rows = session.query(
                    Message.conversation_id,
                    Message.role,
                    func.count(Message.id)
                ).filter(
                    Message.conversation_id.in_(conversation_ids)
                ).group_by(
                    Message.conversation_id,
                    Message.role
                ).all()

                for conversation_id, role_name, count in count_rows:
                    message_counts.setdefault(conversation_id, {"total": 0, "user": 0, "assistant": 0})
                    message_counts[conversation_id]["total"] += count
                    if role_name == "user":
                        message_counts[conversation_id]["user"] = count
                    elif role_name == "assistant":
                        message_counts[conversation_id]["assistant"] = count
            finally:
                session.close()

    conversation_data = build_history_conversation_rows(
        conversations=conversations,
        message_counts=message_counts,
        privacy_alerts=privacy_alerts,
        is_admin=is_admin,
        users=users,
    )
    
    # Create dataframe
    df = pd.DataFrame(conversation_data)
    
    # Display the table with column configuration based on user role
    column_config = {
        "ID": st.column_config.Column("ID", width="small"),
        "Title": st.column_config.Column("Title", width="medium"),
        "Created": st.column_config.Column("Created", width="medium"),
        "Last Updated": st.column_config.Column("Last Updated", width="medium"),
        "Privacy Alert": st.column_config.Column("Privacy Alert", width="small", help="⚠️ indicates privacy concerns detected in this conversation"),
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
    
    # Conversation actions section - different for admin vs regular users
    st.subheader("Conversation Actions")
    
    # Let user select a conversation
    conversation_options = {
        f"{conv['title']} (ID: {conv['id']})": conv["id"] for conv in conversations
    }
    selected_title = st.selectbox("Select a conversation", list(conversation_options.keys()))
    selected_id = conversation_options[selected_title]
    
    # Get the selected conversation details
    selected_conversation = next((c for c in conversations if c["id"] == selected_id), None)
    
    if selected_conversation:
        # Check if admin is viewing someone else's conversation
        is_admin_viewing_others = is_admin and selected_conversation["user_id"] != user_id
        
        # For regular users or admins viewing their own conversations
        if not is_admin_viewing_others:
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
                            pdf_path = export_conversation_to_pdf(
                                selected_id,
                                requesting_user_id=user_id,
                                allow_admin_access=is_admin and not is_admin_viewing_others
                            )
                        
                        # Provide download link
                        with open(pdf_path, "rb") as pdf_file:
                            pdf_bytes = pdf_file.read()
                        try:
                            import os
                            os.remove(pdf_path)
                        except OSError:
                            pass
                        
                        st.download_button(
                            label="Download PDF",
                            data=pdf_bytes,
                            file_name=f"conversation_{selected_id}.pdf",
                            mime="application/pdf"
                        )
                    except Exception as e:
                        st.error(f"Error generating PDF: {str(e)}")
            
            with col3:
                # Delete conversation with confirmation. The confirmation state has to live
                # in session_state: a button nested inside another button's ``if`` is never
                # reached on the rerun triggered by clicking it.
                if st.button("Delete Conversation", key="delete_btn"):
                    st.session_state["pending_delete_conversation_id"] = selected_id

            if st.session_state.get("pending_delete_conversation_id") == selected_id:
                st.warning(f"Are you sure you want to delete '{selected_conversation['title']}'? This action cannot be undone.")
                
                confirm_col1, confirm_col2 = st.columns(2)
                
                with confirm_col1:
                    if st.button("Yes, delete it", key="confirm_delete"):
                        st.session_state.pop("pending_delete_conversation_id", None)
                        # Delete the conversation
                        success = delete_conversation(selected_id, requesting_user_id=user_id)
                        
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
                        st.session_state.pop("pending_delete_conversation_id", None)
                        st.rerun()
            
            # Display conversation preview for user's own conversations
            st.subheader("Conversation Preview")
            
            try:
                # Get a fresh conversation with eagerly loaded messages and files
                fresh_conversation = get_conversation(selected_id, requesting_user_id=user_id, allow_admin_access=is_admin)
                
                # Check if this conversation has privacy alerts
                has_privacy_alert = conversation_has_privacy_alert(selected_conversation, privacy_alerts)
                
                # Display privacy alert if detected
                if has_privacy_alert:
                    st.warning("⚠️ Privacy Alert: This conversation contains messages with potentially sensitive information that triggered privacy scanning alerts.")
                
                fresh_messages = fresh_conversation.get("messages", []) if fresh_conversation else []
                if fresh_messages:
                    # Display messages (limited to 5 for preview)
                    message_limit = 5
                    messages_to_show = fresh_messages[:message_limit]
                    
                    for msg in messages_to_show:
                        if msg.get("role") == "user":
                            with st.chat_message("user"):
                                # Truncate long messages
                                content = msg.get("content", "")
                                if len(content) > 300:
                                    content = content[:300] + "..."
                                
                                st.write(content)
                                
                                # Show files if any
                                for file in msg.get("files", []):
                                    st.caption(f"File: {file['original_name']}")
                        else:
                            with st.chat_message("assistant"):
                                # Truncate long messages
                                content = msg.get("content", "")
                                if len(content) > 300:
                                    content = content[:300] + "..."
                                
                                st.write(content)
                    
                    # Show a message if there are more messages
                    if len(fresh_messages) > message_limit:
                        st.info(f"Showing {message_limit} of {len(fresh_messages)} messages. Open the conversation to see all.")
                else:
                    st.info("No messages in this conversation. Open it to start chatting.")
            except Exception as e:
                st.error(f"Error loading conversation preview: {str(e)}")
                st.info("Try opening the conversation to view messages.")
        
        # For admins viewing other users' conversations - privacy-focused view
        else:
            st.info("⚠️ Privacy Notice: For data privacy reasons, administrators cannot view the content of users' conversations. Only metadata is available.")
            
            # Get privacy events related to this conversation if any
            try:
                session = get_session()
                if not session:
                    st.error("Unable to connect to database. Please try again later.")
                    return
                try:
                    # Check if this conversation has any messages with files
                    message_with_files = session.query(Message).filter(
                        Message.conversation_id == selected_id,
                        Message.files.any()
                    ).first() is not None
                    
                    # Check if this conversation has privacy alerts
                    has_privacy_alert = conversation_has_privacy_alert(selected_conversation, privacy_alerts)
                    
                    # Get detailed stats about the conversation
                    user_message_count = session.query(Message).filter(
                        Message.conversation_id == selected_id,
                        Message.role == "user"
                    ).count()
                    
                    assistant_message_count = session.query(Message).filter(
                        Message.conversation_id == selected_id,
                        Message.role == "assistant"
                    ).count()
                    
                    # Get username of conversation owner
                    username = users.get(selected_conversation["user_id"], f"User {selected_conversation['user_id']}")
                    
                    # Show metadata in organized format
                    metadata_col1, metadata_col2 = st.columns(2)
                    
                    with metadata_col1:
                        st.write(f"**Title:** {selected_conversation['title']}")
                        st.write(f"**Created:** {selected_conversation['created_at'].strftime('%Y-%m-%d %H:%M')}")
                        st.write(f"**User Messages:** {user_message_count}")
                        
                    with metadata_col2:
                        st.write(f"**Owner:** {username}")
                        st.write(f"**Last Updated:** {selected_conversation['updated_at'].strftime('%Y-%m-%d %H:%M')}")
                        st.write(f"**AI Messages:** {assistant_message_count}")
                    
                    # Show additional information about file attachments
                    if message_with_files:
                        st.write("**Files:** This conversation contains file attachments")
                    
                    # Show privacy alert if detected
                    if has_privacy_alert:
                        st.warning("⚠️ **Privacy Alert:** This conversation contains messages with potentially sensitive information that triggered privacy scanning alerts.")
                    
                    # Admin actions for other users' conversations - limited to delete only
                    if st.button("Delete Conversation (Admin Action)", key="admin_delete_btn"):
                        st.session_state["pending_admin_delete_conversation_id"] = selected_id

                    if st.session_state.get("pending_admin_delete_conversation_id") == selected_id:
                        st.warning(f"Are you sure you want to delete this conversation? This action cannot be undone.")
                        
                        confirm_col1, confirm_col2 = st.columns(2)
                        
                        with confirm_col1:
                            if st.button("Yes, delete it", key="admin_confirm_delete"):
                                st.session_state.pop("pending_admin_delete_conversation_id", None)
                                # Delete the conversation
                                success = delete_conversation(selected_id, allow_admin_access=True)
                                
                                if success:
                                    st.success("Conversation deleted successfully.")
                                    st.rerun()
                                else:
                                    st.error("Failed to delete conversation.")
                        
                        with confirm_col2:
                            if st.button("Cancel", key="admin_cancel_delete"):
                                st.session_state.pop("pending_admin_delete_conversation_id", None)
                                st.rerun()
                finally:
                    session.close()
            
            except Exception as e:
                st.error(f"Error loading conversation metadata: {str(e)}")

# If the file is run directly, show the history interface
if __name__ == "__main__" or "show" not in locals():
    # Check if user is authenticated
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.error("You must be logged in to access this page.")
        st.stop()
    
    show()
