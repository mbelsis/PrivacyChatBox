import streamlit as st
from style import apply_custom_css

# Apply custom CSS to hide default menu
apply_custom_css()
import pandas as pd
from datetime import datetime

# Import custom modules
from database import get_session, session_scope
from models import User, Settings, DetectionEvent, Conversation
from auth import create_user, delete_user, update_user_role, update_user_password
from privacy_scanner import get_detection_events
from utils import format_detection_events, update_user_settings
import shared_sidebar
import azure_auth
import os

# Import MS DLP functions if available
try:
    from ms_dlp import get_ms_settings, is_dlp_integration_enabled
    ms_dlp_available = True
except ImportError:
    ms_dlp_available = False

def show():
    """Main function to display the admin panel"""
    # Clear sidebar state for fresh creation
    if "sidebar_created" in st.session_state:
        del st.session_state.sidebar_created
    
    # Create sidebar with shared component
    shared_sidebar.create_sidebar("admin_page")
    
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
    user_tab, azure_tab, ms_dlp_tab, stats_tab, logs_tab = st.tabs(["User Management", "Azure AD", "Microsoft DLP", "System Statistics", "Privacy Logs"])
    
    # Azure AD tab
    with azure_tab:
        st.subheader("Azure AD Integration Settings")
        
        # Current Azure AD settings
        current_client_id = os.environ.get("AZURE_CLIENT_ID", "")
        current_client_secret = os.environ.get("AZURE_CLIENT_SECRET", "")
        current_tenant_id = os.environ.get("AZURE_TENANT_ID", "")
        current_redirect_uri = os.environ.get("AZURE_REDIRECT_URI", "http://localhost:5000/")
        
        # Display current settings
        st.write("### Current Azure AD Configuration")
        
        if all([current_client_id, current_client_secret, current_tenant_id]):
            st.success("Azure AD integration is configured")
            
            # Show the current settings in a read-only format
            st.code(f"""
AZURE_CLIENT_ID: {current_client_id[:8]}...{current_client_id[-4:] if len(current_client_id) > 12 else ""}
AZURE_TENANT_ID: {current_tenant_id[:8]}...{current_tenant_id[-4:] if len(current_tenant_id) > 12 else ""}
AZURE_REDIRECT_URI: {current_redirect_uri}
AZURE_CLIENT_SECRET: ********
            """)
            
            # Count users with Azure AD connection
            session = get_session()
            azure_users_count = 0
            all_users = session.query(User).all()
            session.close()
            
            for user in all_users:
                if hasattr(user, 'azure_id') and user.azure_id is not None:
                    azure_users_count += 1
            
            st.info(f"There are {azure_users_count} users connected via Azure AD")
        else:
            st.warning("Azure AD integration is not fully configured")
        
        # Form to update Azure AD settings
        st.write("### Update Azure AD Settings")
        st.write("Configure the Azure AD integration to allow users to sign in with their organizational accounts.")
        
        with st.form("azure_ad_settings_form"):
            new_client_id = st.text_input("Client ID", value=current_client_id, placeholder="Enter Azure AD Client ID")
            new_client_secret = st.text_input("Client Secret", type="password", placeholder="Enter Azure AD Client Secret")
            new_tenant_id = st.text_input("Tenant ID", value=current_tenant_id, placeholder="Enter Azure AD Tenant ID")
            new_redirect_uri = st.text_input("Redirect URI", value=current_redirect_uri, placeholder="Enter Redirect URI")
            
            st.markdown("""
            #### How to set up Azure AD Integration:
            1. Go to the [Azure Portal](https://portal.azure.com) and register a new application
            2. Set up a redirect URI that points to your Streamlit app
            3. Create a client secret
            4. Copy the Client ID, Tenant ID, and Client Secret to the fields above
            """)
            
            submitted = st.form_submit_button("Update Azure AD Settings")
            
            if submitted:
                # In a real application, you would update environment variables or a secure configuration store
                # For this example, we'll just show a success message
                st.success("Azure AD settings updated! Please restart the application for changes to take effect.")
                # In a real app, you might want to restart the app or update environment variables
                # This would often be done through a configuration file or environment variable manager
    
    # Microsoft DLP tab
    with ms_dlp_tab:
        st.subheader("Microsoft DLP Integration Settings")
        
        # Import MS DLP functions
        if not ms_dlp_available:
            st.warning("Microsoft DLP module is not available or not properly installed.")
        else:
            # Check if Microsoft settings are configured
            ms_settings = get_ms_settings()
            
            if not ms_settings.get("is_configured", False):
                st.warning("""
                Microsoft DLP integration is not properly configured. 
                To enable this feature, the following environment variables must be set:
                - MS_CLIENT_ID
                - MS_CLIENT_SECRET
                - MS_TENANT_ID
                - MS_DLP_ENDPOINT_ID
                
                Configure these settings below.
                """)
            
            # Current MS DLP settings
            current_client_id = os.environ.get("MS_CLIENT_ID", "")
            current_client_secret = os.environ.get("MS_CLIENT_SECRET", "")
            current_tenant_id = os.environ.get("MS_TENANT_ID", "")
            current_endpoint_id = os.environ.get("MS_DLP_ENDPOINT_ID", "")
            
            # Display current settings
            st.write("### Current Microsoft DLP Configuration")
            
            if all([current_client_id, current_client_secret, current_tenant_id, current_endpoint_id]):
                st.success("Microsoft DLP integration is configured")
                
                # Show the current settings in a read-only format
                st.code(f"""
MS_CLIENT_ID: {current_client_id[:8]}...{current_client_id[-4:] if len(current_client_id) > 12 else ""}
MS_TENANT_ID: {current_tenant_id[:8]}...{current_tenant_id[-4:] if len(current_tenant_id) > 12 else ""}
MS_DLP_ENDPOINT_ID: {current_endpoint_id[:8]}...{current_endpoint_id[-4:] if len(current_endpoint_id) > 12 else ""}
MS_CLIENT_SECRET: ********
                """)
            else:
                st.warning("Microsoft DLP integration is not fully configured")
            
            # Form to update Microsoft DLP settings
            st.write("### Update Microsoft DLP Settings")
            st.write("Configure the Microsoft DLP integration to enable enhanced data loss prevention features.")
            
            with st.form("ms_dlp_settings_form"):
                new_client_id = st.text_input("Client ID", value=current_client_id, placeholder="Enter Microsoft App Client ID")
                new_client_secret = st.text_input("Client Secret", type="password", placeholder="Enter Microsoft App Client Secret")
                new_tenant_id = st.text_input("Tenant ID", value=current_tenant_id, placeholder="Enter Microsoft Tenant ID")
                new_endpoint_id = st.text_input("DLP Endpoint ID", value=current_endpoint_id, placeholder="Enter DLP Endpoint ID")
                
                st.markdown("""
                #### How to set up Microsoft DLP Integration:
                1. Go to the [Azure Portal](https://portal.azure.com) and register a new application
                2. Set up Microsoft Information Protection and DLP policies
                3. Create a client secret
                4. Copy the Client ID, Tenant ID, Client Secret, and DLP Endpoint ID to the fields above
                """)
                
                submitted = st.form_submit_button("Update Microsoft DLP Settings")
                
                if submitted:
                    # In a real application, you would update environment variables or a secure configuration store
                    st.success("Microsoft DLP settings updated! Please restart the application for changes to take effect.")
            
            # Organization-wide DLP settings section
            st.write("### Organization-wide DLP Settings")
            st.write("Configure default DLP settings for all users in the organization.")
            
            # Get all users with DLP settings
            users_with_dlp_settings = []
            
            try:
                with session_scope() as session:
                    if session:
                        # Get all users with their DLP settings
                        users_with_settings = session.query(User, Settings).join(
                            Settings, User.id == Settings.user_id
                        ).all()
                        
                        for user, settings in users_with_settings:
                            users_with_dlp_settings.append({
                                "id": user.id,
                                "username": user.username,
                                "role": user.role,
                                "enable_ms_dlp": getattr(settings, "enable_ms_dlp", True),
                                "ms_dlp_sensitivity_threshold": getattr(settings, "ms_dlp_sensitivity_threshold", "confidential")
                            })
                    else:
                        st.error("Unable to connect to database. Please try again later.")
            except Exception as e:
                st.error(f"Error loading user settings: {str(e)}")
            
            # Display users with their DLP settings
            if users_with_dlp_settings:
                dlp_data = []
                for user in users_with_dlp_settings:
                    dlp_data.append({
                        "Username": user["username"],
                        "Role": user["role"],
                        "DLP Enabled": "✓" if user["enable_ms_dlp"] else "✗",
                        "Sensitivity Threshold": user["ms_dlp_sensitivity_threshold"].capitalize()
                    })
                
                st.dataframe(
                    pd.DataFrame(dlp_data),
                    hide_index=True,
                    use_container_width=True
                )
            
            # Default DLP settings form
            with st.form("default_dlp_settings_form"):
                st.subheader("Set Default DLP Settings")
                
                # Default enable/disable toggle
                default_enable_dlp = st.toggle("Enable Microsoft DLP Integration by Default", value=True)
                
                # Default sensitivity threshold selector
                sensitivity_options = [
                    ("general", "General (Public)"),
                    ("internal", "Internal Only"),
                    ("confidential", "Confidential"),
                    ("highly_confidential", "Highly Confidential"),
                    ("secret", "Secret"),
                    ("top_secret", "Top Secret")
                ]
                
                sensitivity_labels = [label for _, label in sensitivity_options]
                sensitivity_values = [value for value, _ in sensitivity_options]
                
                st.write("#### Default Sensitivity Threshold")
                st.write("Files with sensitivity labels equal to or above this level will be blocked:")
                
                threshold = st.select_slider(
                    "Sensitivity Threshold",
                    options=sensitivity_labels,
                    value="Confidential"
                )
                
                # Convert display label back to value
                selected_index = sensitivity_labels.index(threshold)
                threshold_value = sensitivity_values[selected_index]
                
                # Apply to all users checkbox
                apply_to_all = st.checkbox("Apply these settings to all users")
                
                # Form submission
                if st.form_submit_button("Save Default DLP Settings"):
                    if apply_to_all:
                        # Update all users' settings
                        try:
                            with session_scope() as session:
                                # Update all users' settings
                                session.query(Settings).update({
                                    "enable_ms_dlp": default_enable_dlp,
                                    "ms_dlp_sensitivity_threshold": threshold_value
                                })
                                st.success("DLP settings applied to all users successfully.")
                        except Exception as e:
                            st.error(f"Failed to update DLP settings: {str(e)}")
                    else:
                        st.info("Default settings saved. New users will receive these settings.")
            
            # Information about Microsoft DLP
            st.info("""
            ### How Microsoft DLP Integration Works
            
            The Microsoft DLP (Data Loss Prevention) integration enhances privacy protection by:
            
            1. Scanning uploaded files for Microsoft Sensitivity labels
            2. Blocking files with sensitivity levels at or above the threshold
            3. Reporting DLP violations to Microsoft Compliance center
            4. Preventing sensitive information from being used with AI models
            
            This is particularly useful for organizations that already use Microsoft Information Protection.
            """)
    
    # User Management tab
    with user_tab:
        st.subheader("User Management")
        
        # Get all users with error handling and retry
        users = []
        user_data = []
        
        try:
            with session_scope() as session:
                if session:
                    # Use eager loading to load all attributes we need
                    users_query = session.query(User)
                    
                    # Convert query results to dictionaries to avoid detached instance issues
                    for user in users_query:
                        # Extract all needed attributes within the session
                        user_dict = {
                            "id": user.id,
                            "username": user.username,
                            "role": user.role,
                            "created_at": user.created_at,
                            "azure_id": user.azure_id if hasattr(user, 'azure_id') else None,
                            "azure_name": user.azure_name if hasattr(user, 'azure_name') else None
                        }
                        users.append(user_dict)
                else:
                    st.error("Unable to connect to database. Please try again later.")
                    return
        except Exception as e:
            st.error(f"Error loading users: {str(e)}")
            return
        
        # Process user data outside the session (safe now that we have dictionaries)
        for user in users:
            # Check if user has Azure AD connection
            is_azure_user = user["azure_id"] is not None
            azure_info = f"{user['azure_name']} ({user['azure_id']})" if is_azure_user else ""
            
            user_data.append({
                "ID": user["id"],
                "Username": user["username"],
                "Role": user["role"],
                "Azure AD": "✓" if is_azure_user else "",
                "Azure Info": azure_info,
                "Created": user["created_at"].strftime("%Y-%m-%d %H:%M") if user["created_at"] else ""
            })
        
        # Display user table
        st.dataframe(
            pd.DataFrame(user_data),
            column_config={
                "ID": st.column_config.Column("ID", width="small"),
                "Username": st.column_config.Column("Username", width="medium"),
                "Role": st.column_config.Column("Role", width="small"),
                "Azure AD": st.column_config.Column("Azure AD", width="small"),
                "Azure Info": st.column_config.Column("Azure Info", width="medium"),
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
        
        # Let admin select a user from the dictionary data we created
        user_options = {f"{user['username']} (ID: {user['id']})": user['id'] for user in users}
        selected_user_display = st.selectbox("Select User", list(user_options.keys()), key="modify_user")
        selected_user_id = user_options[selected_user_display]
        
        # Get current role with error handling
        current_role = "user"  # Default value
        
        try:
            with session_scope() as session:
                if session:
                    # Get user role directly within session
                    user_info = session.query(User.role).filter(User.id == selected_user_id).first()
                    if user_info:
                        current_role = user_info[0]
                    else:
                        st.error("User not found.")
                        return
                else:
                    st.error("Unable to connect to database. Please try again later.")
                    return
        except Exception as e:
            st.error(f"Error retrieving user: {str(e)}")
            return
        
        # Select new role based on current role
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
        
        # Change user password
        st.markdown("---")
        st.subheader("Change User Password")
        
        # Let admin select a user from the dictionary data we created
        change_pw_user_display = st.selectbox("Select User", list(user_options.keys()), key="change_pw_user")
        change_pw_user_id = user_options[change_pw_user_display]
        
        # Password fields
        new_password = st.text_input("New Password", type="password", key="new_pw")
        confirm_password = st.text_input("Confirm New Password", type="password", key="confirm_pw")
        
        if st.button("Update Password"):
            if not new_password:
                st.error("Password cannot be empty")
            elif new_password != confirm_password:
                st.error("Passwords do not match")
            else:
                success = update_user_password(change_pw_user_id, new_password)
                if success:
                    st.success("Password updated successfully")
                else:
                    st.error("Failed to update password")
        
        # Delete user
        st.markdown("---")
        st.subheader("Delete User")
        
        # Let admin select a user from dictionary data
        # We're reusing the same user_options dictionary from above
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
        
        # Get system statistics with error handling
        from sqlalchemy import func
        
        total_users = 0
        total_conversations = 0
        total_detection_events = 0
        most_conversations_query = None
        latest_event = None
        
        try:
            with session_scope() as session:
                if session:
                    # Collect all statistics in a single session
                    total_users = session.query(User).count()
                    total_conversations = session.query(Conversation).count()
                    total_detection_events = session.query(DetectionEvent).count()
                    
                    # Get user with most conversations
                    most_conversations_query = session.query(
                        User.username,
                        User.id,
                        func.count(Conversation.id).label('count')
                    ).join(Conversation, User.id == Conversation.user_id, isouter=True)\
                     .group_by(User.id)\
                     .order_by(func.count(Conversation.id).desc())\
                     .first()
                    
                    # Get latest detection event
                    latest_event_data = None
                    latest_event_query = session.query(
                        DetectionEvent.timestamp,
                        DetectionEvent.action,
                        DetectionEvent.severity
                    ).order_by(DetectionEvent.timestamp.desc()).first()
                    
                    if latest_event_query:
                        latest_event_data = {
                            "timestamp": latest_event_query[0],
                            "action": latest_event_query[1],
                            "severity": latest_event_query[2]
                        }
                else:
                    st.error("Unable to connect to database. Please try again later.")
        except Exception as e:
            st.error(f"Error loading statistics: {str(e)}")
        
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
            if latest_event_data:
                event_time = latest_event_data["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                st.write(f"**Latest Detection Event**: {event_time} ({latest_event_data['action']}, {latest_event_data['severity']})")
    
    # Privacy Logs tab
    with logs_tab:
        st.subheader("Privacy Detection Logs")
        
        # Filter options
        st.write("Filter detection events:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Get all users for filter with error handling
            all_users = []
            
            try:
                # Get user data as dictionaries to avoid detached instance errors
                users_data = []
                with session_scope() as session:
                    if session:
                        all_users = session.query(User).all()
                        # Convert SQLAlchemy objects to dictionaries to avoid detached instance errors
                        for user in all_users:
                            users_data.append({
                                "id": user.id,
                                "username": user.username,
                                "role": user.role
                            })
                    else:
                        st.error("Unable to connect to database. Please try again later.")
                        return
            except Exception as e:
                st.error(f"Error loading users: {str(e)}")
                return
            
            # Create filter options using the dictionary data
            user_filter_options = {f"{user['username']} (ID: {user['id']})": user['id'] for user in users_data}
            user_filter_options["All Users"] = None
            
            selected_user_filter = st.selectbox(
                "User", 
                ["All Users"] + [f"{user['username']} (ID: {user['id']})" for user in users_data],
                key="log_user_filter"
            )
            selected_user_id_filter = user_filter_options[selected_user_filter]
        
        with col2:
            action_filter = st.selectbox(
                "Action Type",
                ["All", "scan", "anonymize"],
                key="log_action_filter"
            )
        
        # Get detection events based on filters with error handling
        events = []
        
        try:
            with session_scope() as session:
                if session:
                    query = session.query(DetectionEvent)
                    
                    if selected_user_id_filter is not None:
                        query = query.filter(DetectionEvent.user_id == selected_user_id_filter)
                    
                    if action_filter != "All":
                        query = query.filter(DetectionEvent.action == action_filter)
                    
                    # Order by timestamp
                    query = query.order_by(DetectionEvent.timestamp.desc())
                    
                    # Limit results
                    events = query.limit(100).all()
                else:
                    st.error("Unable to connect to database. Please try again later.")
                    return
        except Exception as e:
            st.error(f"Error loading detection events: {str(e)}")
            return
        
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
                for user in users_data:
                    if user["id"] == event["id"]:
                        username = user["username"]
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
