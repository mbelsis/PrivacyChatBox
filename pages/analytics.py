import streamlit as st
from style import apply_custom_css

# Apply custom CSS to hide default menu
apply_custom_css()
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
from collections import Counter
from database import get_session
from models import DetectionEvent, User, Message, Conversation
from sqlalchemy import func, desc, case, distinct, extract, cast, String, Float
from sqlalchemy.orm import aliased
import shared_sidebar

def show():
    """Main function to display the analytics dashboard"""
    # Clear sidebar state for fresh creation
    if "sidebar_created" in st.session_state:
        del st.session_state.sidebar_created
    
    # Create sidebar with shared component
    shared_sidebar.create_sidebar("analytics_page")
    
    st.title("📈 Analytics Dashboard")
    
    # Check if user is authenticated and is admin
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.error("You must be logged in to access this page.")
        st.stop()
    
    # Check if user is admin
    if st.session_state.get("role") != "admin":
        st.error("You must be an admin to access this page.")
        st.stop()
    
    # Check if there's any data in the database
    with get_session() as session:
        user_count = session.query(func.count(User.id)).scalar() or 0
    
    if user_count == 0:
        st.info("No data available yet. Analytics will be populated as users start using the platform.")
        
        # Show empty state with placeholder metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Users", 0)
        with col2:
            st.metric("Total Conversations", 0)
        with col3:
            st.metric("Total Messages", 0)
        
        return
    
    # Tabs for different analytics views
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 Privacy Insights", 
        "🤖 Model Usage", 
        "📊 User Activity",
        "🧮 System Stats"
    ])
    
    with tab1:
        show_privacy_insights()
    
    with tab2:
        show_model_usage()
    
    with tab3:
        show_user_activity()
    
    with tab4:
        show_system_stats()

def show_privacy_insights():
    """Display privacy-related insights"""
    st.header("Privacy Insights")
    
    # Date range filter
    col1, col2 = st.columns(2)
    with col1:
        date_range = st.selectbox(
            "Time Period",
            options=["Last 7 days", "Last 30 days", "Last 90 days", "All time"],
            index=1
        )
    
    # Convert date range to actual dates
    end_date = datetime.now()
    if date_range == "Last 7 days":
        start_date = end_date - timedelta(days=7)
    elif date_range == "Last 30 days":
        start_date = end_date - timedelta(days=30)
    elif date_range == "Last 90 days":
        start_date = end_date - timedelta(days=90)
    else:
        start_date = datetime(2020, 1, 1)  # Effectively all time
    
    with get_session() as session:
        # Get detection events within the date range
        events = session.query(DetectionEvent).filter(
            DetectionEvent.timestamp >= start_date,
            DetectionEvent.timestamp <= end_date
        ).all()
        
        # Get message count for the same period for comparison
        message_count = session.query(func.count(Message.id)).filter(
            Message.timestamp >= start_date,
            Message.timestamp <= end_date,
            Message.role == "user"
        ).scalar() or 0
    
    # Overview metrics
    st.subheader("Privacy Detection Overview")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_detections = len(events)
        st.metric("Total Detections", total_detections)
    
    with col2:
        detection_ratio = f"{(total_detections / message_count) * 100:.1f}%" if message_count > 0 else "0%"
        st.metric("Detection Rate", detection_ratio, help="Percentage of user messages that triggered privacy detections")
    
    with col3:
        anonymization_count = sum(1 for event in events if event.action == "anonymize")
        anonymization_rate = f"{(anonymization_count / total_detections) * 100:.1f}%" if total_detections > 0 else "0%"
        st.metric("Anonymization Rate", anonymization_rate, help="Percentage of detections that were anonymized")
    
    # Prepare data for charts
    if events:
        # Severity distribution
        severity_counts = Counter(event.severity for event in events)
        severity_df = pd.DataFrame({
            'Severity': list(severity_counts.keys()),
            'Count': list(severity_counts.values())
        })
        
        # Detection types
        pattern_types = []
        for event in events:
            patterns = event.get_detected_patterns()
            if patterns:
                for pattern_type in patterns.keys():
                    pattern_types.append(pattern_type)
        
        pattern_counts = Counter(pattern_types)
        pattern_df = pd.DataFrame({
            'Pattern Type': list(pattern_counts.keys()),
            'Count': list(pattern_counts.values())
        }).sort_values('Count', ascending=False)
        
        # Time series data
        dates = [event.timestamp.date() for event in events]
        date_counts = Counter(dates)
        date_df = pd.DataFrame({
            'Date': list(date_counts.keys()),
            'Count': list(date_counts.values())
        }).sort_values('Date')
        
        # Display charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Detection Severity")
            fig = px.pie(
                severity_df, 
                values='Count', 
                names='Severity',
                color='Severity',
                color_discrete_map={'low': '#90EE90', 'medium': '#FFA500', 'high': '#FF6347'},
                hole=0.4
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Most Common Detection Types")
            fig = px.bar(
                pattern_df.head(6), 
                x='Pattern Type', 
                y='Count',
                color='Count',
                color_continuous_scale='Viridis'
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        # Timeline of detections
        st.subheader("Detection Trend")
        fig = px.line(
            date_df, 
            x='Date', 
            y='Count',
            markers=True
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Raw data table
        with st.expander("View Raw Detection Data"):
            # Create a more readable dataframe
            data = []
            for event in events:
                patterns = event.get_detected_patterns()
                pattern_str = ', '.join([f"{k}: {len(v)}" for k, v in patterns.items()]) if patterns else "None"
                data.append({
                    'Timestamp': event.timestamp,
                    'User ID': event.user_id,
                    'Action': event.action,
                    'Severity': event.severity,
                    'Detected Patterns': pattern_str,
                    'Files': event.file_names if event.file_names else "None"
                })
            
            events_df = pd.DataFrame(data)
            st.dataframe(events_df)
    else:
        st.info("No privacy detection events found for the selected time period.")

def show_model_usage():
    """Display AI model usage analytics"""
    st.header("AI Model Usage Analytics")
    
    # Date range filter
    col1, col2 = st.columns(2)
    with col1:
        date_range = st.selectbox(
            "Time Period",
            options=["Last 7 days", "Last 30 days", "Last 90 days", "All time"],
            index=1,
            key="model_date_range"
        )
    
    # Convert date range to actual dates
    end_date = datetime.now()
    if date_range == "Last 7 days":
        start_date = end_date - timedelta(days=7)
    elif date_range == "Last 30 days":
        start_date = end_date - timedelta(days=30)
    elif date_range == "Last 90 days":
        start_date = end_date - timedelta(days=90)
    else:
        start_date = datetime(2020, 1, 1)  # Effectively all time
    
    # Query model usage from database
    with get_session() as session:
        # We need to join with users to get their settings
        # Since we don't have a direct model tracking table, we'll check user settings
        # and count conversations during the period
        User_alias = aliased(User)
        
        # Get conversation counts by user during period
        conversation_data = session.query(
            User_alias.id,
            User_alias.username,
            func.count(Conversation.id).label('conversation_count'),
            func.count(Message.id).filter(Message.role == 'assistant').label('response_count')
        ).join(
            Conversation, User_alias.id == Conversation.user_id
        ).outerjoin(
            Message, Conversation.id == Message.conversation_id
        ).filter(
            Conversation.created_at >= start_date,
            Conversation.created_at <= end_date
        ).group_by(
            User_alias.id, User_alias.username
        ).all()
        
        # Get user settings for model information
        users_with_settings = session.query(
            User, User.settings
        ).all()
        
        # Extract model usage data
        model_data = []
        for user, settings in users_with_settings:
            # Find conversation count for this user
            user_conv_data = next((data for data in conversation_data if data[0] == user.id), None)
            conv_count = user_conv_data[2] if user_conv_data else 0
            response_count = user_conv_data[3] if user_conv_data else 0
            
            # Only include users with activity
            if conv_count > 0:
                provider = settings.llm_provider if settings else "unknown"
                
                # Determine the specific model
                model = "unknown"
                if provider == "openai":
                    model = settings.openai_model if settings else "unknown"
                elif provider == "claude":
                    model = settings.claude_model if settings else "unknown"
                elif provider == "gemini":
                    model = settings.gemini_model if settings else "unknown"
                elif provider == "local":
                    model = "local_model"
                
                model_data.append({
                    'user_id': user.id,
                    'username': user.username,
                    'provider': provider,
                    'model': model,
                    'conversations': conv_count,
                    'responses': response_count
                })
    
    # Create a DataFrame for visualization
    if model_data:
        df = pd.DataFrame(model_data)
        
        # Overall metrics
        st.subheader("Model Usage Overview")
        col1, col2, col3 = st.columns(3)
        with col1:
            total_conversations = df['conversations'].sum()
            st.metric("Total Conversations", total_conversations)
        with col2:
            total_responses = df['responses'].sum()
            st.metric("Total AI Responses", total_responses)
        with col3:
            avg_responses = round(total_responses / total_conversations, 1) if total_conversations > 0 else 0
            st.metric("Avg. Responses per Conversation", avg_responses)
        
        # Provider breakdown
        st.subheader("Provider Distribution")
        provider_counts = df.groupby('provider').agg({'responses': 'sum'}).reset_index()
        
        fig = px.pie(
            provider_counts, 
            values='responses', 
            names='provider',
            color='provider',
            color_discrete_map={
                'openai': '#74aa9c', 
                'claude': '#ac6aac', 
                'gemini': '#4285F4',
                'local': '#ffa500',
                'unknown': '#888888'
            },
            hole=0.4
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Model breakdown
        st.subheader("Top Models Used")
        model_counts = df.groupby('model').agg({'responses': 'sum'}).reset_index()
        model_counts = model_counts.sort_values('responses', ascending=False)
        
        fig = px.bar(
            model_counts.head(6), 
            x='model', 
            y='responses',
            color='model',
            labels={'model': 'Model', 'responses': 'Number of Responses'}
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # User model preferences
        st.subheader("User Model Preferences")
        user_model_df = df[['username', 'provider', 'model', 'responses']].sort_values('responses', ascending=False)
        
        # Show as a table
        with st.expander("View User Model Preferences"):
            st.dataframe(user_model_df)
    else:
        st.info("No model usage data found for the selected time period.")

def show_user_activity():
    """Display user activity analytics"""
    st.header("User Activity Analytics")
    
    # Date range filter
    col1, col2 = st.columns(2)
    with col1:
        date_range = st.selectbox(
            "Time Period",
            options=["Last 7 days", "Last 30 days", "Last 90 days", "All time"],
            index=1,
            key="user_date_range"
        )
    
    # Convert date range to actual dates
    end_date = datetime.now()
    if date_range == "Last 7 days":
        start_date = end_date - timedelta(days=7)
    elif date_range == "Last 30 days":
        start_date = end_date - timedelta(days=30)
    elif date_range == "Last 90 days":
        start_date = end_date - timedelta(days=90)
    else:
        start_date = datetime(2020, 1, 1)  # Effectively all time
    
    # Query user activity
    with get_session() as session:
        # Get basic user metrics
        user_metrics = session.query(
            User.id,
            User.username,
            User.role,
            User.created_at,
            func.count(distinct(Conversation.id)).label('conversation_count'),
            func.count(Message.id).filter(Message.role == 'user').label('message_count'),
            func.count(Message.id).filter(Message.role == 'assistant').label('response_count')
        ).outerjoin(
            Conversation, User.id == Conversation.user_id
        ).outerjoin(
            Message, Conversation.id == Message.conversation_id
        ).filter(
            User.created_at <= end_date
        ).group_by(
            User.id, User.username, User.role, User.created_at
        ).all()
        
        # Get time-based activity data
        daily_activity = session.query(
            func.date(Message.timestamp).label('date'),
            func.count(Message.id).label('message_count')
        ).filter(
            Message.timestamp >= start_date,
            Message.timestamp <= end_date
        ).group_by(
            func.date(Message.timestamp)
        ).order_by(
            func.date(Message.timestamp)
        ).all()
        
        # Get hourly distribution
        hourly_activity = session.query(
            func.extract('hour', Message.timestamp).label('hour'),
            func.count(Message.id).label('message_count')
        ).filter(
            Message.timestamp >= start_date,
            Message.timestamp <= end_date
        ).group_by(
            func.extract('hour', Message.timestamp)
        ).order_by(
            func.extract('hour', Message.timestamp)
        ).all()
    
    # Create DataFrames for visualization
    user_df = pd.DataFrame([
        {
            'User ID': um[0],
            'Username': um[1],
            'Role': um[2],
            'Join Date': um[3],
            'Conversations': um[4],
            'Messages Sent': um[5],
            'Responses Received': um[6]
        }
        for um in user_metrics
    ])
    
    daily_df = pd.DataFrame([
        {'Date': da[0], 'Message Count': da[1]}
        for da in daily_activity
    ])
    
    hourly_df = pd.DataFrame([
        {'Hour': ha[0], 'Message Count': ha[1]}
        for ha in hourly_activity
    ])
    
    # Fill in missing hours
    all_hours = pd.DataFrame({'Hour': range(24)})
    hourly_df = pd.merge(all_hours, hourly_df, on='Hour', how='left').fillna(0)
    
    # Display dashboards
    if not user_df.empty:
        # Active user metrics
        active_users = len(user_df[user_df['Messages Sent'] > 0])
        total_users = len(user_df)
        
        st.subheader("User Overview")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Users", total_users)
        
        with col2:
            st.metric("Active Users", active_users)
        
        with col3:
            active_ratio = f"{(active_users / total_users) * 100:.1f}%" if total_users > 0 else "0%"
            st.metric("User Activation Rate", active_ratio)
        
        # User activity graphs
        st.subheader("User Engagement")
        
        # Most active users
        active_user_df = user_df.sort_values('Messages Sent', ascending=False).head(5)
        
        fig = px.bar(
            active_user_df,
            x='Username',
            y=['Messages Sent', 'Responses Received'],
            barmode='group',
            labels={'value': 'Count', 'variable': 'Type'},
            title="Most Active Users"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Daily activity trend
        if not daily_df.empty:
            st.subheader("Daily Activity Trend")
            fig = px.line(
                daily_df,
                x='Date',
                y='Message Count',
                markers=True,
                title="Messages Per Day"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Hourly distribution
        if not hourly_df.empty:
            st.subheader("Time of Day Activity")
            fig = px.bar(
                hourly_df,
                x='Hour',
                y='Message Count',
                color='Message Count',
                color_continuous_scale='Viridis',
                title="Message Distribution by Hour of Day"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # User table
        with st.expander("View All User Data"):
            st.dataframe(user_df.sort_values('Messages Sent', ascending=False))
    else:
        st.info("No user activity data found for the selected time period.")

def show_system_stats():
    """Display system statistics"""
    st.header("System Statistics")
    
    with get_session() as session:
        # Total database records
        user_count = session.query(func.count(User.id)).scalar() or 0
        conversation_count = session.query(func.count(Conversation.id)).scalar() or 0
        message_count = session.query(func.count(Message.id)).scalar() or 0
        detection_count = session.query(func.count(DetectionEvent.id)).scalar() or 0
        
        # Get some database stats
        total_storage = session.query(
            func.sum(func.length(cast(Message.content, String)))
        ).scalar() or 0
        
        # Convert to MB
        total_storage_mb = total_storage / (1024 * 1024)
        
        # Get the oldest and newest records
        oldest_message = session.query(func.min(Message.timestamp)).scalar()
        newest_message = session.query(func.max(Message.timestamp)).scalar()
        
        # Calculate average message length
        avg_message_length = session.query(
            func.avg(func.length(cast(Message.content, String)))
        ).scalar() or 0
    
    # Display metrics
    st.subheader("Database Overview")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Users", user_count)
    with col2:
        st.metric("Total Conversations", conversation_count)
    with col3:
        st.metric("Total Messages", message_count)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Detection Events", detection_count)
    with col2:
        st.metric("Storage Used", f"{total_storage_mb:.2f} MB")
    with col3:
        st.metric("Avg Message Length", f"{avg_message_length:.0f} chars")
    
    # System uptime and activity period
    st.subheader("System Activity")
    
    col1, col2 = st.columns(2)
    
    # Initialize days_active
    days_active = 0
    
    with col1:
        if oldest_message and newest_message:
            days_active = (newest_message - oldest_message).days
            # If less than 1 day, set to 1 to avoid division by zero
            days_active = max(1, days_active)
            st.metric("Days Active", days_active)
        else:
            st.metric("Days Active", 0)
    
    with col2:
        messages_per_day = message_count / days_active if days_active > 0 else 0
        st.metric("Avg Messages/Day", f"{messages_per_day:.1f}")
    
    # Database growth over time
    st.subheader("Database Growth")
    
    with get_session() as session:
        # Query message count by date
        message_growth = session.query(
            func.date(Message.timestamp).label('date'),
            func.count(Message.id).label('message_count')
        ).group_by(
            func.date(Message.timestamp)
        ).order_by(
            func.date(Message.timestamp)
        ).all()
    
    if message_growth:
        # Create DataFrame and calculate cumulative sum
        growth_df = pd.DataFrame([
            {'Date': mg[0], 'Daily Count': mg[1]}
            for mg in message_growth
        ])
        
        growth_df['Cumulative Count'] = growth_df['Daily Count'].cumsum()
        
        # Create the chart
        fig = go.Figure()
        
        # Add daily count as bars
        fig.add_trace(go.Bar(
            x=growth_df['Date'],
            y=growth_df['Daily Count'],
            name='Daily Count',
            marker_color='lightblue'
        ))
        
        # Add cumulative count as line
        fig.add_trace(go.Scatter(
            x=growth_df['Date'],
            y=growth_df['Cumulative Count'],
            name='Cumulative Count',
            mode='lines+markers',
            line=dict(color='darkblue', width=2),
            marker=dict(size=4)
        ))
        
        # Update layout
        fig.update_layout(
            title='Message Growth Over Time',
            xaxis_title='Date',
            yaxis_title='Count',
            hovermode='x',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No message history found to display growth chart.")
    
    # Database performance
    st.subheader("Database Performance Check")
    
    # Simple DB performance test
    start_time = time.time()
    with get_session() as session:
        session.query(User).limit(1).all()
    query_time = time.time() - start_time
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Simple Query Time", f"{query_time*1000:.2f} ms")
    
    # More complex query
    start_time = time.time()
    with get_session() as session:
        session.query(User).join(Conversation).join(Message).limit(10).all()
    complex_query_time = time.time() - start_time
    
    with col2:
        st.metric("Complex Query Time", f"{complex_query_time*1000:.2f} ms")
    
    # Warning if slow
    if complex_query_time > 0.5:  # More than 500ms is slow
        st.warning("Database queries are running slowly. Consider optimization.")
    elif complex_query_time > 0.1:  # More than 100ms is worth noting
        st.info("Database performance is acceptable but could be improved.")
    else:
        st.success("Database is performing well!")