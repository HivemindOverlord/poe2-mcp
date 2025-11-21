"""
Official Path of Exile API Client
Handles character data retrieval with OAuth 2.0 support
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import httpx

try:
    from ..config import settings
except ImportError:
    from src.config import settings
from .rate_limiter import RateLimiter
from .cache_manager import CacheManager

logger = logging.getLogger(__name__)


class PoEAPIClient:
    """
    Client for the official Path of Exile API
    Implements OAuth 2.0, rate limiting, and caching
    """

    def __init__(
        self,
        cache_manager: Optional[CacheManager] = None,
        rate_limiter: Optional[RateLimiter] = None
    ):
        self.base_url = settings.POE_OFFICIAL_API
        self.cache_manager = cache_manager
        self.rate_limiter = rate_limiter or RateLimiter(
            rate_limit=settings.POE_API_RATE_LIMIT
        )

        self.client = httpx.AsyncClient(
            timeout=settings.REQUEST_TIMEOUT,
            headers={
                "User-Agent": "PoE2-Build-Optimizer/1.0"
            }
        )

        self.oauth_token: Optional[str] = None
        self.token_expires: Optional[datetime] = None

    async def _ensure_authenticated(self):
        """Ensure we have a valid OAuth token"""
        if self.oauth_token and self.token_expires:
            if datetime.now() < self.token_expires:
                return

        # Implement OAuth flow
        if not settings.POE_CLIENT_ID or not settings.POE_CLIENT_SECRET:
            logger.warning("PoE OAuth credentials not configured. Using public API only.")
            return

        # TODO: Implement full OAuth 2.0 flow
        # For now, we'll use public API endpoints that don't require auth
        pass

    async def get_character(
        self,
        account_name: str,
        character_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch character data from the official API

        Args:
            account_name: Path of Exile account name
            character_name: Character name

        Returns:
            Character data dictionary or None if not found
        """
        cache_key = f"character:{account_name}:{character_name}"

        # Check cache first
        if self.cache_manager:
            cached_data = await self.cache_manager.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit for character {character_name}")
                return cached_data

        # Apply rate limiting
        await self.rate_limiter.acquire()

        try:
            await self._ensure_authenticated()

            # Construct API URL
            url = f"{self.base_url}/character/{account_name}/{character_name}"

            # Make request
            response = await self.client.get(url)
            response.raise_for_status()

            character_data = response.json()

            # Cache the result
            if self.cache_manager:
                await self.cache_manager.set(
                    cache_key,
                    character_data,
                    ttl=settings.CACHE_TTL
                )

            logger.info(f"Successfully fetched character {character_name}")
            return character_data

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Character {character_name} not found for account {account_name}")
            elif e.response.status_code == 403:
                logger.warning(f"Character {character_name} profile is private")
            else:
                logger.error(f"API error fetching character: {e}")
            return None

        except Exception as e:
            logger.error(f"Error fetching character {character_name}: {e}")
            return None

    async def get_account_characters(
        self,
        account_name: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch all characters for an account

        Args:
            account_name: Path of Exile account name

        Returns:
            List of character dictionaries
        """
        cache_key = f"account_characters:{account_name}"

        # Check cache
        if self.cache_manager:
            cached_data = await self.cache_manager.get(cache_key)
            if cached_data:
                return cached_data

        # Apply rate limiting
        await self.rate_limiter.acquire()

        try:
            await self._ensure_authenticated()

            url = f"{self.base_url}/account/{account_name}/characters"
            response = await self.client.get(url)
            response.raise_for_status()

            characters = response.json()

            # Cache the result
            if self.cache_manager:
                await self.cache_manager.set(
                    cache_key,
                    characters,
                    ttl=settings.CACHE_TTL
                )

            return characters

        except Exception as e:
            logger.error(f"Error fetching account characters: {e}")
            return []

    async def get_passive_tree(self) -> Dict[str, Any]:
        """
        Fetch the passive skill tree data

        Returns:
            Passive tree data
        """
        cache_key = "passive_tree_data"

        # Check cache (passive tree data is static, cache for long time)
        if self.cache_manager:
            cached_data = await self.cache_manager.get(cache_key)
            if cached_data:
                return cached_data

        try:
            # Passive tree endpoint
            url = f"{self.base_url}/passive-tree"
            response = await self.client.get(url)
            response.raise_for_status()

            tree_data = response.json()

            # Cache for 24 hours (passive tree rarely changes)
            if self.cache_manager:
                await self.cache_manager.set(
                    cache_key,
                    tree_data,
                    ttl=86400
                )

            return tree_data

        except Exception as e:
            logger.error(f"Error fetching passive tree: {e}")
            return {}

    async def get_items_data(self) -> Dict[str, Any]:
        """
        Fetch item data from the API

        Returns:
            Item data dictionary
        """
        cache_key = "items_data"

        if self.cache_manager:
            cached_data = await self.cache_manager.get(cache_key)
            if cached_data:
                return cached_data

        try:
            url = f"{self.base_url}/items"
            response = await self.client.get(url)
            response.raise_for_status()

            items_data = response.json()

            # Cache for 24 hours
            if self.cache_manager:
                await self.cache_manager.set(
                    cache_key,
                    items_data,
                    ttl=86400
                )

            return items_data

        except Exception as e:
            logger.error(f"Error fetching items data: {e}")
            return {}

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
