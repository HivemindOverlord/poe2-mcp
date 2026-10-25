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
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

try:
    from ..api.poe_ninja_api import ASCENDANCY_TO_BASE_CLASS, PoeNinjaAPI
    from ..config import settings
    from ..pob.importer import PoBImporter
except ImportError:
    from src.config import settings
    from src.api.poe_ninja_api import PoeNinjaAPI, ASCENDANCY_TO_BASE_CLASS
    from src.pob.importer import PoBImporter

from .cache_manager import CacheManager
from .rate_limiter import RateLimiter

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
        rate_limiter: Optional[RateLimiter] = None,
    ):
        self.cache_manager = cache_manager
        self.rate_limiter = rate_limiter or RateLimiter(
            rate_limit=5
        )  # Be gentle with third-party APIs

        self.client = httpx.AsyncClient(
            timeout=settings.REQUEST_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            follow_redirects=True,
        )

        # Initialize poe.ninja API client
        self.ninja_api = PoeNinjaAPI(
            rate_limiter=self.rate_limiter, cache_manager=self.cache_manager
        )

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

    def _to_poe_ninja_league_slug(self, league: str) -> str:
        """
        Convert league display name to poe.ninja URL slug.

        poe.ninja's 0.5 profile/events APIs require the league slug as a
        path segment (e.g. "runesofaldur"). The slug is what /poe2/api/data/
        index-state returns as ``buildLeagues[].url``. Reuses
        ``PoeNinjaAPI.LEAGUE_MAPPINGS`` for the canonical mapping.

        Args:
            league: Display league name (e.g., "Runes of Aldur")

        Returns:
            URL slug (e.g., "runesofaldur"). Falls back to a lowercased
            no-space version of the input when the mapping is missing —
            works for "Standard"/"Hardcore"-style canonical names.
        """
        mappings = PoeNinjaAPI.LEAGUE_MAPPINGS
        if league in mappings:
            return mappings[league]
        for key, value in mappings.items():
            if key.lower() == league.lower():
                return value
        return league.replace(" ", "").lower()

    async def get_character(
        self, account_name: str, character_name: str, league: str = "Standard"
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
        logger.info(
            f"Fetching character {character_name} for account {account_name} (league: {league})"
        )

        # NOTE (#133): the former tier 1 (PoeNinjaAPI.get_character — snapshot
        # endpoint + HTML scrape) is retired; both its endpoints are dead
        # post-0.5. The profile-API flow below is now the primary path.

        # poe.ninja profile API (SSE events -> model) — the working 0.5 path
        try:
            char_data = await self.get_character_from_poe_ninja(
                account_name, character_name, league
            )
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
        self, account_name: str, character_name: str
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
                    soup = BeautifulSoup(response.text, "html.parser")

                    char_data = {
                        "name": character_name,
                        "account": account_name,
                        "class": "Unknown",
                        "level": 0,
                        "source": "web_scraping",
                    }

                    # Try to extract basic info
                    # Look for common patterns
                    level_patterns = [
                        r"Level:\s*(\d+)",
                        r'level":\s*(\d+)',
                        r"<span.*?level.*?>(\d+)</span>",
                    ]
                    for pattern in level_patterns:
                        match = re.search(pattern, response.text, re.IGNORECASE)
                        if match:
                            char_data["level"] = int(match.group(1))
                            break

                    class_patterns = [
                        r"Class:\s*(\w+)",
                        r'class":\s*"([^"]+)"',
                        r"<span.*?class.*?>([^<]+)</span>",
                    ]
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
        self, account_name: str, character_name: str, league: str = "Standard"
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
            character_data = await self._parse_poe_ninja_page(
                response.text, account_name, character_name, league
            )

            if character_data:
                # Cache the result
                if self.cache_manager:
                    await self.cache_manager.set(cache_key, character_data, ttl=settings.CACHE_TTL)

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
        self, html: str, account_name: str, character_name: str, league: str = "Standard"
    ) -> Optional[Dict[str, Any]]:
        """
        Parse poe.ninja character page HTML to extract character data

        The page uses client-side rendering with JavaScript, so we need to
        look for embedded JSON data or API calls
        """
        try:
            soup = BeautifulSoup(html, "html.parser")

            # poe.ninja uses client-side rendering with Astro/React
            # Look for embedded JSON data in script tags or meta tags
            scripts = soup.find_all("script")

            # Try to find JSON data embedded in the page
            for script in scripts:
                if script.string and "character" in script.string.lower():
                    # Look for JSON data patterns
                    import json
                    import re

                    # Try to extract JSON objects
                    json_pattern = r'\{[^{}]*"character"[^{}]*:.*?\}'
                    matches = re.findall(json_pattern, script.string, re.DOTALL)

                    for match in matches:
                        try:
                            data = json.loads(match)
                            if "character" in data or "characterName" in data:
                                logger.info("Found embedded character data in script tag")
                                return self._normalize_character_data(
                                    data, account_name, character_name
                                )
                        except:
                            continue

            # If we can't find embedded data, we need to make additional API calls
            # poe.ninja likely has an internal API we can use
            logger.warning("Could not find embedded character data, will try API approach")
            return await self._fetch_from_poe_ninja_api(account_name, character_name, league)

        except Exception as e:
            self.last_error_message = f"Error parsing poe.ninja page for {character_name}: {e}"
            logger.error(self.last_error_message)
            return None

    async def _fetch_from_poe_ninja_api(
        self, account_name: str, character_name: str, league: str = "Standard"
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch character data from poe.ninja's internal API

        Based on HAR-captured API flow (re-verified 2026-06-02 against a live
        Runes of Aldur character, issue #131):

        1. ``GET /poe2/api/events/character/{account}/{leagueUrl}/{character}``
           -> SSE stream yielding ``data: {"version": <content-hash int>}``
        2. ``GET /poe2/api/profile/characters/{account}/{leagueUrl}/{character}/model/{version}``
           -> JSON ``{type, charModel: {...}}``

        The ``{leagueUrl}`` segment is the league slug (``runesofaldur``,
        ``runesofaldurhc``, ``standard``, ...) — NOT the display name. The
        endpoint is fully public; no auth required.
        """
        try:
            league_slug = self._to_poe_ninja_league_slug(league)

            # The events API returns Server-Sent Events (SSE) with model ID
            # Format: data: {"version":4211492750}
            events_url = (
                f"{settings.POE_NINJA_PROFILE_URL}/poe2/api/events/character/"
                f"{account_name}/{league_slug}/{character_name}"
            )

            logger.info(f"Fetching character model ID from: {events_url}")
            await self.rate_limiter.acquire()

            # Stream the SSE response and extract the model ID
            async with self.client.stream("GET", events_url) as response:
                if response.status_code != 200:
                    logger.warning(f"Events API returned status: {response.status_code}")
                    return None

                # Read the first SSE message
                model_id = None
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        import json

                        # Parse the SSE data line
                        data_str = line[5:].strip()  # Remove "data:" prefix
                        try:
                            data = json.loads(data_str)
                            model_id = data.get("version")
                            logger.info(f"Got model ID: {model_id}")
                            break  # We only need the first message
                        except:
                            continue

                if not model_id:
                    self.last_error_message = f"Could not extract model ID from poe.ninja events stream for {character_name}"
                    logger.warning(self.last_error_message)
                    return None

            # Now fetch the character model using the ID
            model_url = (
                f"{settings.POE_NINJA_PROFILE_URL}/poe2/api/profile/characters/"
                f"{account_name}/{league_slug}/{character_name}/model/{model_id}"
            )

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
            self.last_error_message = (
                f"Error fetching from poe.ninja internal API for {character_name}: {e}"
            )
            logger.error(self.last_error_message, exc_info=True)
            return None

    async def get_character_from_ladder(
        self, character_name: str, league: str = "Standard"
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
                for entry in data.get("entries", []):
                    char = entry.get("character", {})
                    if char.get("name") == character_name:
                        logger.info(f"Found character {character_name} in ladder")

                        char_data = {
                            "name": char.get("name"),
                            "level": char.get("level"),
                            "class": char.get("class"),
                            "league": league,
                            "account": entry.get("account", {}).get("name"),
                            "experience": char.get("experience"),
                            "rank": entry.get("rank"),
                        }

                        if self.cache_manager:
                            await self.cache_manager.set(
                                cache_key, char_data, ttl=settings.CACHE_TTL
                            )

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
        class_filter: Optional[str] = None,
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
                entries = data.get("entries", [])

                if not entries:
                    break  # No more entries

                for entry in entries:
                    char = entry.get("character", {})
                    account = entry.get("account", {})

                    char_level = char.get("level", 0)
                    char_class = char.get("class", "")

                    # Apply filters
                    if char_level < min_level:
                        continue

                    if class_filter and char_class != class_filter:
                        continue

                    top_characters.append(
                        {
                            "account": account.get("name", ""),
                            "character": char.get("name", ""),
                            "level": char_level,
                            "class": char_class,
                            "rank": entry.get("rank", 0),
                            "dead": entry.get("dead", False),
                            "online": entry.get("online", False),
                        }
                    )

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
        self, raw_data: Dict[str, Any], account_name: str, character_name: str
    ) -> Dict[str, Any]:
        """
        Normalize character data from various sources into a standard format.

        For poe.ninja-sourced characters (where ``charModel`` is present), the
        ``charModel.pathOfBuildingExport`` blob - when non-empty - is decoded
        via the PoB importer and used as the **primary** parse route (#132).
        This sidesteps our local passive-tree resolution gap (CLAUDE.md
        CRITICAL #1): PoB exports embed all allocated passives in their own
        ``passiveTreeName: "PassiveTree-0.5"`` format. poe.ninja-only fields
        not present in the PoB payload (``defensiveStats``, ``breakdowns``,
        ``league``, ``experience``, ``lastSeen``...) are merged on top.

        When the export is missing or fails to decode, falls back to direct
        field-based normalization of ``charModel`` (the pre-#132 path).
        """
        # Check if this is poe.ninja format with charModel
        char_model = raw_data.get("charModel", raw_data)
        pob_export = char_model.get("pathOfBuildingExport", "") or ""

        # ------------------------------------------------------------------
        # Primary route (#132): decode pob_export via the PoB importer.
        # The export is base64+zlib XML; PoBImporter.import_build_sync handles
        # the full parse and returns name/level/class/ascendancy/items/skills/
        # tree/config/stats/notes/version.
        # ------------------------------------------------------------------
        pob_data: Optional[Dict[str, Any]] = None
        if pob_export and pob_export.startswith(("eNr", "eJx", "eJw", "eNo")):
            try:
                pob_data = PoBImporter().import_build_sync(pob_export)
                logger.info(
                    f"Parsed character via pathOfBuildingExport (#132 primary route): "
                    f"{pob_data.get('name')}, {pob_data.get('class')} lvl {pob_data.get('level')}"
                )
            except Exception as e:
                logger.warning(
                    f"pathOfBuildingExport decode failed for {character_name}, "
                    f"falling back to field-based normalize: {e}"
                )
                pob_data = None

        # Passive tree data - poe.ninja uses 'passiveSelection' (list of node IDs)
        passive_data = (
            char_model.get("passiveSelection")  # poe.ninja format: list of node IDs
            or char_model.get("passives")  # Alternative format
            or char_model.get("passiveTree")  # Another alternative
            or char_model.get("hashes")  # Official API format
            or []
        )

        normalised: Dict[str, Any] = {
            "name": char_model.get("name", character_name),
            "account": char_model.get("account", account_name),
            "level": char_model.get("level", 0),
            "class": char_model.get("class", "Unknown"),
            "league": char_model.get("league", "Standard"),
            "experience": char_model.get("experience", 0),
            "items": char_model.get("items", char_model.get("equipment", [])),
            "skills": char_model.get("skills", []),
            "passive_tree": passive_data,
            "keystones": char_model.get("keystones", []),
            "jewels": char_model.get("jewels", []),
            "flasks": char_model.get("flasks", []),
            "charms": char_model.get("charms", []),
            "stats": char_model.get("defensiveStats", {}),
            "pob_export": pob_export,
            "raw_data": raw_data,  # Keep original data for reference
        }

        # ------------------------------------------------------------------
        # Merge PoB-derived fields when available. PoB is authoritative for
        # items/skills/passive_tree (its export embeds them in
        # PassiveTree-0.5 format, no local resolution needed). poe.ninja-only
        # metadata (account, league, experience, defensiveStats, breakdowns)
        # stays from the manual normalize above.
        # ------------------------------------------------------------------
        if pob_data:
            # PoB items/skills/tree are richer and structurally-complete; prefer them.
            if pob_data.get("items"):
                normalised["items"] = pob_data["items"]
            if pob_data.get("skills"):
                normalised["skills"] = pob_data["skills"]
            if pob_data.get("tree"):
                normalised["passive_tree"] = pob_data["tree"]
            # PoB-only enrichment fields - retained alongside poe.ninja stats.
            normalised["ascendancy"] = pob_data.get("ascendancy")
            normalised["pob_config"] = pob_data.get("config", {})
            normalised["pob_stats"] = pob_data.get("stats", {})
            normalised["pob_notes"] = pob_data.get("notes", "")
            normalised["pob_version"] = pob_data.get("version", "Unknown")
            normalised["parse_source"] = "pob_export"
            # Honor PoB level/class only if the poe.ninja record didn't supply them.
            # (poe.ninja is the source of truth for the live snapshot; PoB's copy
            # is what the character last exported.)
            if normalised["level"] == 0 and pob_data.get("level"):
                normalised["level"] = pob_data["level"]
            if normalised["class"] == "Unknown" and pob_data.get("class"):
                normalised["class"] = pob_data["class"]
        else:
            normalised["parse_source"] = "field_normalize"

        # ------------------------------------------------------------------
        # Class/ascendancy disambiguation (#151 regression guard): poe.ninja's
        # charModel `class` field (and PoB's className for ascended chars)
        # carries the ASCENDANCY name ("Infernalist"), not the base class.
        # The mapping previously lived in the retired snapshot-tier normalizer
        # (#166) — apply it here so every route gets Witch/Infernalist split.
        # ------------------------------------------------------------------
        raw_class = normalised.get("class")
        if raw_class and raw_class in ASCENDANCY_TO_BASE_CLASS:
            if not normalised.get("ascendancy") or normalised["ascendancy"] == raw_class:
                normalised["ascendancy"] = raw_class
            normalised["class"] = ASCENDANCY_TO_BASE_CLASS[raw_class]
        elif normalised.get("ascendancy") and normalised.get("class") == normalised.get(
            "ascendancy"
        ):
            base = ASCENDANCY_TO_BASE_CLASS.get(normalised["ascendancy"])
            if base:
                normalised["class"] = base

        return normalised

    async def close(self):
        """Close the HTTP client and ninja API client"""
        await self.client.aclose()
        await self.ninja_api.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
