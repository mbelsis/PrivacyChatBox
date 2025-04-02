import os
import uuid
import tempfile
import mimetypes
from datetime import datetime
from typing import Optional, Tuple, Dict, Any, List
import streamlit as st
from database import get_session, session_scope
from models import Conversation, Message, File, User, Settings

# Import MS DLP functionality for file sensitivity checking
# This import is done in a try-except to allow the app to work without MS DLP integration
try:
    from ms_dlp import scan_file_for_sensitivity, is_dlp_integration_enabled
    MS_DLP_AVAILABLE = True
except ImportError:
    MS_DLP_AVAILABLE = False

def generate_unique_id() -> str:
    """Generate a unique ID for files or conversations"""
    return str(uuid.uuid4())

def save_uploaded_file(uploaded_file) -> Tuple[str, str, int]:
    """
    Save an uploaded file to a temporary location
    
    Args:
        uploaded_file: Streamlit uploaded file object
        
    Returns:
        Tuple containing:
            - Path to the saved file
            - MIME type of the file
            - Size of the file in bytes
    """
    # Create a temporary directory if it doesn't exist
    temp_dir = tempfile.gettempdir()
    
    # Generate a unique filename
    unique_id = generate_unique_id()
    file_extension = os.path.splitext(uploaded_file.name)[1] if "." in uploaded_file.name else ""
    unique_filename = f"{unique_id}{file_extension}"
    
    # Full path to save the file
    file_path = os.path.join(temp_dir, unique_filename)
    
    # Save the file
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Get MIME type and file size
    mime_type = uploaded_file.type or mimetypes.guess_type(uploaded_file.name)[0] or "application/octet-stream"
    file_size = os.path.getsize(file_path)
    
    return file_path, mime_type, file_size

def create_new_conversation(user_id: int, title: str = "New Conversation") -> int:
    """
    Create a new conversation in the database
    
    Args:
        user_id: ID of the user creating the conversation
        title: Title of the conversation
        
    Returns:
        ID of the created conversation
    """
    session = get_session()
    
    # Create new conversation
    conversation = Conversation(
        user_id=user_id,
        title=title
    )
    
    session.add(conversation)
    session.commit()
    
    # Get the new conversation ID
    conversation_id = conversation.id
    
    session.close()
    
    return conversation_id

def get_conversations(user_id: int) -> List[Conversation]:
    """
    Get all conversations for a user
    
    Args:
        user_id: ID of the user
        
    Returns:
        List of conversation objects
    """
    session = get_session()
    
    # Get conversations with message count
    from sqlalchemy import func
    from sqlalchemy.orm import aliased, joinedload
    
    # Create an alias for the Message class
    Message_alias = aliased(Message)
    
    # Query conversations along with their message count
    conversations = session.query(Conversation)\
        .options(joinedload(Conversation.messages))\
        .filter(Conversation.user_id == user_id)\
        .order_by(Conversation.updated_at.desc())\
        .all()
    
    # Detach objects from session
    if conversations:
        session.expunge_all()
    
    session.close()
    
    return conversations

def get_conversation(conversation_id: int) -> Optional[Conversation]:
    """
    Get a specific conversation with all its messages
    
    Args:
        conversation_id: ID of the conversation
        
    Returns:
        Conversation object or None if not found
    """
    session = get_session()
    
    # Use eager loading to load the messages and files
    from sqlalchemy.orm import joinedload
    
    conversation = session.query(Conversation)\
        .options(
            joinedload(Conversation.messages).joinedload(Message.files)
        )\
        .filter(Conversation.id == conversation_id)\
        .first()
    
    # Important: If the conversation exists, make a detached copy of it
    # so we can use it after the session is closed
    if conversation:
        # This keeps the loaded relationships intact
        session.expunge_all()
        
    session.close()
    
    return conversation

def add_message_to_conversation(
    conversation_id: int, 
    role: str, 
    content: str,
    uploaded_files: Optional[List] = None
) -> Tuple[int, Optional[str]]:
    """
    Add a message to a conversation
    
    Args:
        conversation_id: ID of the conversation
        role: Role of the message sender ("user" or "assistant")
        content: Message content
        uploaded_files: List of Streamlit uploaded file objects
        
    Returns:
        Tuple containing:
            - ID of the created message (0 if creation failed due to blocked files)
            - Error message if any files were blocked, None otherwise
    """
    session = get_session()
    
    # Create new message
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content
    )
    
    session.add(message)
    session.commit()
    
    error_message = None
    
    # Add files if provided
    if uploaded_files:
        # Get user ID from conversation for DLP checks
        user_id = None
        if MS_DLP_AVAILABLE:
            conversation = session.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            if conversation:
                user_id = conversation.user_id
        
        for uploaded_file in uploaded_files:
            file_path, mime_type, file_size = save_uploaded_file(uploaded_file)
            
            # Check for Microsoft sensitivity labels if DLP integration is available
            if MS_DLP_AVAILABLE and user_id and is_dlp_integration_enabled(user_id):
                file_allowed, dlp_error = scan_file_for_sensitivity(
                    user_id=user_id,
                    file_path=file_path,
                    file_name=uploaded_file.name,
                    file_mime=mime_type
                )
                
                if not file_allowed:
                    # File blocked by DLP, return error
                    session.close()
                    # Clean up - delete the created message since we're aborting
                    with session_scope() as cleanup_session:
                        msg = cleanup_session.query(Message).filter(Message.id == message.id).first()
                        if msg:
                            cleanup_session.delete(msg)
                    
                    return 0, dlp_error
            
            # File is allowed, continue with adding it
            file = File(
                message_id=message.id,
                original_name=uploaded_file.name,
                path=file_path,
                mime_type=mime_type,
                size=file_size,
                scan_result={}
            )
            
            session.add(file)
        
        session.commit()
    
    # Update conversation timestamp
    conversation = session.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()
    
    if conversation:
        # Update conversation title based on first user message
        if role == "user" and not conversation.title or conversation.title == "New Conversation":
            # Use the first ~30 characters of the message as the title
            new_title = content[:30] + "..." if len(content) > 30 else content
            conversation.title = new_title
            session.commit()
    
    # Get the new message ID
    message_id = message.id
    
    session.close()
    
    return message_id, error_message

def delete_conversation(conversation_id: int) -> bool:
    """
    Delete a conversation and all its messages
    
    Args:
        conversation_id: ID of the conversation to delete
        
    Returns:
        Boolean indicating success
    """
    session = get_session()
    
    # Find conversation
    conversation = session.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()
    
    if not conversation:
        session.close()
        return False
    
    # Delete the conversation (cascade should handle messages and files)
    session.delete(conversation)
    session.commit()
    session.close()
    
    return True

def update_user_settings(user_id: int, settings_data: Dict[str, Any]) -> bool:
    """
    Update user settings
    
    Args:
        user_id: ID of the user
        settings_data: Dictionary of settings to update
        
    Returns:
        Boolean indicating success
    """
    # Use session_scope context manager to avoid detached instance errors
    try:
        with session_scope() as session:
            # Find user settings
            settings = session.query(Settings).filter(
                Settings.user_id == user_id
            ).first()
            
            if not settings:
                return False
            
            # Update settings - only allow updating attributes that exist on the model
            for key, value in settings_data.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)
                    
            # session_scope handles commit and close automatically
            return True
    except Exception as e:
        print(f"Error updating user settings: {str(e)}")
        return False

def format_detection_events(events: List) -> List[Dict[str, Any]]:
    """
    Format detection events for display
    
    Args:
        events: List of DetectionEvent objects
        
    Returns:
        List of formatted events with attributes extracted to avoid detached instance errors
    """
    formatted_events = []
    
    for event in events:
        try:
            # Extract all attributes to prevent detached instance errors
            # Copy all attributes immediately to avoid further access to the detached object
            event_dict = {
                "id": getattr(event, 'id', 0),
                "user_id": getattr(event, 'user_id', 0),
                "timestamp": getattr(event, 'timestamp', None),
                "action": getattr(event, 'action', "unknown"),
                "severity": getattr(event, 'severity', "unknown"),
                "file_names": getattr(event, 'file_names', ""),
                "detected_patterns": getattr(event, 'detected_patterns', {})
            }
            
            # Format timestamp
            timestamp = event_dict["timestamp"].strftime("%Y-%m-%d %H:%M:%S") if event_dict["timestamp"] else "Unknown"
            event_dict["timestamp"] = timestamp
            
            # Handle detected_patterns without calling methods on possibly detached instance
            try:
                # Try to access directly if possible
                if isinstance(event_dict["detected_patterns"], dict):
                    detected_patterns = event_dict["detected_patterns"]
                else:
                    # If it's not a dict already, try to use the JSON data directly
                    import json
                    if hasattr(event, 'detected_patterns') and event.detected_patterns is not None:
                        if isinstance(event.detected_patterns, str):
                            detected_patterns = json.loads(event.detected_patterns)
                        else:
                            detected_patterns = {}
                    else:
                        detected_patterns = {}
            except Exception:
                # Fallback if anything fails
                detected_patterns = {}
            
            # Calculate detection count safely
            try:
                detection_count = sum(len(matches) for matches in detected_patterns.values() if isinstance(matches, list))
            except Exception:
                detection_count = 0
            
            # Update the dictionary with processed values
            event_dict["detected_patterns"] = detected_patterns
            event_dict["detection_count"] = detection_count
            
            formatted_events.append(event_dict)
            
        except Exception as e:
            # Log the error but continue processing other events
            print(f"Error formatting event: {e}")
            continue
    
    return formatted_events


def format_conversation_messages(messages: List) -> List[Dict[str, Any]]:
    """
    Format conversation messages for AI processing
    
    Args:
        messages: List of Message objects
        
    Returns:
        List of formatted messages with attributes extracted to avoid detached instance errors,
        sorted by timestamp
    """
    formatted_messages = []
    
    for message in messages:
        try:
            # Extract all attributes to prevent detached instance errors
            message_dict = {
                "id": getattr(message, 'id', 0),
                "conversation_id": getattr(message, 'conversation_id', 0),
                "role": getattr(message, 'role', "user"),
                "content": getattr(message, 'content', ""),
                "timestamp": getattr(message, 'timestamp', None)
            }
            
            formatted_messages.append(message_dict)
        except Exception as e:
            # Log the error but continue processing other messages
            print(f"Error formatting message: {e}")
            continue
    
    # Sort messages by timestamp
    formatted_messages.sort(key=lambda x: x["timestamp"] if x["timestamp"] else datetime.min)
    
    return formatted_messages
