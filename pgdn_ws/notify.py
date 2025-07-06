"""
Core notification system that routes notifications to appropriate handlers.
"""

import datetime
from typing import Dict, Any, Callable, Optional

from .types.slack import notify_slack
from .types.email import notify_email
from .types.webhook import notify_webhook
from .types.websocket import notify_websocket
from .config import load_config
from .rate_limit import RateLimitManager, RateLimitConfig


# Registry of notification handlers
NOTIFIERS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "slack": notify_slack,
    "email": notify_email,
    "webhook": notify_webhook,
    "websocket": notify_websocket,
}

# Global rate limit manager
_rate_limit_manager: Optional[RateLimitManager] = None


def get_rate_limit_manager() -> RateLimitManager:
    """Get or create the global rate limit manager."""
    global _rate_limit_manager
    
    if _rate_limit_manager is None:
        config_data = load_config()
        use_redis = config_data.get("use_redis_rate_limit", False)
        rate_limit_config = RateLimitConfig(config_data)
        _rate_limit_manager = RateLimitManager(rate_limit_config, use_redis)
    
    return _rate_limit_manager


def notify(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main notification function that routes to appropriate handler.
    
    Args:
        data: Notification data containing type, body, and meta fields
        
    Returns:
        Standardized response with success, type, timestamp, and details
    """
    if not isinstance(data, dict):
        return {
            "success": False,
            "type": "unknown",
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "error": "Invalid input: data must be a dictionary"
        }
    
    notification_type = data.get("type")
    if not notification_type:
        return {
            "success": False,
            "type": "unknown",
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "error": "Missing required field: type"
        }
    
    if notification_type not in NOTIFIERS:
        return {
            "success": False,
            "type": notification_type,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "error": f"Unsupported notification type: {notification_type}"
        }
    
    if "body" not in data:
        return {
            "success": False,
            "type": notification_type,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "error": "Missing required field: body"
        }
    
    # Check rate limits
    rate_limiter = get_rate_limit_manager()
    if not rate_limiter.check_rate_limit(notification_type):
        return rate_limiter.get_rate_limit_error(notification_type)
    
    try:
        notifier = NOTIFIERS[notification_type]
        result = notifier(data)
        
        # Ensure result has required fields
        if not isinstance(result, dict):
            raise ValueError("Notifier must return a dictionary")
        
        # Add timestamp if not present
        if "timestamp" not in result:
            result["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
        
        # Ensure type is set
        if "type" not in result:
            result["type"] = notification_type
            
        return result
        
    except Exception as e:
        return {
            "success": False,
            "type": notification_type,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "error": f"Notification failed: {str(e)}"
        } 