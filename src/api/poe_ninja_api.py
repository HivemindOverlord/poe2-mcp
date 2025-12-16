"""
poe.ninja API Client with Web Scraping Fallback
Fetches character data, build rankings, and economy data from poe.ninja
"""

import httpx
import json
import logging
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
from datetime import datetime

try:
    from ..api.rate_limiter import RateLimiter
    from ..api.cache_manager import CacheManager
except ImportError:
    from src.api.rate_limiter import RateLimiter
    from src.api.cache_manager import CacheManager

logger = logging.getLogger(__name__)


class PoeNinjaAPI:
    """
    poe.ninja API client with web scraping fallback
    Fetches character builds, item prices, and meta information
    """

    # League name to URL slug mapping
    LEAGUE_MAPPINGS = {
        # Abyss League variants
        "Rise of the Abyssal": "abyss",
        "Abyss": "abyss",
        "Abyss Hardcore": "abysshc",
        "Abyss HC": "abysshc",
        "Abyss SSF": "abyssssf",
        "Abyss HC SSF": "abysshcssf",
        "Abyss Hardcore SSF": "abysshcssf",

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
        cache_manager: Optional[CacheManager] = None
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
            }
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

    async def get_character(self, account: str, character: str, league: str = "Abyss") -> Optional[Dict[str, Any]]:
        """
        Fetch character from poe.ninja using their hidden API

        Args:
            account: Path of Exile account name
            character: Character name
            league: League name (default: "Abyss")

        Returns:
            Character data dictionary or None if not found
        """
        cache_key = f"ninja_character_{account}_{character}_{league}"

        # Check cache first
        if self.cache_manager:
            cached = await self.cache_manager.get(cache_key)
            if cached:
                logger.info(f"✅ Cache hit for character {character} ({league})")
                return cached

        try:
            # Rate limit
            await self.rate_limiter.acquire()

            logger.info(f"🔍 Fetching character: {character} (Account: {account}, League: {league})")

            # Use the discovered hidden API endpoint
            char_data = await self._fetch_character_from_api(account, character, league)

            if char_data and self.cache_manager:
                await self.cache_manager.set(cache_key, char_data, ttl=3600)
                logger.info(f"✅ Successfully fetched and cached character {character}")

            return char_data

        except Exception as e:
            logger.error(f"❌ Error fetching character from poe.ninja: {e}", exc_info=True)
            return None

    async def _get_index_state(self) -> Optional[Dict[str, Any]]:
        """
        Fetch the index state which contains snapshot versions for all leagues

        Returns:
            Index state with snapshot versions or None if failed
        """
        try:
            url = f"{self.base_url}/poe2/api/data/index-state"
            logger.debug(f"Fetching index state from: {url}")

            response = await self.client.get(url)

            if response.status_code == 200:
                data = response.json()
                logger.debug(f"✅ Got index state with {len(data.get('snapshotVersions', []))} snapshot versions")
                return data
            else:
                logger.warning(f"⚠️ Index state returned {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"❌ Failed to fetch index state: {e}")
            return None

    async def _fetch_character_from_api(self, account: str, character: str, league: str) -> Optional[Dict[str, Any]]:
        """
        Fetch character using the discovered hidden API

        API Endpoint: /poe2/api/builds/{version}/character
        Parameters: account, name, overview

        Args:
            account: Account name
            character: Character name
            league: League name

        Returns:
            Character data dictionary or None if not found
        """
        try:
            # Step 1: Get index state to find the snapshot version for this league
            index_state = await self._get_index_state()
            if not index_state:
                logger.warning("⚠️ Could not get index state, falling back to HTML scraping")
                return await self._scrape_character_page(account, character, league)

            # Step 2: Find the snapshot version for our league
            league_slug = self._get_league_slug(league)
            snapshot = None

            for snap in index_state.get("snapshotVersions", []):
                if snap.get("url") == league_slug:
                    snapshot = snap
                    break

            if not snapshot:
                logger.warning(f"⚠️ No snapshot found for league '{league}' (slug: '{league_slug}')")
                logger.warning(f"   Available leagues: {[s.get('url') for s in index_state.get('snapshotVersions', [])]}")
                return await self._scrape_character_page(account, character, league)

            version = snapshot.get("version")
            overview = snapshot.get("snapshotName")

            logger.info(f"📡 Using snapshot version: {version}, overview: {overview}")

            # Step 3: Call the character API
            url = f"{self.base_url}/poe2/api/builds/{version}/character"
            params = {
                "account": account,
                "name": character,
                "overview": overview
            }

            logger.debug(f"Calling API: {url}")
            logger.debug(f"Parameters: {params}")

            response = await self.client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Successfully fetched character from API")
                logger.debug(f"   Character: {data.get('name')}, Level: {data.get('level', 'Unknown')}, Class: {data.get('class', 'Unknown')}")
                return self._normalize_api_character_data(data)

            elif response.status_code == 404:
                logger.warning(f"⚠️ Character not found (404)")
                return None

            else:
                logger.warning(f"⚠️ API returned {response.status_code}")
                logger.debug(f"   Response: {response.text[:200]}")
                return await self._scrape_character_page(account, character, league)

        except Exception as e:
            logger.error(f"❌ API fetch failed: {e}", exc_info=True)
            logger.info("   Falling back to HTML scraping")
            return await self._scrape_character_page(account, character, league)

    def _normalize_api_character_data(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize character data from the API to match our expected format

        Args:
            api_data: Raw data from poe.ninja API

        Returns:
            Normalized character data with all stats
        """
        defensive_stats = api_data.get("defensiveStats", {})

        # Log what we're receiving for debugging
        logger.debug(f"🔍 Normalizing API data - defensiveStats: {len(defensive_stats)} fields")
        logger.debug(f"   Life: {defensive_stats.get('life')}, ES: {defensive_stats.get('energyShield')}, EHP: {defensive_stats.get('effectiveHealthPool')}")
        logger.debug(f"   Resistances - Fire: {defensive_stats.get('fireResistance')}, Cold: {defensive_stats.get('coldResistance')}, Lightning: {defensive_stats.get('lightningResistance')}")

        # Map all defensive stats
        stats_dict = {
            # Core defenses
            "life": defensive_stats.get("life", 0),
            "energy_shield": defensive_stats.get("energyShield", 0),
            "mana": defensive_stats.get("mana", 0),
            "spirit": defensive_stats.get("spirit", 0),
            "evasion": defensive_stats.get("evasionRating", 0),
            "armor": defensive_stats.get("armour", 0),

            # Attributes
            "strength": defensive_stats.get("strength", 0),
            "dexterity": defensive_stats.get("dexterity", 0),
            "intelligence": defensive_stats.get("intelligence", 0),

            # Resistances
            "fire_res": defensive_stats.get("fireResistance", 0),
            "cold_res": defensive_stats.get("coldResistance", 0),
            "lightning_res": defensive_stats.get("lightningResistance", 0),
            "chaos_res": defensive_stats.get("chaosResistance", 0),
            "fire_res_overcap": defensive_stats.get("fireResistanceOverCap", 0),
            "cold_res_overcap": defensive_stats.get("coldResistanceOverCap", 0),
            "lightning_res_overcap": defensive_stats.get("lightningResistanceOverCap", 0),
            "chaos_res_overcap": defensive_stats.get("chaosResistanceOverCap", 0),

            # EHP and Maximum Hit Taken
            "effective_health_pool": defensive_stats.get("effectiveHealthPool", 0),
            "physical_max_hit": defensive_stats.get("physicalMaximumHitTaken", 0),
            "fire_max_hit": defensive_stats.get("fireMaximumHitTaken", 0),
            "cold_max_hit": defensive_stats.get("coldMaximumHitTaken", 0),
            "lightning_max_hit": defensive_stats.get("lightningMaximumHitTaken", 0),
            "chaos_max_hit": defensive_stats.get("chaosMaximumHitTaken", 0),
            "lowest_max_hit": defensive_stats.get("lowestMaximumHitTaken", 0),

            # Charges
            "endurance_charges": defensive_stats.get("enduranceCharges", 0),
            "frenzy_charges": defensive_stats.get("frenzyCharges", 0),
            "power_charges": defensive_stats.get("powerCharges", 0),

            # Avoidance & Mitigation
            "block_chance": defensive_stats.get("blockChance", 0),
            "spell_block_chance": defensive_stats.get("spellBlockChance", 0),
            "spell_suppression": defensive_stats.get("spellSuppressionChance", 0),
            # NOTE: spell_dodge removed - PoE2 uses evasion for all hits, not dodge

            # Other stats
            "movement_speed": defensive_stats.get("movementSpeed", 0),
            "item_rarity": defensive_stats.get("itemRarity", 0),

            # Physical damage conversion
            "physical_taken_as": defensive_stats.get("physicalTakenAs", {
                "physical": 100, "fire": 0, "cold": 0, "lightning": 0, "chaos": 0
            }),
        }

        # Extract skill DPS data
        skill_dps = []
        for skill in api_data.get("skills", []):
            for dps_entry in skill.get("dps", []):
                damage_types = dps_entry.get("damageTypes", [0, 0, 0, 0, 0])
                skill_dps.append({
                    "skill_name": dps_entry.get("name", "Unknown"),
                    "total_dps": dps_entry.get("dps", 0),
                    "dot_dps": dps_entry.get("dotDps", 0),
                    "damage_types": damage_types,
                    "damage_breakdown": {
                        "physical": damage_types[0] if len(damage_types) > 0 else 0,
                        "fire": damage_types[1] if len(damage_types) > 1 else 0,
                        "cold": damage_types[2] if len(damage_types) > 2 else 0,
                        "lightning": damage_types[3] if len(damage_types) > 3 else 0,
                        "chaos": damage_types[4] if len(damage_types) > 4 else 0,
                    }
                })

        # Build normalized data structure
        normalized = {
            "name": api_data.get("name", "Unknown"),
            "account": api_data.get("account", "Unknown"),
            "class": api_data.get("class", "Unknown"),
            "level": api_data.get("level", 0),
            "league": api_data.get("league", "Unknown"),

            # Items with details
            "items": [
                {
                    "slot": item.get("itemSlot", 0),
                    "name": item.get("itemData", {}).get("name", ""),
                    "type_line": item.get("itemData", {}).get("typeLine", ""),
                    "base_type": item.get("itemData", {}).get("baseType", ""),
                    "item_level": item.get("itemData", {}).get("ilvl", 0),
                    "rarity": item.get("itemData", {}).get("frameType", 0),
                    "corrupted": item.get("itemData", {}).get("corrupted", False),
                    "icon": item.get("itemData", {}).get("icon", ""),
                    "mods": {
                        "implicit": item.get("itemData", {}).get("implicitMods", []),
                        "explicit": item.get("itemData", {}).get("explicitMods", []),
                        "crafted": item.get("itemData", {}).get("craftedMods", []),
                        "enchant": item.get("itemData", {}).get("enchantMods", [])
                    }
                }
                for item in api_data.get("items", [])
            ],

            # Skills (raw)
            "skills": api_data.get("skills", []),

            # Skill DPS (normalized)
            "skill_dps": skill_dps,

            # Passives
            "passives": api_data.get("passiveSelection", []),
            "passive_set_1": api_data.get("passiveSelectionSet1", []),
            "passive_set_2": api_data.get("passiveSelectionSet2", []),

            # Keystones
            "keystones": [
                {
                    "name": keystone.get("name", "Unknown"),
                    "icon": keystone.get("icon", ""),
                    "stats": keystone.get("stats", [])
                }
                for keystone in api_data.get("keystones", [])
            ],

            # Flasks
            "flasks": [
                {
                    "name": flask.get("itemData", {}).get("typeLine", "Unknown Flask"),
                    "base_type": flask.get("itemData", {}).get("baseType", ""),
                    "item_level": flask.get("itemData", {}).get("ilvl", 0),
                    "mods": flask.get("itemData", {}).get("explicitMods", []),
                    "icon": flask.get("itemData", {}).get("icon", "")
                }
                for flask in api_data.get("flasks", [])
            ],

            # Jewels
            "jewels": [
                {
                    "name": jewel.get("itemData", {}).get("name") or jewel.get("itemData", {}).get("typeLine", "Unknown Jewel"),
                    "base_type": jewel.get("itemData", {}).get("baseType", ""),
                    "item_level": jewel.get("itemData", {}).get("ilvl", 0),
                    "mods": jewel.get("itemData", {}).get("explicitMods", []),
                    "icon": jewel.get("itemData", {}).get("icon", ""),
                    "position": {
                        "x": jewel.get("itemData", {}).get("x", 0),
                        "y": jewel.get("itemData", {}).get("y", 0)
                    }
                }
                for jewel in api_data.get("jewels", [])
            ],

            # Path of Building export
            "pob_export": api_data.get("pathOfBuildingExport", ""),

            # Stats (nested format)
            "stats": stats_dict,

            # Metadata
            "source": "poe.ninja API",
            "fetched_at": datetime.utcnow().isoformat(),
            "weapon_swap_active": api_data.get("useSecondWeaponSet", False)
        }

        # ALSO add stats at top level for tools that expect them there
        normalized.update(stats_dict)

        logger.info(f"✅ Normalized character data:")
        logger.info(f"   Defenses - Life: {stats_dict.get('life')}, ES: {stats_dict.get('energy_shield')}, EHP: {stats_dict.get('effective_health_pool')}")
        logger.info(f"   Skills with DPS: {len(skill_dps)}")
        logger.info(f"   Keystones: {len(normalized['keystones'])}")
        logger.info(f"   Items: {len(normalized['items'])}, Flasks: {len(normalized['flasks'])}, Jewels: {len(normalized['jewels'])}")

        return normalized

    async def _scrape_character_page(self, account: str, character: str, league: str = "Abyss") -> Optional[Dict[str, Any]]:
        """
        Scrape character data from poe.ninja profile page

        Args:
            account: Account name
            character: Character name
            league: League name (default: "Abyss")

        Returns:
            Parsed character data
        """
        try:
            # Convert league to URL slug (e.g., "Abyss" -> "abyss")
            league_slug = self._get_league_slug(league)

            # CRITICAL FIX: Based on HAR file analysis, the correct URL format includes league
            # Format: https://poe.ninja/poe2/builds/{league}/character/{account}/{character}
            urls = [
                f"{self.base_url}/poe2/builds/{league_slug}/character/{account}/{character}",
                f"{self.base_url}/builds/{league_slug}/character/{account}/{character}",  # Fallback without poe2
            ]

            logger.info(f"📡 Attempting to fetch from poe.ninja with league '{league}' (slug: '{league_slug}')")

            for i, url in enumerate(urls, 1):
                try:
                    logger.debug(f"  [{i}/{len(urls)}] Trying URL: {url}")
                    response = await self.client.get(url)

                    logger.debug(f"  [{i}/{len(urls)}] Response: {response.status_code}")

                    if response.status_code == 200:
                        logger.info(f"✅ Successfully fetched from: {url}")
                        return await self._parse_character_html(response.text, account, character)
                    else:
                        logger.debug(f"  [{i}/{len(urls)}] Non-200 status: {response.status_code}")

                except Exception as e:
                    logger.debug(f"  [{i}/{len(urls)}] Exception: {e}")
                    continue

            logger.warning(f"❌ Could not fetch character {character} from any poe.ninja URL")
            logger.warning(f"   Tried {len(urls)} URLs with league slug '{league_slug}'")
            return None

        except Exception as e:
            logger.error(f"❌ Character scraping error: {e}", exc_info=True)
            return None

    async def _parse_character_html(self, html: str, account: str, character: str) -> Optional[Dict[str, Any]]:
        """
        Parse character data from HTML page

        Args:
            html: HTML content
            account: Account name
            character: Character name

        Returns:
            Parsed character data
        """
        try:
            logger.debug(f"📄 Parsing HTML (length: {len(html)} chars)")
            soup = BeautifulSoup(html, 'html.parser')

            # Look for embedded JSON data in script tags
            scripts = soup.find_all('script')
            logger.debug(f"🔎 Found {len(scripts)} script tags in HTML")

            for i, script in enumerate(scripts, 1):
                if script.string and ('window.__NUXT__' in script.string or 'window.__data' in script.string):
                    try:
                        # Extract JSON data
                        script_content = script.string

                        # Try NUXT data first
                        if 'window.__NUXT__' in script_content:
                            logger.debug(f"  [Script {i}] Found window.__NUXT__ data")
                            json_start = script_content.find('window.__NUXT__=') + len('window.__NUXT__=')
                            json_end = script_content.find('</script>', json_start)
                            json_str = script_content[json_start:json_end].strip()
                            if json_str.endswith(';'):
                                json_str = json_str[:-1]

                            logger.debug(f"  [Script {i}] Parsing JSON (length: {len(json_str)} chars)")
                            data = json.loads(json_str)
                            logger.info(f"✅ Successfully parsed window.__NUXT__ JSON")
                            return self._extract_character_from_nuxt(data, account, character)

                        # Try __data format
                        elif 'window.__data' in script_content:
                            logger.debug(f"  [Script {i}] Found window.__data")
                            json_start = script_content.find('window.__data=') + len('window.__data=')
                            json_end = script_content.find(';', json_start)
                            json_str = script_content[json_start:json_end].strip()

                            logger.debug(f"  [Script {i}] Parsing JSON (length: {len(json_str)} chars)")
                            data = json.loads(json_str)
                            logger.info(f"✅ Successfully parsed window.__data JSON")
                            return self._extract_character_from_data(data, account, character)

                    except json.JSONDecodeError as e:
                        logger.warning(f"  [Script {i}] Failed to parse JSON: {e}")
                        continue

            # Fallback: parse HTML structure directly
            logger.warning(f"⚠️ No embedded JSON found, falling back to HTML parsing")
            return self._parse_character_from_html(soup, account, character)

        except Exception as e:
            logger.error(f"❌ HTML parsing error: {e}", exc_info=True)
            return None

    def _extract_character_from_nuxt(self, data: Dict, account: str, character: str) -> Dict[str, Any]:
        """Extract character data from NUXT format"""
        try:
            # Navigate NUXT data structure
            if 'data' in data:
                char_data = data['data'][0] if isinstance(data['data'], list) else data['data']
            else:
                char_data = data

            return {
                "name": character,
                "account": account,
                "class": char_data.get("class", "Unknown"),
                "level": char_data.get("level", 0),
                "league": char_data.get("league", "Unknown"),
                "items": char_data.get("items", []),
                "skills": char_data.get("skills", []),
                "passives": char_data.get("passiveSkills", []),
                "stats": char_data.get("stats", {}),
                "source": "poe.ninja",
                "fetched_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error extracting NUXT data: {e}")
            return self._create_minimal_character(account, character)

    def _extract_character_from_data(self, data: Dict, account: str, character: str) -> Dict[str, Any]:
        """Extract character data from __data format"""
        return {
            "name": character,
            "account": account,
            "class": data.get("class", "Unknown"),
            "level": data.get("level", 0),
            "league": data.get("league", "Unknown"),
            "items": data.get("items", []),
            "skills": data.get("skills", []),
            "passives": data.get("passives", []),
            "stats": data.get("stats", {}),
            "source": "poe.ninja",
            "fetched_at": datetime.utcnow().isoformat()
        }

    def _parse_character_from_html(self, soup: BeautifulSoup, account: str, character: str) -> Dict[str, Any]:
        """Parse character data directly from HTML structure (fallback)"""
        try:
            # Try to extract basic info from HTML
            char_data = self._create_minimal_character(account, character)

            # Look for character level
            level_elem = soup.find(class_=['level', 'character-level'])
            if level_elem:
                try:
                    char_data["level"] = int(level_elem.text.strip())
                except ValueError:
                    pass

            # Look for character class
            class_elem = soup.find(class_=['class', 'character-class'])
            if class_elem:
                char_data["class"] = class_elem.text.strip()

            return char_data

        except Exception as e:
            logger.error(f"HTML structure parsing error: {e}")
            return self._create_minimal_character(account, character)

    def _create_minimal_character(self, account: str, character: str) -> Dict[str, Any]:
        """Create minimal character data structure"""
        return {
            "name": character,
            "account": account,
            "class": "Unknown",
            "level": 0,
            "league": "Unknown",
            "items": [],
            "skills": [],
            "passives": [],
            "stats": {},
            "source": "poe.ninja (minimal)",
            "fetched_at": datetime.utcnow().isoformat()
        }

    async def get_top_builds(
        self,
        league: str = "Standard",
        class_name: Optional[str] = None,
        skill: Optional[str] = None,
        limit: int = 10
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
                logger.warning(f"poe.ninja builds page returned {response.status_code} for league '{league_slug}'")
                return []

        except Exception as e:
            logger.error(f"Error fetching top builds: {e}")
            return []

    async def _parse_builds_page(
        self,
        html: str,
        class_filter: Optional[str],
        skill_filter: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Parse builds from HTML page (NUXT data extraction)"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            builds = []

            # poe.ninja uses NUXT, so data is embedded in JavaScript
            # Look for __NUXT__ data
            for script in soup.find_all('script'):
                script_content = script.string
                if not script_content:
                    continue

                # Try to find NUXT data
                if 'window.__NUXT__' in script_content or '__NUXT__=' in script_content:
                    try:
                        # Extract JSON from the script
                        start_marker = '__NUXT__='
                        if start_marker in script_content:
                            json_start = script_content.find(start_marker) + len(start_marker)
                            # Find the end - it's usually a semicolon or end of script
                            json_end = script_content.find('</script>', json_start)
                            if json_end == -1:
                                json_end = len(script_content)

                            json_str = script_content[json_start:json_end].strip()
                            if json_str.endswith(';'):
                                json_str = json_str[:-1]

                            # Parse the NUXT data
                            nuxt_data = json.loads(json_str)
                            builds = self._extract_builds_from_nuxt(nuxt_data, class_filter, skill_filter, limit)

                            if builds:
                                return builds

                    except json.JSONDecodeError as e:
                        logger.debug(f"Failed to parse NUXT data: {e}")
                        continue

            # Fallback: Try to find build data in alternative locations
            # Some pages might have data in different formats
            logger.warning("Could not find NUXT data, trying HTML fallback")

            # Look for build listings in HTML
            build_elements = soup.find_all(class_=['build-row', 'build-item', 'character-row'])

            for elem in build_elements[:limit * 2]:  # Get extra in case of filtering
                build = self._extract_build_info(elem)

                if build:
                    # Apply filters
                    if class_filter and build.get("class") != class_filter:
                        continue
                    if skill_filter and skill_filter.lower() not in build.get("main_skill", "").lower():
                        continue

                    builds.append(build)

                    if len(builds) >= limit:
                        break

            return builds

        except Exception as e:
            logger.error(f"Build parsing error: {e}")
            return []

    def _extract_builds_from_nuxt(
        self,
        nuxt_data: Dict,
        class_filter: Optional[str],
        skill_filter: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Extract build data from NUXT structure"""
        builds = []

        try:
            # NUXT data structure varies, but typically:
            # __NUXT__.data[0] or __NUXT__.state
            # Navigate through the data structure to find builds/characters

            # Try different paths
            data_sources = [
                nuxt_data.get('data', []),
                nuxt_data.get('state', {}).get('builds', []),
                nuxt_data.get('state', {}).get('characters', []),
            ]

            # Also check nested structures
            if isinstance(nuxt_data, dict):
                for key in nuxt_data:
                    val = nuxt_data[key]
                    if isinstance(val, list) and len(val) > 0:
                        # Check if this looks like build data
                        if isinstance(val[0], dict) and ('character' in val[0] or 'name' in val[0]):
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
                                if class_filter and build.get("class", "").lower() != class_filter.lower():
                                    continue
                                if skill_filter and skill_filter.lower() not in build.get("main_skill", "").lower():
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
                                        if class_filter and build.get("class", "").lower() != class_filter.lower():
                                            continue
                                        if skill_filter and skill_filter.lower() not in build.get("main_skill", "").lower():
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
                "character": raw_data.get("character", raw_data.get("name", raw_data.get("characterName", ""))),
                "class": raw_data.get("class", raw_data.get("className", raw_data.get("ascendancy", ""))),
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
                "dps": 0
            }

            # Try to extract from data attributes or text content
            class_elem = element.find(class_=['class', 'build-class'])
            if class_elem:
                build["class"] = class_elem.text.strip()

            level_elem = element.find(class_=['level', 'build-level'])
            if level_elem:
                try:
                    build["level"] = int(level_elem.text.strip())
                except ValueError:
                    pass

            return build if build["account"] or build["character"] else None

        except Exception as e:
            logger.debug(f"Failed to extract build info: {e}")
            return None

    async def get_item_prices(self, league: str = "Standard", item_type: str = "UniqueWeapon") -> List[Dict[str, Any]]:
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
            params = {
                "league": league,
                "type": item_type
            }

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
        Get Path of Building import code for a character using poe.ninja's hidden API

        This endpoint returns a PoB code that can be imported into Path of Building

        Args:
            account: Path of Exile account name
            character: Character name

        Returns:
            Base64-encoded PoB build code or None if not found

        Example:
            >>> api = PoeNinjaAPI()
            >>> pob_code = await api.get_pob_import("Tomawar40-2671", "DoesFireWorkGoodNow")
            >>> print(pob_code)
            'eJyLjgUAARUAuQ==' # Base64 PoB code
        """
        cache_key = f"ninja_pob_{account}_{character}"

        # Check cache first
        if self.cache_manager:
            cached = await self.cache_manager.get(cache_key)
            if cached:
                logger.info(f"✅ Cache hit for PoB code: {character}")
                return cached

        try:
            # Rate limit
            await self.rate_limiter.acquire()

            logger.info(f"📦 Fetching PoB code for character: {character} (Account: {account})")

            # Call the discovered PoB import API
            url = f"{self.base_url}/poe2/api/builds/pob/import"
            params = {
                "accountName": account,
                "characterName": character
            }

            logger.debug(f"Calling PoB API: {url}")
            logger.debug(f"Parameters: {params}")

            # Add referer header to appear as if coming from character page
            headers = {
                "Referer": f"{self.base_url}/poe2/builds/character/{account}/{character}",
                "Accept": "application/json",
            }

            response = await self.client.get(url, params=params, headers=headers)

            if response.status_code == 200:
                data = response.json()

                # The API should return a PoB code
                # Based on typical poe.ninja API structure, it might be in data['pob'] or data['code']
                pob_code = data.get("pob") or data.get("code") or data.get("build")

                if pob_code:
                    logger.info(f"✅ Successfully fetched PoB code for {character}")

                    if self.cache_manager:
                        await self.cache_manager.set(cache_key, pob_code, ttl=3600)

                    return pob_code
                else:
                    logger.warning(f"⚠️ PoB API returned success but no code found")
                    logger.debug(f"   Response data keys: {list(data.keys())}")
                    # Return the full data in case it's in a different format
                    return data

            elif response.status_code == 404:
                logger.warning(f"⚠️ Character not found for PoB import (404)")
                return None

            else:
                logger.warning(f"⚠️ PoB API returned {response.status_code}")
                logger.debug(f"   Response: {response.text[:200]}")
                return None

        except Exception as e:
            logger.error(f"❌ PoB import API failed: {e}", exc_info=True)
            return None

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
