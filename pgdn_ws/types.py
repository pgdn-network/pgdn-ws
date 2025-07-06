# pgdn_ws/types.py
from typing import Dict, Any, Optional, List, Callable, Awaitable
from pydantic import BaseModel, Field
from datetime import datetime, UTC
from enum import Enum

class MessageType(str, Enum):
    # System messages
    CONNECTION = "connection"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"
    
    # Notification types
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    DANGER = "danger"
    
    # Custom types (extendable)
    CUSTOM = "custom"

class NotificationMessage(BaseModel):
    type: str
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    user_id: Optional[str] = None
    group_ids: Optional[List[str]] = None
    
    def dict(self, **kwargs):
        """Override dict to handle datetime serialization"""
        data = self.model_dump(**kwargs)
        # Convert datetime to ISO format string
        if isinstance(data.get('timestamp'), datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        return data
    
    def model_dump(self, **kwargs):
        """Pydantic v2 method"""
        data = super().model_dump(**kwargs)
        # Convert datetime to ISO format string
        if isinstance(data.get('timestamp'), datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        return data

# Type aliases
AuthHandler = Callable[[str], Awaitable[Optional[Dict[str, Any]]]]
MessageHandler = Callable[[Dict[str, Any], str], Awaitable[None]]
