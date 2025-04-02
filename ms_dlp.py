import os
import json
import logging
import mimetypes
from typing import Dict, List, Tuple, Optional, Any
import msal
import requests
from datetime import datetime
import streamlit as st
from database import get_session, session_scope
from models import User, Settings, DetectionEvent

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ms_dlp")

# Constants
MS_GRAPH_ENDPOINT = "https://graph.microsoft.com/v1.0"
MS_DLP_ENDPOINT = "https://api.security.microsoft.com/api/sensitivityLabels"
MS_COMPLIANCE_ENDPOINT = "https://compliance.microsoft.com/api/dlp/incidents"

# Sensitivity levels in order of increasing sensitivity
SENSITIVITY_LEVELS = {
    "general": 0,  # Public/General
    "internal": 1,  # Internal Only
    "confidential": 2,  # Confidential
    "highly_confidential": 3,  # Highly Confidential
    "secret": 4,  # Secret
    "top_secret": 5   # Top Secret
}

# Cache for MS Graph authentication tokens
TOKEN_CACHE = {}

def get_ms_settings() -> Dict[str, str]:
    """Get Microsoft settings from environment variables"""
    required_settings = [
        "MS_CLIENT_ID",
        "MS_CLIENT_SECRET",
        "MS_TENANT_ID",
        "MS_DLP_ENDPOINT_ID"
    ]
    
    settings = {}
    missing_settings = []
    
    for setting in required_settings:
        value = os.environ.get(setting)
        if not value:
            missing_settings.append(setting)
        settings[setting] = value
    
    if missing_settings:
        missing_str = ", ".join(missing_settings)
        logger.error(f"Missing required Microsoft settings: {missing_str}")
        settings["is_configured"] = False
    else:
        settings["is_configured"] = True
        
    return settings

def get_ms_graph_token() -> Optional[str]:
    """Get a Microsoft Graph API token"""
    settings = get_ms_settings()
    
    if not settings["is_configured"]:
        return None
    
    # Check if we have a valid cached token
    cache_key = f"{settings['MS_CLIENT_ID']}_{settings['MS_TENANT_ID']}"
    if cache_key in TOKEN_CACHE:
        token_info = TOKEN_CACHE[cache_key]
        if token_info["expires_at"] > datetime.now().timestamp():
            return token_info["access_token"]
    
    # No valid token in cache, get a new one
    authority = f"https://login.microsoftonline.com/{settings['MS_TENANT_ID']}"
    scopes = ["https://graph.microsoft.com/.default"]
    
    app = msal.ConfidentialClientApplication(
        settings["MS_CLIENT_ID"],
        client_credential=settings["MS_CLIENT_SECRET"],
        authority=authority
    )
    
    result = app.acquire_token_for_client(scopes=scopes)
    
    if "access_token" in result:
        # Cache the token
        TOKEN_CACHE[cache_key] = {
            "access_token": result["access_token"],
            "expires_at": datetime.now().timestamp() + result["expires_in"]
        }
        return result["access_token"]
    else:
        logger.error(f"Error getting Microsoft Graph token: {result.get('error')}")
        logger.error(f"Error description: {result.get('error_description')}")
        return None

def check_sensitivity_label(file_path: str, file_mime: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Check if a file has Microsoft Sensitivity labels
    
    Args:
        file_path: Path to the file to check
        file_mime: MIME type of the file
        
    Returns:
        Tuple containing:
            - Boolean indicating if the file has a sensitivity label above the threshold
            - Dictionary with sensitivity information or None if no sensitivity found
    """
    # Get Microsoft Graph API token
    token = get_ms_graph_token()
    if not token:
        logger.warning("Unable to get Microsoft Graph token, skipping sensitivity check")
        return False, None
    
    # Supported file types for sensitivity labels
    supported_extensions = [
        ".docx", ".xlsx", ".pptx",  # Office formats
        ".pdf",  # PDF
        ".txt", ".csv",  # Text formats
        ".msg", ".eml"  # Email formats
    ]
    
    # Check if file extension is supported
    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext not in supported_extensions:
        logger.info(f"File type {file_ext} not supported for sensitivity label checking")
        return False, None
    
    try:
        # Read the file
        with open(file_path, "rb") as f:
            file_content = f.read()
            
        # Get MS settings
        settings = get_ms_settings()
        
        # Set up headers for API call
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": file_mime
        }
        
        # Call Microsoft DLP API to check for sensitivity labels
        endpoint = f"{MS_DLP_ENDPOINT}/check"
        response = requests.post(
            endpoint,
            headers=headers,
            data=file_content
        )
        
        # Throw an error if response is not successful
        response.raise_for_status()
        
        # Parse the response
        label_info = response.json()
        
        # Check if any sensitivity label was found
        if not label_info.get("sensitivityLabel"):
            return False, None
        
        # Extract sensitivity level and return the sensitivity info
        # Note: We only return the sensitivity info here, the threshold check is done in scan_file_for_sensitivity
        # where we have access to user-specific settings
        sensitivity = label_info["sensitivityLabel"]
        
        # Return False for exceeds_threshold since we'll check this in scan_file_for_sensitivity
        # with the user's specific threshold setting
        return False, sensitivity
        
    except Exception as e:
        logger.error(f"Error checking sensitivity label: {str(e)}")
        return False, None

def report_dlp_violation(
    user_id: int,
    file_path: str, 
    file_name: str,
    sensitivity_info: Dict[str, Any]
) -> bool:
    """
    Report a DLP violation to Microsoft
    
    Args:
        user_id: ID of the user who tried to upload the file
        file_path: Path to the sensitive file
        file_name: Original name of the file
        sensitivity_info: Sensitivity information from the check
        
    Returns:
        Boolean indicating success
    """
    # Get Microsoft Graph API token
    token = get_ms_graph_token()
    if not token:
        logger.warning("Unable to get Microsoft Graph token, skipping DLP violation report")
        return False
    
    try:
        # Get user information
        with session_scope() as session:
            user = session.query(User).filter(User.id == user_id).first()
            username = user.username if user else "Unknown"
            azure_id = user.azure_id if user else None
        
        # Get MS settings
        settings = get_ms_settings()
        
        # Create payload for DLP incident
        payload = {
            "title": f"Sensitive file upload blocked: {file_name}",
            "description": f"User {username} attempted to upload a sensitive file to PrivacyChatBoX",
            "severity": "medium",
            "status": "active",
            "sensitivityLevel": sensitivity_info.get("sensitivity", "unknown"),
            "sensitivityLabelId": sensitivity_info.get("id", "unknown"),
            "contentInfo": {
                "fileName": file_name,
                "fileType": os.path.splitext(file_name)[1].lower(),
                "sensitivityLabelName": sensitivity_info.get("name", "Unknown"),
                "detectedTime": datetime.now().isoformat()
            },
            "userInfo": {
                "username": username,
                "azureId": azure_id
            },
            "appInfo": {
                "appName": "PrivacyChatBoX",
                "appId": settings.get("MS_CLIENT_ID")
            },
            "endpointId": settings.get("MS_DLP_ENDPOINT_ID")
        }
        
        # Set up headers for API call
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Call Microsoft DLP API to report the incident
        endpoint = MS_COMPLIANCE_ENDPOINT
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload
        )
        
        # Check response
        if response.status_code in (200, 201, 202, 204):
            logger.info(f"Successfully reported DLP violation for file: {file_name}")
            
            # Log the event in our database
            with session_scope() as session:
                event = DetectionEvent(
                    user_id=user_id,
                    action="block_sensitive_file",
                    severity="high",
                    detected_patterns={"sensitivity_label": [sensitivity_info]},
                    file_names=file_name
                )
                session.add(event)
                
            return True
        else:
            logger.error(f"Error reporting DLP violation: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error reporting DLP violation: {str(e)}")
        return False

def scan_file_for_sensitivity(user_id: int, file_path: str, file_name: str, file_mime: str) -> Tuple[bool, Optional[str]]:
    """
    Scan a file for Microsoft Sensitivity labels and block if needed
    
    Args:
        user_id: ID of the user who uploaded the file
        file_path: Path to the file to scan
        file_name: Original name of the file
        file_mime: MIME type of the file
        
    Returns:
        Tuple containing:
            - Boolean indicating if the file is allowed (True) or blocked (False)
            - Error message if blocked, None otherwise
    """
    # Check if DLP integration is enabled for this user
    if not is_dlp_integration_enabled(user_id):
        return True, None
    
    # Get user settings for the sensitivity threshold
    blocking_threshold = "confidential"  # Default threshold
    with session_scope() as session:
        user_settings = session.query(Settings).filter(
            Settings.user_id == user_id
        ).first()
        
        if user_settings and hasattr(user_settings, "ms_dlp_sensitivity_threshold"):
            blocking_threshold = user_settings.ms_dlp_sensitivity_threshold
    
    # Check for sensitivity labels
    exceeds_threshold, sensitivity_info = check_sensitivity_label(file_path, file_mime)
    
    # If sensitivity info was found, we need to manually determine if it exceeds the threshold
    # rather than using the value from check_sensitivity_label which uses a hardcoded threshold
    if sensitivity_info:
        # Extract sensitivity level
        sensitivity_level = sensitivity_info.get("sensitivity") or "general"
        
        # Convert to numerical values for comparison
        detected_level = SENSITIVITY_LEVELS.get(sensitivity_level.lower(), 0)
        threshold_level = SENSITIVITY_LEVELS.get(blocking_threshold.lower(), 2)  # Default is confidential (2)
        
        # Determine if file exceeds threshold based on user settings
        exceeds_threshold = detected_level >= threshold_level
    
    if exceeds_threshold and sensitivity_info:
        # File has sensitivity label above threshold, block it
        
        # Report the violation to Microsoft DLP
        report_success = report_dlp_violation(user_id, file_path, file_name, sensitivity_info)
        
        # Create error message
        sensitivity_name = sensitivity_info.get("name", "Unknown")
        error_message = (
            f"File blocked due to Microsoft sensitivity label: {sensitivity_name}. "
            f"This file has been flagged as sensitive content and cannot be uploaded."
        )
        
        return False, error_message
    
    # No sensitivity label or below threshold, allow the file
    return True, None

def setup_ms_dlp_integration():
    """
    Set up Microsoft DLP integration - run this to add columns to Settings model if needed
    (For future implementation)
    """
    # This function is a placeholder for future enhancements
    # such as adding DLP-specific columns to the Settings model
    # or creating new tables for DLP configurations
    pass

def is_dlp_integration_enabled(user_id: int) -> bool:
    """
    Check if Microsoft DLP integration is enabled for a user
    
    Args:
        user_id: ID of the user
        
    Returns:
        Boolean indicating if DLP integration is enabled
    """
    # Check if Microsoft settings are configured
    settings = get_ms_settings()
    if not settings["is_configured"]:
        return False
    
    # Check if the columns exist in the database
    with session_scope() as session:
        import sqlalchemy as sa
        from sqlalchemy import inspect
        
        # Get the table inspector
        inspector = inspect(session.bind)
        columns = [column['name'] for column in inspector.get_columns('settings')]
        
        # If the required columns don't exist, run the migration
        if 'enable_ms_dlp' not in columns or 'ms_dlp_sensitivity_threshold' not in columns:
            logger.warning("DLP columns don't exist in Settings table, running migration...")
            
            # Close the current session before modifying the schema
            session.close()
            
            # Run the migration to add the columns
            from migration_add_dlp_columns import run_migration
            run_migration()
            
            # Return default value since columns were just added
            return True
    
    # Check user-specific settings
    with session_scope() as session:
        user_settings = session.query(Settings).filter(
            Settings.user_id == user_id
        ).first()
        
        if user_settings and hasattr(user_settings, "enable_ms_dlp"):
            return user_settings.enable_ms_dlp
    
    # Default to enabled if no user-specific setting is found
    return True