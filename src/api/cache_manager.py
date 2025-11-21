"""
Multi-tier caching system
Supports in-memory, Redis, and SQLite caching
"""

import json
import logging
import pickle
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import aiosqlite

try:
    from ..config import settings, CACHE_DIR
except ImportError:
    from src.config import settings, CACHE_DIR

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Multi-tier cache manager
    L1: In-memory (fastest, limited size)
    L2: Redis (optional, shared across instances)
    L3: SQLite (persistent, slower)
    """

    def __init__(self, enable_redis: bool = False) -> None:
        self.enable_redis = enable_redis and settings.REDIS_ENABLED

        # L1: In-memory cache
        self.memory_cache: Dict[str, tuple[Any, datetime]] = {}
        self.max_memory_items = 1000

        # L2: Redis client (optional)
        self.redis_client = None

        # L3: SQLite cache
        self.sqlite_path = CACHE_DIR / "cache.db"
        self.sqlite_conn: Optional[aiosqlite.Connection] = None

    async def initialize(self):
        """Initialize cache connections"""
        try:
            # Initialize Redis if enabled
            if self.enable_redis:
                try:
                    import aioredis
                    self.redis_client = await aioredis.from_url(
                        settings.REDIS_URL,
                        encoding="utf-8",
                        decode_responses=True
                    )

                    # Test the connection with a ping
                    try:
                        await self.redis_client.ping()
                        logger.info("Redis cache initialized and connection verified")
                    except Exception as ping_error:
                        logger.warning(
                            f"Redis client created but connection test failed: {ping_error}. "
                            f"Disabling Redis cache."
                        )
                        # Clean up failed connection
                        try:
                            await self.redis_client.close()
                        except:
                            pass
                        self.redis_client = None
                        self.enable_redis = False

                except ImportError:
                    logger.warning(
                        "aioredis module not installed. "
                        "Install with: pip install aioredis"
                    )
                    self.redis_client = None
                    self.enable_redis = False
                except Exception as e:
                    logger.warning(f"Failed to initialize Redis client: {e}")
                    self.redis_client = None
                    self.enable_redis = False

            # Initialize SQLite cache
            self.sqlite_conn = await aiosqlite.connect(str(self.sqlite_path))
            await self._init_sqlite_schema()
            logger.info("SQLite cache initialized")

        except Exception as e:
            logger.error(f"Cache initialization failed: {e}")

    async def _init_sqlite_schema(self):
        """Initialize SQLite cache schema"""
        await self.sqlite_conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value BLOB,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await self.sqlite_conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires_at
            ON cache(expires_at)
        """)
        await self.sqlite_conn.commit()

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache (checks all tiers)

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        # Try L1: Memory cache
        if key in self.memory_cache:
            value, expires_at = self.memory_cache[key]
            if datetime.now() < expires_at:
                logger.debug(f"L1 cache hit: {key}")
                return value
            else:
                # Expired, remove from memory
                del self.memory_cache[key]

        # Try L2: Redis cache
        if self.redis_client:
            try:
                value = await self.redis_client.get(key)
                if value:
                    logger.debug(f"L2 cache hit: {key}")
                    # Deserialize
                    deserialized = json.loads(value)
                    # Store in L1 for next time
                    self._set_memory_cache(key, deserialized, 300)  # 5 min in L1
                    return deserialized
            except Exception as e:
                logger.warning(f"Redis get error: {e}")

        # Try L3: SQLite cache
        if self.sqlite_conn:
            try:
                async with self.sqlite_conn.execute(
                    "SELECT value, expires_at FROM cache WHERE key = ?",
                    (key,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        value_blob, expires_at_str = row
                        expires_at = datetime.fromisoformat(expires_at_str)

                        if datetime.now() < expires_at:
                            logger.debug(f"L3 cache hit: {key}")
                            # Deserialize
                            value = pickle.loads(value_blob)
                            # Store in higher tiers for next time
                            self._set_memory_cache(key, value, 300)
                            return value
                        else:
                            # Expired, delete from SQLite
                            await self.sqlite_conn.execute(
                                "DELETE FROM cache WHERE key = ?",
                                (key,)
                            )
                            await self.sqlite_conn.commit()
            except Exception as e:
                logger.warning(f"SQLite get error: {e}")

        return None

    async def set(self, key: str, value: Any, ttl: int = 3600):
        """
        Set value in cache (all tiers)

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        expires_at = datetime.now() + timedelta(seconds=ttl)

        # Set in L1: Memory cache
        self._set_memory_cache(key, value, ttl)

        # Set in L2: Redis cache
        if self.redis_client:
            try:
                serialized = json.dumps(value)
                await self.redis_client.setex(key, ttl, serialized)
            except Exception as e:
                logger.warning(f"Redis set error: {e}")

        # Set in L3: SQLite cache
        if self.sqlite_conn:
            try:
                value_blob = pickle.dumps(value)
                await self.sqlite_conn.execute(
                    "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
                    (key, value_blob, expires_at.isoformat())
                )
                await self.sqlite_conn.commit()
            except Exception as e:
                logger.warning(f"SQLite set error: {e}")

    def _set_memory_cache(self, key: str, value: Any, ttl: int):
        """Set value in memory cache with size limit"""
        # If cache is full, remove oldest items
        if len(self.memory_cache) >= self.max_memory_items:
            # Remove expired items first
            now = datetime.now()
            expired_keys = [
                k for k, (_, exp) in self.memory_cache.items()
                if exp < now
            ]
            for k in expired_keys:
                del self.memory_cache[k]

            # If still full, remove oldest 10%
            if len(self.memory_cache) >= self.max_memory_items:
                to_remove = int(self.max_memory_items * 0.1)
                for k in list(self.memory_cache.keys())[:to_remove]:
                    del self.memory_cache[k]

        expires_at = datetime.now() + timedelta(seconds=ttl)
        self.memory_cache[key] = (value, expires_at)

    async def delete(self, key: str):
        """Delete key from all cache tiers"""
        # Delete from L1
        if key in self.memory_cache:
            del self.memory_cache[key]

        # Delete from L2
        if self.redis_client:
            try:
                await self.redis_client.delete(key)
            except Exception as e:
                logger.warning(f"Redis delete error: {e}")

        # Delete from L3
        if self.sqlite_conn:
            try:
                await self.sqlite_conn.execute(
                    "DELETE FROM cache WHERE key = ?",
                    (key,)
                )
                await self.sqlite_conn.commit()
            except Exception as e:
                logger.warning(f"SQLite delete error: {e}")

    async def clear(self):
        """Clear all caches"""
        # Clear L1
        self.memory_cache.clear()

        # Clear L2
        if self.redis_client:
            try:
                await self.redis_client.flushdb()
            except Exception as e:
                logger.warning(f"Redis clear error: {e}")

        # Clear L3
        if self.sqlite_conn:
            try:
                await self.sqlite_conn.execute("DELETE FROM cache")
                await self.sqlite_conn.commit()
            except Exception as e:
                logger.warning(f"SQLite clear error: {e}")

    async def cleanup_expired(self):
        """Remove expired entries from all caches"""
        # L1 cleanup
        now = datetime.now()
        expired_keys = [
            k for k, (_, exp) in self.memory_cache.items()
            if exp < now
        ]
        for k in expired_keys:
            del self.memory_cache[k]

        # L3 cleanup (Redis handles expiry automatically)
        if self.sqlite_conn:
            try:
                await self.sqlite_conn.execute(
                    "DELETE FROM cache WHERE expires_at < ?",
                    (now.isoformat(),)
                )
                await self.sqlite_conn.commit()
            except Exception as e:
                logger.warning(f"SQLite cleanup error: {e}")

    async def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = {
            "l1_memory_items": len(self.memory_cache),
            "l1_max_items": self.max_memory_items
        }

        if self.sqlite_conn:
            try:
                async with self.sqlite_conn.execute(
                    "SELECT COUNT(*) FROM cache"
                ) as cursor:
                    row = await cursor.fetchone()
                    stats["l3_sqlite_items"] = row[0] if row else 0
            except Exception as e:
                logger.warning(f"SQLite stats error: {e}")

        return stats

    async def close(self):
        """Close cache connections"""
        if self.redis_client:
            try:
                await self.redis_client.close()
            except Exception as e:
                logger.warning(f"Redis close error: {e}")

        if self.sqlite_conn:
            try:
                await self.sqlite_conn.close()
            except Exception as e:
                logger.warning(f"SQLite close error: {e}")
