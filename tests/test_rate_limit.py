"""
Tests for rate limiting functionality.
"""

import time
import pytest
from unittest.mock import patch, MagicMock
from pgdn_ws.rate_limit import (
    InMemoryRateLimiter, 
    RedisRateLimiter, 
    RateLimitConfig, 
    RateLimitManager
)
from pgdn_ws import notify


class TestInMemoryRateLimiter:
    """Test in-memory rate limiter."""
    
    def test_allows_initial_requests(self):
        """Test that initial requests are allowed."""
        limiter = InMemoryRateLimiter()
        
        # Should allow first request
        assert limiter.is_allowed("test", 5, 60) is True
        
        # Should allow up to limit
        for _ in range(4):
            assert limiter.is_allowed("test", 5, 60) is True
    
    def test_blocks_after_limit(self):
        """Test that requests are blocked after limit is reached."""
        limiter = InMemoryRateLimiter()
        
        # Use up all tokens
        for _ in range(5):
            assert limiter.is_allowed("test", 5, 60) is True
        
        # Next request should be blocked
        assert limiter.is_allowed("test", 5, 60) is False
    
    def test_tokens_refill_over_time(self):
        """Test that tokens are refilled over time."""
        limiter = InMemoryRateLimiter()
        
        # Use up all tokens
        for _ in range(5):
            limiter.is_allowed("test", 5, 60)
        
        # Should be blocked initially
        assert limiter.is_allowed("test", 5, 60) is False
        
        # Mock time to simulate passage of time
        with patch('time.time') as mock_time:
            # Simulate 30 seconds passing (should refill ~2.5 tokens)
            mock_time.return_value = time.time() + 30
            
            # Should now allow some requests
            assert limiter.is_allowed("test", 5, 60) is True
            assert limiter.is_allowed("test", 5, 60) is True
            # Third request should be blocked
            assert limiter.is_allowed("test", 5, 60) is False
    
    def test_different_keys_independent(self):
        """Test that different keys have independent rate limits."""
        limiter = InMemoryRateLimiter()
        
        # Use up limit for key1
        for _ in range(5):
            limiter.is_allowed("key1", 5, 60)
        
        # key1 should be blocked
        assert limiter.is_allowed("key1", 5, 60) is False
        
        # key2 should still be allowed
        assert limiter.is_allowed("key2", 5, 60) is True


class TestRedisRateLimiter:
    """Test Redis-backed rate limiter."""
    
    @patch('pgdn_ws.rate_limit.redis')
    def test_allows_initial_requests(self, mock_redis_module):
        """Test that initial requests are allowed."""
        mock_redis_client = MagicMock()
        mock_pipeline = MagicMock()
        mock_redis_client.pipeline.return_value = mock_pipeline
        mock_pipeline.execute.return_value = [None, 0, None, None]  # 0 current requests
        
        limiter = RedisRateLimiter(mock_redis_client)
        
        assert limiter.is_allowed("test", 5, 60) is True
    
    @patch('pgdn_ws.rate_limit.redis')
    def test_blocks_after_limit(self, mock_redis_module):
        """Test that requests are blocked after limit is reached."""
        mock_redis_client = MagicMock()
        mock_pipeline = MagicMock()
        mock_redis_client.pipeline.return_value = mock_pipeline
        mock_pipeline.execute.return_value = [None, 5, None, None]  # 5 current requests
        
        limiter = RedisRateLimiter(mock_redis_client)
        
        assert limiter.is_allowed("test", 5, 60) is False
    
    @patch('pgdn_ws.rate_limit.redis')
    def test_fails_open_on_redis_error(self, mock_redis_module):
        """Test that limiter fails open when Redis is unavailable."""
        mock_redis_client = MagicMock()
        mock_redis_client.pipeline.side_effect = Exception("Redis connection failed")
        
        limiter = RedisRateLimiter(mock_redis_client)
        
        # Should allow request when Redis fails
        assert limiter.is_allowed("test", 5, 60) is True


class TestRateLimitConfig:
    """Test rate limit configuration."""
    
    def test_empty_config(self):
        """Test empty configuration."""
        config = RateLimitConfig({})
        
        assert config.enabled is False
        assert config.get_limit("slack") is None
        assert config.has_limit("slack") is False
    
    def test_valid_config(self):
        """Test valid configuration."""
        config_data = {
            "rate_limits": {
                "slack": {"calls": 10, "period": 60},
                "email": {"calls": 50, "period": 3600}
            }
        }
        
        config = RateLimitConfig(config_data)
        
        assert config.enabled is True
        assert config.has_limit("slack") is True
        assert config.has_limit("email") is True
        assert config.has_limit("webhook") is False
        
        slack_limit = config.get_limit("slack")
        assert slack_limit == {"calls": 10, "period": 60}
        
        email_limit = config.get_limit("email")
        assert email_limit == {"calls": 50, "period": 3600}
    
    def test_invalid_config_ignored(self):
        """Test that invalid config entries are ignored."""
        config_data = {
            "rate_limits": {
                "slack": {"calls": 10, "period": 60},
                "invalid": {"calls": "not_a_number"},
                "missing_period": {"calls": 10}
            }
        }
        
        config = RateLimitConfig(config_data)
        
        assert config.enabled is True
        assert config.has_limit("slack") is True
        assert config.has_limit("invalid") is False
        assert config.has_limit("missing_period") is False


class TestRateLimitManager:
    """Test rate limit manager."""
    
    def test_no_limits_configured(self):
        """Test behavior when no limits are configured."""
        config = RateLimitConfig({})
        manager = RateLimitManager(config)
        
        # Should allow all requests
        assert manager.check_rate_limit("slack") is True
        assert manager.check_rate_limit("email") is True
    
    def test_with_limits_configured(self):
        """Test behavior with limits configured."""
        config_data = {
            "rate_limits": {
                "slack": {"calls": 2, "period": 60}
            }
        }
        config = RateLimitConfig(config_data)
        manager = RateLimitManager(config)
        
        # Should allow up to limit
        assert manager.check_rate_limit("slack") is True
        assert manager.check_rate_limit("slack") is True
        
        # Should block after limit
        assert manager.check_rate_limit("slack") is False
        
        # Should still allow other types
        assert manager.check_rate_limit("email") is True
    
    def test_rate_limit_error_response(self):
        """Test rate limit error response format."""
        manager = RateLimitManager()
        error = manager.get_rate_limit_error("slack")
        
        assert error["success"] is False
        assert error["type"] == "slack"
        assert error["error"] == "Rate limit exceeded"
        assert "timestamp" in error


class TestNotifyWithRateLimit:
    """Test notify function with rate limiting."""
    
    @patch('pgdn_ws.notify.load_config')
    @patch('pgdn_ws.types.slack.requests.post')
    @patch('pgdn_ws.types.slack.os.getenv')
    def test_rate_limit_blocks_notification(self, mock_getenv, mock_post, mock_load_config):
        """Test that rate limiting blocks notifications."""
        # Setup mocks
        mock_load_config.return_value = {
            "rate_limits": {
                "slack": {"calls": 1, "period": 60}
            }
        }
        mock_getenv.return_value = "https://hooks.slack.com/test"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Reset rate limiter to pick up new config
        import pgdn_ws.notify
        pgdn_ws.notify._rate_limit_manager = None
        
        data = {
            "type": "slack",
            "body": "test",
            "meta": {"channel": "#test"}
        }
        
        # First request should succeed
        result1 = notify(data)
        assert result1["success"] is True
        
        # Second request should be rate limited
        result2 = notify(data)
        assert result2["success"] is False
        assert result2["error"] == "Rate limit exceeded"
        
        # Only one actual HTTP request should have been made
        assert mock_post.call_count == 1
    
    @patch('pgdn_ws.notify.load_config')
    def test_no_rate_limit_when_disabled(self, mock_load_config):
        """Test that notifications work normally when rate limiting is disabled."""
        mock_load_config.return_value = {}
        
        # Reset rate limiter
        import pgdn_ws.notify
        pgdn_ws.notify._rate_limit_manager = None
        
        data = {
            "type": "slack",
            "body": "test",
            "meta": {"channel": "#test"}
        }
        
        # Should get normal error (missing webhook URL) not rate limit error
        result = notify(data)
        assert result["success"] is False
        assert "Rate limit exceeded" not in result["error"]
        assert "Missing Slack webhook URL" in result["error"] 