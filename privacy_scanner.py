import re
import json
import uuid
import time
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
import streamlit as st
from database import get_session, session_scope
from models import User, Settings, DetectionEvent

# Define patterns with their levels and confidence scores
DEFAULT_PATTERNS = [
    # Basic identifiers - Standard level
    {"name": "credit_card", "pattern": r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b", "level": "standard", "confidence": 0.95},
    {"name": "ssn", "pattern": r"\b(?!000|666|9\d{2})\d{3}[- ]?(?!00)\d{2}[- ]?(?!0000)\d{4}\b", "level": "standard", "confidence": 0.95},
    {"name": "email", "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "level": "standard", "confidence": 0.9},
    {"name": "phone_number", "pattern": r"\b(?:\+?\d{1,3}[ -]?)?(?:\(?\d{2,4}\)?[ -]?)?\d{3,4}[ -]?\d{3,4}\b", "level": "standard", "confidence": 0.85},
    {"name": "msisdn", "pattern": r"\+?[1-9]\d{6,14}\b", "level": "standard", "confidence": 0.9},
    {"name": "ip_address", "pattern": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "level": "standard", "confidence": 0.8},
    {"name": "date_of_birth", "pattern": r"\b(?:\d{2}[/-]\d{2}[/-]\d{4}|\d{4}[/-]\d{2}[/-]\d{2})\b", "level": "standard", "confidence": 0.8},
    {"name": "address", "pattern": r"\b\d{1,5}\s+(?:[A-Za-z]+\s?)+\s+(Street|St|Avenue|Ave|Boulevard|Blvd|Road|Rd|Drive|Dr|Lane|Ln)\b", "level": "standard", "confidence": 0.85},
    
    # Credentials - Standard level
    {"name": "password", "pattern": r"\b(password|passwd|pwd)[\"]?\s*[:=]\s*[\"]?.{6,}[\"]?\b", "level": "standard", "confidence": 0.95},
    {"name": "api_key", "pattern": r"\b(?:api_key|apikey|access_token|token|secret|bearer)[\"]?\s*[:=]\s*[\"]?[A-Za-z0-9\-_]{16,64}[\"]?\b", "level": "standard", "confidence": 0.95},
    
    # Cloud provider tokens - Standard level
    {"name": "aws_access_key", "pattern": r"AKIA[0-9A-Z]{16}", "level": "standard", "confidence": 0.98},
    {"name": "aws_secret_key", "pattern": r"(?i)aws_secret_access_key\s*[:=]\s*[\"]?[A-Za-z0-9/+=]{40}[\"]?", "level": "standard", "confidence": 0.98},
    {"name": "google_api_key", "pattern": r"AIza[0-9A-Za-z\-_]{35}", "level": "standard", "confidence": 0.98},
    
    # Classification terms - Standard level
    {"name": "classification", "pattern": r"\b(confidential|strictly confidential|secret|internal use only|proprietary|classified)\b", "level": "standard", "confidence": 0.8},
    
    # JWT token - Standard level
    {"name": "jwt", "pattern": r"\beyJ[A-Za-z0-9\-_]+?\.eyJ[A-Za-z0-9\-_]+?\.[A-Za-z0-9\-_]+\b", "level": "standard", "confidence": 0.9},
    
    # Private keys - Standard level
    {"name": "private_key", "pattern": r"-----BEGIN (RSA|DSA|EC|OPENSSH)? PRIVATE KEY-----", "level": "standard", "confidence": 0.98},
    
    # Names and personal info - Strict level
    {"name": "name", "pattern": r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b", "level": "strict", "confidence": 0.7},
    
    # URLs and web resources - Strict level
    {"name": "url", "pattern": r"https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)", "level": "strict", "confidence": 0.7},
    
    # IDs and identifiers - Strict level
    {"name": "uuid", "pattern": r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", "level": "strict", "confidence": 0.8},
    {"name": "passport", "pattern": r"\b[A-Z]{1,2}[0-9]{6,9}\b", "level": "strict", "confidence": 0.85},
    
    # Financial information - Strict level
    {"name": "iban", "pattern": r"\b[A-Z]{2}\d{2}(?:[ ]?[0-9A-Z]){11,30}\b", "level": "strict", "confidence": 0.9},
    {"name": "bank_account", "pattern": r"\b[0-9]{8,17}\b", "level": "strict", "confidence": 0.75},
    
    # Regional specific identifiers - Strict level
    {"name": "uk_nino", "pattern": r"\b(?!BG|GB|NK|KN|TN|NT|ZZ)([A-CEGHJ-PR-TW-Z]{2})\d{6}[A-D]\b", "level": "strict", "confidence": 0.9},
    {"name": "greek_amka", "pattern": r"\b\d{11}\b", "level": "strict", "confidence": 0.85},
    {"name": "greek_tax_id", "pattern": r"\b\d{9}\b", "level": "strict", "confidence": 0.85}
]

# Precompile all patterns at module load time
COMPILED_PATTERNS = {}

for pattern in DEFAULT_PATTERNS:
    COMPILED_PATTERNS[pattern["name"]] = {
        "regex": re.compile(pattern["pattern"]),
        "level": pattern["level"],
        "confidence": pattern["confidence"]
    }

# Generate dictionaries from patterns for backward compatibility
STANDARD_PATTERNS = {pattern["name"]: pattern["pattern"] for pattern in DEFAULT_PATTERNS if pattern["level"] == "standard"}
STRICT_PATTERNS = {**STANDARD_PATTERNS}
STRICT_PATTERNS.update({pattern["name"]: pattern["pattern"] for pattern in DEFAULT_PATTERNS if pattern["level"] == "strict"})

# Precompiled pattern dictionaries
COMPILED_STANDARD_PATTERNS = {name: COMPILED_PATTERNS[name] for name in STANDARD_PATTERNS.keys()}
COMPILED_STRICT_PATTERNS = {name: COMPILED_PATTERNS[name] for name in STRICT_PATTERNS.keys()}

def get_user_settings(user_id: int) -> Optional[Settings]:
    """Get user settings for privacy scanning"""
    try:
        with session_scope() as session:
            settings = session.query(Settings).filter(Settings.user_id == user_id).first()
            
            # If we found settings, create a copy of important attributes to avoid detached instance errors
            if settings:
                return Settings(
                    id=settings.id,
                    user_id=settings.user_id,
                    scan_enabled=settings.scan_enabled,
                    scan_level=settings.scan_level,
                    auto_anonymize=settings.auto_anonymize,
                    disable_scan_for_local_model=settings.disable_scan_for_local_model,
                    custom_patterns=settings.custom_patterns,
                    enable_ms_dlp=getattr(settings, 'enable_ms_dlp', True),
                    ms_dlp_sensitivity_threshold=getattr(settings, 'ms_dlp_sensitivity_threshold', 'confidential')
                )
            return None
    except Exception as e:
        print(f"Error getting user settings: {str(e)}")
        return None

def scan_text(user_id: int, text: str, minimum_confidence: float = 0.7) -> Tuple[bool, Dict[str, List[str]]]:
    """
    Scan text for sensitive information using precompiled regex patterns
    
    Args:
        user_id: ID of the current user
        text: Text to scan
        minimum_confidence: Minimum confidence score to consider a match (0.0-1.0)
        
    Returns:
        Tuple containing:
            - Boolean indicating if sensitive information was found
            - Dictionary of detected patterns with type as key and list of matches as value
    """
    start_time = time.time()
    settings = get_user_settings(user_id)
    
    if not settings:
        return False, {}
    
    # If scanning is disabled, return no matches
    if not settings.scan_enabled:
        return False, {}
    
    # Determine which pattern set to use based on scan level
    if settings.scan_level == "strict":
        compiled_patterns = COMPILED_STRICT_PATTERNS.copy()
    else:  # "standard" or any other value
        compiled_patterns = COMPILED_STANDARD_PATTERNS.copy()
    
    # Add custom patterns if available
    custom_patterns = settings.get_custom_patterns()
    is_strict_mode = settings.scan_level == "strict"
    
    # Compile and add custom patterns
    custom_compiled_patterns = {}
    for pattern_dict in custom_patterns:
        if isinstance(pattern_dict, dict) and "name" in pattern_dict and "pattern" in pattern_dict:
            # Check if pattern has a level attribute (backward compatibility)
            pattern_level = pattern_dict.get("level", "standard")
            pattern_confidence = pattern_dict.get("confidence", 0.8)  # Default confidence for custom patterns
            
            # Only add the pattern if:
            # - In strict mode: include all patterns (both standard and strict)
            # - In standard mode: only include patterns marked as "standard"
            if is_strict_mode or pattern_level == "standard":
                # Compile the custom pattern
                try:
                    regex = re.compile(pattern_dict["pattern"])
                    custom_compiled_patterns[pattern_dict["name"]] = {
                        "regex": regex,
                        "level": pattern_level,
                        "confidence": pattern_confidence
                    }
                except Exception as e:
                    print(f"Error compiling custom pattern {pattern_dict['name']}: {str(e)}")
    
    # Merge custom patterns with standard/strict patterns
    compiled_patterns.update(custom_compiled_patterns)
    
    # Scan text with all patterns using precompiled regex
    detected = {}
    for pattern_name, pattern_info in compiled_patterns.items():
        # Skip patterns with confidence below threshold
        if pattern_info["confidence"] < minimum_confidence:
            continue
            
        # Use the precompiled regex for faster matching
        matches = pattern_info["regex"].findall(text)
        if matches:
            detected[pattern_name] = matches
    
    # Determine if sensitive information was found
    sensitive_found = len(detected) > 0
    
    # Log detection event if sensitive information was found
    if sensitive_found:
        try:
            with session_scope() as session:
                detection_event = DetectionEvent(
                    user_id=user_id,
                    timestamp=datetime.now(),
                    action="scan",
                    severity="high" if len(detected) > 2 else "medium" if len(detected) > 0 else "low",
                    detected_patterns=detected,
                    file_names=""
                )
                session.add(detection_event)
                # session_scope handles commit and close
        except Exception as e:
            print(f"Error logging detection event: {str(e)}")
    
    # Optionally log performance metrics
    scan_time = time.time() - start_time
    if sensitive_found:
        print(f"Privacy scan completed in {scan_time:.4f}s: found {len(detected)} pattern types")
    
    return sensitive_found, detected

def scan_file_content(user_id: int, file_content: str, file_name: str) -> Tuple[bool, Dict[str, List[str]]]:
    """
    Scan file content for sensitive information (basic version for direct string content)
    
    Args:
        user_id: ID of the current user
        file_content: Content of the file as string
        file_name: Name of the file
        
    Returns:
        Tuple containing:
            - Boolean indicating if sensitive information was found
            - Dictionary of detected patterns with type as key and list of matches as value
    """
    sensitive_found, detected = scan_text(user_id, file_content)
    
    # Log detection event if sensitive information was found
    if sensitive_found:
        try:
            with session_scope() as session:
                detection_event = DetectionEvent(
                    user_id=user_id,
                    timestamp=datetime.now(),
                    action="scan",
                    severity="high" if len(detected) > 2 else "medium" if len(detected) > 0 else "low",
                    detected_patterns=detected,
                    file_names=file_name
                )
                session.add(detection_event)
                # session_scope handles commit and close
        except Exception as e:
            print(f"Error logging file detection event: {str(e)}")
    
    return sensitive_found, detected

def scan_file_path(user_id: int, file_path: str, file_name: str, file_type: str) -> Tuple[bool, Dict[str, List[str]], float]:
    """
    Scan a file from disk using chunked processing for large files
    
    Args:
        user_id: ID of the current user
        file_path: Path to the file on disk
        file_name: Original name of the file
        file_type: MIME type or file extension
        
    Returns:
        Tuple containing:
            - Boolean indicating if sensitive information was found
            - Dictionary of detected patterns with type as key and list of matches as value
            - Processing time in seconds
    """
    import file_processor
    
    # Create a scanner function that will be applied to each chunk
    def chunk_scanner(text_chunk: str) -> Tuple[bool, Dict[str, List[str]]]:
        # Skip empty chunks
        if not text_chunk or len(text_chunk.strip()) == 0:
            return False, {}
        
        # Use our normal scan_text function
        return scan_text(user_id, text_chunk)
    
    # Process the file in chunks with parallel processing
    sensitive_found, detected, processing_time = file_processor.scan_file_chunks(
        file_path=file_path,
        file_type=file_type,
        scanner_func=chunk_scanner,
        chunk_size=2000,  # Adjust based on expected file sizes
        max_workers=4     # Adjust based on system capabilities
    )
    
    # Log detection event if sensitive information was found
    if sensitive_found:
        try:
            with session_scope() as session:
                detection_event = DetectionEvent(
                    user_id=user_id,
                    timestamp=datetime.now(),
                    action="scan",
                    severity="high" if len(detected) > 2 else "medium" if len(detected) > 0 else "low",
                    detected_patterns=detected,
                    file_names=file_name
                )
                session.add(detection_event)
                # session_scope handles commit and close
        except Exception as e:
            print(f"Error logging file detection event: {str(e)}")
    
    # Log performance metrics
    print(f"File scan completed in {processing_time:.4f}s: found {len(detected)} pattern types in {file_name}")
    
    return sensitive_found, detected, processing_time

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
    
    # If no sensitive information found, return original text
    settings = get_user_settings(user_id)
    if not sensitive_found or not settings:
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
            elif pattern_type == "phone_number" or pattern_type == "msisdn":
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
            elif pattern_type == "api_key" or "key" in pattern_type or "token" in pattern_type:
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
            elif pattern_type == "bank_account" or pattern_type == "iban":
                # Replace with "[REDACTED BANK ACCOUNT]"
                replacement = "[REDACTED BANK ACCOUNT]"
            elif pattern_type == "aws_access_key" or pattern_type == "aws_secret_key":
                # Replace with "[REDACTED AWS KEY]"
                replacement = "[REDACTED AWS KEY]"
            elif pattern_type == "google_api_key":
                # Replace with "[REDACTED GOOGLE API KEY]"
                replacement = "[REDACTED GOOGLE API KEY]"
            elif pattern_type == "classification":
                # Replace with "[CLASSIFIED DOCUMENT]"
                replacement = "[CLASSIFIED DOCUMENT]"
            elif pattern_type == "jwt":
                # Replace with "[REDACTED JWT TOKEN]"
                replacement = "[REDACTED JWT TOKEN]"
            elif pattern_type == "private_key":
                # Replace with "[REDACTED PRIVATE KEY]"
                replacement = "[REDACTED PRIVATE KEY]"
            elif pattern_type == "uk_nino":
                # Replace with "[REDACTED UK NINO]"
                replacement = "[REDACTED UK NINO]"
            elif pattern_type == "greek_amka" or pattern_type == "greek_tax_id":
                # Replace with "[REDACTED GREEK ID]"
                replacement = "[REDACTED GREEK ID]"
            else:
                # Generic replacement for custom patterns
                replacement = f"[REDACTED {pattern_type.upper()}]"
            
            # Replace in text
            anonymized_text = anonymized_text.replace(match, replacement)
    
    # Log anonymization event
    try:
        with session_scope() as session:
            detection_event = DetectionEvent(
                user_id=user_id,
                timestamp=datetime.now(),
                action="anonymize",
                severity="high" if len(detected) > 2 else "medium" if len(detected) > 0 else "low",
                detected_patterns=detected,
                file_names=""
            )
            session.add(detection_event)
            # session_scope handles commit and close
    except Exception as e:
        print(f"Error logging anonymization event: {str(e)}")
    
    return anonymized_text, detected

def get_detection_events(user_id: Optional[int] = None, limit: int = 50, include_username: bool = False) -> List[Dict[str, Any]]:
    """
    Get recent detection events for a user or all users
    
    Args:
        user_id: ID of the user, or None to get events for all users (admin only)
        limit: Maximum number of events to return
        include_username: Whether to include username in the results (for admin view)
        
    Returns:
        List of formatted detection events as dictionaries to avoid detached instance errors
    """
    try:
        with session_scope() as session:
            # Create base query
            query = session.query(DetectionEvent)
            
            # Filter by user if specified
            if user_id is not None:
                query = query.filter(DetectionEvent.user_id == user_id)
            
            # Get username mapping if needed
            usernames = {}
            if include_username:
                from models import User
                users = session.query(User).all()
                usernames = {user.id: user.username for user in users}
            
            # Execute query with ordering and limit
            events = query.order_by(
                DetectionEvent.timestamp.desc()
            ).limit(limit).all()
            
            # Format events to avoid detached instance errors
            formatted_events = []
            for event in events:
                try:
                    # Create a dictionary with all needed attributes
                    event_dict = {
                        "id": event.id,
                        "user_id": event.user_id,
                        "timestamp": event.timestamp,
                        "action": event.action,
                        "severity": event.severity,
                        "file_names": event.file_names,
                        "detected_patterns": event.detected_patterns if isinstance(event.detected_patterns, dict) else {}
                    }
                    
                    # Add username for admin view if requested
                    if include_username and event.user_id in usernames:
                        event_dict["username"] = usernames[event.user_id]
                    
                    formatted_events.append(event_dict)
                except Exception as e:
                    print(f"Error formatting event: {str(e)}")
                    continue
                    
            return formatted_events
    except Exception as e:
        print(f"Error getting detection events: {str(e)}")
        return []
