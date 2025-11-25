"""
Shared Rate Limiter for DeepSeek API
Coordinates rate limiting across multiple bots using the same API key
"""

import time
import threading
import logging

logger = logging.getLogger(__name__)


class SharedRateLimiter:
    """Thread-safe rate limiter shared across all bots"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize rate limiter"""
        if self._initialized:
            return
        
        self._min_request_interval = 1.0  # 1 second between requests (shared across bots)
        self._last_request_time = None
        self._request_lock = threading.Lock()
        self._request_count = 0
        self._request_count_lock = threading.Lock()
        
        self._initialized = True
        logger.info("✅ Shared rate limiter initialized (1.0s between requests)")
    
    def wait_if_needed(self, bot_name: str = "unknown"):
        """
        Wait if needed to respect rate limit
        
        Args:
            bot_name: Name of bot making request (for logging)
        """
        with self._request_lock:
            if self._last_request_time is not None:
                elapsed = time.time() - self._last_request_time
                if elapsed < self._min_request_interval:
                    wait_time = self._min_request_interval - elapsed
                    logger.debug(f"[{bot_name}] Rate limit: waiting {wait_time:.2f}s")
                    time.sleep(wait_time)
            
            self._last_request_time = time.time()
            
            with self._request_count_lock:
                self._request_count += 1
                if self._request_count % 10 == 0:
                    logger.info(f"📊 Shared API usage: {self._request_count} requests (from {bot_name})")
    
    def get_stats(self):
        """Get rate limiter stats"""
        with self._request_count_lock:
            return {
                'total_requests': self._request_count,
                'min_interval': self._min_request_interval
            }


