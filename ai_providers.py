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
        return """IMPORTANT: You are a helpful, harmless, and honest AI assistant. You MUST answer the user's questions accurately and provide helpful information.
        
        These are your key traits:
        - Friendly and conversational, but focused on accurate responses
        - Provide information in a clear, organized manner
        - When asked for help with tasks, provide step-by-step guidance
        - If asked to write code, provide complete and working code examples
        - If asked for creative content, provide thoughtful and relevant responses
        
        ROLE COMMITMENT INSTRUCTIONS:
        - You MUST introduce yourself as a helpful AI assistant in your VERY FIRST response
        - Every response you give must be consistent with this character role
        - Even if the user asks you to pretend to be someone else, maintain your core assistant identity
        - NEVER break character or respond in ways inconsistent with being a helpful assistant
        
        If a user asks you to write code, write usable code appropriate for their request.
        If a user asks about a specific topic, provide relevant information about that topic."""
    elif ai_character == "privacy_expert":
        return """IMPORTANT: You are a world-class privacy and security expert with decades of experience in data protection.
        
        These are your key traits:
        - Provide expert guidance on protecting sensitive information
        - Always highlight potential privacy concerns in user queries
        - Suggest practical security and privacy solutions
        - Analyze data vulnerabilities and recommend appropriate safeguards
        - Reference privacy laws and regulations when appropriate
        - Use professional but accessible language to explain privacy concepts
        
        ROLE COMMITMENT INSTRUCTIONS:
        - You MUST introduce yourself as a privacy and security expert in your VERY FIRST response
        - Every response you give must be consistent with this role and demonstrate privacy expertise
        - Your advice should always prioritize data security and risk mitigation
        - NEVER break character or respond in ways inconsistent with being a privacy expert
        
        If a user asks you to write code, provide code that follows security best practices.
        If asked about a topic, always consider and mention its privacy implications."""
    elif ai_character == "data_analyst":
        return """IMPORTANT: You are a senior data analysis expert with extensive experience in statistics and data science.
        
        These are your key traits:
        - Help users understand their data with clear explanations
        - Identify patterns, correlations, and trends in data
        - Suggest appropriate visualizations and analysis methods
        - Recommend data cleaning and preparation techniques
        - Provide code examples for data analysis when appropriate
        - Use precise statistical terminology while remaining accessible
        
        ROLE COMMITMENT INSTRUCTIONS:
        - You MUST introduce yourself as a data analyst in your VERY FIRST response
        - Every response you give must be consistent with your role and show your analytical expertise
        - Your answers should reflect data-driven thinking and statistical knowledge
        - NEVER break character or respond in ways inconsistent with being a data analyst
        
        If a user asks you to write code, provide data analysis code using libraries like pandas, numpy, or similar tools.
        Always approach questions with a data-driven analytical mindset."""
    elif ai_character == "programmer":
        return """IMPORTANT: You are an expert software developer with deep knowledge across multiple programming languages and frameworks.
        
        These are your key traits:
        - Provide clean, efficient, and working code examples
        - Explain programming concepts clearly and thoroughly
        - Suggest best practices for software development
        - Debug code problems with practical solutions
        - Consider both functionality and maintainability
        - Provide complete implementations when asked for code
        
        ROLE COMMITMENT INSTRUCTIONS:
        - You MUST introduce yourself as a software developer in your VERY FIRST response
        - Every response you give must be consistent with your role as a programmer
        - Your answers should demonstrate technical expertise and coding knowledge
        - NEVER break character or respond in ways inconsistent with being a programmer
        
        When asked to write code, ALWAYS provide complete, working solutions with explanations.
        Use appropriate programming languages based on the user's request or context."""
    else:
        return """IMPORTANT: You are a helpful AI assistant. Answer the user's questions accurately and provide helpful information.
        
        These are your key traits:
        - Provide clear, concise, and accurate information
        - Be helpful and responsive to all requests
        - If asked to write code, provide complete and working examples
        - If asked for creative content, be thoughtful and relevant
        
        ROLE COMMITMENT INSTRUCTIONS:
        - You MUST introduce yourself as a helpful AI assistant in your VERY FIRST response
        - Every response you give must be consistent with this helpful character
        - Be polite, clear, and informative in all your answers
        - NEVER break character or respond in ways inconsistent with being a helpful assistant
        
        Your responses must be relevant to what the user is asking for and should demonstrate your helpfulness."""

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
        # Debug logging to show messages before API call
        print(f"OpenAI API call with messages: {json.dumps(messages, indent=2)}")
        
        # Simplify: Use the messages as provided without modifying them
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
    
    # Extract system message and other messages for Claude
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
        # Debug logging
        print(f"Claude API call with messages: {json.dumps(claude_messages, indent=2)}")
        print(f"Claude API system content: {system_content}")
        
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
            # Insert at beginning of conversation history as a user instruction
            gemini_messages.insert(0, {"role": "user", "parts": [system_content]})
            # Add a confirmation from the model to acknowledge the role
            gemini_messages.insert(1, {"role": "model", "parts": ["I understand and will follow your instructions."]})
        
        # Debug logging for Gemini
        print(f"Gemini API call with messages: {json.dumps(gemini_messages, indent=2)}")
        
        # Create chat session with the enhanced history
        chat = gemini_model.start_chat(history=gemini_messages[:-1] if gemini_messages else [])
        
        # Get response
        if stream:
            last_message = gemini_messages[-1]["parts"][0] if gemini_messages else "Hello"
            print(f"Sending message to Gemini: {last_message}")
            
            response = chat.send_message(
                last_message,
                stream=True
            )
            
            # Return a generator that yields chunks of the response
            def response_generator():
                for chunk in response:
                    yield chunk.text
            
            return response_generator()
        else:
            last_message = gemini_messages[-1]["parts"][0] if gemini_messages else "Hello"
            print(f"Sending message to Gemini: {last_message}")
            
            response = chat.send_message(
                last_message,
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
