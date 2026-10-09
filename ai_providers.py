import os
import json
import time
import copy
import threading
from types import SimpleNamespace
from typing import Dict, Any, Optional, List, Generator, Union
import streamlit as st
import requests
from database import get_session, session_scope
from models import Settings

# Import API clients
import openai
from anthropic import Anthropic
from google import genai
from google.genai import types as genai_types

from model_catalog import get_hosted_models, resolve_model

# Upper bound on generated tokens. Reasoning models (GPT-5+/6) spend part of this
# budget on hidden reasoning, so it must be generous enough to leave room for output.
MAX_OUTPUT_TOKENS = 4096


def get_gemini_api_key() -> str:
    """Gemini key: GOOGLE_API_KEY (documented) or GEMINI_API_KEY (google-genai default)."""
    return os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or ""

def get_user_settings(user_id: int) -> Optional[SimpleNamespace]:
    """Get user settings from the database"""
    try:
        with session_scope() as session:
            settings = session.query(Settings).filter(Settings.user_id == user_id).first()
            
            # If we found settings, create a copy of important attributes to avoid detached instance errors
            if settings:
                return SimpleNamespace(
                    id=settings.id,
                    user_id=settings.user_id,
                    llm_provider=settings.llm_provider,
                    ai_character=settings.ai_character,
                    openai_api_key=settings.openai_api_key,
                    # Retired model IDs saved by older versions resolve to a supported one.
                    openai_model=resolve_model("openai", settings.openai_model),
                    claude_api_key=settings.claude_api_key,
                    claude_model=resolve_model("claude", settings.claude_model),
                    gemini_api_key=settings.gemini_api_key,
                    gemini_model=resolve_model("gemini", settings.gemini_model),
                    serpapi_key=settings.serpapi_key,
                    local_model_path=settings.local_model_path,
                    local_model_context_size=settings.local_model_context_size,
                    local_model_gpu_layers=settings.local_model_gpu_layers,
                    local_model_temperature=settings.local_model_temperature,
                    scan_enabled=settings.scan_enabled,
                    scan_level=settings.scan_level,
                    auto_anonymize=settings.auto_anonymize,
                    disable_scan_for_local_model=settings.disable_scan_for_local_model,
                    custom_patterns=list(settings.get_custom_patterns()),
                    enable_ms_dlp=getattr(settings, 'enable_ms_dlp', True),
                    ms_dlp_sensitivity_threshold=getattr(settings, 'ms_dlp_sensitivity_threshold', 'confidential')
                )
            return None
    except Exception as e:
        print(f"Error getting user settings: {str(e)}")
        return None

def get_available_models() -> Dict[str, List[str]]:
    """Get list of available models for each provider"""
    # Get available local models
    local_models = []
    try:
        models_dir = os.path.join(os.getcwd(), "models")
        if os.path.exists(models_dir):
            for filename in os.listdir(models_dir):
                if filename.endswith(".gguf"):
                    local_models.append(filename)
    except Exception as e:
        print(f"Error listing local models: {str(e)}")
    
    # If no local models found, add a placeholder
    if not local_models:
        local_models = ["Please download a model first"]
    
    models = get_hosted_models()
    models["local"] = local_models
    return models

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
    override_provider: Optional[str] = None,
    bypass_privacy_scan: bool = False,
    input_already_processed: bool = False
) -> Union[str, Generator[str, None, None]]:
    """
    Get a response from the configured AI model
    
    Args:
        user_id: ID of the current user
        messages: List of messages in the conversation
        stream: Whether to stream the response
        override_model: Optional model name to override the one in settings
        override_provider: Optional provider name to override the one in settings
        bypass_privacy_scan: Whether to bypass privacy scanning for this request
        
    Returns:
        Either a string response or a generator that yields chunks of the response
    """
    # Get user settings
    settings = get_user_settings(user_id)
    
    if not settings:
        return "Error: User settings not found"
    
    # Create a copy of settings to avoid modifying the original.
    settings_copy = SimpleNamespace(**copy.deepcopy(vars(settings)))
    
    # Override provider if specified
    if override_provider and override_provider.strip():
        settings_copy.llm_provider = override_provider
    
    # Override model if specified
    if override_model and override_model.strip():
        # Check which provider we're using and update the appropriate model
        if settings_copy.llm_provider == "openai":
            settings_copy.openai_model = resolve_model("openai", override_model)
        elif settings_copy.llm_provider == "claude":
            settings_copy.claude_model = resolve_model("claude", override_model)
        elif settings_copy.llm_provider == "gemini":
            settings_copy.gemini_model = resolve_model("gemini", override_model)
    
    # Automatically bypass privacy scanning for local models if configured
    provider = settings_copy.llm_provider
    if provider == "local" and settings_copy.disable_scan_for_local_model:
        bypass_privacy_scan = True
    
    # Check if we need to apply privacy scanning to the messages
    if not input_already_processed and not bypass_privacy_scan and len(messages) > 0:
        from privacy_scanner import scan_text, anonymize_text
        
        # Only scan user messages
        for i, message in enumerate(messages):
            if message["role"] == "user":
                # Check if we should anonymize or just scan
                if settings_copy.auto_anonymize:
                    anonymized_text, detected_patterns = anonymize_text(user_id, message["content"])
                    if detected_patterns:
                        messages[i]["content"] = anonymized_text
                else:
                    # Just scan for logging purposes
                    scan_text(user_id, message["content"])
    
    # Route to appropriate provider
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
    # Get API key from environment variable first, then fallback to settings
    api_key = os.environ.get("OPENAI_API_KEY", "")
    model = settings.openai_model
    
    if not api_key:
        return "Error: OpenAI API key not found in environment variables. Please add it to your .env file or environment variables with the key OPENAI_API_KEY."
    
    # Initialize OpenAI client
    client = openai.OpenAI(api_key=api_key)
    
    try:
        # GPT-5 and later are reasoning models: they reject ``max_tokens`` (replaced by
        # ``max_completion_tokens``) and any non-default ``temperature``. Both settings
        # below are accepted by every current chat-completions model.
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=stream,
            max_completion_tokens=MAX_OUTPUT_TOKENS
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
    # Get API key from environment variable first, then fallback to settings
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    model = settings.claude_model
    
    if not api_key:
        return "Error: Claude API key not found in environment variables. Please add it to your .env file or environment variables with the key ANTHROPIC_API_KEY."
    
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
        # Only pass ``system`` when one exists: the SDK rejects an explicit ``None``.
        request_kwargs = {
            "model": model,
            "messages": claude_messages,
            "max_tokens": MAX_OUTPUT_TOKENS,
            "stream": stream,
        }
        if system_content:
            request_kwargs["system"] = system_content

        # Create completion request
        response = client.messages.create(**request_kwargs)
        
        if stream:
            # Return a generator that yields chunks of the response
            def response_generator():
                for chunk in response:
                    if getattr(chunk, "type", "") == "content_block_delta":
                        text_delta = getattr(getattr(chunk, "delta", None), "text", None)
                        if text_delta:
                            yield text_delta
            
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
    """Get response from Google Gemini via the ``google-genai`` SDK.

    The previous ``google-generativeai`` package is end-of-life. With ``google-genai``
    the system prompt is passed as a real ``system_instruction`` instead of being
    injected as a fake first user turn.
    """
    api_key = get_gemini_api_key()
    model = resolve_model("gemini", settings.gemini_model)
    
    if not api_key:
        return "Error: Gemini API key not found in environment variables. Please add it to your .env file or environment variables with the key GOOGLE_API_KEY."

    system_content = None
    contents = []
    for msg in messages:
        if msg["role"] == "system":
            system_content = msg["content"]
        elif msg["role"] in ("user", "assistant"):
            contents.append(genai_types.Content(
                role="user" if msg["role"] == "user" else "model",
                parts=[genai_types.Part.from_text(text=msg["content"])],
            ))

    if not contents or contents[-1].role != "user":
        return "Error: Gemini requests must end with a user message."

    history, last_message = contents[:-1], contents[-1].parts[0].text
    config = genai_types.GenerateContentConfig(
        system_instruction=system_content,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )

    try:
        client = genai.Client(api_key=api_key)
        chat = client.chats.create(model=model, config=config, history=history)

        if stream:
            response = chat.send_message_stream(last_message)

            def response_generator():
                for chunk in response:
                    if chunk.text:
                        yield chunk.text

            return response_generator()

        return chat.send_message(last_message).text or ""

    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower() and "model" in error_msg.lower():
            available_models_str = ", ".join(get_hosted_models()["gemini"])
            return f"Error: The selected Gemini model '{model}' is not available. Please update your settings to use one of the available models: {available_models_str}"
        return f"Error calling Gemini API: {error_msg}"

# Loaded llama.cpp models are expensive (seconds to minutes and gigabytes of RAM), so keep
# the most recently used one instead of re-reading the file for every chat turn.
_LOCAL_MODEL_CACHE: Dict[Any, Any] = {}
_LOCAL_MODEL_LOCK = threading.Lock()


def _coalesce(value: Any, default: Any) -> Any:
    """Return ``default`` only for ``None``; ``0`` and ``0.0`` are legitimate settings."""
    return default if value is None else value


def _load_local_model(model_path: str, n_ctx: int, n_gpu_layers: int):
    from llama_cpp import Llama

    cache_key = (os.path.abspath(model_path), os.path.getmtime(model_path), n_ctx, n_gpu_layers)
    with _LOCAL_MODEL_LOCK:
        cached = _LOCAL_MODEL_CACHE.get(cache_key)
        if cached is not None:
            return cached

        model = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            verbose=False
        )
        # Keep a single model resident to bound memory usage.
        _LOCAL_MODEL_CACHE.clear()
        _LOCAL_MODEL_CACHE[cache_key] = model
        return model


def get_local_response(
    settings: Settings, 
    messages: List[Dict[str, str]], 
    stream: bool = True
) -> Union[str, Generator[str, None, None]]:
    """Get response from local LLM using llama-cpp-python"""
    # Get model path from settings
    model_path = settings.local_model_path
    
    if not model_path:
        return "Error: Local model path not configured in settings"
    
    if not os.path.exists(model_path):
        return f"Error: Local model file not found at {model_path}"

    temperature = _coalesce(getattr(settings, "local_model_temperature", None), 0.7)
    
    try:
        # Initialize local model with settings from the user's configuration
        model = _load_local_model(
            model_path=model_path,
            n_ctx=_coalesce(getattr(settings, "local_model_context_size", None), 2048),
            n_gpu_layers=_coalesce(getattr(settings, "local_model_gpu_layers", None), -1),
        )
        
        # Format messages into a prompt for the local model
        prompt = ""
        system_message = None
        
        # Extract system message if present
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
                break
        
        # Add system message at the beginning if present
        if system_message:
            prompt += f"SYSTEM: {system_message}\n\n"
        
        # Add conversation history
        for msg in messages:
            if msg["role"] != "system":  # Skip system message as we've already added it
                role = "USER" if msg["role"] == "user" else "ASSISTANT"
                prompt += f"{role}: {msg['content']}\n"
        
        # Add final prompt for response
        prompt += "ASSISTANT: "
        
        if stream:
            def response_generator():
                # Generate tokens in streaming mode
                response = ""
                for output in model.create_completion(
                    prompt=prompt,
                    max_tokens=1024,
                    stop=["USER:", "\nUSER", "SYSTEM:"],
                    temperature=temperature,
                    stream=True
                ):
                    chunk = output["choices"][0]["text"]
                    response += chunk
                    yield chunk
            
            return response_generator()
        else:
            # Generate complete response at once
            response = model.create_completion(
                prompt=prompt,
                max_tokens=1024,
                stop=["USER:", "\nUSER", "SYSTEM:"],
                temperature=temperature
            )
            
            result = response["choices"][0]["text"]
            return result
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error using local LLM: {error_details}")
        return f"Error using local LLM: {str(e)}"
