import streamlit as st
import pandas as pd
from datetime import datetime

# Import custom modules
from database import get_session
from models import User, Settings, DetectionEvent, Conversation
from auth import create_user, delete_user, update_user_role
from privacy_scanner import get_detection_events
from utils import format_detection_events

def show():
    """Main function to display the admin panel"""
    # Page settings
    st.title("👑 Admin Panel")
    
    # Get user information
    user_id = st.session_state.user_id
    role = st.session_state.role
    
    # Check if user is admin
    if role != "admin":
        st.error("You do not have permission to access this page.")
        return
    
    # Create tabs for different admin functions
    user_tab, stats_tab, logs_tab = st.tabs(["User Management", "System Statistics", "Privacy Logs"])
    
    # User Management tab
    with user_tab:
        st.subheader("User Management")
        
        # Get all users
        session = get_session()
        users = session.query(User).all()
        session.close()
        
        # Create a dataframe from users
        user_data = []
        
        for user in users:
            user_data.append({
                "ID": user.id,
                "Username": user.username,
                "Role": user.role,
                "Created": user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else ""
            })
        
        # Display user table
        st.dataframe(
            pd.DataFrame(user_data),
            column_config={
                "ID": st.column_config.Column("ID", width="small"),
                "Username": st.column_config.Column("Username", width="medium"),
                "Role": st.column_config.Column("Role", width="small"),
                "Created": st.column_config.Column("Created", width="medium")
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Create sections for user actions
        st.markdown("---")
        
        # Create new user
        st.subheader("Create New User")
        
        new_username = st.text_input("Username", key="new_username")
        new_password = st.text_input("Password", type="password", key="new_password")
        new_role = st.selectbox("Role", ["user", "admin"], index=0, key="new_role")
        
        if st.button("Create User"):
            if not new_username or not new_password:
                st.error("Username and password are required")
            else:
                success = create_user(new_username, new_password, role=new_role)
                if success:
                    st.success(f"User '{new_username}' created successfully")
                    st.rerun()
                else:
                    st.error("Failed to create user. Username may already exist.")
        
        # Modify user role
        st.markdown("---")
        st.subheader("Modify User Role")
        
        # Let admin select a user
        user_options = {f"{user.username} (ID: {user.id})": user.id for user in users}
        selected_user_display = st.selectbox("Select User", list(user_options.keys()), key="modify_user")
        selected_user_id = user_options[selected_user_display]
        
        # Get current role
        session = get_session()
        selected_user = session.query(User).filter(User.id == selected_user_id).first()
        session.close()
        
        if selected_user:
            current_role = selected_user.role
            new_role = st.selectbox(
                "New Role", 
                ["user", "admin"], 
                index=0 if current_role == "user" else 1,
                key="change_role"
            )
            
            if st.button("Update Role"):
                if selected_user_id == user_id and new_role != "admin":
                    st.error("You cannot remove your own admin privileges")
                else:
                    success = update_user_role(selected_user_id, new_role)
                    if success:
                        st.success(f"User role updated to '{new_role}'")
                        st.rerun()
                    else:
                        st.error("Failed to update user role")
        
        # Delete user
        st.markdown("---")
        st.subheader("Delete User")
        
        # Let admin select a user
        delete_user_display = st.selectbox("Select User", list(user_options.keys()), key="delete_user")
        delete_user_id = user_options[delete_user_display]
        
        if st.button("Delete User"):
            if delete_user_id == user_id:
                st.error("You cannot delete your own account")
            else:
                # Confirm deletion
                st.warning(f"Are you sure you want to delete user '{delete_user_display.split(' (ID:')[0]}'? This action cannot be undone.")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Yes, delete user", key="confirm_delete"):
                        success = delete_user(delete_user_id)
                        if success:
                            st.success("User deleted successfully")
                            st.rerun()
                        else:
                            st.error("Failed to delete user")
                
                with col2:
                    if st.button("Cancel", key="cancel_delete"):
                        st.rerun()
    
    # System Statistics tab
    with stats_tab:
        st.subheader("System Statistics")
        
        # Get system statistics
        session = get_session()
        
        total_users = session.query(User).count()
        total_conversations = session.query(Conversation).count()
        total_detection_events = session.query(DetectionEvent).count()
        
        # Get user with most conversations
        from sqlalchemy import func
        
        most_conversations_query = session.query(
            User.username,
            User.id,
            func.count(Conversation.id).label('count')
        ).join(Conversation, User.id == Conversation.user_id, isouter=True)\
         .group_by(User.id)\
         .order_by(func.count(Conversation.id).desc())\
         .first()
        
        # Get latest detection event
        latest_event = session.query(DetectionEvent).order_by(DetectionEvent.timestamp.desc()).first()
        
        # Close session
        session.close()
        
        # Display statistics in columns
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Users", total_users)
        
        with col2:
            st.metric("Total Conversations", total_conversations)
        
        with col3:
            st.metric("Detection Events", total_detection_events)
        
        # Display additional statistics
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if most_conversations_query:
                username, user_id, count = most_conversations_query
                st.write(f"**Most Active User**: {username} ({count} conversations)")
        
        with col2:
            if latest_event:
                event_time = latest_event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                st.write(f"**Latest Detection Event**: {event_time} ({latest_event.action}, {latest_event.severity})")
    
    # Privacy Logs tab
    with logs_tab:
        st.subheader("Privacy Detection Logs")
        
        # Filter options
        st.write("Filter detection events:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Get all users for filter
            session = get_session()
            all_users = session.query(User).all()
            session.close()
            
            user_filter_options = {f"{user.username} (ID: {user.id})": user.id for user in all_users}
            user_filter_options["All Users"] = None
            
            selected_user_filter = st.selectbox(
                "User", 
                ["All Users"] + [f"{user.username} (ID: {user.id})" for user in all_users],
                key="log_user_filter"
            )
            selected_user_id_filter = user_filter_options[selected_user_filter]
        
        with col2:
            action_filter = st.selectbox(
                "Action Type",
                ["All", "scan", "anonymize"],
                key="log_action_filter"
            )
        
        # Get detection events based on filters
        session = get_session()
        
        query = session.query(DetectionEvent)
        
        if selected_user_id_filter is not None:
            query = query.filter(DetectionEvent.user_id == selected_user_id_filter)
        
        if action_filter != "All":
            query = query.filter(DetectionEvent.action == action_filter)
        
        # Order by timestamp
        query = query.order_by(DetectionEvent.timestamp.desc())
        
        # Limit results
        events = query.limit(100).all()
        
        # Close session
        session.close()
        
        # Format events for display
        formatted_events = format_detection_events(events)
        
        # Display events
        if formatted_events:
            st.write(f"Showing {len(formatted_events)} most recent events:")
            
            # Convert to dataframe for display
            events_data = []
            
            for event in formatted_events:
                # Get username
                username = ""
                for user in all_users:
                    if user.id == event["id"]:
                        username = user.username
                        break
                
                events_data.append({
                    "Timestamp": event["timestamp"],
                    "Action": event["action"].capitalize(),
                    "Severity": event["severity"].capitalize(),
                    "Detections": event["detection_count"],
                    "File": event["file_names"] if event["file_names"] else "N/A"
                })
            
            # Display dataframe
            st.dataframe(
                pd.DataFrame(events_data),
                column_config={
                    "Timestamp": st.column_config.Column("Timestamp", width="medium"),
                    "Action": st.column_config.Column("Action", width="small"),
                    "Severity": st.column_config.Column("Severity", width="small"),
                    "Detections": st.column_config.Column("Detections", width="small"),
                    "File": st.column_config.Column("File", width="medium")
                },
                hide_index=True,
                use_container_width=True
            )
            
            # Let admin view details of an event
            st.markdown("---")
            st.subheader("View Event Details")
            
            # Create a dropdown with event timestamps
            event_options = {event["timestamp"]: i for i, event in enumerate(formatted_events)}
            selected_event_time = st.selectbox("Select event timestamp", list(event_options.keys()))
            selected_event_index = event_options[selected_event_time]
            selected_event = formatted_events[selected_event_index]
            
            # Display event details
            st.write(f"**Timestamp**: {selected_event['timestamp']}")
            st.write(f"**Action**: {selected_event['action']}")
            st.write(f"**Severity**: {selected_event['severity']}")
            
            if selected_event["file_names"]:
                st.write(f"**File**: {selected_event['file_names']}")
            
            # Display detected patterns
            st.write("**Detected Patterns**:")
            
            for pattern_type, matches in selected_event["detected_patterns"].items():
                st.write(f"- **{pattern_type}**: {', '.join(matches[:3])}" + 
                       (f" and {len(matches) - 3} more" if len(matches) > 3 else ""))
        else:
            st.info("No detection events found matching the filters.")

# If the file is run directly, show the admin interface
if __name__ == "__main__" or "show" not in locals():
    # Check if user is authenticated and is an admin
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.error("You must be logged in to access this page.")
        st.stop()
    
    if "role" not in st.session_state or st.session_state.role != "admin":
        st.error("You do not have permission to access this page.")
        st.stop()
    
    show()
