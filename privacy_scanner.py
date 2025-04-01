import re
import json
import uuid
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
import streamlit as st
from database import get_session
from models import User, Settings, DetectionEvent

# Define standard regex patterns for sensitive data
STANDARD_PATTERNS = {
    "credit_card": r"\b(?:\d{4}[ -]?){3}\d{4}\b",
    "ssn": r"\b\d{3}[-]?\d{2}[-]?\d{4}\b",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone_number": r"\b(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "ip_address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
    "date_of_birth": r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b",
    "address": r"\b\d+\s+[A-Za-z0-9\s,]+\b(?:street|st|avenue|ave|road|rd|highway|hwy|square|sq|trail|trl|drive|dr|court|ct|parkway|pkwy|circle|cir|boulevard|blvd)\b\s*(?:[A-Za-z]+\s*,\s*)?(?:[A-Za-z]+\s*,\s*)?(?:\d{5}(?:-\d{4})?)?",
    "password": r"\b(?:password|passwd|pwd)[\s:=]+\S+\b",
    "api_key": r"\b(?:sk-|pk-|api[-_]?key|token)[-_a-zA-Z0-9]{10,}\b"
}

# Additional patterns for strict scanning
STRICT_PATTERNS = {
    **STANDARD_PATTERNS,
    "name": r"\b(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.)\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b",
    "url": r"https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)",
    "uuid": r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    "passport": r"\b[A-Z]{1,2}[0-9]{6,9}\b",
    "bank_account": r"\b[0-9]{8,17}\b"
}

def get_user_settings(user_id: int) -> Optional[Settings]:
    """Get user settings for privacy scanning"""
    session = get_session()
    settings = session.query(Settings).filter(Settings.user_id == user_id).first()
    session.close()
    return settings

def scan_text(user_id: int, text: str) -> Tuple[bool, Dict[str, List[str]]]:
    """
    Scan text for sensitive information
    
    Args:
        user_id: ID of the current user
        text: Text to scan
        
    Returns:
        Tuple containing:
            - Boolean indicating if sensitive information was found
            - Dictionary of detected patterns with type as key and list of matches as value
    """
    settings = get_user_settings(user_id)
    
    if not settings:
        return False, {}
    
    # If scanning is disabled, return no matches
    if not settings.scan_enabled:
        return False, {}
    
    # Determine which pattern set to use based on scan level
    if settings.scan_level == "strict":
        patterns = STRICT_PATTERNS.copy()
    else:  # "standard" or any other value
        patterns = STANDARD_PATTERNS.copy()
    
    # Add custom patterns if available
    custom_patterns = settings.get_custom_patterns()
    for pattern_dict in custom_patterns:
        if isinstance(pattern_dict, dict) and "name" in pattern_dict and "pattern" in pattern_dict:
            patterns[pattern_dict["name"]] = pattern_dict["pattern"]
    
    # Scan text with all patterns
    detected = {}
    for pattern_name, pattern in patterns.items():
        matches = re.findall(pattern, text)
        if matches:
            detected[pattern_name] = matches
    
    # Determine if sensitive information was found
    sensitive_found = len(detected) > 0
    
    # Log detection event if sensitive information was found
    if sensitive_found:
        session = get_session()
        detection_event = DetectionEvent(
            user_id=user_id,
            timestamp=datetime.now(),
            action="scan",
            severity="high" if len(detected) > 2 else "medium" if len(detected) > 0 else "low",
            detected_patterns=detected,
            file_names=""
        )
        session.add(detection_event)
        session.commit()
        session.close()
    
    return sensitive_found, detected

def scan_file_content(user_id: int, file_content: str, file_name: str) -> Tuple[bool, Dict[str, List[str]]]:
    """
    Scan file content for sensitive information
    
    Args:
        user_id: ID of the current user
        file_content: Content of the file
        file_name: Name of the file
        
    Returns:
        Tuple containing:
            - Boolean indicating if sensitive information was found
            - Dictionary of detected patterns with type as key and list of matches as value
    """
    sensitive_found, detected = scan_text(user_id, file_content)
    
    # Log detection event if sensitive information was found
    if sensitive_found:
        session = get_session()
        detection_event = DetectionEvent(
            user_id=user_id,
            timestamp=datetime.now(),
            action="scan",
            severity="high" if len(detected) > 2 else "medium" if len(detected) > 0 else "low",
            detected_patterns=detected,
            file_names=file_name
        )
        session.add(detection_event)
        session.commit()
        session.close()
    
    return sensitive_found, detected

def anonymize_text(user_id: int, text: str) -> Tuple[str, Dict[str, List[str]]]:
    """
    Anonymize sensitive information in text
    
    Args:
        user_id: ID of the current user
        text: Text to anonymize
        
    Returns:
        Tuple containing:
            - Anonymized text
            - Dictionary of detected patterns with type as key and list of matches as value
    """
    sensitive_found, detected = scan_text(user_id, text)
    
    # If no sensitive information found or auto-anonymize is disabled, return original text
    settings = get_user_settings(user_id)
    if not sensitive_found or not settings or not settings.auto_anonymize:
        return text, detected
    
    # Anonymize each detected pattern
    anonymized_text = text
    for pattern_type, matches in detected.items():
        for match in matches:
            if pattern_type == "credit_card":
                # Replace with "XXXX-XXXX-XXXX-1234" (keeping last 4 digits if possible)
                last_four = match[-4:] if len(match) >= 4 else "1234"
                replacement = f"XXXX-XXXX-XXXX-{last_four}"
            elif pattern_type == "ssn":
                # Replace with "XXX-XX-1234" (keeping last 4 digits if possible)
                last_four = match[-4:] if len(match) >= 4 else "1234"
                replacement = f"XXX-XX-{last_four}"
            elif pattern_type == "email":
                # Replace with "email@redacted.com"
                replacement = "email@redacted.com"
            elif pattern_type == "phone_number":
                # Replace with "(XXX) XXX-1234" (keeping last 4 digits if possible)
                last_four = match[-4:] if len(match) >= 4 else "1234"
                replacement = f"(XXX) XXX-{last_four}"
            elif pattern_type == "ip_address":
                # Replace with "XXX.XXX.XXX.XXX"
                replacement = "XXX.XXX.XXX.XXX"
            elif pattern_type == "date_of_birth":
                # Replace with "XX/XX/XXXX"
                replacement = "XX/XX/XXXX"
            elif pattern_type == "address":
                # Replace with "[REDACTED ADDRESS]"
                replacement = "[REDACTED ADDRESS]"
            elif pattern_type == "password":
                # Replace with "password: [REDACTED]"
                replacement = "password: [REDACTED]"
            elif pattern_type == "api_key":
                # Replace with "[REDACTED API KEY]"
                replacement = "[REDACTED API KEY]"
            elif pattern_type == "name":
                # Replace with "[REDACTED NAME]"
                replacement = "[REDACTED NAME]"
            elif pattern_type == "url":
                # Replace with "[REDACTED URL]"
                replacement = "[REDACTED URL]"
            elif pattern_type == "uuid":
                # Replace with "[REDACTED UUID]"
                replacement = "[REDACTED UUID]"
            elif pattern_type == "passport":
                # Replace with "[REDACTED PASSPORT]"
                replacement = "[REDACTED PASSPORT]"
            elif pattern_type == "bank_account":
                # Replace with "[REDACTED BANK ACCOUNT]"
                replacement = "[REDACTED BANK ACCOUNT]"
            else:
                # Generic replacement for custom patterns
                replacement = f"[REDACTED {pattern_type.upper()}]"
            
            # Replace in text
            anonymized_text = anonymized_text.replace(match, replacement)
    
    # Log anonymization event
    session = get_session()
    detection_event = DetectionEvent(
        user_id=user_id,
        timestamp=datetime.now(),
        action="anonymize",
        severity="high" if len(detected) > 2 else "medium" if len(detected) > 0 else "low",
        detected_patterns=detected,
        file_names=""
    )
    session.add(detection_event)
    session.commit()
    session.close()
    
    return anonymized_text, detected

def get_detection_events(user_id: int, limit: int = 50) -> List[DetectionEvent]:
    """Get recent detection events for a user"""
    session = get_session()
    events = session.query(DetectionEvent).filter(
        DetectionEvent.user_id == user_id
    ).order_by(
        DetectionEvent.timestamp.desc()
    ).limit(limit).all()
    session.close()
    return events
