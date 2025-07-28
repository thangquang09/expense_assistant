#!/usr/bin/env python3
"""
Configuration Management for Expense Tracker
Handles LLM model configuration persistence
"""

import os
import json
from typing import Dict, Any, Optional

CONFIG_FILE = "app_config.json"

DEFAULT_CONFIG = {
    "llm_model": "gemini",  # Default model
    "model_settings": {
        "gemini": {
            "provider": "google",
            "model_name": "gemini-1.5-flash",
            "api_key_env": "GEMINI_API_KEY"
        },
        "llama3": {
            "provider": "ollama", 
            "model_name": "llama3:8b",
            "base_url": "http://localhost:11434"
        }
    }
}

def load_config() -> Dict[str, Any]:
    """Load configuration from file or create default if not exists"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Merge with default to ensure all keys exist
                merged_config = DEFAULT_CONFIG.copy()
                merged_config.update(config)
                return merged_config
        except Exception as e:
            print(f"⚠️ Error loading config: {e}, using default")
            return DEFAULT_CONFIG.copy()
    else:
        # Create default config file
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

def save_config(config: Dict[str, Any]) -> bool:
    """Save configuration to file"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Error saving config: {e}")
        return False

def get_current_model() -> str:
    """Get currently configured LLM model"""
    config = load_config()
    return config.get("llm_model", "gemini")

def set_current_model(model_name: str) -> bool:
    """Set current LLM model and save config"""
    config = load_config()
    
    # Validate model name
    valid_models = list(config["model_settings"].keys())
    if model_name not in valid_models:
        print(f"❌ Invalid model: {model_name}")
        print(f"💡 Available models: {', '.join(valid_models)}")
        return False
    
    config["llm_model"] = model_name
    success = save_config(config)
    
    if success:
        model_info = config["model_settings"][model_name]
        provider = model_info["provider"]
        print(f"✅ Đã cấu hình mô hình: {model_name} ({provider})")
        
        if provider == "ollama":
            print(f"🔧 Model: {model_info['model_name']}")
            print(f"🌐 URL: {model_info['base_url']}")
            print("💡 Đảm bảo Ollama đang chạy: ollama serve")
        else:
            print(f"🔧 Model: {model_info['model_name']}")
            print(f"🔑 API Key: {model_info['api_key_env']}")
    
    return success

def get_model_settings(model_name: Optional[str] = None) -> Dict[str, Any]:
    """Get settings for specified model or current model"""
    config = load_config()
    
    if model_name is None:
        model_name = config.get("llm_model", "gemini")
    
    return config["model_settings"].get(model_name, config["model_settings"]["gemini"])

def list_available_models() -> Dict[str, Dict[str, Any]]:
    """List all available models with their settings"""
    config = load_config()
    return config["model_settings"] 