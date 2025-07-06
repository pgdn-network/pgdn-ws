"""
Tests for the core notify functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
from pgdn_ws import notify


class TestNotifyCore:
    """Test core notification functionality."""
    
    def test_invalid_input_not_dict(self):
        """Test handling of invalid input that's not a dictionary."""
        result = notify("not a dict")
        
        assert result["success"] is False
        assert result["type"] == "unknown"
        assert "Invalid input" in result["error"]
        assert "timestamp" in result
    
    def test_missing_type_field(self):
        """Test handling of missing type field."""
        data = {"body": "test message"}
        result = notify(data)
        
        assert result["success"] is False
        assert result["type"] == "unknown"
        assert "Missing required field: type" in result["error"]
    
    def test_unsupported_notification_type(self):
        """Test handling of unsupported notification type."""
        data = {
            "type": "unsupported",
            "body": "test message"
        }
        result = notify(data)
        
        assert result["success"] is False
        assert result["type"] == "unsupported"
        assert "Unsupported notification type" in result["error"]
    
    def test_missing_body_field(self):
        """Test handling of missing body field."""
        data = {"type": "slack"}
        result = notify(data)
        
        assert result["success"] is False
        assert result["type"] == "slack"
        assert "Missing required field: body" in result["error"]


class TestSlackNotification:
    """Test Slack notification functionality."""
    
    @patch('pgdn_ws.types.slack.requests.post')
    @patch('pgdn_ws.types.slack.os.getenv')
    def test_slack_success(self, mock_getenv, mock_post):
        """Test successful Slack notification."""
        # Setup mocks
        mock_getenv.return_value = "https://hooks.slack.com/test"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        data = {
            "type": "slack",
            "body": "Hello",
            "meta": {"channel": "#general"}
        }
        
        result = notify(data)
        
        assert result["success"] is True
        assert result["type"] == "slack"
        assert result["details"]["channel"] == "#general"
        assert result["details"]["status_code"] == 200
        assert "timestamp" in result
    
    def test_slack_missing_channel(self):
        """Test Slack notification with missing channel."""
        data = {
            "type": "slack",
            "body": "Hello",
            "meta": {}
        }
        
        result = notify(data)
        
        assert result["success"] is False
        assert result["type"] == "slack"
        assert "Missing required meta field: channel" in result["error"]
    
    def test_slack_missing_webhook_url(self):
        """Test Slack notification with missing webhook URL."""
        data = {
            "type": "slack",
            "body": "Hello",
            "meta": {"channel": "#general"}
        }
        
        result = notify(data)
        
        assert result["success"] is False
        assert result["type"] == "slack"
        assert "Missing Slack webhook URL" in result["error"]


class TestEmailNotification:
    """Test email notification functionality."""
    
    @patch('pgdn_ws.types.email.smtplib.SMTP')
    @patch('pgdn_ws.types.email.os.getenv')
    def test_email_success(self, mock_getenv, mock_smtp_class):
        """Test successful email notification."""
        # Setup mocks
        mock_getenv.side_effect = lambda key, default=None: {
            'EMAIL_FROM': 'test@example.com',
            'SMTP_SERVER': 'localhost',
            'SMTP_PORT': '587'
        }.get(key, default)
        
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server
        
        data = {
            "type": "email",
            "body": "Urgent Alert",
            "meta": {
                "to": "admin@example.com",
                "subject": "Alert"
            }
        }
        
        result = notify(data)
        
        assert result["success"] is True
        assert result["type"] == "email"
        assert result["details"]["to"] == "admin@example.com"
        assert result["details"]["subject"] == "Alert"
        assert "timestamp" in result
    
    def test_email_missing_to(self):
        """Test email notification with missing 'to' field."""
        data = {
            "type": "email",
            "body": "Urgent Alert",
            "meta": {}
        }
        
        result = notify(data)
        
        assert result["success"] is False
        assert result["type"] == "email"
        assert "Missing required meta field: to" in result["error"]


class TestWebhookNotification:
    """Test webhook notification functionality."""
    
    @patch('pgdn_ws.types.webhook.requests.post')
    def test_webhook_post(self, mock_post):
        """Test successful webhook notification."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        data = {
            "type": "webhook",
            "body": {"event": "scan_complete"},
            "meta": {"url": "http://localhost:8000/hook"}
        }
        
        result = notify(data)
        
        assert result["success"] is True
        assert result["type"] == "webhook"
        assert result["details"]["url"] == "http://localhost:8000/hook"
        assert result["details"]["status_code"] == 200
        assert "timestamp" in result
    
    def test_webhook_missing_url(self):
        """Test webhook notification with missing URL."""
        data = {
            "type": "webhook",
            "body": {"event": "scan_complete"},
            "meta": {}
        }
        
        result = notify(data)
        
        assert result["success"] is False
        assert result["type"] == "webhook"
        assert "Missing required meta field: url" in result["error"]


class TestWebsocketNotification:
    """Test websocket notification functionality."""
    
    @patch('pgdn_ws.types.websocket.redis.Redis')
    def test_websocket_publish(self, mock_redis_class):
        """Test successful websocket notification via Redis pub/sub."""
        # Setup mock
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.publish.return_value = 2  # 2 subscribers reached
        mock_redis_class.return_value = mock_redis
        
        data = {
            "type": "websocket",
            "body": {"message": "event X"},
            "meta": {"channel": "pgdn-alerts"}
        }
        
        result = notify(data)
        
        assert result["success"] is True
        assert result["type"] == "websocket"
        assert result["details"]["channel"] == "pgdn-alerts"
        assert result["details"]["subscribers_reached"] == 2
        assert "timestamp" in result
    
    def test_websocket_missing_channel(self):
        """Test websocket notification with missing channel."""
        data = {
            "type": "websocket",
            "body": {"message": "event X"},
            "meta": {}
        }
        
        result = notify(data)
        
        assert result["success"] is False
        assert result["type"] == "websocket"
        assert "Missing required meta field: channel" in result["error"]


class TestTimestampHandling:
    """Test timestamp handling in responses."""
    
    @patch('pgdn_ws.types.slack.requests.post')
    @patch('pgdn_ws.types.slack.os.getenv')
    def test_timestamp_added_if_missing(self, mock_getenv, mock_post):
        """Test that timestamp is added if notifier doesn't provide it."""
        mock_getenv.return_value = "https://hooks.slack.com/test"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        data = {
            "type": "slack",
            "body": "Test",
            "meta": {"channel": "#test"}
        }
        
        result = notify(data)
        
        assert "timestamp" in result
        assert result["timestamp"].endswith("Z")


class TestExtensibility:
    """Test the extensibility of the notification system."""
    
    def test_can_add_new_notifier(self):
        """Test that new notifiers can be registered."""
        from pgdn_ws.notify import NOTIFIERS
        
        def custom_notifier(data):
            return {
                "success": True,
                "type": "custom",
                "details": {"custom": True}
            }
        
        # Save original state
        original_notifiers = NOTIFIERS.copy()
        
        try:
            # Add custom notifier
            NOTIFIERS["custom"] = custom_notifier
            
            data = {
                "type": "custom",
                "body": "test"
            }
            
            result = notify(data)
            
            assert result["success"] is True
            assert result["type"] == "custom"
            assert result["details"]["custom"] is True
            
        finally:
            # Restore original state
            NOTIFIERS.clear()
            NOTIFIERS.update(original_notifiers) 