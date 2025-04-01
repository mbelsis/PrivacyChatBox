import os
import uuid
import tempfile
import mimetypes
from typing import Optional, Tuple, Dict, Any, List
import streamlit as st
from database import get_session
from models import Conversation, Message, File, User, Settings

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
    conversations = session.query(Conversation).filter(
        Conversation.user_id == user_id
    ).order_by(
        Conversation.updated_at.desc()
    ).all()
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
    conversation = session.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()
    session.close()
    
    return conversation

def add_message_to_conversation(
    conversation_id: int, 
    role: str, 
    content: str,
    uploaded_files: List = None
) -> int:
    """
    Add a message to a conversation
    
    Args:
        conversation_id: ID of the conversation
        role: Role of the message sender ("user" or "assistant")
        content: Message content
        uploaded_files: List of Streamlit uploaded file objects
        
    Returns:
        ID of the created message
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
    
    # Add files if provided
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_path, mime_type, file_size = save_uploaded_file(uploaded_file)
            
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
    
    return message_id

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
    session = get_session()
    
    # Find user settings
    settings = session.query(Settings).filter(
        Settings.user_id == user_id
    ).first()
    
    if not settings:
        session.close()
        return False
    
    # Update settings
    for key, value in settings_data.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    
    session.commit()
    session.close()
    
    return True

def format_detection_events(events: List) -> List[Dict[str, Any]]:
    """
    Format detection events for display
    
    Args:
        events: List of DetectionEvent objects
        
    Returns:
        List of formatted events
    """
    formatted_events = []
    
    for event in events:
        # Format timestamp
        timestamp = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        # Get detection count
        detected_patterns = event.get_detected_patterns()
        detection_count = sum(len(matches) for matches in detected_patterns.values())
        
        # Format event
        formatted_event = {
            "id": event.id,
            "timestamp": timestamp,
            "action": event.action,
            "severity": event.severity,
            "detection_count": detection_count,
            "detected_patterns": detected_patterns,
            "file_names": event.file_names
        }
        
        formatted_events.append(formatted_event)
    
    return formatted_events
