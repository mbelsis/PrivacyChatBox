# Local LLM Integration Documentation

This document provides detailed information about the local Language Model (LLM) integration in PrivacyChatBoX, allowing users to run AI models directly on their own hardware without requiring external API access.

## Overview

PrivacyChatBoX supports running local language models through the llama-cpp-python library, which provides high-performance inference for GGUF format models. This integration allows users to:

1. Process all data locally without sending information to external APIs
2. Operate without an internet connection or API keys
3. Customize model parameters for their specific needs
4. Manage their own model files through a user-friendly interface

## Supported Models

The application supports any model in the GGUF format, including:

- **Llama 2/3**: Meta's open-source LLMs in various sizes
- **Mistral**: Efficient models with strong instruction following
- **Phi-2**: Microsoft's compact but powerful models
- **TinyLlama**: Ultra-lightweight models for testing and resource-constrained environments
- **Custom models**: Any GGUF model can be uploaded and used

By default, the application provides easy access to download several pre-configured models directly within the UI.

## Model Manager Interface

The Model Manager page is accessible from the sidebar and provides three main sections:

### 1. Download & Manage Models

This tab allows users to:
- Browse pre-configured models organized by size category (Tiny, Small, Medium)
- View model details including size, quantization, and description
- Download models directly from Hugging Face with progress tracking
- Upload custom GGUF models from their local system
- Select which model to use for chat

### 2. Model Testing

This tab allows users to:
- Test the currently selected model with custom prompts
- Configure context size and GPU layers for testing
- View generated outputs to verify model performance

### 3. Configuration

This tab allows users to:
- Set the default context window size (token limit)
- Configure GPU acceleration settings
- Adjust the temperature parameter for generation
- Toggle privacy scanning for local models

## Technical Implementation

### Model Storage

Models are stored in the `models/` directory at the root of the application. This directory is created automatically if it doesn't exist.

### File Structure

```
models/
├── phi-2.Q4_K_M.gguf              # Example small model from Microsoft
├── mistral-7b-instruct-v0.2.Q4_K_M.gguf  # Example medium model
├── llama-2-7b-chat.Q4_K_M.gguf    # Example medium model from Meta
└── tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf  # Example tiny model
```

### Database Schema

Local LLM settings are stored in the `settings` table with the following columns:

```sql
local_model_path VARCHAR DEFAULT '',
local_model_context_size INTEGER DEFAULT 2048,
local_model_gpu_layers INTEGER DEFAULT -1,
local_model_temperature FLOAT DEFAULT 0.7,
disable_scan_for_local_model BOOLEAN DEFAULT TRUE,
```

### Key Files and Modules

- **model_utils.py**: Core utilities for managing model files
- **test_local_llm.py**: Standalone testing script for local models 
- **ai_providers.py**: Integration with the main chat interface
- **pages/model_manager.py**: UI for model management
- **migration_add_local_llm_columns.py**: Database migration for local LLM support

## Using Local Models in Chat

To use local models in the chat interface:

1. Navigate to the Model Manager page
2. Download or upload a GGUF model
3. Select the model by clicking "Select" next to the desired model
4. Go to the Settings page and change the LLM Provider to "Local LLM"
5. Return to the Chat page to start using the local model

## Hardware Requirements

Local LLM inference requires sufficient RAM to load the model. Recommended system requirements:

- **Small models (< 3GB)**: At least 8GB of RAM
- **Medium models (3-5GB)**: At least 16GB of RAM
- **Large models (> 5GB)**: 32GB+ of RAM recommended

GPU acceleration is optional but highly recommended for faster inference. The application will automatically use CPU if no GPU is available.

## Privacy Considerations

Local LLM processing provides enhanced privacy as all data remains on your device. The application offers an option to bypass privacy scanning when using local models since data never leaves your system.

## Troubleshooting

If you encounter issues with local models:

1. **Model fails to load**: Ensure you have sufficient RAM available
2. **Slow inference**: Consider enabling GPU acceleration or using a smaller model
3. **Out of memory errors**: Reduce the context size or use a more efficient quantized model
4. **Model not found**: Verify the path in settings matches an existing model file

## Additional Resources

- [llama-cpp-python GitHub](https://github.com/abetlen/llama-cpp-python)
- [Hugging Face GGUF Models](https://huggingface.co/models?sort=trending&search=gguf)
- [GGUF Format Documentation](https://github.com/ggerganov/ggml/blob/master/docs/gguf.md)