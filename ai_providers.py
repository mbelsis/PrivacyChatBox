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
        return "You are a helpful, harmless, and honest AI assistant. Answer the user's questions accurately and provide helpful information."
    elif ai_character == "privacy_expert":
        return "You are a privacy and security expert. Provide guidance on protecting sensitive information and maintaining privacy. Highlight potential privacy concerns in user's queries."
    elif ai_character == "data_analyst":
        return "You are a data analysis expert. Help the user analyze and understand their data, providing insights and recommendations for better data management and visualization."
    elif ai_character == "programmer":
        return "You are a programming assistant. Help the user with coding questions, debugging, and providing code examples. Explain technical concepts clearly."
    else:
        return "You are a helpful AI assistant. Answer the user's questions accurately and provide helpful information."

def get_ai_response(
    user_id: int, 
    messages: List[Dict[str, str]], 
    stream: bool = True
) -> Union[str, Generator[str, None, None]]:
    """
    Get a response from the configured AI model
    
    Args:
        user_id: ID of the current user
        messages: List of messages in the conversation
        stream: Whether to stream the response
        
    Returns:
        Either a string response or a generator that yields chunks of the response
    """
    settings = get_user_settings(user_id)
    
    if not settings:
        return "Error: User settings not found"
    
    provider = settings.llm_provider
    
    if provider == "openai":
        return get_openai_response(settings, messages, stream)
    elif provider == "claude":
        return get_claude_response(settings, messages, stream)
    elif provider == "gemini":
        return get_gemini_response(settings, messages, stream)
    elif provider == "local":
        return get_local_response(settings, messages, stream)
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
            stream=stream
        )
        
        if stream:
            # Return a generator that yields chunks of the response
            def response_generator():
                collected_messages = []
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        collected_messages.append(content)
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
    
    # Add system message as user message if present
    if system_content:
        gemini_messages.insert(0, {"role": "user", "parts": [f"System instruction: {system_content}"]})
    
    try:
        # Create chat session
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
        return f"Error calling Gemini API: {str(e)}"

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
