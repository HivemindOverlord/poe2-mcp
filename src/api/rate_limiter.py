"""
Rate Limiter for API requests
Implements token bucket algorithm with adaptive rate limiting
"""

import asyncio
import time
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter with adaptive backoff
    """

    def __init__(
        self,
        rate_limit: int = 10,  # requests per minute
        burst: int = 3,  # max burst size
        adaptive: bool = True  # enable adaptive rate limiting
    ):
        self.rate_limit = rate_limit
        self.burst = burst
        self.adaptive = adaptive

        # Token bucket
        self.tokens = burst
        self.max_tokens = burst
        self.last_update = time.time()

        # Adaptive rate limiting
        self.consecutive_failures = 0
        self.current_backoff = 1.0

        # Statistics
        self.total_requests = 0
        self.total_waits = 0
        self.total_wait_time = 0.0

        self._lock = asyncio.Lock()

    async def acquire(self):
        """
        Acquire a token (wait if necessary)
        """
        async with self._lock:
            # Refill tokens based on time passed
            now = time.time()
            time_passed = now - self.last_update
            tokens_to_add = time_passed * (self.rate_limit / 60.0)

            self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
            self.last_update = now

            # If no tokens available, wait
            if self.tokens < 1.0:
                wait_time = (1.0 - self.tokens) * (60.0 / self.rate_limit)

                # Apply adaptive backoff if enabled
                if self.adaptive and self.consecutive_failures > 0:
                    wait_time *= self.current_backoff

                logger.debug(f"Rate limit: waiting {wait_time:.2f}s")

                self.total_waits += 1
                self.total_wait_time += wait_time

                await asyncio.sleep(wait_time)

                # Refill after wait
                self.tokens = 1.0

            # Consume a token
            self.tokens -= 1.0
            self.total_requests += 1

    def record_success(self):
        """Record a successful request (resets backoff)"""
        if self.consecutive_failures > 0:
            logger.debug("Request successful, resetting backoff")

        self.consecutive_failures = 0
        self.current_backoff = 1.0

    def record_failure(self):
        """Record a failed request (increases backoff)"""
        self.consecutive_failures += 1
        self.current_backoff = min(
            32.0,  # Max 32x backoff
            2.0 ** self.consecutive_failures
        )

        logger.warning(
            f"Request failed, backoff increased to {self.current_backoff}x "
            f"({self.consecutive_failures} consecutive failures)"
        )

    def get_statistics(self) -> Dict[str, float]:
        """Get rate limiter statistics"""
        return {
            "total_requests": self.total_requests,
            "total_waits": self.total_waits,
            "total_wait_time": self.total_wait_time,
            "average_wait_time": (
                self.total_wait_time / self.total_waits
                if self.total_waits > 0 else 0
            ),
            "current_backoff": self.current_backoff,
            "consecutive_failures": self.consecutive_failures,
            "tokens_available": self.tokens
        }

    def reset(self):
        """Reset the rate limiter"""
        self.tokens = self.max_tokens
        self.last_update = time.time()
        self.consecutive_failures = 0
        self.current_backoff = 1.0


class MultiRateLimiter:
    """
    Manages multiple rate limiters for different API endpoints
    """

    def __init__(self):
        self.limiters: Dict[str, RateLimiter] = {}

    def get_limiter(self, endpoint: str, rate_limit: int = 10) -> RateLimiter:
        """Get or create a rate limiter for an endpoint"""
        if endpoint not in self.limiters:
            self.limiters[endpoint] = RateLimiter(rate_limit=rate_limit)
        return self.limiters[endpoint]

    async def acquire(self, endpoint: str, rate_limit: int = 10):
        """Acquire a token for the specified endpoint"""
        limiter = self.get_limiter(endpoint, rate_limit)
        await limiter.acquire()

    def record_success(self, endpoint: str):
        """Record success for an endpoint"""
        if endpoint in self.limiters:
            self.limiters[endpoint].record_success()

    def record_failure(self, endpoint: str):
        """Record failure for an endpoint"""
        if endpoint in self.limiters:
            self.limiters[endpoint].record_failure()

    def get_statistics(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all rate limiters"""
        return {
            endpoint: limiter.get_statistics()
            for endpoint, limiter in self.limiters.items()
        }
