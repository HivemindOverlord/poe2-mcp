"""
Character Data Fetcher
Fetches character data from multiple sources with intelligent fallback:
1. poe.ninja API (primary)
2. poe.ninja web scraping (fallback)
3. Official PoE ladder API (fallback)
4. Direct web scraping (last resort)
"""

import logging
import re
from typing import Optional, Dict, Any, List
import httpx
from bs4 import BeautifulSoup

try:
    from ..config import settings
    from ..api.poe_ninja_api import PoeNinjaAPI
except ImportError:
    from src.config import settings
    from src.api.poe_ninja_api import PoeNinjaAPI
from .rate_limiter import RateLimiter
from .cache_manager import CacheManager

logger = logging.getLogger(__name__)


class CharacterFetcher:
    """
    Fetch character data from multiple sources with intelligent fallback
    No OAuth2 required - uses public data from poe.ninja and ladder API
    """

    # League name mappings for official PoE API
    # Maps display names to API identifiers
    LEAGUE_NAME_MAPPINGS = {
        "Rise of the Abyssal": "Abyss",
        "Abyss": "Abyss",
        "Abyss Hardcore": "Hardcore Abyss",
        "Abyss SSF": "SSF Abyss",
        "Abyss Hardcore SSF": "SSF Hardcore Abyss",
    }

    def __init__(
        self,
        cache_manager: Optional[CacheManager] = None,
        rate_limiter: Optional[RateLimiter] = None
    ):
        self.cache_manager = cache_manager
        self.rate_limiter = rate_limiter or RateLimiter(rate_limit=5)  # Be gentle with third-party APIs

        self.client = httpx.AsyncClient(
            timeout=settings.REQUEST_TIMEOUT,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            follow_redirects=True
        )

        # Initialize poe.ninja API client
        self.ninja_api = PoeNinjaAPI(rate_limiter=self.rate_limiter, cache_manager=self.cache_manager)

        # Track last error message for debugging
        self.last_error_message: str = ""

    def _normalize_league_name(self, league: str) -> str:
        """
        Normalize league name for official PoE API

        Args:
            league: Display league name (e.g., "Rise of the Abyssal")

        Returns:
            API league identifier (e.g., "Abyss")
        """
        # Check exact match first
        if league in self.LEAGUE_NAME_MAPPINGS:
            return self.LEAGUE_NAME_MAPPINGS[league]

        # Check case-insensitive match
        for key, value in self.LEAGUE_NAME_MAPPINGS.items():
            if key.lower() == league.lower():
                return value

        # Return as-is if no mapping found (works for Standard, Hardcore, etc.)
        return league

    async def get_character(
        self,
        account_name: str,
        character_name: str,
        league: str = "Standard"
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch character data using all available sources with intelligent fallback

        Priority order:
        1. poe.ninja API (new enhanced client)
        2. poe.ninja web scraping (SSE/model API)
        3. Official ladder API
        4. Direct HTML scraping

        Args:
            account_name: PoE account name
            character_name: Character name
            league: League name

        Returns:
            Character data dictionary or None if not found
        """
        logger.info(f"Fetching character {character_name} for account {account_name} (league: {league})")

        # Try poe.ninja API first (most reliable)
        try:
            logger.debug(f"  Trying poe.ninja API with league={league}")
            char_data = await self.ninja_api.get_character(account_name, character_name, league)
            if char_data and char_data.get("level", 0) > 0:
                logger.info(f"✅ Successfully fetched from poe.ninja API")
                self.last_error_message = ""  # Clear error on success
                return char_data
        except Exception as e:
            self.last_error_message = f"poe.ninja API error: {str(e)}"
            logger.warning(f"⚠️ {self.last_error_message}")

        # Fallback to poe.ninja SSE/model API
        try:
            char_data = await self.get_character_from_poe_ninja(account_name, character_name, league)
            if char_data and char_data.get("level", 0) > 0:
                logger.info("Successfully fetched from poe.ninja SSE API")
                self.last_error_message = ""  # Clear error on success
                return char_data
        except Exception as e:
            self.last_error_message = f"poe.ninja SSE API error: {str(e)}"
            logger.warning(self.last_error_message)

        # Fallback to ladder API
        try:
            char_data = await self.get_character_from_ladder(character_name, league)
            if char_data:
                logger.info("Successfully fetched from ladder API")
                self.last_error_message = ""  # Clear error on success
                return char_data
        except Exception as e:
            self.last_error_message = f"Ladder API error: {str(e)}"
            logger.warning(self.last_error_message)

        # Last resort: direct HTML scraping
        try:
            char_data = await self._scrape_character_direct(account_name, character_name)
            if char_data:
                logger.info("Successfully fetched via direct scraping")
                self.last_error_message = ""  # Clear error on success
                return char_data
        except Exception as e:
            self.last_error_message = f"Direct scraping error: {str(e)}"
            logger.warning(self.last_error_message)

        # All methods exhausted
        self.last_error_message = (
            f"Character '{character_name}' not found after trying all sources "
            f"(account: {account_name}, league: {league}). "
            f"Verify the character exists and is public."
        )
        logger.error(self.last_error_message)
        return None

    async def _scrape_character_direct(
        self,
        account_name: str,
        character_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Direct web scraping as last resort
        Tries multiple URL patterns and parsing strategies
        """
        urls_to_try = [
            f"https://poe.ninja/poe2/builds/character/{account_name}/{character_name}",
            f"https://www.pathofexile.com/account/view-profile/{account_name}/characters/{character_name}",
            f"https://poe.ninja/builds/character/{account_name}/{character_name}",
        ]

        for url in urls_to_try:
            try:
                await self.rate_limiter.acquire()
                logger.debug(f"Trying direct scrape from: {url}")

                response = await self.client.get(url)
                if response.status_code == 200:
                    # Try to parse any character data we can find
                    soup = BeautifulSoup(response.text, 'html.parser')

                    char_data = {
                        "name": character_name,
                        "account": account_name,
                        "class": "Unknown",
                        "level": 0,
                        "source": "web_scraping"
                    }

                    # Try to extract basic info
                    # Look for common patterns
                    level_patterns = [r'Level:\s*(\d+)', r'level":\s*(\d+)', r'<span.*?level.*?>(\d+)</span>']
                    for pattern in level_patterns:
                        match = re.search(pattern, response.text, re.IGNORECASE)
                        if match:
                            char_data["level"] = int(match.group(1))
                            break

                    class_patterns = [r'Class:\s*(\w+)', r'class":\s*"([^"]+)"', r'<span.*?class.*?>([^<]+)</span>']
                    for pattern in class_patterns:
                        match = re.search(pattern, response.text, re.IGNORECASE)
                        if match:
                            char_data["class"] = match.group(1)
                            break

                    if char_data["level"] > 0:
                        logger.info(f"Extracted basic character data from {url}")
                        return char_data

            except Exception as e:
                logger.debug(f"Failed to scrape {url}: {e}")
                continue

        # All scraping attempts failed
        self.last_error_message = (
            f"Could not scrape character data for {character_name} "
            f"(account: {account_name}) from any URL"
        )
        logger.warning(self.last_error_message)
        return None

    async def get_character_from_poe_ninja(
        self,
        account_name: str,
        character_name: str,
        league: str = "Standard"
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch character data from poe.ninja profile page

        Args:
            account_name: PoE account name (e.g., "Tomawar40-2671")
            character_name: Character name
            league: League name (default: "Standard")

        Returns:
            Character data dictionary or None if not found
        """
        cache_key = f"poeninja_char:{account_name}:{character_name}"

        # Check cache
        if self.cache_manager:
            cached_data = await self.cache_manager.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit for character {character_name}")
                return cached_data

        # Apply rate limiting
        await self.rate_limiter.acquire()

        try:
            # URL format: https://poe.ninja/poe2/profile/{account}/character/{character}
            url = f"{settings.POE_NINJA_PROFILE_URL}/poe2/profile/{account_name}/character/{character_name}"
            logger.info(f"Fetching character from poe.ninja: {url}")

            response = await self.client.get(url)
            response.raise_for_status()

            # Parse the HTML to extract character data
            character_data = await self._parse_poe_ninja_page(response.text, account_name, character_name)

            if character_data:
                # Cache the result
                if self.cache_manager:
                    await self.cache_manager.set(
                        cache_key,
                        character_data,
                        ttl=settings.CACHE_TTL
                    )

                logger.info(f"Successfully fetched character {character_name} from poe.ninja")
                return character_data
            else:
                self.last_error_message = (
                    f"Could not parse character data from poe.ninja for {character_name} "
                    f"(account: {account_name})"
                )
                logger.warning(self.last_error_message)
                return None

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                self.last_error_message = (
                    f"Character {character_name} not found on poe.ninja "
                    f"(HTTP 404 - account: {account_name})"
                )
                logger.warning(self.last_error_message)
            else:
                self.last_error_message = (
                    f"HTTP {e.response.status_code} error fetching character from poe.ninja: {e}"
                )
                logger.error(self.last_error_message)
            return None

        except Exception as e:
            self.last_error_message = f"Unexpected error fetching character from poe.ninja: {e}"
            logger.error(self.last_error_message)
            return None

    async def _parse_poe_ninja_page(
        self,
        html: str,
        account_name: str,
        character_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Parse poe.ninja character page HTML to extract character data

        The page uses client-side rendering with JavaScript, so we need to
        look for embedded JSON data or API calls
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # poe.ninja uses client-side rendering with Astro/React
            # Look for embedded JSON data in script tags or meta tags
            scripts = soup.find_all('script')

            # Try to find JSON data embedded in the page
            for script in scripts:
                if script.string and 'character' in script.string.lower():
                    # Look for JSON data patterns
                    import json
                    import re

                    # Try to extract JSON objects
                    json_pattern = r'\{[^{}]*"character"[^{}]*:.*?\}'
                    matches = re.findall(json_pattern, script.string, re.DOTALL)

                    for match in matches:
                        try:
                            data = json.loads(match)
                            if 'character' in data or 'characterName' in data:
                                logger.info("Found embedded character data in script tag")
                                return self._normalize_character_data(data, account_name, character_name)
                        except:
                            continue

            # If we can't find embedded data, we need to make additional API calls
            # poe.ninja likely has an internal API we can use
            logger.warning("Could not find embedded character data, will try API approach")
            return await self._fetch_from_poe_ninja_api(account_name, character_name)

        except Exception as e:
            self.last_error_message = f"Error parsing poe.ninja page for {character_name}: {e}"
            logger.error(self.last_error_message)
            return None

    async def _fetch_from_poe_ninja_api(
        self,
        account_name: str,
        character_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch character data from poe.ninja's internal API
        Based on actual API endpoints found in HAR file analysis
        """
        try:
            # The events API returns Server-Sent Events (SSE) with model ID
            # Format: data: {"version":4211492750}
            events_url = f"{settings.POE_NINJA_PROFILE_URL}/poe2/api/events/character/{account_name}/{character_name}"

            logger.info(f"Fetching character model ID from: {events_url}")
            await self.rate_limiter.acquire()

            # Stream the SSE response and extract the model ID
            async with self.client.stream('GET', events_url) as response:
                if response.status_code != 200:
                    logger.warning(f"Events API returned status: {response.status_code}")
                    return None

                # Read the first SSE message
                model_id = None
                async for line in response.aiter_lines():
                    if line.startswith('data:'):
                        import json
                        # Parse the SSE data line
                        data_str = line[5:].strip()  # Remove "data:" prefix
                        try:
                            data = json.loads(data_str)
                            model_id = data.get('version')
                            logger.info(f"Got model ID: {model_id}")
                            break  # We only need the first message
                        except:
                            continue

                if not model_id:
                    self.last_error_message = (
                        f"Could not extract model ID from poe.ninja events stream for {character_name}"
                    )
                    logger.warning(self.last_error_message)
                    return None

            # Now fetch the character model using the ID
            model_url = f"{settings.POE_NINJA_PROFILE_URL}/poe2/api/profile/characters/{account_name}/{character_name}/model/{model_id}"

            logger.info(f"Fetching character model from: {model_url}")
            await self.rate_limiter.acquire()

            model_response = await self.client.get(model_url)
            if model_response.status_code == 200:
                model_data = model_response.json()
                logger.info("Successfully fetched character model data")
                return self._normalize_character_data(model_data, account_name, character_name)
            else:
                self.last_error_message = (
                    f"Model API returned HTTP {model_response.status_code} for {character_name}"
                )
                logger.error(self.last_error_message)
                return None

        except Exception as e:
            self.last_error_message = f"Error fetching from poe.ninja internal API for {character_name}: {e}"
            logger.error(self.last_error_message, exc_info=True)
            return None

    async def get_character_from_ladder(
        self,
        character_name: str,
        league: str = "Standard"
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch character data from official PoE ladder API (public, no auth required)

        Args:
            character_name: Character name to search for
            league: League name (display name or API name)

        Returns:
            Character data or None
        """
        # Normalize league name for official API
        api_league = self._normalize_league_name(league)

        cache_key = f"ladder_char:{api_league}:{character_name}"

        if self.cache_manager:
            cached_data = await self.cache_manager.get(cache_key)
            if cached_data:
                return cached_data

        try:
            # The ladder API is public and doesn't require OAuth
            # Format: /api/ladders/{league}?limit=200&offset=0
            # Note: POE_OFFICIAL_API already includes /api
            base_url = f"{settings.POE_OFFICIAL_API}/ladders/{api_league}"

            # We need to search through ladder pages to find the character
            # This is not ideal but works for public characters
            for offset in range(0, 1000, 200):  # Search first 1000 characters
                await self.rate_limiter.acquire()

                url = f"{base_url}?limit=200&offset={offset}"
                response = await self.client.get(url)
                response.raise_for_status()

                data = response.json()

                # Search for the character in the ladder
                for entry in data.get('entries', []):
                    char = entry.get('character', {})
                    if char.get('name') == character_name:
                        logger.info(f"Found character {character_name} in ladder")

                        char_data = {
                            'name': char.get('name'),
                            'level': char.get('level'),
                            'class': char.get('class'),
                            'league': league,
                            'account': entry.get('account', {}).get('name'),
                            'experience': char.get('experience'),
                            'rank': entry.get('rank'),
                        }

                        if self.cache_manager:
                            await self.cache_manager.set(cache_key, char_data, ttl=settings.CACHE_TTL)

                        return char_data

            self.last_error_message = (
                f"Character {character_name} not found in top 1000 of {api_league} ladder"
            )
            logger.warning(self.last_error_message)
            return None

        except Exception as e:
            self.last_error_message = f"Error fetching from ladder API ({api_league}): {e}"
            logger.error(self.last_error_message)
            return None

    async def get_top_ladder_characters(
        self,
        league: str = "Standard",
        limit: int = 100,
        min_level: int = 1,
        class_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get top characters from the ladder

        Args:
            league: League name (display name or API name)
            limit: Number of characters to return
            min_level: Minimum level filter
            class_filter: Filter by character class (e.g., "Stormweaver")

        Returns:
            List of character info dicts with account, character, level, class
        """
        # Normalize league name for official API
        api_league = self._normalize_league_name(league)

        cache_key = f"top_ladder:{api_league}:{limit}:{min_level}:{class_filter}"

        if self.cache_manager:
            cached = await self.cache_manager.get(cache_key)
            if cached:
                return cached

        try:
            base_url = f"{settings.POE_OFFICIAL_API}/ladders/{api_league}"
            top_characters = []

            # Fetch ladder pages until we have enough characters
            offset = 0
            while len(top_characters) < limit and offset < 1000:
                await self.rate_limiter.acquire()

                url = f"{base_url}?limit=200&offset={offset}"
                logger.info(f"Fetching ladder page: offset={offset}")

                response = await self.client.get(url)
                response.raise_for_status()

                data = response.json()
                entries = data.get('entries', [])

                if not entries:
                    break  # No more entries

                for entry in entries:
                    char = entry.get('character', {})
                    account = entry.get('account', {})

                    char_level = char.get('level', 0)
                    char_class = char.get('class', '')

                    # Apply filters
                    if char_level < min_level:
                        continue

                    if class_filter and char_class != class_filter:
                        continue

                    top_characters.append({
                        'account': account.get('name', ''),
                        'character': char.get('name', ''),
                        'level': char_level,
                        'class': char_class,
                        'rank': entry.get('rank', 0),
                        'dead': entry.get('dead', False),
                        'online': entry.get('online', False),
                    })

                    if len(top_characters) >= limit:
                        break

                offset += 200

            logger.info(f"Found {len(top_characters)} characters from ladder")

            # Cache for 30 minutes
            if self.cache_manager and top_characters:
                await self.cache_manager.set(cache_key, top_characters, ttl=1800)

            return top_characters

        except Exception as e:
            logger.error(f"Error fetching top ladder characters: {e}")
            return []

    def _normalize_character_data(
        self,
        raw_data: Dict[str, Any],
        account_name: str,
        character_name: str
    ) -> Dict[str, Any]:
        """
        Normalize character data from various sources into a standard format
        Handles poe.ninja API format
        """
        # Check if this is poe.ninja format with charModel
        char_model = raw_data.get('charModel', raw_data)

        return {
            'name': char_model.get('name', character_name),
            'account': char_model.get('account', account_name),
            'level': char_model.get('level', 0),
            'class': char_model.get('class', 'Unknown'),
            'league': char_model.get('league', 'Standard'),
            'experience': char_model.get('experience', 0),
            'items': char_model.get('items', char_model.get('equipment', [])),
            'skills': char_model.get('skills', []),
            'passive_tree': char_model.get('passives', char_model.get('passiveTree', {})),
            'stats': char_model.get('defensiveStats', {}),
            'raw_data': raw_data  # Keep original data for reference
        }

    async def close(self):
        """Close the HTTP client and ninja API client"""
        await self.client.aclose()
        await self.ninja_api.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
