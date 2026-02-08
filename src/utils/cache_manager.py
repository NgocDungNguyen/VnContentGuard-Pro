"""
VnContentGuard Pro v3 - Cache Manager
======================================
In-memory TTL cache for API results.
Reduces redundant API calls for:
- Article summaries (cached per URL)
- Batch comment analysis (cached per article+comments hash)
"""

import hashlib
import json
import time
from typing import Any, Dict, Optional


class CacheManager:
    """
    In-memory cache with TTL (time-to-live) expiration.

    Usage:
        cache = CacheManager(ttl_seconds=86400)  # 24h
        cache.set("key", {"data": "value"})
        result = cache.get("key")  # returns value or None if expired
    """

    def __init__(self, ttl_seconds: int = 86400):
        """Initialize cache with TTL in seconds (default: 24 hours)."""
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl_seconds
        self.hits = 0
        self.misses = 0

    def _hash_key(self, data: str) -> str:
        """Generate a stable hash key from string data."""
        return hashlib.md5(data.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve cached value if it exists and hasn't expired.

        Returns None if key not found or expired.
        """
        if key not in self.cache:
            self.misses += 1
            return None

        entry = self.cache[key]
        if time.time() - entry["timestamp"] > self.ttl:
            del self.cache[key]
            self.misses += 1
            return None

        self.hits += 1
        return entry["value"]

    def set(self, key: str, value: Any) -> None:
        """Store a value in the cache with the current timestamp."""
        self.cache[key] = {
            "value": value,
            "timestamp": time.time(),
        }

    def clear(self) -> None:
        """Clear all cached entries."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        total = self.hits + self.misses
        return {
            "total_entries": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{(self.hits / total * 100):.1f}%" if total > 0 else "N/A",
        }
