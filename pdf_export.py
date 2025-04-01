import os
import tempfile
from datetime import datetime
from typing import List, Dict, Any, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from database import get_session
from models import Conversation, Message, User

def get_conversation(conversation_id: int) -> Optional[Conversation]:
    """Get conversation details from the database"""
    session = get_session()
    conversation = session.query(Conversation).filter(Conversation.id == conversation_id).first()
    session.close()
    return conversation

def get_user(user_id: int) -> Optional[User]:
    """Get user details from the database"""
    session = get_session()
    user = session.query(User).filter(User.id == user_id).first()
    session.close()
    return user

def export_conversation_to_pdf(conversation_id: int) -> str:
    """
    Export a conversation to PDF
    
    Args:
        conversation_id: ID of the conversation to export
        
    Returns:
        Path to the generated PDF file
    """
    # Get conversation details
    conversation = get_conversation(conversation_id)
    if not conversation:
        raise ValueError(f"Conversation with ID {conversation_id} not found")
    
    # Get user details
    user = get_user(conversation.user_id)
    if not user:
        raise ValueError(f"User with ID {conversation.user_id} not found")
    
    # Create temporary file
    temp_dir = tempfile.gettempdir()
    pdf_filename = f"conversation_{conversation_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = os.path.join(temp_dir, pdf_filename)
    
    # Create PDF document
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    heading_style = styles["Heading2"]
    normal_style = styles["Normal"]
    
    # Create custom styles
    user_message_style = ParagraphStyle(
        "UserMessage",
        parent=normal_style,
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=colors.blue,
        spaceBefore=6,
        spaceAfter=2
    )
    
    assistant_message_style = ParagraphStyle(
        "AssistantMessage",
        parent=normal_style,
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.black,
        spaceBefore=2,
        spaceAfter=6,
        leftIndent=20
    )
    
    # Create document elements
    elements = []
    
    # Add title
    elements.append(Paragraph(f"Conversation: {conversation.title}", title_style))
    elements.append(Spacer(1, 12))
    
    # Add metadata
    metadata = [
        ["Username:", user.username],
        ["Created:", conversation.created_at.strftime("%Y-%m-%d %H:%M:%S")],
        ["Updated:", conversation.updated_at.strftime("%Y-%m-%d %H:%M:%S")]
    ]
    
    # Create metadata table
    metadata_table = Table(metadata, colWidths=[100, 300])
    metadata_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica'),
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.gray),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey)
    ]))
    
    elements.append(metadata_table)
    elements.append(Spacer(1, 24))
    
    # Add messages
    elements.append(Paragraph("Conversation", heading_style))
    elements.append(Spacer(1, 12))
    
    for message in conversation.messages:
        if message.role == "user":
            elements.append(Paragraph(f"User:", user_message_style))
            elements.append(Paragraph(message.content, normal_style))
            
            # Add files if any
            if message.files:
                for file in message.files:
                    elements.append(Paragraph(f"File: {file.original_name} ({file.mime_type})", 
                                             ParagraphStyle(
                                                 "FileInfo",
                                                 parent=normal_style,
                                                 fontSize=8,
                                                 textColor=colors.gray,
                                                 leftIndent=10
                                             )))
        else:
            elements.append(Paragraph(f"Assistant:", assistant_message_style))
            elements.append(Paragraph(message.content, normal_style))
        
        elements.append(Spacer(1, 6))
    
    # Build PDF
    doc.build(elements)
    
    return pdf_path
