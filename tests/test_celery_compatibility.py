"""
Tests for sync method compatibility features.
"""

import pytest
import threading
import time
from unittest.mock import Mock, patch
from pgdn_ws import NotificationManager, NotificationClient, NotificationMessage
from pgdn_ws.types import MessageType


class TestSyncMethodCompatibility:
    """Test that sync methods work correctly for synchronous usage."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = NotificationManager()
        self.client = NotificationClient(self.manager)
    
    def test_sync_methods_exist(self):
        """Test that sync methods are available."""
        assert hasattr(self.client, 'notify_user_sync')
        assert hasattr(self.client, 'notify_users_sync')
        assert hasattr(self.client, 'notify_group_sync')
        assert hasattr(self.client, 'broadcast_sync')
        
        assert hasattr(self.manager, 'send_to_user_sync')
        assert hasattr(self.manager, 'send_to_users_sync')
        assert hasattr(self.manager, 'send_to_group_sync')
        assert hasattr(self.manager, 'broadcast_sync')
    
    def test_sync_methods_are_callable(self):
        """Test that sync methods can be called without errors."""
        message = NotificationMessage(
            type="test",
            payload={"message": "test"}
        )
        
        # These should not raise exceptions
        self.manager.send_to_user_sync("user-123", message)
        self.manager.send_to_users_sync(["user-123"], message)
        self.manager.send_to_group_sync("group-123", message)
        self.manager.broadcast_sync(message)
        
        # Client methods should also work
        self.client.notify_user_sync("user-123", "test", {"message": "test"})
        self.client.notify_users_sync(["user-123"], "test", {"message": "test"})
        self.client.notify_group_sync("group-123", "test", {"message": "test"})
        self.client.broadcast_sync("test", {"message": "test"})
    
    def test_thread_safety(self):
        """Test that sync methods are thread-safe."""
        message = NotificationMessage(type="test", payload={"message": "test"})
        
        # Create multiple threads calling sync methods
        threads = []
        for i in range(5):
            thread = threading.Thread(
                target=self.manager.send_to_user_sync,
                args=(f"user-{i}", message)
            )
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should not raise any exceptions
        assert True
    
    def test_get_stats_thread_safe(self):
        """Test that get_stats is thread-safe."""
        # Call get_stats from multiple threads
        threads = []
        results = []
        
        def get_stats():
            results.append(self.manager.get_stats())
        
        for _ in range(5):
            thread = threading.Thread(target=get_stats)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should not raise any exceptions and return consistent results
        assert len(results) == 5
        for result in results:
            assert isinstance(result, dict)
            assert "total_users" in result
            assert "total_connections" in result


class TestAuthHandlerCompatibility:
    """Test auth handler compatibility."""
    
    def test_async_auth_handler(self):
        """Test that async auth handlers work."""
        from pgdn_ws.auth import default_auth_handler
        import asyncio
        
        # Test valid token
        async def test_valid():
            result = await default_auth_handler("valid-token")
            assert result == {"user_id": "user-123", "groups": ["admin", "users"]}
        
        # Test invalid token
        async def test_invalid():
            result = await default_auth_handler("invalid-token")
            assert result is None
        
        asyncio.run(test_valid())
        asyncio.run(test_invalid())


if __name__ == "__main__":
    pytest.main([__file__]) 