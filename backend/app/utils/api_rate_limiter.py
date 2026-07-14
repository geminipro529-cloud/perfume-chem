"""
Universal API Rate Limiter with Token Bucket + Sliding Windows

Supports multiple providers (Cerebras, Baseten, OpenAI, etc.) with configurable
rate limits and multi-window tracking (minute, hour, day).
"""

import asyncio
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Deque, Dict, Optional

import yaml

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimitWindow:
    """Tracks requests in a time window"""
    window_seconds: int
    max_requests: int
    requests: Deque[float] = field(default_factory=deque)

    def add_request(self, timestamp: float) -> None:
        """Add a request timestamp"""
        self.requests.append(timestamp)
        self._cleanup(timestamp)

    def _cleanup(self, current_time: float) -> None:
        """Remove expired timestamps"""
        cutoff = current_time - self.window_seconds
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()

    def is_allowed(self, current_time: float) -> bool:
        """Check if request is allowed"""
        self._cleanup(current_time)
        return len(self.requests) < self.max_requests

    def get_usage(self, current_time: float) -> Dict:
        """Get current usage stats"""
        self._cleanup(current_time)
        return {
            "used": len(self.requests),
            "limit": self.max_requests,
            "remaining": self.max_requests - len(self.requests),
            "window_seconds": self.window_seconds
        }

    def wait_time(self, current_time: float) -> float:
        """Calculate wait time until next request is allowed"""
        self._cleanup(current_time)
        if len(self.requests) < self.max_requests:
            return 0.0

        # Wait until oldest request expires
        oldest = self.requests[0]
        return max(0.0, (oldest + self.window_seconds) - current_time)


@dataclass
class TokenBucket:
    """Token bucket for fractional rate limiting (e.g., 0.5 req/sec)"""
    rate: float  # tokens per second
    capacity: float
    tokens: float = field(init=False)
    last_update: float = field(init=False)

    def __post_init__(self):
        self.tokens = self.capacity
        self.last_update = time.time()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + (elapsed * self.rate))
        self.last_update = now

    def is_allowed(self) -> bool:
        """Check if request is allowed"""
        self._refill()
        return self.tokens >= 1.0

    def consume(self, tokens: float = 1.0) -> bool:
        """Consume tokens if available"""
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def wait_time(self) -> float:
        """Calculate wait time for next token"""
        self._refill()
        if self.tokens >= 1.0:
            return 0.0
        deficit = 1.0 - self.tokens
        return deficit / self.rate if self.rate > 0 else float('inf')


@dataclass
class TokenCounter:
    """Tracks token usage in a time window"""
    window_seconds: int
    max_tokens: int
    token_requests: Deque[tuple[float, int]] = field(default_factory=deque)  # (timestamp, tokens)

    def add_tokens(self, timestamp: float, num_tokens: int) -> None:
        """Add token usage"""
        self.token_requests.append((timestamp, num_tokens))
        self._cleanup(timestamp)

    def _cleanup(self, current_time: float) -> None:
        """Remove expired entries"""
        cutoff = current_time - self.window_seconds
        while self.token_requests and self.token_requests[0][0] < cutoff:
            self.token_requests.popleft()

    def get_total_tokens(self, current_time: float) -> int:
        """Get total tokens used in window"""
        self._cleanup(current_time)
        return sum(tokens for _, tokens in self.token_requests)

    def is_allowed(self, current_time: float, num_tokens: int) -> bool:
        """Check if tokens can be used"""
        total = self.get_total_tokens(current_time)
        return total + num_tokens <= self.max_tokens

    def get_usage(self, current_time: float) -> Dict:
        """Get current usage stats"""
        used = self.get_total_tokens(current_time)
        return {
            "used": used,
            "limit": self.max_tokens,
            "remaining": self.max_tokens - used,
            "window_seconds": self.window_seconds
        }

    def wait_time(self, current_time: float, num_tokens: int) -> float:
        """Calculate wait time until tokens are available"""
        self._cleanup(current_time)
        used = sum(tokens for _, tokens in self.token_requests)
        remaining = self.max_tokens - used

        if remaining >= num_tokens:
            return 0.0

        shortage = num_tokens - remaining
        accumulated = 0
        for timestamp, tokens in self.token_requests:
            accumulated += tokens
            if accumulated >= shortage:
                return max(0.0, (timestamp + self.window_seconds) - current_time)

        if self.token_requests:
            return max(0.0, (self.token_requests[0][0] + self.window_seconds) - current_time)

        return 0.0


@dataclass
class ProviderLimits:
    """Rate limits for a provider"""
    provider: str

    # Request limits
    requests_per_minute: Optional[int] = None
    requests_per_hour: Optional[int] = None
    requests_per_day: Optional[int] = None
    requests_per_second: Optional[float] = None  # Fractional for sub-second rates

    # Token limits
    tokens_per_minute: Optional[int] = None
    tokens_per_hour: Optional[int] = None
    tokens_per_day: Optional[int] = None

    # Safety and backoff settings
    burst_allowance: float = 0.9
    min_backoff_seconds: Optional[float] = None
    max_backoff_seconds: Optional[float] = None
    backoff_multiplier: Optional[float] = None

    # Internal tracking
    _windows: Dict[str, RateLimitWindow] = field(default_factory=dict, init=False)
    _token_bucket: Optional[TokenBucket] = field(default=None, init=False)
    _token_counters: Dict[str, TokenCounter] = field(default_factory=dict, init=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False)

    def __post_init__(self):
        """Initialize tracking structures"""
        # Request windows
        if self.requests_per_minute:
            self._windows['minute'] = RateLimitWindow(60, self.requests_per_minute)
        if self.requests_per_hour:
            self._windows['hour'] = RateLimitWindow(3600, self.requests_per_hour)
        if self.requests_per_day:
            self._windows['day'] = RateLimitWindow(86400, self.requests_per_day)

        # Token bucket for fractional rates
        if self.requests_per_second:
            capacity = max(1.0, self.requests_per_second * 2 * self.burst_allowance)
            self._token_bucket = TokenBucket(self.requests_per_second, capacity)

        # Token counters
        if self.tokens_per_minute:
            self._token_counters['minute'] = TokenCounter(60, self.tokens_per_minute)
        if self.tokens_per_hour:
            self._token_counters['hour'] = TokenCounter(3600, self.tokens_per_hour)
        if self.tokens_per_day:
            self._token_counters['day'] = TokenCounter(86400, self.tokens_per_day)

    def is_allowed(self, num_tokens: int = 0) -> tuple[bool, Optional[str]]:
        """
        Check if request is allowed

        Returns:
            (allowed, reason) - True if allowed, False with reason if not
        """
        with self._lock:
            current_time = time.time()

            # Check token bucket first (for fractional rates)
            if self._token_bucket and not self._token_bucket.is_allowed():
                wait = self._token_bucket.wait_time()
                return False, f"Token bucket: wait {wait:.2f}s"

            # Check all request windows
            for name, window in self._windows.items():
                if not window.is_allowed(current_time):
                    wait = window.wait_time(current_time)
                    return False, f"{name} limit: wait {wait:.2f}s"

            # Check token limits
            if num_tokens > 0:
                for name, counter in self._token_counters.items():
                    if not counter.is_allowed(current_time, num_tokens):
                        usage = counter.get_usage(current_time)
                        return False, f"{name} token limit: {usage['used']}/{usage['limit']} tokens used"

            return True, None

    def record_request(self, num_tokens: int = 0) -> None:
        """Record a successful request"""
        with self._lock:
            current_time = time.time()

            # Consume token bucket
            if self._token_bucket:
                self._token_bucket.consume(1.0)

            # Record in all windows
            for window in self._windows.values():
                window.add_request(current_time)

            # Record tokens
            if num_tokens > 0:
                for counter in self._token_counters.values():
                    counter.add_tokens(current_time, num_tokens)

    def wait_time(self, num_tokens: int = 0) -> float:
        """Get minimum wait time before next request"""
        with self._lock:
            current_time = time.time()
            wait_times = []

            if self._token_bucket:
                wait_times.append(self._token_bucket.wait_time())

            for window in self._windows.values():
                wait_times.append(window.wait_time(current_time))

            if num_tokens > 0:
                for counter in self._token_counters.values():
                    wait_times.append(counter.wait_time(current_time, num_tokens))

            return max(wait_times) if wait_times else 0.0

    def get_usage(self) -> Dict:
        """Get usage statistics"""
        with self._lock:
            current_time = time.time()

            usage = {
                "provider": self.provider,
                "requests": {},
                "tokens": {}
            }

            for name, window in self._windows.items():
                usage["requests"][name] = window.get_usage(current_time)

            for name, counter in self._token_counters.items():
                usage["tokens"][name] = counter.get_usage(current_time)

            if self._token_bucket:
                self._token_bucket._refill()
                usage["token_bucket"] = {
                    "tokens": self._token_bucket.tokens,
                    "capacity": self._token_bucket.capacity,
                    "rate": self._token_bucket.rate
                }

            return usage


class APIRateLimiter:
    """Universal API rate limiter supporting multiple providers"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize rate limiter

        Args:
            config_path: Path to YAML config file. If None, uses default config.
        """
        self.providers: Dict[str, ProviderLimits] = {}
        self._lock = threading.RLock()

        if config_path:
            self.load_config(config_path)
        else:
            self._load_default_config()

    def _load_default_config(self) -> None:
        """Load default configuration"""
        # Try to load from backend/app/config/rate_limits.yaml
        # From api_rate_limiter.py in utils/: go up 2 levels to reach backend/app/
        config_file = Path(__file__).parent.parent / "config" / "rate_limits.yaml"
        if config_file.exists():
            self.load_config(str(config_file))
        else:
            logger.warning("No rate limit config found, using minimal defaults")
            # Add minimal default limits
            self.add_provider("default", requests_per_minute=60)

    def load_config(self, config_path: str) -> None:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            providers_config = config.get('providers', config) if isinstance(config, dict) else {}
            for provider_name, limits in providers_config.items():
                if not isinstance(limits, dict):
                    continue
                self.add_provider(
                    provider_name,
                    requests_per_minute=limits.get('requests_per_minute'),
                    requests_per_hour=limits.get('requests_per_hour'),
                    requests_per_day=limits.get('requests_per_day'),
                    requests_per_second=limits.get('requests_per_second'),
                    tokens_per_minute=limits.get('tokens_per_minute'),
                    tokens_per_hour=limits.get('tokens_per_hour'),
                    tokens_per_day=limits.get('tokens_per_day'),
                    burst_allowance=limits.get('burst_allowance', 0.9),
                    min_backoff_seconds=limits.get('min_backoff_seconds'),
                    max_backoff_seconds=limits.get('max_backoff_seconds'),
                    backoff_multiplier=limits.get('backoff_multiplier')
                )

            logger.info(f"Loaded rate limits for {len(self.providers)} providers from {config_path}")
        except Exception as e:
            logger.error(f"Failed to load rate limit config: {e}")
            raise

    def add_provider(
        self,
        provider: str,
        requests_per_minute: Optional[int] = None,
        requests_per_hour: Optional[int] = None,
        requests_per_day: Optional[int] = None,
        requests_per_second: Optional[float] = None,
        tokens_per_minute: Optional[int] = None,
        tokens_per_hour: Optional[int] = None,
        tokens_per_day: Optional[int] = None,
        burst_allowance: float = 0.9,
        min_backoff_seconds: Optional[float] = None,
        max_backoff_seconds: Optional[float] = None,
        backoff_multiplier: Optional[float] = None
    ) -> None:
        """Add or update provider rate limits"""
        with self._lock:
            self.providers[provider] = ProviderLimits(
                provider=provider,
                requests_per_minute=requests_per_minute,
                requests_per_hour=requests_per_hour,
                requests_per_day=requests_per_day,
                requests_per_second=requests_per_second,
                tokens_per_minute=tokens_per_minute,
                tokens_per_hour=tokens_per_hour,
                tokens_per_day=tokens_per_day,
                burst_allowance=burst_allowance,
                min_backoff_seconds=min_backoff_seconds,
                max_backoff_seconds=max_backoff_seconds,
                backoff_multiplier=backoff_multiplier
            )
            logger.info(f"Added rate limits for provider: {provider}")

    async def acquire(
        self,
        provider: str,
        num_tokens: int = 0,
        max_retries: int = 3,
        backoff_factor: float = 2.0
    ) -> None:
        """
        Acquire permission to make API call (async with retries)

        Args:
            provider: Provider name
            num_tokens: Number of tokens this request will use
            max_retries: Maximum retry attempts
            backoff_factor: Backoff multiplier for retries

        Raises:
            ValueError: If provider not found
            RuntimeError: If max retries exceeded
        """
        if provider not in self.providers:
            raise ValueError(f"Unknown provider: {provider}")

        limits = self.providers[provider]
        retries = 0

        while retries <= max_retries:
            allowed, reason = limits.is_allowed(num_tokens)

            if allowed:
                limits.record_request(num_tokens)
                return

            # Calculate wait time
            wait_time = limits.wait_time(num_tokens=num_tokens)
            backoff_multiplier = limits.backoff_multiplier or backoff_factor
            min_backoff = limits.min_backoff_seconds or 0.0
            max_backoff = limits.max_backoff_seconds
            base_wait = max(wait_time, min_backoff)
            if base_wait <= 0:
                base_wait = 0.1

            if retries < max_retries:
                # Add exponential backoff
                wait_with_backoff = base_wait * (backoff_multiplier ** retries)
                if max_backoff is not None:
                    wait_with_backoff = min(wait_with_backoff, max_backoff)
                logger.info(
                    f"Rate limit hit for {provider}: {reason}. "
                    f"Waiting {wait_with_backoff:.2f}s (retry {retries + 1}/{max_retries})"
                )
                await asyncio.sleep(wait_with_backoff)
                retries += 1
            else:
                raise RuntimeError(
                    f"Rate limit exceeded for {provider} after {max_retries} retries: {reason}"
                )

    def get_usage(self, provider: Optional[str] = None) -> Dict:
        """
        Get usage statistics

        Args:
            provider: Specific provider name, or None for all providers

        Returns:
            Dictionary with usage stats
        """
        with self._lock:
            if provider:
                if provider not in self.providers:
                    raise ValueError(f"Unknown provider: {provider}")
                return self.providers[provider].get_usage()
            else:
                return {
                    name: limits.get_usage()
                    for name, limits in self.providers.items()
                }

    def reset_provider(self, provider: str) -> None:
        """Reset usage tracking for a provider"""
        with self._lock:
            if provider in self.providers:
                # Recreate the provider limits to reset counters
                old_limits = self.providers[provider]
                self.providers[provider] = ProviderLimits(
                    provider=old_limits.provider,
                    requests_per_minute=old_limits.requests_per_minute,
                    requests_per_hour=old_limits.requests_per_hour,
                    requests_per_day=old_limits.requests_per_day,
                    requests_per_second=old_limits.requests_per_second,
                    tokens_per_minute=old_limits.tokens_per_minute,
                    tokens_per_hour=old_limits.tokens_per_hour,
                    tokens_per_day=old_limits.tokens_per_day
                )
                logger.info(f"Reset rate limiter for provider: {provider}")


# Singleton instance
_rate_limiter: Optional[APIRateLimiter] = None


def get_rate_limiter(config_path: Optional[str] = None) -> APIRateLimiter:
    """Get or create global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = APIRateLimiter(config_path)
    return _rate_limiter
