#!/usr/bin/env python3
"""
Quick script to switch AI providers

Usage:
    python switch_provider.py cerebras
    python switch_provider.py openai
    python switch_provider.py baseten
    python switch_provider.py huggingface
    python switch_provider.py ollama
"""

import sys
from pathlib import Path


def update_env_file(provider: str):
    """Update AI_PROVIDER in .env file"""
    
    valid_providers = ["cerebras", "openai", "baseten", "huggingface", "ollama"]
    if provider.lower() not in valid_providers:
        print(f"[ERROR] Invalid provider: {provider}")
        print(f"   Valid options: {', '.join(valid_providers)}")
        return False
    
    env_file = Path(__file__).parent / ".env"
    
    # Read current .env
    if env_file.exists():
        with open(env_file, 'r') as f:
            lines = f.readlines()
    else:
        print("[WARN] .env file not found, creating new one...")
        lines = []
    
    # Update or add AI_PROVIDER
    updated = False
    for i, line in enumerate(lines):
        if line.startswith("AI_PROVIDER="):
            lines[i] = f"AI_PROVIDER={provider.lower()}\n"
            updated = True
            break
    
    if not updated:
        # Add to top of file
        lines.insert(0, f"AI_PROVIDER={provider.lower()}\n")
    
    # Write back
    with open(env_file, 'w') as f:
        f.writelines(lines)
    
    print(f"[OK] Switched to {provider.upper()}")
    print(f"   File: {env_file}")
    
    # Show requirements
    if provider.lower() == "cerebras":
        print("\n[INFO] Required settings:")
        print("   CEREBRAS_API_KEY=your-key-here")
    elif provider.lower() == "openai":
        print("\n[INFO] Required settings:")
        print("   OPENAI_API_KEY=your-key-here")
    elif provider.lower() == "baseten":
        print("\n[INFO] Required settings:")
        print("   BASETEN_API_KEY=your-key-here")
        print("   BASETEN_MODEL_ID=your-model-id")
    elif provider.lower() == "huggingface":
        print("\n[INFO] Required settings:")
        print("   HF_API_KEY=your-huggingface-token")
        print("   HF_MODEL=ehartford/dolphin-2.5-mixtral-8x7b (or your model)")
        print("\n[INFO] Optional for local inference:")
        print("   HF_LOCAL_MODEL_PATH=/path/to/local/model")
        print("   HF_BASE_URL=https://api-inference.huggingface.co/v1/ (default)")
    elif provider.lower() == "ollama":
        print("\n[INFO] Required settings:")
        print("   OLLAMA_BASE_URL=http://localhost:11434/v1 (or your Ollama server)")
        print("   OLLAMA_MODEL=hf.co/PsiPi/ehartford_dolphin-2.5-mixtral-8x7b-GGUF:Q3_K_L (or your model)")
        print("\n[INFO] Optional settings:")
        print("   OLLAMA_TLS_SKIP_VERIFY=1 (if using self-signed cert)")
        print("   OLLAMA_API_KEY=not required (Ollama doesn't require API key)")
    
    print("\n[INFO] Restart your FastAPI server for changes to take effect")
    return True


def show_current():
    """Show current provider"""
    env_file = Path(__file__).parent / ".env"
    
    if not env_file.exists():
        print("[WARN] No .env file found")
        return
    
    with open(env_file, 'r') as f:
        for line in f:
            if line.startswith("AI_PROVIDER="):
                provider = line.strip().split("=")[1]
                print(f"Current provider: {provider.upper()}")
                return
    
    print("[WARN] AI_PROVIDER not set in .env (defaulting to Cerebras)")


if __name__ == "__main__":
    print("=" * 60)
    print("AI Provider Switcher")
    print("=" * 60)
    print()
    
    if len(sys.argv) < 2:
        print("Usage: python switch_provider.py [cerebras|openai|baseten|huggingface|ollama]")
        print()
        show_current()
    else:
        provider = sys.argv[1]
        update_env_file(provider)