"""
poe.ninja API Client with Web Scraping Fallback
Fetches character data, build rankings, and economy data from poe.ninja
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

import httpx
from bs4 import BeautifulSoup

try:
    from ..api.cache_manager import CacheManager
    from ..api.rate_limiter import RateLimiter
except ImportError:
    from src.api.cache_manager import CacheManager
    from src.api.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# PoE2 Ascendancy to Base Class mapping
# Maps ascendancy class names to their base class
ASCENDANCY_TO_BASE_CLASS = {
    # Warrior ascendancies
    "Titan": "Warrior",
    "Warbringer": "Warrior",
    "Smith of Kitava": "Warrior",
    # Ranger ascendancies
    "Deadeye": "Ranger",
    "Pathfinder": "Ranger",
    # Huntress ascendancies
    "Amazon": "Huntress",
    "Ritualist": "Huntress",
    # Witch ascendancies
    "Infernalist": "Witch",
    "Blood Mage": "Witch",
    "Bloodmage": "Witch",  # Alternate spelling
    "Lich": "Witch",
    "Abyssal Lich": "Witch",
    # Sorceress ascendancies
    "Stormweaver": "Sorceress",
    "Chronomancer": "Sorceress",
    "Disciple of Varashta": "Sorceress",
    # Mercenary ascendancies
    "Tactician": "Mercenary",
    "Witchhunter": "Mercenary",
    "Gemling Legionnaire": "Mercenary",
    # Monk ascendancies
    "Invoker": "Monk",
    "Acolyte of Chayula": "Monk",
    # Druid ascendancies
    "Oracle": "Druid",
    "Shaman": "Druid",
}

# Base classes (not ascendancies)
BASE_CLASSES = {"Warrior", "Ranger", "Huntress", "Witch", "Sorceress", "Mercenary", "Monk", "Druid"}


# poe.ninja URL shapes that identify a character. Ordered most-specific first;
# the 3-segment profile form is what poe.ninja actually links post-0.5
# (league slug sits BETWEEN account and /character/).
_POE_NINJA_URL_PATTERNS = [
    # /poe2/profile/{account}/{league}/character/{char} — current 0.5 format
    re.compile(
        r"poe\.ninja/poe2/profile/(?P<account>[^/?#\s]+)/(?P<league>[^/?#\s]+)/character/(?P<character>[^/?#\s]+)"
    ),
    # /poe2/profile/{account}/character/{char} — pre-0.5 / league-less form
    re.compile(
        r"poe\.ninja/poe2/profile/(?P<account>[^/?#\s]+)/character/(?P<character>[^/?#\s]+)"
    ),
    # /poe2/builds/{league}/character/{account}/{char}
    re.compile(
        r"poe\.ninja/poe2/builds/(?P<league>[^/?#\s]+)/character/(?P<account>[^/?#\s]+)/(?P<character>[^/?#\s]+)"
    ),
    # /poe2/builds/character/{account}/{char} — legacy
    re.compile(r"poe\.ninja/poe2/builds/character/(?P<account>[^/?#\s]+)/(?P<character>[^/?#\s]+)"),
    # /builds/character/{account}/{char} — PoE1-style legacy
    re.compile(r"poe\.ninja/builds/character/(?P<account>[^/?#\s]+)/(?P<character>[^/?#\s]+)"),
]


def league_slug_to_display(slug: Optional[str]) -> Optional[str]:
    """
    Reverse-map a poe.ninja URL slug to its canonical display name.

    LEAGUE_MAPPINGS lists the canonical full name first for each slug
    (e.g. "Runes of Aldur" before "RoA"), so first match wins. Returns
    None for unknown slugs — callers can pass the raw slug through to
    the fetcher, whose own slug normalisation is a lowercase no-op on it.
    """
    if not slug:
        return None
    slug_lower = slug.lower()
    for display, mapped in PoeNinjaAPI.LEAGUE_MAPPINGS.items():
        if mapped == slug_lower:
            return display
    return None


def parse_poe_ninja_url(url: str) -> Optional[Dict[str, Optional[str]]]:
    """
    Extract account / character / league from any known poe.ninja URL shape.

    Returns a dict with keys ``account``, ``character``, ``league_slug``
    (raw slug from the URL, or None when the URL form has no league
    segment) and ``league`` (display name when the slug is known,
    else None). Returns None when no pattern matches.
    """
    for pattern in _POE_NINJA_URL_PATTERNS:
        match = pattern.search(url)
        if match:
            groups = match.groupdict()
            league_slug = groups.get("league")
            return {
                "account": unquote(groups["account"]),
                "character": unquote(groups["character"]),
                "league_slug": league_slug,
                "league": league_slug_to_display(league_slug),
            }
    return None


class PoeNinjaAPI:
    """
    poe.ninja API client with web scraping fallback
    Fetches character builds, item prices, and meta information
    """

    # League name to URL slug mapping
    LEAGUE_MAPPINGS = {
        # Runes of Aldur variants (current league - Patch 0.5 "Return of the Ancients")
        # Slugs confirmed via /poe2/api/data/index-state on 2026-05-29
        "Runes of Aldur": "runesofaldur",
        "RoA": "runesofaldur",
        "Runes of Aldur Hardcore": "runesofaldurhc",
        "Runes of Aldur HC": "runesofaldurhc",
        "Runes of Aldur SSF": "runesofaldurssf",
        "Runes of Aldur HC SSF": "runesofaldurhcssf",
        "Runes of Aldur Hardcore SSF": "runesofaldurhcssf",
        # Vaal League variants (Fate of the Vaal - previous league)
        "Fate of the Vaal": "vaal",
        "FotV": "vaal",
        "Vaal": "vaal",
        "Vaal Hardcore": "vaalhc",
        "Vaal HC": "vaalhc",
        "Vaal SSF": "vaalssf",
        "Vaal HC SSF": "vaalhcssf",
        "Vaal Hardcore SSF": "vaalhcssf",
        # Abyss League variants
        "Rise of the Abyssal": "abyss",
        "Abyss": "abyss",
        "Abyss Hardcore": "abysshc",
        "Abyss HC": "abysshc",
        "Abyss SSF": "abyssssf",
        "Abyss HC SSF": "abysshcssf",
        "Abyss Hardcore SSF": "abysshcssf",
        # Dawn League variants
        "Dawn of the Hunt": "dawn",
        "Dawn": "dawn",
        "Dawn Hardcore": "dawnhc",
        "Dawn HC": "dawnhc",
        "Dawn SSF": "dawnssf",
        "Dawn HC SSF": "dawnhcssf",
        # Standard leagues
        "Standard": "standard",
        "Hardcore": "hardcore",
        "SSF Standard": "ssf-standard",
        "SSF Hardcore": "ssf-hardcore",
        # Race events (add as discovered)
        "Act 4 Boss Kill Race 3 SSF": "act4bosskillrace3ssf",
    }

    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        cache_manager: Optional[CacheManager] = None,
    ):
        self.base_url = "https://poe.ninja"
        self.api_base = f"{self.base_url}/api/data"
        self.rate_limiter = rate_limiter or RateLimiter(rate_limit=20)
        self.cache_manager = cache_manager
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "PoE2-MCP-Server/1.0",
                "Accept": "application/json, text/html",
            },
        )

    def _get_league_slug(self, league: str) -> str:
        """
        Convert league name to poe.ninja URL slug

        Args:
            league: Full league name (e.g., "Rise of the Abyssal")

        Returns:
            URL slug (e.g., "abyss")
        """
        # Check exact match first
        if league in self.LEAGUE_MAPPINGS:
            return self.LEAGUE_MAPPINGS[league]

        # Check case-insensitive match
        for key, value in self.LEAGUE_MAPPINGS.items():
            if key.lower() == league.lower():
                return value

        # Default: convert to lowercase and replace spaces with hyphens
        return league.lower().replace(" ", "-")

    async def get_character(
        self, account: str, character: str, league: str = "Runes of Aldur"
    ) -> Optional[Dict[str, Any]]:
        """
        RETIRED (#133) — always returns None.

        This method used the pre-0.5 snapshot endpoint
        (``/poe2/api/builds/{version}/character``), which is dead post-0.5
        (404 for any character not in a specific snapshot), with an HTML
        scrape fallback that is equally dead (Astro SPA shells carry no
        embedded data). Both code paths were removed.

        The working per-character fetch is the no-auth profile API flow in
        ``CharacterFetcher.get_character`` (events SSE → model — see #131).
        Use ``list_account_characters`` here for account-level enumeration.
        """
        logger.debug(
            f"PoeNinjaAPI.get_character({account}/{character}) is retired (#133) — "
            f"use CharacterFetcher.get_character (profile API flow)"
        )
        return None

    # ------------------------------------------------------------------
    # Profile API (post-0.5, no auth) — account enumeration + char model.
    # Endpoint map from the 2026-06-02 HAR analysis (#133/#134):
    #   GET /poe2/api/events/characters/{account}            -> SSE {"version": N}
    #   GET /poe2/api/profile/characters/{account}/{N}       -> JSON char list
    #   GET /poe2/api/events/character/{acct}/{slug}/{char}  -> SSE {"version": M}
    #   GET /poe2/api/profile/characters/{acct}/{slug}/{char}/model/{M}
    #                                                        -> {type, charModel}
    # ------------------------------------------------------------------

    async def _read_sse_version(self, url: str) -> Optional[int]:
        """Read the first ``data: {"version": N}`` message from an SSE URL."""
        await self.rate_limiter.acquire()
        try:
            async with self.client.stream("GET", url) as response:
                if response.status_code != 200:
                    logger.warning(f"SSE endpoint returned {response.status_code}: {url}")
                    return None
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        try:
                            return json.loads(line[5:].strip()).get("version")
                        except (json.JSONDecodeError, AttributeError):
                            continue
        except Exception as e:
            logger.warning(f"SSE read failed for {url}: {e}")
        return None

    async def list_account_characters(self, account: str) -> Optional[List[Dict[str, Any]]]:
        """
        Enumerate ALL characters on an account's public poe.ninja profile.

        Two-step profile-API flow: account SSE for the list version, then
        the character-list endpoint. Each item carries name, level, league,
        ``leagueUrl`` (the slug the model endpoint needs), ``className``,
        ``isCurrent``, ``updated``, and a skills summary.

        Returns the list, or None when the account is private/unknown or
        the endpoint shape changed.
        """
        cache_key = f"ninja_char_list_{account}"
        if self.cache_manager:
            cached = await self.cache_manager.get(cache_key)
            if cached:
                return cached

        version = await self._read_sse_version(
            f"{self.base_url}/poe2/api/events/characters/{account}"
        )
        if version is None:
            logger.warning(f"No list version from account events SSE for {account}")
            return None

        await self.rate_limiter.acquire()
        try:
            url = f"{self.base_url}/poe2/api/profile/characters/{account}/{version}"
            response = await self.client.get(url)
            if response.status_code != 200:
                logger.warning(f"Character list returned {response.status_code} for {account}")
                return None
            characters = response.json()
            if not isinstance(characters, list):
                logger.warning(
                    f"Unexpected character-list shape for {account}: {type(characters).__name__}"
                )
                return None
            if self.cache_manager:
                await self.cache_manager.set(cache_key, characters, ttl=600)
            logger.info(f"Enumerated {len(characters)} characters for account {account}")
            return characters
        except Exception as e:
            logger.error(f"Character-list fetch failed for {account}: {e}")
            return None

    async def resolve_character_league(self, account: str, character: str) -> Optional[str]:
        """
        Resolve a character's league slug (``leagueUrl``) via enumeration —
        answers "which league is this character in" without guessing, which
        the model endpoint needs as a path segment.
        """
        characters = await self.list_account_characters(account)
        if not characters:
            return None
        wanted = character.lower().strip()
        for entry in characters:
            if str(entry.get("name", "")).lower() == wanted:
                return entry.get("leagueUrl")
        logger.warning(f"Character {character} not in {account}'s profile list")
        return None

    async def _fetch_char_model(
        self, account: str, league_url: str, character: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch the raw ``{type, charModel}`` blob via the profile API."""
        version = await self._read_sse_version(
            f"{self.base_url}/poe2/api/events/character/{account}/{league_url}/{character}"
        )
        if version is None:
            return None
        await self.rate_limiter.acquire()
        try:
            url = (
                f"{self.base_url}/poe2/api/profile/characters/"
                f"{account}/{league_url}/{character}/model/{version}"
            )
            response = await self.client.get(url)
            if response.status_code != 200:
                logger.warning(f"Model endpoint returned {response.status_code} for {character}")
                return None
            return response.json()
        except Exception as e:
            logger.error(f"Model fetch failed for {character}: {e}")
            return None

    async def get_top_builds(
        self,
        league: str = "Standard",
        class_name: Optional[str] = None,
        skill: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get top builds from poe.ninja ladder

        Args:
            league: League name (e.g., "Rise of the Abyssal", "Standard")
            class_name: Filter by character class
            skill: Filter by main skill
            limit: Maximum number of builds to return

        Returns:
            List of build data dictionaries
        """
        # Get the URL slug for this league
        league_slug = self._get_league_slug(league)

        cache_key = f"ninja_top_builds_{league_slug}_{class_name}_{skill}_{limit}"

        if self.cache_manager:
            cached = await self.cache_manager.get(cache_key)
            if cached:
                return cached

        try:
            await self.rate_limiter.acquire()

            # Use league slug in the URL path
            url = f"{self.base_url}/poe2/builds/{league_slug}"

            logger.info(f"Fetching top builds from: {url}")

            response = await self.client.get(url)

            if response.status_code == 200:
                builds = await self._parse_builds_page(response.text, class_name, skill, limit)

                if builds and self.cache_manager:
                    await self.cache_manager.set(cache_key, builds, ttl=1800)

                logger.info(f"Found {len(builds)} builds from poe.ninja")
                return builds
            else:
                logger.warning(
                    f"poe.ninja builds page returned {response.status_code} for league '{league_slug}'"
                )
                return []

        except Exception as e:
            logger.error(f"Error fetching top builds: {e}")
            return []

    async def _parse_builds_page(
        self, html: str, class_filter: Optional[str], skill_filter: Optional[str], limit: int
    ) -> List[Dict[str, Any]]:
        """Parse builds from HTML page (NUXT data extraction)"""
        try:
            soup = BeautifulSoup(html, "html.parser")
            builds = []

            # poe.ninja uses NUXT, so data is embedded in JavaScript
            # Look for __NUXT__ data
            for script in soup.find_all("script"):
                script_content = script.string
                if not script_content:
                    continue

                # Try to find NUXT data
                if "window.__NUXT__" in script_content or "__NUXT__=" in script_content:
                    try:
                        # Extract JSON from the script
                        start_marker = "__NUXT__="
                        if start_marker in script_content:
                            json_start = script_content.find(start_marker) + len(start_marker)
                            # Find the end - it's usually a semicolon or end of script
                            json_end = script_content.find("</script>", json_start)
                            if json_end == -1:
                                json_end = len(script_content)

                            json_str = script_content[json_start:json_end].strip()
                            if json_str.endswith(";"):
                                json_str = json_str[:-1]

                            # Parse the NUXT data
                            nuxt_data = json.loads(json_str)
                            builds = self._extract_builds_from_nuxt(
                                nuxt_data, class_filter, skill_filter, limit
                            )

                            if builds:
                                return builds

                    except json.JSONDecodeError as e:
                        logger.debug(f"Failed to parse NUXT data: {e}")
                        continue

            # Fallback: Try to find build data in alternative locations
            # Some pages might have data in different formats
            logger.warning("Could not find NUXT data, trying HTML fallback")

            # Look for build listings in HTML
            build_elements = soup.find_all(class_=["build-row", "build-item", "character-row"])

            for elem in build_elements[: limit * 2]:  # Get extra in case of filtering
                build = self._extract_build_info(elem)

                if build:
                    # Apply filters
                    if class_filter and build.get("class") != class_filter:
                        continue
                    if (
                        skill_filter
                        and skill_filter.lower() not in build.get("main_skill", "").lower()
                    ):
                        continue

                    builds.append(build)

                    if len(builds) >= limit:
                        break

            return builds

        except Exception as e:
            logger.error(f"Build parsing error: {e}")
            return []

    def _extract_builds_from_nuxt(
        self, nuxt_data: Dict, class_filter: Optional[str], skill_filter: Optional[str], limit: int
    ) -> List[Dict[str, Any]]:
        """Extract build data from NUXT structure"""
        builds = []

        try:
            # NUXT data structure varies, but typically:
            # __NUXT__.data[0] or __NUXT__.state
            # Navigate through the data structure to find builds/characters

            # Try different paths
            data_sources = [
                nuxt_data.get("data", []),
                nuxt_data.get("state", {}).get("builds", []),
                nuxt_data.get("state", {}).get("characters", []),
            ]

            # Also check nested structures
            if isinstance(nuxt_data, dict):
                for key in nuxt_data:
                    val = nuxt_data[key]
                    if isinstance(val, list) and len(val) > 0:
                        # Check if this looks like build data
                        if isinstance(val[0], dict) and ("character" in val[0] or "name" in val[0]):
                            data_sources.append(val)

            for data_source in data_sources:
                if not data_source:
                    continue

                # Handle list of builds
                if isinstance(data_source, list):
                    for item in data_source:
                        if isinstance(item, dict):
                            build = self._normalize_build_data(item)

                            if build:
                                # Apply filters
                                if (
                                    class_filter
                                    and build.get("class", "").lower() != class_filter.lower()
                                ):
                                    continue
                                if (
                                    skill_filter
                                    and skill_filter.lower()
                                    not in build.get("main_skill", "").lower()
                                ):
                                    continue

                                builds.append(build)

                                if len(builds) >= limit:
                                    return builds

                # Handle nested structure
                elif isinstance(data_source, dict):
                    for key, value in data_source.items():
                        if isinstance(value, list):
                            for item in value:
                                if isinstance(item, dict):
                                    build = self._normalize_build_data(item)

                                    if build:
                                        # Apply filters
                                        if (
                                            class_filter
                                            and build.get("class", "").lower()
                                            != class_filter.lower()
                                        ):
                                            continue
                                        if (
                                            skill_filter
                                            and skill_filter.lower()
                                            not in build.get("main_skill", "").lower()
                                        ):
                                            continue

                                        builds.append(build)

                                        if len(builds) >= limit:
                                            return builds

        except Exception as e:
            logger.error(f"Error extracting builds from NUXT data: {e}")

        return builds

    def _normalize_build_data(self, raw_data: Dict) -> Optional[Dict[str, Any]]:
        """Normalize build data from various sources"""
        try:
            # Try to extract common fields
            build = {
                "account": raw_data.get("account", raw_data.get("accountName", "")),
                "character": raw_data.get(
                    "character", raw_data.get("name", raw_data.get("characterName", ""))
                ),
                "class": raw_data.get(
                    "class", raw_data.get("className", raw_data.get("ascendancy", ""))
                ),
                "level": raw_data.get("level", 0),
                "main_skill": raw_data.get("mainSkill", raw_data.get("skill", "")),
                "dps": raw_data.get("dps", 0),
            }

            # Skip if we don't have at least character name
            if not build["character"]:
                return None

            return build

        except Exception as e:
            logger.debug(f"Failed to normalize build data: {e}")
            return None

    def _extract_build_info(self, element) -> Optional[Dict[str, Any]]:
        """Extract build information from HTML element"""
        try:
            build = {
                "account": element.get("data-account", ""),
                "character": element.get("data-character", ""),
                "class": "",
                "level": 0,
                "main_skill": "",
                "dps": 0,
            }

            # Try to extract from data attributes or text content
            class_elem = element.find(class_=["class", "build-class"])
            if class_elem:
                build["class"] = class_elem.text.strip()

            level_elem = element.find(class_=["level", "build-level"])
            if level_elem:
                try:
                    build["level"] = int(level_elem.text.strip())
                except ValueError:
                    pass

            return build if build["account"] or build["character"] else None

        except Exception as e:
            logger.debug(f"Failed to extract build info: {e}")
            return None

    async def get_item_prices(
        self, league: str = "Standard", item_type: str = "UniqueWeapon"
    ) -> List[Dict[str, Any]]:
        """
        Get item prices from poe.ninja economy API

        Args:
            league: League name
            item_type: Type of items (UniqueWeapon, UniqueArmour, etc.)

        Returns:
            List of items with prices
        """
        cache_key = f"ninja_prices_{league}_{item_type}"

        if self.cache_manager:
            cached = await self.cache_manager.get(cache_key)
            if cached:
                return cached

        try:
            await self.rate_limiter.acquire()

            url = f"{self.api_base}/itemoverview"
            params = {"league": league, "type": item_type}

            response = await self.client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                items = data.get("lines", [])

                if items and self.cache_manager:
                    await self.cache_manager.set(cache_key, items, ttl=3600)

                return items

            return []

        except Exception as e:
            logger.error(f"Error fetching item prices: {e}")
            return []

    async def get_pob_import(self, account: str, character: str) -> Optional[str]:
        """
        Get the Path of Building export code for a character.

        Rewired (#133): the old ``/poe2/api/builds/pob/import`` snapshot
        endpoint is dead post-0.5. The export now comes from the profile
        API's character model — ``charModel.pathOfBuildingExport`` — via:
        enumeration (league resolution) → char SSE (version) → model.

        Args:
            account: Path of Exile account name
            character: Character name (league auto-resolved from the
                account's profile list)

        Returns:
            Base64-encoded PoB build code, or None when the account is
            private, the character is unknown, or no export is embedded.
        """
        cache_key = f"ninja_pob_{account}_{character}"

        if self.cache_manager:
            cached = await self.cache_manager.get(cache_key)
            if cached:
                logger.info(f"✅ Cache hit for PoB code: {character}")
                return cached

        try:
            logger.info(f"📦 Fetching PoB code via profile API: {character} (Account: {account})")

            league_url = await self.resolve_character_league(account, character)
            if not league_url:
                logger.warning(
                    f"⚠️ Could not resolve league for {character} — account "
                    f"private or character not on {account}'s profile"
                )
                return None

            model = await self._fetch_char_model(account, league_url, character)
            if not model:
                return None

            char_model = model.get("charModel") or {}
            pob_code = char_model.get("pathOfBuildingExport")

            if pob_code:
                logger.info(f"✅ Got PoB export from charModel for {character}")
                if self.cache_manager:
                    await self.cache_manager.set(cache_key, pob_code, ttl=3600)
                return pob_code

            logger.warning(
                f"⚠️ Character model for {character} has no pathOfBuildingExport "
                f"(keys: {list(char_model.keys())[:10]})"
            )
            return None

        except Exception as e:
            logger.error(f"❌ PoB export fetch failed: {e}", exc_info=True)
            return None

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
