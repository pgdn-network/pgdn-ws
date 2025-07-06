"""
Rate limiting functionality for pgdn-notify.
"""

import time
import threading
from typing import Dict, Any, Optional, Union
from collections import defaultdict
import datetime
import os

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    pass


class InMemoryRateLimiter:
    """In-memory token bucket rate limiter."""
    
    def __init__(self):
        self._buckets: Dict[str, Dict[str, Union[int, float]]] = defaultdict(dict)
        self._lock = threading.Lock()
    
    def is_allowed(self, key: str, max_calls: int, period: int) -> bool:
        """
        Check if request is allowed based on token bucket algorithm.
        
        Args:
            key: Unique identifier for the rate limit (e.g., 'slack', 'email')
            max_calls: Maximum number of calls allowed
            period: Time period in seconds
            
        Returns:
            True if request is allowed, False otherwise
        """
        with self._lock:
            now = time.time()
            bucket = self._buckets[key]
            
            # Initialize bucket if it doesn't exist
            if 'tokens' not in bucket:
                bucket['tokens'] = max_calls
                bucket['last_refill'] = now
                bucket['tokens'] -= 1
                return True
            
            # Calculate tokens to add based on elapsed time
            elapsed = now - bucket['last_refill']
            tokens_to_add = elapsed * (max_calls / period)
            bucket['tokens'] = min(max_calls, bucket['tokens'] + tokens_to_add)
            bucket['last_refill'] = now
            
            # Check if we have tokens available
            if bucket['tokens'] >= 1:
                bucket['tokens'] -= 1
                return True
            
            return False


class RedisRateLimiter:
    """Redis-backed rate limiter using sliding window."""
    
    def __init__(self, redis_client: Optional[Any] = None):
        if not REDIS_AVAILABLE:
            raise ImportError("Redis not available. Install with: pip install redis")
        
        if redis_client is None:
            # Create default Redis client
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            redis_db = int(os.getenv("REDIS_DB", "0"))
            redis_password = os.getenv("REDIS_PASSWORD")
            
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True
            )
        else:
            self.redis_client = redis_client
    
    def is_allowed(self, key: str, max_calls: int, period: int) -> bool:
        """
        Check if request is allowed using Redis sliding window.
        
        Args:
            key: Unique identifier for the rate limit
            max_calls: Maximum number of calls allowed
            period: Time period in seconds
            
        Returns:
            True if request is allowed, False otherwise
        """
        try:
            pipe = self.redis_client.pipeline()
            now = time.time()
            window_start = now - period
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current entries
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(now): now})
            
            # Set expiration
            pipe.expire(key, period)
            
            results = pipe.execute()
            current_count = results[1]  # Count after removing old entries
            
            return current_count < max_calls
            
        except Exception:
            # If Redis fails, allow the request (fail open)
            return True


class RateLimitConfig:
    """Configuration for rate limits."""
    
    def __init__(self, config_data: Optional[Dict[str, Any]] = None):
        """
        Initialize rate limit configuration.
        
        Args:
            config_data: Dictionary containing rate limit settings
        """
        self.limits: Dict[str, Dict[str, int]] = {}
        self.enabled = False
        
        if config_data:
            self._load_config(config_data)
    
    def _load_config(self, config_data: Dict[str, Any]):
        """Load configuration from dictionary."""
        rate_limits = config_data.get("rate_limits", {})
        
        for notification_type, limits in rate_limits.items():
            if isinstance(limits, dict) and "calls" in limits and "period" in limits:
                self.limits[notification_type] = {
                    "calls": int(limits["calls"]),
                    "period": int(limits["period"])
                }
                self.enabled = True
    
    def get_limit(self, notification_type: str) -> Optional[Dict[str, int]]:
        """Get rate limit for a notification type."""
        return self.limits.get(notification_type)
    
    def has_limit(self, notification_type: str) -> bool:
        """Check if notification type has rate limit configured."""
        return notification_type in self.limits


class RateLimitManager:
    """Manages rate limiting for notifications."""
    
    def __init__(self, config: Optional[RateLimitConfig] = None, use_redis: bool = False):
        """
        Initialize rate limit manager.
        
        Args:
            config: Rate limit configuration
            use_redis: Whether to use Redis-backed rate limiting
        """
        self.config = config or RateLimitConfig()
        self.use_redis = use_redis and REDIS_AVAILABLE
        
        if self.use_redis:
            self.limiter = RedisRateLimiter()
        else:
            self.limiter = InMemoryRateLimiter()
    
    def check_rate_limit(self, notification_type: str) -> bool:
        """
        Check if notification is allowed based on rate limits.
        
        Args:
            notification_type: Type of notification (slack, email, etc.)
            
        Returns:
            True if allowed, False if rate limited
        """
        if not self.config.enabled or not self.config.has_limit(notification_type):
            return True
        
        limit_config = self.config.get_limit(notification_type)
        if not limit_config:
            return True
        
        return self.limiter.is_allowed(
            key=f"pgdn_ws_{notification_type}",
            max_calls=limit_config["calls"],
            period=limit_config["period"]
        )
    
    def get_rate_limit_error(self, notification_type: str) -> Dict[str, Any]:
        """Generate standardized rate limit error response."""
        return {
            "success": False,
            "type": notification_type,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "error": "Rate limit exceeded"
        } 