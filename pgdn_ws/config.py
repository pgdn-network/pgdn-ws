"""
Configuration loading for pgdn-notify.
"""

import os
import json
from typing import Dict, Any, Optional

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


def load_config_from_file(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from file (JSON or YAML).
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration dictionary
    """
    if not os.path.exists(config_path):
        return {}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            if config_path.endswith(('.yml', '.yaml')):
                if not YAML_AVAILABLE:
                    raise ImportError("PyYAML not available. Install with: pip install PyYAML")
                return yaml.safe_load(f) or {}
            else:
                return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load config file {config_path}: {e}")
        return {}


def load_config_from_env() -> Dict[str, Any]:
    """
    Load configuration from environment variables.
    
    Environment variables:
    - PGDN_NOTIFY_RATE_LIMIT_ENABLED: Enable rate limiting (true/false)
    - PGDN_NOTIFY_RATE_LIMIT_SLACK_CALLS: Slack rate limit calls
    - PGDN_NOTIFY_RATE_LIMIT_SLACK_PERIOD: Slack rate limit period
    - PGDN_NOTIFY_RATE_LIMIT_EMAIL_CALLS: Email rate limit calls
    - PGDN_NOTIFY_RATE_LIMIT_EMAIL_PERIOD: Email rate limit period
    - PGDN_NOTIFY_RATE_LIMIT_WEBHOOK_CALLS: Webhook rate limit calls
    - PGDN_NOTIFY_RATE_LIMIT_WEBHOOK_PERIOD: Webhook rate limit period
    - PGDN_NOTIFY_RATE_LIMIT_WEBSOCKET_CALLS: Websocket rate limit calls
    - PGDN_NOTIFY_RATE_LIMIT_WEBSOCKET_PERIOD: Websocket rate limit period
    - PGDN_NOTIFY_USE_REDIS_RATE_LIMIT: Use Redis for rate limiting (true/false)
    
    Returns:
        Configuration dictionary
    """
    config = {}
    
    # Check if rate limiting is enabled
    if os.getenv("PGDN_NOTIFY_RATE_LIMIT_ENABLED", "").lower() == "true":
        config["rate_limits"] = {}
        
        # Load rate limits for each notification type
        notification_types = ["slack", "email", "webhook", "websocket"]
        
        for notification_type in notification_types:
            calls_key = f"PGDN_NOTIFY_RATE_LIMIT_{notification_type.upper()}_CALLS"
            period_key = f"PGDN_NOTIFY_RATE_LIMIT_{notification_type.upper()}_PERIOD"
            
            calls = os.getenv(calls_key)
            period = os.getenv(period_key)
            
            if calls and period:
                try:
                    config["rate_limits"][notification_type] = {
                        "calls": int(calls),
                        "period": int(period)
                    }
                except ValueError:
                    print(f"Warning: Invalid rate limit values for {notification_type}")
    
    # Redis configuration
    if os.getenv("PGDN_NOTIFY_USE_REDIS_RATE_LIMIT", "").lower() == "true":
        config["use_redis_rate_limit"] = True
    
    return config


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from multiple sources.
    
    Priority order:
    1. Provided config file
    2. ./pgdn_ws_config.yml
    3. ./pgdn_ws_config.yaml
    4. ./pgdn_ws_config.json
    5. Environment variables
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        Merged configuration dictionary
    """
    config = {}
    
    # Load from environment variables first (lowest priority)
    env_config = load_config_from_env()
    if env_config:
        config.update(env_config)
    
    # Load from default config files
    default_paths = [
        "pgdn_ws_config.yml",
        "pgdn_ws_config.yaml", 
        "pgdn_ws_config.json"
    ]
    
    for path in default_paths:
        if os.path.exists(path):
            file_config = load_config_from_file(path)
            if file_config:
                config.update(file_config)
            break
    
    # Load from provided config file (highest priority)
    if config_path:
        file_config = load_config_from_file(config_path)
        if file_config:
            config.update(file_config)
    
    return config 