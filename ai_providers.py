import os
import json
import time
from typing import Dict, Any, Optional, List, Generator, Union
import streamlit as st
import requests
from database import get_session
from models import Settings

# Import API clients
import openai
from anthropic import Anthropic
from google.generativeai import GenerativeModel
import google.generativeai as genai

def get_user_settings(user_id: int) -> Optional[Settings]:
    """Get user settings from the database"""
    session = get_session()
    settings = session.query(Settings).filter(Settings.user_id == user_id).first()
    session.close()
    return settings

def get_available_models() -> Dict[str, List[str]]:
    """Get list of available models for each provider"""
    return {
        "openai": [
            "gpt-4o", 
            "gpt-4-turbo", 
            "gpt-4", 
            "gpt-3.5-turbo"
        ],
        "claude": [
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229", 
            "claude-3-haiku-20240307"
        ],
        "gemini": [
            "gemini-1.5-pro",
            "gemini-1.5-flash"
        ],
        "local": [
            "Please specify path in settings"
        ]
    }

def create_system_prompt(ai_character: str) -> str:
    """Create a system prompt based on the AI character setting"""
    if ai_character == "assistant":
        return """You are a helpful, harmless, and honest AI assistant. Answer the user's questions accurately and provide helpful information. 
        You should be friendly and conversational but focused on providing accurate and useful responses.
        Always maintain this role throughout the conversation."""
    elif ai_character == "privacy_expert":
        return """You are a world-class privacy and security expert with decades of experience in data protection.
        Your role is to provide guidance on protecting sensitive information and maintaining privacy.
        Highlight potential privacy concerns in the user's queries and suggest practical solutions.
        You should analyze potential data vulnerabilities and recommend appropriate safeguards.
        Always maintain this expert role throughout the conversation."""
    elif ai_character == "data_analyst":
        return """You are a senior data analysis expert with extensive experience in statistics and data science.
        Your role is to help the user analyze and understand their data, providing insights and recommendations.
        You should look for patterns, suggest visualizations, and help interpret results.
        When reviewing data, consider potential correlations, outliers, and meaningful trends.
        Always maintain this expert analyst role throughout the conversation."""
    elif ai_character == "programmer":
        return """You are an expert software developer with deep knowledge across multiple programming languages and frameworks.
        Your role is to help with coding questions, debugging, and providing clean, efficient code examples.
        Explain technical concepts clearly and suggest best practices for software development.
        Consider both functionality and maintainability in your solutions.
        Always maintain this expert developer role throughout the conversation."""
    else:
        return """You are a helpful AI assistant. Answer the user's questions accurately and provide helpful information.
        Always maintain a helpful and informative demeanor throughout the conversation."""

def get_ai_response(
    user_id: int, 
    messages: List[Dict[str, str]], 
    stream: bool = True,
    override_model: Optional[str] = None,
    override_provider: Optional[str] = None
) -> Union[str, Generator[str, None, None]]:
    """
    Get a response from the configured AI model
    
    Args:
        user_id: ID of the current user
        messages: List of messages in the conversation
        stream: Whether to stream the response
        override_model: Optional model name to override the one in settings
        override_provider: Optional provider name to override the one in settings
        
    Returns:
        Either a string response or a generator that yields chunks of the response
    """
    # Get user settings
    settings = get_user_settings(user_id)
    
    if not settings:
        return "Error: User settings not found"
    
    # Create a copy of settings to avoid modifying the original
    import copy
    settings_copy = copy.copy(settings)
    
    # Override provider if specified
    if override_provider and override_provider.strip():
        settings_copy.llm_provider = override_provider
    
    # Override model if specified
    if override_model and override_model.strip():
        # Check which provider we're using and update the appropriate model
        if settings_copy.llm_provider == "openai":
            settings_copy.openai_model = override_model
        elif settings_copy.llm_provider == "claude":
            settings_copy.claude_model = override_model
        elif settings_copy.llm_provider == "gemini":
            settings_copy.gemini_model = override_model
    
    # Route to appropriate provider
    provider = settings_copy.llm_provider
    
    if provider == "openai":
        return get_openai_response(settings_copy, messages, stream)
    elif provider == "claude":
        return get_claude_response(settings_copy, messages, stream)
    elif provider == "gemini":
        return get_gemini_response(settings_copy, messages, stream)
    elif provider == "local":
        return get_local_response(settings_copy, messages, stream)
    else:
        return "Error: Invalid AI provider selected"

def get_openai_response(
    settings: Settings, 
    messages: List[Dict[str, str]], 
    stream: bool = True
) -> Union[str, Generator[str, None, None]]:
    """Get response from OpenAI API"""
    # Get API key from settings
    api_key = settings.openai_api_key
    model = settings.openai_model
    
    if not api_key:
        return "Error: OpenAI API key not configured in settings"
    
    # Initialize OpenAI client
    client = openai.OpenAI(api_key=api_key)
    
    try:
        # Create completion request
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=stream,
            temperature=0.7,
            max_tokens=1500
        )
        
        if stream:
            # Return a generator that yields chunks of the response
            def response_generator():
                for chunk in response:
                    if chunk.choices and hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content is not None:
                        content = chunk.choices[0].delta.content
                        yield content
            
            return response_generator()
        else:
            # Return the full response
            return response.choices[0].message.content
    
    except Exception as e:
        return f"Error calling OpenAI API: {str(e)}"

def get_claude_response(
    settings: Settings, 
    messages: List[Dict[str, str]], 
    stream: bool = True
) -> Union[str, Generator[str, None, None]]:
    """Get response from Anthropic Claude API"""
    # Get API key from settings
    api_key = settings.claude_api_key
    model = settings.claude_model
    
    if not api_key:
        return "Error: Claude API key not configured in settings"
    
    # Initialize Anthropic client
    client = Anthropic(api_key=api_key)
    
    # Convert messages to Claude format
    claude_messages = []
    system_content = None
    
    for msg in messages:
        if msg["role"] == "system":
            system_content = msg["content"]
        else:
            claude_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
    
    try:
        # Create completion request
        response = client.messages.create(
            model=model,
            messages=claude_messages,
            system=system_content,
            stream=stream
        )
        
        if stream:
            # Return a generator that yields chunks of the response
            def response_generator():
                for chunk in response:
                    if chunk.delta.text:
                        yield chunk.delta.text
            
            return response_generator()
        else:
            # Return the full response
            return response.content[0].text
    
    except Exception as e:
        return f"Error calling Claude API: {str(e)}"

def get_gemini_response(
    settings: Settings, 
    messages: List[Dict[str, str]], 
    stream: bool = True
) -> Union[str, Generator[str, None, None]]:
    """Get response from Google Gemini API"""
    # Get API key from settings
    api_key = settings.gemini_api_key
    model = settings.gemini_model
    
    if not api_key:
        return "Error: Gemini API key not configured in settings"
    
    # Configure API
    genai.configure(api_key=api_key)
    
    # Check and correct model name if needed
    available_models = get_available_models()["gemini"]
    if model not in available_models:
        # Default to first available model if specified model not found
        model = available_models[0]
        # Update user's settings in the database
        try:
            session = get_session()
            user_settings = session.query(Settings).filter(Settings.gemini_api_key == api_key).first()
            if user_settings:
                user_settings.gemini_model = model
                session.commit()
            session.close()
        except Exception:
            # Continue even if we can't update the settings
            pass
    
    try:
        # Initialize model
        gemini_model = GenerativeModel(model)
        
        # Convert messages to Gemini format
        gemini_messages = []
        system_content = None
        
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            elif msg["role"] == "user":
                gemini_messages.append({"role": "user", "parts": [msg["content"]]})
            elif msg["role"] == "assistant":
                gemini_messages.append({"role": "model", "parts": [msg["content"]]})
        
        # Add system message at the beginning as a clear instruction from user
        # This approach makes Gemini treat the system prompt as instructions it should follow
        if system_content:
            # Create a strong system instruction that Gemini will follow
            formatted_system = f"""IMPORTANT INSTRUCTIONS: 
You MUST act according to the following role throughout our ENTIRE conversation. 
Do not break character under any circumstances:

{system_content}

Remember these instructions and embody this role consistently in all your responses."""
            
            # Insert at beginning of conversation history as a user instruction
            gemini_messages.insert(0, {"role": "user", "parts": [formatted_system]})
            # Add a confirmation from the model to acknowledge the role
            gemini_messages.insert(1, {"role": "model", "parts": ["I understand my role and will act accordingly throughout our conversation."]})
        
        # Create chat session with the enhanced history
        chat = gemini_model.start_chat(history=gemini_messages[:-1] if gemini_messages else [])
        
        # Get response
        if stream:
            response = chat.send_message(
                gemini_messages[-1]["parts"][0] if gemini_messages else "Hello",
                stream=True
            )
            
            # Return a generator that yields chunks of the response
            def response_generator():
                for chunk in response:
                    yield chunk.text
            
            return response_generator()
        else:
            response = chat.send_message(
                gemini_messages[-1]["parts"][0] if gemini_messages else "Hello",
                stream=False
            )
            return response.text
    
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg and "models/" in error_msg:
            # If it's a model not found error, provide a more helpful message
            available_models_str = ", ".join(available_models)
            return f"Error: The selected Gemini model '{model}' is not available. Please update your settings to use one of the available models: {available_models_str}"
        return f"Error calling Gemini API: {error_msg}"

def get_local_response(
    settings: Settings, 
    messages: List[Dict[str, str]], 
    stream: bool = True
) -> str:
    """Get response from local LLM"""
    # This function would connect to a locally hosted model
    # Since we don't have direct access to a local LLM in this environment,
    # we'll return a message indicating this functionality needs to be configured
    model_path = settings.local_model_path
    
    if not model_path:
        return "Error: Local model path not configured in settings"
    
    return "Local model support requires additional configuration. Please check the documentation for setting up local LLM integration."
