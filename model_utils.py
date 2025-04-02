"""
Utility functions for managing local LLM models
Used for downloading, verifying, and testing local models
"""

import os
import json
import shutil
import hashlib
from typing import Dict, Any, Optional, List
import requests
from tqdm import tqdm
import streamlit as st

# Default models available for download
DEFAULT_MODELS = {
    "phi-2.Q4_K_M.gguf": {
        "name": "Phi-2 (Microsoft)",
        "size": "2.9GB",
        "description": "Compact but powerful model from Microsoft",
        "url": "https://huggingface.co/TheBloke/phi-2-GGUF/resolve/main/phi-2.Q4_K_M.gguf",
        "md5": "bc33a1791219b5abb9432f3f581a55f3",
        "recommended_ctx": 4096,
        "category": "Small",
        "quantization": "Q4_K_M",
        "family": "phi"
    },
    "mistral-7b-instruct-v0.2.Q4_K_M.gguf": {
        "name": "Mistral 7B Instruct",
        "size": "4.37GB",
        "description": "Efficient model with strong instruction following",
        "url": "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
        "md5": "71512e9f27482fa9a00039c9b452b94e",
        "recommended_ctx": 8192,
        "category": "Medium",
        "quantization": "Q4_K_M",
        "family": "mistral"
    },
    "llama-2-7b-chat.Q4_K_M.gguf": {
        "name": "Llama 2 7B Chat",
        "size": "4.78GB",
        "description": "Meta's Llama 2 optimized for chat",
        "url": "https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf",
        "md5": "84a0925f5f6073238f64684327587e9d",
        "recommended_ctx": 4096,
        "category": "Medium",
        "quantization": "Q4_K_M",
        "family": "llama"
    },
    "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf": {
        "name": "TinyLlama 1.1B Chat",
        "size": "610MB",
        "description": "Ultra-compact model, great for testing",
        "url": "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
        "md5": "3951db6b4de4d4af8833f50231d8a8aa",
        "recommended_ctx": 2048,
        "category": "Tiny",
        "quantization": "Q4_K_M",
        "family": "llama"
    }
}

def ensure_models_directory() -> str:
    """
    Ensure the models directory exists and return its path
    
    Returns:
        Path to models directory
    """
    models_dir = os.path.join(os.getcwd(), "models")
    os.makedirs(models_dir, exist_ok=True)
    return models_dir

def get_model_info(model_filename: str) -> Optional[Dict[str, Any]]:
    """
    Get information about a model from the DEFAULT_MODELS dictionary
    
    Args:
        model_filename: Filename of the model
        
    Returns:
        Model information dictionary or None if not found
    """
    return DEFAULT_MODELS.get(model_filename)

def download_model(model_filename: str, force: bool = False) -> Optional[str]:
    """
    Download a model from the default models list
    
    Args:
        model_filename: Filename of the model to download
        force: Whether to force download even if the file exists
        
    Returns:
        Path to the downloaded model file, or None if download failed
    """
    # Get model info
    model_info = get_model_info(model_filename)
    if not model_info:
        st.error(f"Model {model_filename} not found in available models")
        return None
    
    # Prepare path
    models_dir = ensure_models_directory()
    model_path = os.path.join(models_dir, model_filename)
    
    # Check if already exists and not forcing redownload
    if os.path.exists(model_path) and not force:
        # Verify integrity
        st.info(f"Model already exists at {model_path}. Verifying integrity...")
        with open(model_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        
        if file_hash == model_info.get('md5'):
            st.success(f"Model integrity verified. Ready to use.")
            return model_path
        else:
            st.warning(f"Model integrity check failed. Will redownload.")
    
    # Download model
    url = model_info.get('url')
    if not url:
        st.error("Model URL not found")
        return None
    
    st.info(f"Downloading {model_info.get('name')} ({model_info.get('size')})...")
    st.info(f"This may take some time depending on your internet connection.")
    
    try:
        # Stream download with progress bar
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        # Create a temporary file for downloading
        temp_path = model_path + ".download"
        
        with open(temp_path, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=model_filename) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
        
        # Verify download
        with open(temp_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        
        if file_hash == model_info.get('md5'):
            # Move to final location
            shutil.move(temp_path, model_path)
            st.success(f"Download complete and verified. Model saved to {model_path}")
            return model_path
        else:
            os.remove(temp_path)
            st.error("Downloaded file integrity check failed. Please try again.")
            return None
            
    except Exception as e:
        st.error(f"Error downloading model: {str(e)}")
        # Clean up partial download
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return None

def list_available_models() -> Dict[str, Dict[str, Any]]:
    """
    List available models and their download status
    
    Returns:
        Dictionary with model information and download status
    """
    models_dir = ensure_models_directory()
    result = {}
    
    # Check default models
    for filename, info in DEFAULT_MODELS.items():
        model_path = os.path.join(models_dir, filename)
        is_downloaded = os.path.exists(model_path)
        
        # Verify hash if downloaded
        verified = False
        if is_downloaded:
            try:
                with open(model_path, 'rb') as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                verified = file_hash == info.get('md5')
            except:
                verified = False
        
        result[filename] = {
            **info,
            "downloaded": is_downloaded,
            "verified": verified,
            "path": model_path if is_downloaded else None
        }
    
    # Add custom models (those in models directory not in DEFAULT_MODELS)
    for filename in os.listdir(models_dir):
        if filename.endswith('.gguf') and filename not in DEFAULT_MODELS:
            model_path = os.path.join(models_dir, filename)
            file_size = os.path.getsize(model_path)
            size_mb = file_size / (1024 * 1024)
            size_str = f"{size_mb:.2f}MB" if size_mb < 1024 else f"{size_mb/1024:.2f}GB"
            
            result[filename] = {
                "name": filename,
                "size": size_str,
                "description": "Custom model",
                "downloaded": True,
                "verified": True,  # We trust user's custom models
                "path": model_path,
                "category": "Custom",
                "recommended_ctx": 4096  # Default value
            }
    
    return result

def show_model_download_ui() -> Optional[str]:
    """
    Display a Streamlit UI for downloading and managing models
    
    Returns:
        Path to the selected model or None if no model selected
    """
    st.header("Local LLM Model Manager")
    
    # Get available models
    models = list_available_models()
    
    # Tab UI for model operations
    tab1, tab2 = st.tabs(["Download Models", "Manage Models"])
    
    selected_model_path = None
    
    with tab1:
        st.subheader("Download Pre-configured Models")
        
        # Group models by category
        models_by_category = {}
        for filename, info in models.items():
            category = info.get('category', 'Other')
            if category not in models_by_category:
                models_by_category[category] = []
            models_by_category[category].append((filename, info))
        
        # Display models by category
        for category in sorted(models_by_category.keys()):
            with st.expander(f"{category} Models", expanded=True):
                for filename, info in sorted(models_by_category[category]):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.write(f"**{info['name']}** ({info['size']})")
                        st.write(info['description'])
                        
                    with col2:
                        status = "✅" if info['downloaded'] and info['verified'] else \
                                 "⚠️" if info['downloaded'] and not info['verified'] else "❌"
                        st.write(f"Status: {status}")
                        
                    with col3:
                        if not info['downloaded'] or not info['verified']:
                            if st.button("Download", key=f"download_{filename}"):
                                path = download_model(filename)
                                # Force refresh of the page
                                st.rerun()
                        else:
                            if st.button("Redownload", key=f"redownload_{filename}"):
                                path = download_model(filename, force=True)
                                # Force refresh of the page
                                st.rerun()
        
        # Upload custom model
        st.subheader("Upload Custom Model")
        uploaded_file = st.file_uploader("Upload a GGUF model", type=['gguf'])
        
        if uploaded_file is not None:
            # Save the uploaded file
            models_dir = ensure_models_directory()
            model_path = os.path.join(models_dir, uploaded_file.name)
            
            with open(model_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.success(f"Model uploaded successfully to {model_path}")
            
            # Force refresh of the page
            st.experimental_rerun()
    
    with tab2:
        st.subheader("Manage Downloaded Models")
        
        downloaded_models = {k: v for k, v in models.items() if v['downloaded']}
        
        if not downloaded_models:
            st.info("No models downloaded yet. Use the Download Models tab to get started.")
        else:
            # Display downloaded models with management options
            for filename, info in downloaded_models.items():
                with st.expander(info['name'], expanded=False):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Path:** {info['path']}")
                        st.write(f"**Size:** {info['size']}")
                        st.write(f"**Category:** {info.get('category', 'Custom')}")
                        if 'family' in info:
                            st.write(f"**Family:** {info['family']}")
                        if 'quantization' in info:
                            st.write(f"**Quantization:** {info['quantization']}")
                        st.write(f"**Recommended Context Size:** {info.get('recommended_ctx', 'Unknown')}")
                        
                    with col2:
                        if st.button("Delete", key=f"delete_{filename}"):
                            try:
                                os.remove(info['path'])
                                st.success(f"Deleted model: {filename}")
                                # Force refresh of the page
                                st.experimental_rerun()
                            except Exception as e:
                                st.error(f"Error deleting model: {str(e)}")
                        
                        if st.button("Select", key=f"select_{filename}"):
                            selected_model_path = info['path']
                            # Highlight selection
                            st.success(f"Selected model: {filename}")
    
    return selected_model_path