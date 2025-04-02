"""
Test script for local LLM integration
This script allows testing the local LLM integration without running the full application
"""

import os
import sys
import argparse
from llama_cpp import Llama
from typing import Optional

def test_local_model(model_path: str, prompt: str, n_ctx: int = 2048, n_gpu_layers: int = -1) -> Optional[str]:
    """
    Test a local LLM model with a given prompt
    
    Args:
        model_path: Path to the model file
        prompt: Input prompt to generate from
        n_ctx: Context window size
        n_gpu_layers: Number of GPU layers to use (-1 for all)
        
    Returns:
        Generated response or None if failed
    """
    # Check if model exists
    if not os.path.exists(model_path):
        print(f"Error: Model file not found at '{model_path}'")
        return None
    
    print(f"Loading model from '{model_path}'...")
    print(f"Context size: {n_ctx}, GPU layers: {n_gpu_layers}")
    
    try:
        # Initialize model
        model = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            verbose=True
        )
        
        print(f"Model loaded successfully. Generating response to prompt: '{prompt}'")
        
        # Generate response
        response = model.generate(
            prompt,
            max_tokens=512,
            temperature=0.7,
            stop=["USER:", "\nUSER", "SYSTEM:"],
        )
        
        result = response["choices"][0]["text"]
        print(f"Generated response: '{result}'")
        return result
    
    except Exception as e:
        print(f"Error loading or running model: {str(e)}")
        return None

def main():
    """Main function for CLI usage"""
    parser = argparse.ArgumentParser(description="Test local LLM integration")
    parser.add_argument("--model", "-m", type=str, required=True, help="Path to model file")
    parser.add_argument("--prompt", "-p", type=str, default="Tell me about privacy in AI systems", help="Input prompt")
    parser.add_argument("--context", "-c", type=int, default=2048, help="Context window size")
    parser.add_argument("--gpu", "-g", type=int, default=-1, help="Number of GPU layers (-1 for all)")
    
    args = parser.parse_args()
    
    # Run test with provided arguments
    test_local_model(args.model, args.prompt, args.context, args.gpu)

if __name__ == "__main__":
    main()