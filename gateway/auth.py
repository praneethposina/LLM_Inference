"""
API key management and authentication.
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

# Simple file-based API key storage (for M1)
# In production, use a proper database
KEYS_FILE = Path(__file__).parent / "api_keys.json"


def _load_keys() -> Dict[str, Dict]:
    """Load API keys from file."""
    if not KEYS_FILE.exists():
        # Create default key for development
        default_keys = {
            "sk-dev-default-key-12345": {
                "key_id": "default",
                "created_at": datetime.now().isoformat(),
                "rate_limit": 30,  # requests per minute
                "active": True
            }
        }
        _save_keys(default_keys)
        return default_keys
    
    with open(KEYS_FILE, "r") as f:
        return json.load(f)


def _save_keys(keys: Dict[str, Dict]):
    """Save API keys to file."""
    with open(KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=2)


def verify_api_key(api_key: str) -> Optional[Dict]:
    """
    Verify an API key and return its metadata.
    
    Args:
        api_key: The API key to verify
        
    Returns:
        Key metadata if valid, None otherwise
    """
    keys = _load_keys()
    key_info = keys.get(api_key)
    
    if not key_info or not key_info.get("active", True):
        return None
    
    return {
        "key_id": key_info.get("key_id", "unknown"),
        "rate_limit": key_info.get("rate_limit", 30),
        "created_at": key_info.get("created_at")
    }


def create_api_key(key_id: str, rate_limit: int = 30) -> str:
    """
    Create a new API key.
    
    Args:
        key_id: Human-readable identifier
        rate_limit: Requests per minute
        
    Returns:
        The generated API key
    """
    import secrets
    
    keys = _load_keys()
    
    # Generate a secure key
    api_key = f"sk-{secrets.token_urlsafe(32)}"
    
    keys[api_key] = {
        "key_id": key_id,
        "created_at": datetime.now().isoformat(),
        "rate_limit": rate_limit,
        "active": True
    }
    
    _save_keys(keys)
    return api_key


def list_api_keys() -> list[Dict]:
    """List all API keys (without exposing full keys)."""
    keys = _load_keys()
    return [
        {
            "key_id": info.get("key_id"),
            "prefix": key[:20] + "...",
            "created_at": info.get("created_at"),
            "rate_limit": info.get("rate_limit"),
            "active": info.get("active", True)
        }
        for key, info in keys.items()
    ]


def revoke_api_key(api_key: str) -> bool:
    """Revoke an API key."""
    keys = _load_keys()
    if api_key in keys:
        keys[api_key]["active"] = False
        _save_keys(keys)
        return True
    return False


def revoke_api_key_by_id(key_id: str) -> bool:
    """Revoke an API key by key_id."""
    keys = _load_keys()
    for api_key, info in keys.items():
        if info.get("key_id") == key_id:
            keys[api_key]["active"] = False
            _save_keys(keys)
            return True
    return False

