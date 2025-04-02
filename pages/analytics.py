import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import json
import calendar

# Import custom modules
from database import get_session, session_scope
from models import Conversation, Message, File, DetectionEvent, User, Settings
from utils import format_detection_events
from sqlalchemy.sql import func
import shared_sidebar
from style import apply_custom_css

# Apply custom CSS
apply_custom_css()

def show():
    """Main function to display the advanced analytics dashboard"""
    # Clear sidebar state for fresh creation
    if "sidebar_created" in st.session_state:
        del st.session_state.sidebar_created
    
    # Create sidebar with shared component
    shared_sidebar.create_sidebar("analytics_page")
    
    # Page settings
    st.title("📊 Advanced Analytics Dashboard")
    
    # Get user information
    user_id = st.session_state.user_id
    role = st.session_state.role
    
    if not user_id:
        st.error("You must be logged in to access this page.")
        return
    
    # Check if user is admin - admins see system-wide analytics
    is_admin = role == "admin"
    
    # Create tabs for different analytics categories
    usage_tab, privacy_tab, pattern_tab, conversation_tab = st.tabs([
        "📈 Usage Metrics", 
        "🔒 Privacy Analytics", 
        "🔍 Pattern Analytics",
        "💬 Conversation Analytics"
    ])
    
    # Usage Metrics Tab
    with usage_tab:
        st.subheader("Usage Metrics")
        
        # Time period selector
        time_periods = {
            "Last 7 days": 7,
            "Last 30 days": 30,
            "Last 90 days": 90,
            "All time": 0
        }
        
        time_period = st.selectbox(
            "Time Period", 
            list(time_periods.keys())
        )
        
        days = time_periods[time_period]
        cutoff_date = datetime.now() - timedelta(days=days) if days > 0 else None
        
        # User filter for admins
        selected_user_id = None
        if is_admin:
            st.markdown("---")
            
            # Get all users
            try:
                user_options = {"All Users": None}
                with session_scope() as session:
                    users = session.query(User).all()
                    for user in users:
                        user_options[f"{user.username} (ID: {user.id})"] = user.id
                
                user_filter = st.selectbox(
                    "Filter by User",
                    list(user_options.keys())
                )
                
                selected_user_id = user_options[user_filter]
            except Exception as e:
                st.error(f"Error loading users: {str(e)}")
        
        # Fetch metrics data
        try:
            with session_scope() as session:
                # Base queries that will be filtered
                conversations_query = session.query(Conversation)
                messages_query = session.query(Message).join(
                    Conversation, Message.conversation_id == Conversation.id
                )
                detection_query = session.query(DetectionEvent)
                
                # Apply user filter
                if selected_user_id:
                    conversations_query = conversations_query.filter(Conversation.user_id == selected_user_id)
                    messages_query = messages_query.filter(Conversation.user_id == selected_user_id)
                    detection_query = detection_query.filter(DetectionEvent.user_id == selected_user_id)
                elif not is_admin:
                    # Regular users only see their own data
                    conversations_query = conversations_query.filter(Conversation.user_id == user_id)
                    messages_query = messages_query.filter(Conversation.user_id == user_id)
                    detection_query = detection_query.filter(DetectionEvent.user_id == user_id)
                
                # Apply time filter
                if cutoff_date:
                    conversations_query = conversations_query.filter(Conversation.created_at >= cutoff_date)
                    messages_query = messages_query.filter(Message.timestamp >= cutoff_date)
                    detection_query = detection_query.filter(DetectionEvent.timestamp >= cutoff_date)
                
                # Get counts
                total_conversations = conversations_query.count()
                total_messages = messages_query.count()
                total_user_messages = messages_query.filter(Message.role == "user").count()
                total_ai_messages = messages_query.filter(Message.role == "assistant").count()
                total_detection_events = detection_query.count()
                
                # Additional counts for specific metrics
                total_blocked_files = detection_query.filter(DetectionEvent.action == "block_sensitive_file").count()
                total_anonymize_events = detection_query.filter(DetectionEvent.action == "anonymize").count()
                
                # Usage by date for time series
                conversations_by_date = {}
                messages_by_date = {}
                detections_by_date = {}
                
                # Time grouping
                time_group = func.date(Conversation.created_at)
                
                # Determine date buckets based on time period
                if days == 0:  # All time
                    # Group by month if all time
                    time_group = func.date_trunc('month', Conversation.created_at)
                elif days > 30:  # Last 90 days
                    # Group by week if more than 30 days
                    time_group = func.date_trunc('week', Conversation.created_at)
                
                # Get conversations by date
                conversations_by_date_query = session.query(
                    time_group,
                    func.count(Conversation.id)
                ).group_by(time_group).all()
                
                # Get messages by date
                messages_by_date_query = session.query(
                    func.date(Message.timestamp),
                    func.count(Message.id)
                ).join(
                    Conversation, Message.conversation_id == Conversation.id
                )
                
                # Apply user filter to messages
                if selected_user_id:
                    messages_by_date_query = messages_by_date_query.filter(Conversation.user_id == selected_user_id)
                elif not is_admin:
                    messages_by_date_query = messages_by_date_query.filter(Conversation.user_id == user_id)
                
                # Apply time filter to messages
                if cutoff_date:
                    messages_by_date_query = messages_by_date_query.filter(Message.timestamp >= cutoff_date)
                
                messages_by_date_query = messages_by_date_query.group_by(func.date(Message.timestamp)).all()
                
                # Get detections by date
                detections_by_date_query = session.query(
                    func.date(DetectionEvent.timestamp),
                    func.count(DetectionEvent.id)
                )
                
                # Apply user filter to detections
                if selected_user_id:
                    detections_by_date_query = detections_by_date_query.filter(DetectionEvent.user_id == selected_user_id)
                elif not is_admin:
                    detections_by_date_query = detections_by_date_query.filter(DetectionEvent.user_id == user_id)
                
                # Apply time filter to detections
                if cutoff_date:
                    detections_by_date_query = detections_by_date_query.filter(DetectionEvent.timestamp >= cutoff_date)
                
                detections_by_date_query = detections_by_date_query.group_by(func.date(DetectionEvent.timestamp)).all()
                
                # Format date keys for a uniform approach
                for date_obj, count in conversations_by_date_query:
                    if isinstance(date_obj, datetime):
                        date_key = date_obj.strftime('%Y-%m-%d')
                    else:
                        date_key = date_obj.strftime('%Y-%m-%d') if hasattr(date_obj, 'strftime') else str(date_obj)
                    conversations_by_date[date_key] = count
                
                for date_obj, count in messages_by_date_query:
                    if isinstance(date_obj, datetime):
                        date_key = date_obj.strftime('%Y-%m-%d')
                    else:
                        date_key = date_obj.strftime('%Y-%m-%d') if hasattr(date_obj, 'strftime') else str(date_obj)
                    messages_by_date[date_key] = count
                
                for date_obj, count in detections_by_date_query:
                    if isinstance(date_obj, datetime):
                        date_key = date_obj.strftime('%Y-%m-%d')
                    else:
                        date_key = date_obj.strftime('%Y-%m-%d') if hasattr(date_obj, 'strftime') else str(date_obj)
                    detections_by_date[date_key] = count
        
        except Exception as e:
            st.error(f"Error loading metrics: {str(e)}")
            total_conversations = 0
            total_messages = 0
            total_user_messages = 0
            total_ai_messages = 0
            total_detection_events = 0
            total_blocked_files = 0
            total_anonymize_events = 0
            conversations_by_date = {}
            messages_by_date = {}
            detections_by_date = {}
        
        # Display key metrics
        st.markdown("### Key Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Conversations", total_conversations)
        
        with col2:
            st.metric("Total Messages", total_messages)
            st.metric("User Messages", total_user_messages, delta=f"{total_user_messages/total_messages*100:.1f}%" if total_messages > 0 else None)
        
        with col3:
            st.metric("AI Responses", total_ai_messages, delta=f"{total_ai_messages/total_messages*100:.1f}%" if total_messages > 0 else None)
        
        with col4:
            st.metric("Privacy Events", total_detection_events)
            st.metric("Blocked Files", total_blocked_files)
        
        # Activity over time
        st.markdown("### Activity Over Time")
        
        # Merge all date data for the time series
        all_dates = sorted(set(list(conversations_by_date.keys()) + 
                            list(messages_by_date.keys()) + 
                            list(detections_by_date.keys())))
        
        # Create a clean dataframe with all dates
        time_series_data = []
        for date_str in all_dates:
            time_series_data.append({
                "Date": date_str,
                "Conversations": conversations_by_date.get(date_str, 0),
                "Messages": messages_by_date.get(date_str, 0),
                "Privacy Events": detections_by_date.get(date_str, 0)
            })
        
        df_time_series = pd.DataFrame(time_series_data)
        if not df_time_series.empty:
            df_time_series["Date"] = pd.to_datetime(df_time_series["Date"])
            df_time_series = df_time_series.sort_values("Date")
            
            # Create the time series visualization
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=df_time_series["Date"], 
                y=df_time_series["Conversations"],
                mode='lines+markers',
                name='Conversations',
                marker=dict(size=8),
                line=dict(width=2, color='#1f77b4')
            ))
            
            fig.add_trace(go.Scatter(
                x=df_time_series["Date"], 
                y=df_time_series["Messages"],
                mode='lines+markers',
                name='Messages',
                marker=dict(size=8),
                line=dict(width=2, color='#ff7f0e')
            ))
            
            fig.add_trace(go.Scatter(
                x=df_time_series["Date"], 
                y=df_time_series["Privacy Events"],
                mode='lines+markers',
                name='Privacy Events',
                marker=dict(size=8),
                line=dict(width=2, color='#d62728')
            ))
            
            fig.update_layout(
                title="Activity Trends",
                xaxis_title="Date",
                yaxis_title="Count",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                margin=dict(l=20, r=20, t=40, b=20),
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No activity data available for the selected period.")
    
    # Privacy Analytics Tab
    with privacy_tab:
        st.subheader("Privacy Analytics")
        
        try:
            with session_scope() as session:
                # Base detection query
                detection_query = session.query(DetectionEvent)
                
                # Apply user filter
                if selected_user_id:
                    detection_query = detection_query.filter(DetectionEvent.user_id == selected_user_id)
                elif not is_admin:
                    detection_query = detection_query.filter(DetectionEvent.user_id == user_id)
                
                # Apply time filter
                if cutoff_date:
                    detection_query = detection_query.filter(DetectionEvent.timestamp >= cutoff_date)
                
                # Get all detection events
                detection_events = detection_query.all()
                
                # Prepare data for analytics
                severity_counts = {"low": 0, "medium": 0, "high": 0}
                action_counts = {"scan": 0, "anonymize": 0, "block_sensitive_file": 0}
                
                # Process all detection events
                pattern_counts = {}
                for event in detection_events:
                    # Count by severity
                    if event.severity in severity_counts:
                        severity_counts[event.severity] += 1
                    
                    # Count by action
                    if event.action in action_counts:
                        action_counts[event.action] += 1
                    
                    # Count by pattern type
                    try:
                        patterns = event.get_detected_patterns()
                        for pattern_type, matches in patterns.items():
                            if pattern_type not in pattern_counts:
                                pattern_counts[pattern_type] = 0
                            pattern_counts[pattern_type] += len(matches)
                    except:
                        pass
                
                # Format action names for display
                action_display = {
                    "scan": "Content Scan",
                    "anonymize": "Content Anonymization",
                    "block_sensitive_file": "Blocked Sensitive Files"
                }
                
                # Create dataframes for charts
                severity_df = pd.DataFrame({
                    "Severity": list(severity_counts.keys()),
                    "Count": list(severity_counts.values())
                })
                
                action_df = pd.DataFrame({
                    "Action": [action_display.get(action, action) for action in action_counts.keys()],
                    "Count": list(action_counts.values())
                })
                
                pattern_df = pd.DataFrame({
                    "Pattern": list(pattern_counts.keys()),
                    "Count": list(pattern_counts.values())
                })
                pattern_df = pattern_df.sort_values("Count", ascending=False).head(10)
        
        except Exception as e:
            st.error(f"Error loading privacy analytics: {str(e)}")
            severity_df = pd.DataFrame({"Severity": [], "Count": []})
            action_df = pd.DataFrame({"Action": [], "Count": []})
            pattern_df = pd.DataFrame({"Pattern": [], "Count": []})
        
        # Display charts
        col1, col2 = st.columns(2)
        
        with col1:
            if severity_df["Count"].sum() > 0:
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
                    title="Detection Events by Severity"
                )
                fig.update_layout(
                    legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No severity data available for the selected period.")
        
        with col2:
            if action_df["Count"].sum() > 0:
                fig = px.pie(
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
                    title="Detection Events by Action Type"
                )
                fig.update_layout(
                    legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No action data available for the selected period.")
        
        # Top detected patterns
        st.subheader("Top Detected Pattern Types")
        
        if not pattern_df.empty and pattern_df["Count"].sum() > 0:
            # Create bar chart for top patterns
            fig = px.bar(
                pattern_df,
                x="Pattern",
                y="Count",
                color="Count",
                color_continuous_scale="Viridis",
                title="Most Frequently Detected Pattern Types"
            )
            fig.update_layout(xaxis_title="Pattern Type", yaxis_title="Number of Detections")
            st.plotly_chart(fig, use_container_width=True)
            
            # Events over time
            st.subheader("Privacy Events Over Time")
            
            # Group events by day
            event_dates = {}
            for event in detection_events:
                date_str = event.timestamp.strftime('%Y-%m-%d')
                if date_str not in event_dates:
                    event_dates[date_str] = {"scan": 0, "anonymize": 0, "block_sensitive_file": 0}
                event_dates[date_str][event.action] += 1
            
            # Create dataframe for time series
            event_time_data = []
            for date_str, counts in event_dates.items():
                event_time_data.append({
                    "Date": date_str,
                    "Content Scan": counts["scan"],
                    "Content Anonymization": counts["anonymize"],
                    "Blocked Files": counts["block_sensitive_file"]
                })
            
            df_event_time = pd.DataFrame(event_time_data)
            if not df_event_time.empty:
                df_event_time["Date"] = pd.to_datetime(df_event_time["Date"])
                df_event_time = df_event_time.sort_values("Date")
                
                # Create stacked area chart
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=df_event_time["Date"], 
                    y=df_event_time["Content Scan"],
                    mode='lines',
                    name='Content Scan',
                    stackgroup='one',
                    line=dict(width=0.5, color='#42A5F5')
                ))
                
                fig.add_trace(go.Scatter(
                    x=df_event_time["Date"], 
                    y=df_event_time["Content Anonymization"],
                    mode='lines',
                    name='Content Anonymization',
                    stackgroup='one',
                    line=dict(width=0.5, color='#AB47BC')
                ))
                
                fig.add_trace(go.Scatter(
                    x=df_event_time["Date"], 
                    y=df_event_time["Blocked Files"],
                    mode='lines',
                    name='Blocked Files',
                    stackgroup='one',
                    line=dict(width=0.5, color='#F44336')
                ))
                
                fig.update_layout(
                    title="Privacy Events by Day",
                    xaxis_title="Date",
                    yaxis_title="Number of Events",
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ),
                    margin=dict(l=20, r=20, t=40, b=20),
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No time-based event data available for the selected period.")
            
        else:
            st.info("No pattern data available for the selected period.")
    
    # Pattern Analytics Tab
    with pattern_tab:
        st.subheader("Pattern Detection Analytics")
        
        # Get all unique pattern types detected
        try:
            with session_scope() as session:
                # Base detection query
                detection_query = session.query(DetectionEvent)
                
                # Apply user filter
                if selected_user_id:
                    detection_query = detection_query.filter(DetectionEvent.user_id == selected_user_id)
                elif not is_admin:
                    detection_query = detection_query.filter(DetectionEvent.user_id == user_id)
                
                # Apply time filter
                if cutoff_date:
                    detection_query = detection_query.filter(DetectionEvent.timestamp >= cutoff_date)
                
                # Process pattern categories
                all_patterns = {}
                
                # Categorize patterns for easier analysis
                pattern_categories = {
                    "Personal Information": ["name", "email", "phone_number", "date_of_birth", "address", "ssn", "passport", "uk_nino", "greek_amka", "greek_tax_id"],
                    "Financial Information": ["credit_card", "bank_account", "iban"],
                    "Credentials & Access": ["password", "api_key", "jwt", "aws_access_key", "aws_secret_key", "google_api_key", "private_key"],
                    "Network & Technical": ["ip_address", "url", "uuid", "msisdn"],
                    "Classification Terms": ["classification"],
                    "Custom Patterns": []  # Will be filled with patterns not in the above categories
                }
                
                pattern_category_map = {}
                for category, patterns in pattern_categories.items():
                    for pattern in patterns:
                        pattern_category_map[pattern] = category
                
                # Process events
                for event in detection_query.all():
                    try:
                        patterns = event.get_detected_patterns()
                        for pattern_type, matches in patterns.items():
                            if pattern_type not in all_patterns:
                                all_patterns[pattern_type] = 0
                            all_patterns[pattern_type] += len(matches)
                            
                            # If pattern isn't in our category map, add it to custom patterns
                            if pattern_type not in pattern_category_map:
                                pattern_category_map[pattern_type] = "Custom Patterns"
                                if pattern_type not in pattern_categories["Custom Patterns"]:
                                    pattern_categories["Custom Patterns"].append(pattern_type)
                    except:
                        pass
                
                # Create category totals
                category_totals = {category: 0 for category in pattern_categories.keys()}
                for pattern, count in all_patterns.items():
                    category = pattern_category_map.get(pattern, "Custom Patterns")
                    category_totals[category] += count
                
                # Create dataframe for category chart
                category_df = pd.DataFrame({
                    "Category": list(category_totals.keys()),
                    "Count": list(category_totals.values())
                })
                category_df = category_df[category_df["Count"] > 0]  # Remove empty categories
                category_df = category_df.sort_values("Count", ascending=False)
                
                # Create dataframe for pattern breakdown
                pattern_breakdown = []
                for pattern, count in all_patterns.items():
                    category = pattern_category_map.get(pattern, "Custom Patterns")
                    pattern_breakdown.append({
                        "Pattern": pattern,
                        "Category": category,
                        "Count": count
                    })
                
                pattern_breakdown_df = pd.DataFrame(pattern_breakdown)
                pattern_breakdown_df = pattern_breakdown_df.sort_values("Count", ascending=False)
        
        except Exception as e:
            st.error(f"Error loading pattern analytics: {str(e)}")
            category_df = pd.DataFrame({"Category": [], "Count": []})
            pattern_breakdown_df = pd.DataFrame({"Pattern": [], "Category": [], "Count": []})
        
        # Display category chart
        if not category_df.empty and category_df["Count"].sum() > 0:
            st.markdown("### Pattern Detections by Category")
            
            fig = px.bar(
                category_df,
                x="Category",
                y="Count",
                color="Category",
                title="Detected Patterns by Category"
            )
            fig.update_layout(xaxis_title="Category", yaxis_title="Number of Detections")
            st.plotly_chart(fig, use_container_width=True)
            
            # Display pattern breakdown
            st.markdown("### Top 15 Detected Patterns")
            
            if not pattern_breakdown_df.empty:
                top_patterns = pattern_breakdown_df.head(15)
                
                fig = px.bar(
                    top_patterns,
                    x="Pattern",
                    y="Count",
                    color="Category",
                    title="Top 15 Most Frequently Detected Patterns"
                )
                fig.update_layout(xaxis_title="Pattern Type", yaxis_title="Number of Detections")
                st.plotly_chart(fig, use_container_width=True)
                
                # Show pattern details table
                st.markdown("### Pattern Detection Details")
                
                pattern_table = pattern_breakdown_df.copy()
                pattern_table = pattern_table.sort_values(["Category", "Count"], ascending=[True, False])
                
                st.dataframe(
                    pattern_table,
                    column_config={
                        "Pattern": st.column_config.Column("Pattern Type", width="medium"),
                        "Category": st.column_config.Column("Category", width="medium"),
                        "Count": st.column_config.Column("Detections", width="small")
                    },
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("No pattern breakdown data available for the selected period.")
        else:
            st.info("No pattern category data available for the selected period.")
    
    # Conversation Analytics Tab
    with conversation_tab:
        st.subheader("Conversation Analytics")
        
        try:
            with session_scope() as session:
                # Base queries
                conversations_query = session.query(Conversation)
                messages_query = session.query(Message).join(
                    Conversation, Message.conversation_id == Conversation.id
                )
                
                # Apply user filter
                if selected_user_id:
                    conversations_query = conversations_query.filter(Conversation.user_id == selected_user_id)
                    messages_query = messages_query.filter(Conversation.user_id == selected_user_id)
                elif not is_admin:
                    conversations_query = conversations_query.filter(Conversation.user_id == user_id)
                    messages_query = messages_query.filter(Conversation.user_id == user_id)
                
                # Apply time filter
                if cutoff_date:
                    conversations_query = conversations_query.filter(Conversation.created_at >= cutoff_date)
                    messages_query = messages_query.filter(Message.timestamp >= cutoff_date)
                
                # Messages by role
                message_roles = session.query(
                    Message.role,
                    func.count(Message.id)
                ).join(
                    Conversation, Message.conversation_id == Conversation.id
                )
                
                # Apply filters to role query
                if selected_user_id:
                    message_roles = message_roles.filter(Conversation.user_id == selected_user_id)
                elif not is_admin:
                    message_roles = message_roles.filter(Conversation.user_id == user_id)
                
                if cutoff_date:
                    message_roles = message_roles.filter(Message.timestamp >= cutoff_date)
                
                message_roles = message_roles.group_by(Message.role).all()
                
                # Create role counts dictionary
                role_counts = {}
                for role, count in message_roles:
                    role_counts[role] = count
                
                # Calculate average messages per conversation
                total_conversations = conversations_query.count()
                total_messages = messages_query.count()
                avg_messages = total_messages / total_conversations if total_conversations > 0 else 0
                
                # Get hourly distribution of messages
                hourly_distribution = session.query(
                    func.extract('hour', Message.timestamp).label('hour'),
                    func.count(Message.id)
                ).join(
                    Conversation, Message.conversation_id == Conversation.id
                )
                
                # Apply filters to hourly query
                if selected_user_id:
                    hourly_distribution = hourly_distribution.filter(Conversation.user_id == selected_user_id)
                elif not is_admin:
                    hourly_distribution = hourly_distribution.filter(Conversation.user_id == user_id)
                
                if cutoff_date:
                    hourly_distribution = hourly_distribution.filter(Message.timestamp >= cutoff_date)
                
                hourly_distribution = hourly_distribution.group_by('hour').all()
                
                # Create hourly distribution dictionary
                hours_dict = {i: 0 for i in range(24)}
                for hour, count in hourly_distribution:
                    hour = int(hour)
                    hours_dict[hour] = count
                
                # Convert to dataframe
                hourly_df = pd.DataFrame({
                    "Hour": list(hours_dict.keys()),
                    "Messages": list(hours_dict.values())
                })
                hourly_df = hourly_df.sort_values("Hour")
                
                # Get conversation length distribution
                conv_lengths = {}
                for conv in conversations_query.all():
                    msg_count = sum(1 for _ in session.query(Message).filter(Message.conversation_id == conv.id))
                    
                    # Group into buckets
                    if msg_count <= 2:
                        bucket = "1-2 messages"
                    elif msg_count <= 5:
                        bucket = "3-5 messages"
                    elif msg_count <= 10:
                        bucket = "6-10 messages"
                    elif msg_count <= 20:
                        bucket = "11-20 messages"
                    else:
                        bucket = "21+ messages"
                    
                    if bucket not in conv_lengths:
                        conv_lengths[bucket] = 0
                    conv_lengths[bucket] += 1
                
                # Define order for buckets
                bucket_order = ["1-2 messages", "3-5 messages", "6-10 messages", "11-20 messages", "21+ messages"]
                
                # Create dataframe for conversation lengths
                length_data = []
                for bucket in bucket_order:
                    if bucket in conv_lengths:
                        length_data.append({
                            "Length": bucket,
                            "Conversations": conv_lengths[bucket]
                        })
                
                length_df = pd.DataFrame(length_data)
                
                # Create dataframe for message roles
                role_data = []
                for role, count in role_counts.items():
                    display_role = "User" if role == "user" else "AI Assistant" if role == "assistant" else role.capitalize()
                    role_data.append({
                        "Role": display_role,
                        "Messages": count
                    })
                
                role_df = pd.DataFrame(role_data)
                
        except Exception as e:
            st.error(f"Error loading conversation analytics: {str(e)}")
            hourly_df = pd.DataFrame({"Hour": [], "Messages": []})
            length_df = pd.DataFrame({"Length": [], "Conversations": []})
            role_df = pd.DataFrame({"Role": [], "Messages": []})
            avg_messages = 0
        
        # Display key statistics
        st.markdown("### Conversation Statistics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Avg. Messages per Conversation", f"{avg_messages:.1f}")
        
        # Display charts for conversation analytics
        st.markdown("### Message Distribution by Hour")
        
        if not hourly_df.empty and hourly_df["Messages"].sum() > 0:
            # Format hours for display (12-hour format with AM/PM)
            hourly_df["Hour Display"] = hourly_df["Hour"].apply(
                lambda x: f"{x if x < 12 else x-12 if x > 12 else 12}{' AM' if x < 12 else ' PM'}"
            )
            
            fig = px.bar(
                hourly_df,
                x="Hour",
                y="Messages",
                title="Message Activity by Hour of Day",
                color="Messages",
                color_continuous_scale="Viridis"
            )
            
            # Customize x-axis to show hours in 12-hour format
            fig.update_layout(
                xaxis=dict(
                    tickmode='array',
                    tickvals=list(range(24)),
                    ticktext=[f"{h if h < 12 else h-12 if h > 12 else 12}{' AM' if h < 12 else ' PM'}" for h in range(24)]
                ),
                xaxis_title="Hour of Day",
                yaxis_title="Number of Messages"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hourly message data available for the selected period.")
        
        # Create side-by-side charts for conversation length and message roles
        col1, col2 = st.columns(2)
        
        with col1:
            if not length_df.empty and length_df["Conversations"].sum() > 0:
                st.markdown("### Conversation Length Distribution")
                
                fig = px.pie(
                    length_df,
                    values="Conversations",
                    names="Length",
                    title="Conversations by Length",
                    color_discrete_sequence=px.colors.sequential.Viridis
                )
                
                fig.update_layout(
                    legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No conversation length data available for the selected period.")
        
        with col2:
            if not role_df.empty and role_df["Messages"].sum() > 0:
                st.markdown("### Message Distribution by Role")
                
                fig = px.pie(
                    role_df,
                    values="Messages",
                    names="Role",
                    title="Messages by Role",
                    color_discrete_sequence=px.colors.sequential.Plasma
                )
                
                fig.update_layout(
                    legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No message role data available for the selected period.")