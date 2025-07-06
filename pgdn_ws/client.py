from typing import Optional, Dict, Any, List
from .manager import notification_manager, NotificationManager
from .types import NotificationMessage

class NotificationClient:
    """Client for sending notifications from within your FastAPI app"""

    def __init__(self, manager: NotificationManager = None):
        self.manager = manager or notification_manager

    # Async methods (for use in FastAPI endpoints)
    async def notify_user(
        self,
        user_id: str,
        message_type: str,
        payload: Dict[str, Any]
    ):
        """Send notification to a specific user"""
        message = NotificationMessage(
            type=message_type,
            payload=payload,
            user_id=user_id
        )
        await self.manager.send_to_user(user_id, message)

    async def notify_users(
        self,
        user_ids: List[str],
        message_type: str,
        payload: Dict[str, Any]
    ):
        """Send notification to multiple users"""
        message = NotificationMessage(
            type=message_type,
            payload=payload
        )
        await self.manager.send_to_users(user_ids, message)

    async def notify_group(
        self,
        group_id: str,
        message_type: str,
        payload: Dict[str, Any]
    ):
        """Send notification to a group"""
        message = NotificationMessage(
            type=message_type,
            payload=payload,
            group_ids=[group_id]
        )
        await self.manager.send_to_group(group_id, message)

    async def broadcast(
        self,
        message_type: str,
        payload: Dict[str, Any],
        exclude_users: Optional[List[str]] = None
    ):
        """Broadcast to all users"""
        message = NotificationMessage(
            type=message_type,
            payload=payload
        )
        await self.manager.broadcast(message, exclude_users)

    # Sync methods for synchronous contexts
    def notify_user_sync(
        self,
        user_id: str,
        message_type: str,
        payload: Dict[str, Any]
    ):
        """Send notification to a specific user (sync version)"""
        message = NotificationMessage(
            type=message_type,
            payload=payload,
            user_id=user_id
        )
        self.manager.send_to_user_sync(user_id, message)

    def notify_users_sync(
        self,
        user_ids: List[str],
        message_type: str,
        payload: Dict[str, Any]
    ):
        """Send notification to multiple users (sync version)"""
        message = NotificationMessage(
            type=message_type,
            payload=payload
        )
        self.manager.send_to_users_sync(user_ids, message)

    def notify_group_sync(
        self,
        group_id: str,
        message_type: str,
        payload: Dict[str, Any]
    ):
        """Send notification to a group (sync version)"""
        message = NotificationMessage(
            type=message_type,
            payload=payload,
            group_ids=[group_id]
        )
        self.manager.send_to_group_sync(group_id, message)

    def broadcast_sync(
        self,
        message_type: str,
        payload: Dict[str, Any],
        exclude_users: Optional[List[str]] = None
    ):
        """Broadcast to all users (sync version)"""
        message = NotificationMessage(
            type=message_type,
            payload=payload
        )
        self.manager.broadcast_sync(message, exclude_users)

    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return self.manager.get_stats()

# Default client instance
notify = NotificationClient()
