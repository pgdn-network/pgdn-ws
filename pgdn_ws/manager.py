# pgdn_ws/manager.py
from typing import Dict, Set, List, Optional, Any
from fastapi import WebSocket
import json
import asyncio
import logging
from datetime import datetime, UTC
from .types import NotificationMessage, MessageHandler

logger = logging.getLogger("pgdn-notify")

class NotificationManager:
    def __init__(self):
        # Store connections by user_id
        self._user_connections: Dict[str, Set[WebSocket]] = {}
        # Store connections by group_id
        self._group_connections: Dict[str, Set[WebSocket]] = {}
        # Map websocket to user info
        self._connection_info: Dict[WebSocket, Dict[str, Any]] = {}
        # Message handlers
        self._message_handlers: Dict[str, MessageHandler] = {}
        
    async def connect(self, websocket: WebSocket, user_info: Dict[str, Any]):
        """Connect a user websocket"""
        await websocket.accept()
        
        user_id = user_info.get("user_id")
        groups = user_info.get("groups", [])
        
        # Store connection info
        self._connection_info[websocket] = user_info
        
        # Add to user connections
        if user_id:
            if user_id not in self._user_connections:
                self._user_connections[user_id] = set()
            self._user_connections[user_id].add(websocket)
        
        # Add to group connections
        for group_id in groups:
            if group_id not in self._group_connections:
                self._group_connections[group_id] = set()
            self._group_connections[group_id].add(websocket)
        
        logger.info(f"User {user_id} connected with groups {groups}")
        
        # Send connection confirmation
        await self._send_to_websocket(websocket, {
            "type": "connection",
            "status": "connected",
            "user_id": user_id,
            "timestamp": datetime.now(UTC).isoformat()
        })
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a websocket"""
        info = self._connection_info.get(websocket)
        if not info:
            return
            
        user_id = info.get("user_id")
        groups = info.get("groups", [])
        
        # Remove from user connections
        if user_id and user_id in self._user_connections:
            self._user_connections[user_id].discard(websocket)
            if not self._user_connections[user_id]:
                del self._user_connections[user_id]
        
        # Remove from group connections
        for group_id in groups:
            if group_id in self._group_connections:
                self._group_connections[group_id].discard(websocket)
                if not self._group_connections[group_id]:
                    del self._group_connections[group_id]
        
        # Clean up connection info
        del self._connection_info[websocket]
        
        logger.info(f"User {user_id} disconnected")
    
    async def _send_to_websocket(self, websocket: WebSocket, data: dict):
        """Send data to a specific websocket"""
        try:
            await websocket.send_json(data)
        except Exception as e:
            logger.error(f"Error sending to websocket: {e}")
            self.disconnect(websocket)
    
    async def send_to_user(self, user_id: str, message: NotificationMessage):
        """Send notification to specific user"""
        logger.info(f"send_to_user called for {user_id}")
        
        if user_id not in self._user_connections:
            logger.warning(f"User {user_id} not connected")
            return
            
        # Get the message data with proper serialization
        if hasattr(message, 'model_dump'):
            data = message.model_dump()  # Pydantic v2
        else:
            data = message.dict()  # Pydantic v1
            
        # Ensure timestamp is serialized
        if isinstance(data.get('timestamp'), datetime):
            data['timestamp'] = data['timestamp'].isoformat()
            
        logger.info(f"Sending message to {user_id}: {data}")
        
        dead_connections = []
        
        for websocket in self._user_connections[user_id]:
            try:
                await websocket.send_json(data)
                logger.info(f"Message sent successfully to {user_id}")
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
                dead_connections.append(websocket)
        
        # Clean up dead connections
        for conn in dead_connections:
            self.disconnect(conn)
    
    async def send_to_users(self, user_ids: List[str], message: NotificationMessage):
        """Send notification to multiple users"""
        tasks = []
        for user_id in user_ids:
            tasks.append(self.send_to_user(user_id, message))
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def send_to_group(self, group_id: str, message: NotificationMessage):
        """Send notification to all users in a group"""
        if group_id not in self._group_connections:
            return
            
        if hasattr(message, 'model_dump'):
            data = message.model_dump()
        else:
            data = message.dict()
            
        if isinstance(data.get('timestamp'), datetime):
            data['timestamp'] = data['timestamp'].isoformat()
            
        dead_connections = []
        
        for websocket in self._group_connections[group_id]:
            try:
                await websocket.send_json(data)
            except Exception:
                dead_connections.append(websocket)
        
        # Clean up dead connections
        for conn in dead_connections:
            self.disconnect(conn)
    
    async def broadcast(self, message: NotificationMessage, exclude_users: Optional[List[str]] = None):
        """Broadcast to all connected users"""
        exclude_users = exclude_users or []
        
        if hasattr(message, 'model_dump'):
            data = message.model_dump()
        else:
            data = message.dict()
            
        if isinstance(data.get('timestamp'), datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        
        tasks = []
        for user_id, connections in self._user_connections.items():
            if user_id not in exclude_users:
                for websocket in connections:
                    tasks.append(self._send_to_websocket(websocket, data))
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    # Sync methods for synchronous contexts
    def send_to_user_sync(self, user_id: str, message: NotificationMessage):
        """Send notification to specific user (sync version)"""
        try:
            asyncio.run(self.send_to_user(user_id, message))
        except RuntimeError:
            # If we're already in an event loop, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.send_to_user(user_id, message))
            finally:
                loop.close()
    
    def send_to_users_sync(self, user_ids: List[str], message: NotificationMessage):
        """Send notification to multiple users (sync version)"""
        try:
            asyncio.run(self.send_to_users(user_ids, message))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.send_to_users(user_ids, message))
            finally:
                loop.close()
    
    def send_to_group_sync(self, group_id: str, message: NotificationMessage):
        """Send notification to all users in a group (sync version)"""
        try:
            asyncio.run(self.send_to_group(group_id, message))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.send_to_group(group_id, message))
            finally:
                loop.close()
    
    def broadcast_sync(self, message: NotificationMessage, exclude_users: Optional[List[str]] = None):
        """Broadcast to all connected users (sync version)"""
        try:
            asyncio.run(self.broadcast(message, exclude_users))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.broadcast(message, exclude_users))
            finally:
                loop.close()
    
    def register_handler(self, message_type: str, handler: MessageHandler):
        """Register a custom message handler"""
        self._message_handlers[message_type] = handler
    
    async def handle_message(self, websocket: WebSocket, message: dict):
        """Handle incoming websocket message"""
        message_type = message.get("type")
        user_info = self._connection_info.get(websocket, {})
        
        # Built-in handlers
        if message_type == "ping":
            await self._send_to_websocket(websocket, {
                "type": "pong",
                "timestamp": message.get("timestamp")
            })
            return
        
        # Custom handlers
        handler = self._message_handlers.get(message_type)
        if handler:
            await handler(message, user_info.get("user_id"))
    
    def get_stats(self) -> dict:
        """Get connection statistics"""
        return {
            "total_users": len(self._user_connections),
            "total_connections": sum(len(conns) for conns in self._user_connections.values()),
            "groups": list(self._group_connections.keys()),
            "users": list(self._user_connections.keys())
        }

# Global manager instance
notification_manager = NotificationManager()
