import streamlit as st
from style import apply_custom_css

# Apply custom CSS to hide default menu
apply_custom_css()
import pandas as pd
from datetime import datetime, timedelta
from database import session_scope
from models import DetectionEvent, User, Message, Conversation
from sqlalchemy import func, distinct
import shared_sidebar

def show():
    """Main function to display the simplified analytics dashboard"""
    try:
        # Clear sidebar state to ensure it's recreated
        if "sidebar_created" in st.session_state:
            del st.session_state.sidebar_created
        
        # Create sidebar with shared component
        shared_sidebar.create_sidebar("analytics_page")
        
        st.title("📈 Analytics Dashboard")
        
        # Debugging check for session state
        st.write("Session State Keys:", list(st.session_state.keys()))
        
        # Check if user is authenticated and is admin
        if "authenticated" not in st.session_state or not st.session_state.authenticated:
            st.error("You must be logged in to access this page.")
            return
        
        # Check if user is admin
        if st.session_state.get("role") != "admin":
            st.error("You must be an admin to access this page.")
            return
        
        # Display just the system overview to start
        get_system_overview()
        
        # Only proceed with the rest if system overview worked
        try:
            # Display user activity metrics
            get_user_activity()
            
            # Display simple model usage
            get_model_usage()
            
            # Display privacy metrics
            get_privacy_metrics()
        except Exception as e:
            st.error(f"Error loading analytics components: {str(e)}")
            st.exception(e)
    except Exception as e:
        st.error(f"Critical error in analytics page: {str(e)}")
        st.exception(e)

def get_system_overview():
    """Display basic system statistics"""
    st.header("System Overview")
    
    # Initialize counters
    user_count = 0
    conversation_count = 0 
    message_count = 0
    detection_count = 0
    
    try:
        with session_scope() as session:
            if session:
                # Get basic counts using simple aggregations
                user_count = session.query(func.count(User.id)).scalar() or 0
                conversation_count = session.query(func.count(Conversation.id)).scalar() or 0
                message_count = session.query(func.count(Message.id)).scalar() or 0
                detection_count = session.query(func.count(DetectionEvent.id)).scalar() or 0
            else:
                st.warning("Could not connect to the database.")
                return
    except Exception as e:
        st.error(f"Database error: {str(e)}")
        return
    
    # Display metrics in a clean grid
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Users", user_count)
    
    with col2:
        st.metric("Conversations", conversation_count)
    
    with col3:
        st.metric("Messages", message_count)
    
    with col4:
        st.metric("Privacy Detections", detection_count)

def get_user_activity():
    """Display simplified user activity metrics"""
    st.header("User Activity")
    
    try:
        with session_scope() as session:
            if session:
                # Get users with their activity counts
                users_data = []
                users = session.query(
                    User.id,
                    User.username,
                    User.role,
                    func.count(distinct(Conversation.id)).label('conversations'),
                    func.count(Message.id).filter(Message.role == 'user').label('messages')
                ).outerjoin(
                    Conversation, User.id == Conversation.user_id
                ).outerjoin(
                    Message, Conversation.id == Message.conversation_id
                ).group_by(
                    User.id, User.username, User.role
                ).all()
                
                # Extract data safely within the session
                for user in users:
                    users_data.append({
                        'user_id': user[0],
                        'username': user[1],
                        'role': user[2],
                        'conversations': user[3],
                        'messages': user[4]
                    })
                
                # Count active users (those with at least one message)
                total_users = len(users_data)
                active_users = sum(1 for user in users_data if user['messages'] > 0)
                active_rate = f"{(active_users / total_users) * 100:.1f}%" if total_users > 0 else "0%"
                
                # Display user activity metrics
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Active Users", f"{active_users} / {total_users}")
                with col2:
                    st.metric("Activity Rate", active_rate)
                
                # Create and display a dataframe with user activity
                if users_data:
                    df = pd.DataFrame(users_data)
                    
                    # Sort by message count
                    if not df.empty and 'messages' in df.columns:
                        df = df.sort_values('messages', ascending=False)
                        
                        # Show the table
                        st.subheader("User Activity Details")
                        st.dataframe(df[['username', 'role', 'conversations', 'messages']])
                else:
                    st.info("No user activity data available.")
            else:
                st.warning("Could not connect to the database.")
    except Exception as e:
        st.error(f"Error retrieving user activity: {str(e)}")

def get_model_usage():
    """Display simplified model usage metrics"""
    st.header("AI Model Usage")
    
    try:
        with session_scope() as session:
            if session:
                # Simply count assistant messages as a basic metric
                message_count = session.query(func.count(Message.id)).filter(
                    Message.role == 'assistant'
                ).scalar() or 0
                
                st.metric("Total AI Responses", message_count)
                
                # Display a simple note about model usage
                st.info("For detailed model analytics, check the Settings page to see which AI models are configured.")
            else:
                st.warning("Could not connect to the database.")
    except Exception as e:
        st.error(f"Error retrieving model usage: {str(e)}")
        st.exception(e)  # Show detailed error for debugging

def get_privacy_metrics():
    """Display simplified privacy-related metrics"""
    st.header("Privacy Insights")
    
    try:
        with session_scope() as session:
            if session:
                # Get basic detection event counts
                total_detections = session.query(func.count(DetectionEvent.id)).scalar() or 0
                
                if total_detections > 0:
                    # Count by severity
                    severity_data = []
                    severity_counts = session.query(
                        DetectionEvent.severity,
                        func.count(DetectionEvent.id)
                    ).group_by(
                        DetectionEvent.severity
                    ).all()
                    
                    # Extract data safely
                    for severity in severity_counts:
                        severity_data.append({
                            'severity': severity[0],
                            'count': severity[1],
                            'percentage': f"{(severity[1] / total_detections) * 100:.1f}%"
                        })
                    
                    # Count by action type
                    action_data = []
                    action_counts = session.query(
                        DetectionEvent.action,
                        func.count(DetectionEvent.id)
                    ).group_by(
                        DetectionEvent.action
                    ).all()
                    
                    # Extract data safely
                    for action in action_counts:
                        action_data.append({
                            'action': action[0],
                            'count': action[1],
                            'percentage': f"{(action[1] / total_detections) * 100:.1f}%"
                        })
                    
                    # Display metrics
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Detection Severity")
                        if severity_data:
                            st.dataframe(pd.DataFrame(severity_data))
                        else:
                            st.info("No severity data available.")
                    
                    with col2:
                        st.subheader("Actions Taken")
                        if action_data:
                            st.dataframe(pd.DataFrame(action_data))
                        else:
                            st.info("No action data available.")
                else:
                    st.info("No privacy detection events recorded yet.")
            else:
                st.warning("Could not connect to the database.")
    except Exception as e:
        st.error(f"Error retrieving privacy metrics: {str(e)}")