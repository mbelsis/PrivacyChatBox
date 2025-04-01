from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import json
import datetime

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String, default="user")  # "admin" or "user"
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    settings = relationship("Settings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    detection_events = relationship("DetectionEvent", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")

class Settings(Base):
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    
    # LLM provider settings
    llm_provider = Column(String, default="openai")  # openai, claude, gemini, local
    ai_character = Column(String, default="assistant")
    
    # API keys and model selection
    openai_api_key = Column(String, default="")
    openai_model = Column(String, default="gpt-4o")
    
    claude_api_key = Column(String, default="")
    claude_model = Column(String, default="claude-3-5-sonnet-20241022")
    
    gemini_api_key = Column(String, default="")
    gemini_model = Column(String, default="gemini-1.5-pro")
    
    serpapi_key = Column(String, default="")
    local_model_path = Column(String, default="")
    
    # Privacy settings
    scan_enabled = Column(Boolean, default=True)
    scan_level = Column(String, default="standard")  # standard, strict
    auto_anonymize = Column(Boolean, default=True)
    disable_scan_for_local_model = Column(Boolean, default=True)
    custom_patterns = Column(JSON, default=list)
    
    # Updated timestamp
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="settings")
    
    def get_custom_patterns(self):
        """Get custom patterns as a list"""
        if isinstance(self.custom_patterns, list):
            return self.custom_patterns
        elif isinstance(self.custom_patterns, str):
            try:
                return json.loads(self.custom_patterns)
            except:
                return []
        else:
            return []
    
    def set_custom_patterns(self, patterns):
        """Set custom patterns from a list"""
        if isinstance(patterns, list):
            self.custom_patterns = patterns
        else:
            self.custom_patterns = []

class DetectionEvent(Base):
    __tablename__ = "detection_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    timestamp = Column(DateTime, default=func.now())
    action = Column(String)  # "scan", "anonymize"
    severity = Column(String)  # "low", "medium", "high"
    detected_patterns = Column(JSON)
    file_names = Column(String, default="")
    
    # Relationships
    user = relationship("User", back_populates="detection_events")
    
    def get_detected_patterns(self):
        """Get detected patterns as a dictionary"""
        if isinstance(self.detected_patterns, dict):
            return self.detected_patterns
        elif isinstance(self.detected_patterns, str):
            try:
                return json.loads(self.detected_patterns)
            except:
                return {}
        else:
            return {}

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    title = Column(String, default="New Conversation")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convert conversation to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "messages": [message.to_dict() for message in self.messages]
        }

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"))
    role = Column(String)  # "user" or "assistant"
    content = Column(Text)
    timestamp = Column(DateTime, default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    files = relationship("File", back_populates="message", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convert message to dictionary"""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "files": [file.to_dict() for file in self.files]
        }

class File(Base):
    __tablename__ = "files"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"))
    original_name = Column(String)
    path = Column(String)
    mime_type = Column(String)
    size = Column(Integer)
    scan_result = Column(JSON)
    
    # Relationships
    message = relationship("Message", back_populates="files")
    
    def get_scan_result(self):
        """Get scan result as a dictionary"""
        if isinstance(self.scan_result, dict):
            return self.scan_result
        elif isinstance(self.scan_result, str):
            try:
                return json.loads(self.scan_result)
            except:
                return {}
        else:
            return {}
    
    def to_dict(self):
        """Convert file to dictionary"""
        return {
            "id": self.id,
            "message_id": self.message_id,
            "original_name": self.original_name,
            "path": self.path,
            "mime_type": self.mime_type,
            "size": self.size,
            "scan_result": self.get_scan_result()
        }
