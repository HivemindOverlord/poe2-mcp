"""
Path of Exile Trade API Client
Searches the official trade market for items

Enhanced with gear evaluation for intelligent upgrade recommendations.
"""

import httpx
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    from ..config import settings
    from .rate_limiter import RateLimiter
    from .cache_manager import CacheManager
    from ..analyzer.gear_evaluator import GearEvaluator, GearStats, UpgradeRecommendation
except ImportError:
    from src.config import settings
    from src.api.rate_limiter import RateLimiter
    from src.api.cache_manager import CacheManager
    from src.analyzer.gear_evaluator import GearEvaluator, GearStats, UpgradeRecommendation

logger = logging.getLogger(__name__)


class TradeAPI:
    """
    Official Path of Exile Trade API client
    Searches for items on the trade market
    """

    def __init__(
        self,
        cache_manager: Optional[CacheManager] = None,
        rate_limiter: Optional[RateLimiter] = None,
        poesessid: Optional[str] = None
    ):
        self.base_url = "https://www.pathofexile.com"
        self.cache_manager = cache_manager
        self.rate_limiter = rate_limiter or RateLimiter(rate_limit=2)  # Very conservative for trade API

        # Use provided poesessid, or fall back to config
        self.poesessid = poesessid or settings.POESESSID

        if not self.poesessid:
            logger.warning(
                "No POESESSID cookie configured. Trade API searches may be limited or fail.\n"
                "Use the 'setup_trade_auth' MCP tool for automated setup.\n"
                "Or see .env.example for manual cookie extraction instructions."
            )

        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0",
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.5",
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "https://www.pathofexile.com",
                "DNT": "1",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
            }
        )

        # Add session cookie if provided
        if self.poesessid:
            self.client.cookies.set("POESESSID", self.poesessid, domain="www.pathofexile.com")

    async def search_items(
        self,
        league: str,
        filters: Dict[str, Any],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for items on the trade market

        Args:
            league: League name (e.g., "Abyss", "Standard")
            filters: Search filters (mods, stats, type, etc.)
            limit: Maximum number of results

        Returns:
            List of item listings with pricing and details
        """
        try:
            await self.rate_limiter.acquire()

            # Build search query
            query = self._build_search_query(filters)

            # Perform search - Note: /api/trade2/search/poe2/{league}
            search_url = f"{self.base_url}/api/trade2/search/poe2/{league}"

            # Add referer header for this specific request
            headers = {"Referer": f"{self.base_url}/trade2/search/poe2/{league}"}

            logger.info(f"Searching trade market in {league}")
            logger.debug(f"Query: {query}")

            response = await self.client.post(search_url, json=query, headers=headers)
            response.raise_for_status()

            search_result = response.json()
            result_ids = search_result.get("result", [])[:limit]
            query_id = search_result.get("id")  # Get query ID for fetching

            if not result_ids:
                logger.info("No items found matching criteria")
                return []

            logger.info(f"Found {len(result_ids)} items, fetching details...")

            # Fetch item details
            await asyncio.sleep(0.5)  # Rate limiting between requests
            items = await self._fetch_item_details(result_ids, query_id)

            return items

        except httpx.HTTPStatusError as e:
            logger.error(f"Trade API HTTP error: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Trade API error: {e}")
            return []

    async def _fetch_item_details(self, item_ids: List[str], query_id: str = None) -> List[Dict[str, Any]]:
        """Fetch full details for items by their IDs"""
        try:
            await self.rate_limiter.acquire()

            # Join IDs with commas
            id_string = ",".join(item_ids[:10])  # Max 10 at a time

            # PoE2 trade API uses /api/trade2/fetch/
            fetch_url = f"{self.base_url}/api/trade2/fetch/{id_string}"

            # Add query parameter if we have a query_id
            if query_id:
                fetch_url += f"?query={query_id}"

            response = await self.client.get(fetch_url)
            response.raise_for_status()

            data = response.json()
            items = []

            for item_data in data.get("result", []):
                item = self._parse_item_listing(item_data)
                if item:
                    items.append(item)

            return items

        except Exception as e:
            logger.error(f"Error fetching item details: {e}")
            return []

    def _parse_item_listing(self, raw_data: Dict) -> Optional[Dict[str, Any]]:
        """Parse raw item listing data into structured format"""
        try:
            listing = raw_data.get("listing", {})
            item = raw_data.get("item", {})

            return {
                "id": raw_data.get("id"),
                "name": item.get("name", ""),
                "type": item.get("typeLine", ""),
                "base_type": item.get("baseType", ""),
                "item_level": item.get("ilvl", 0),
                "corrupted": item.get("corrupted", False),
                "price": {
                    "amount": listing.get("price", {}).get("amount"),
                    "currency": listing.get("price", {}).get("currency"),
                    "type": listing.get("price", {}).get("type"),
                },
                "seller": {
                    "account": listing.get("account", {}).get("name"),
                    "character": listing.get("account", {}).get("lastCharacterName"),
                    "online": listing.get("account", {}).get("online", False),
                },
                "properties": item.get("properties", []),
                "requirements": item.get("requirements", []),
                "explicit_mods": item.get("explicitMods", []),
                "implicit_mods": item.get("implicitMods", []),
                "enchant_mods": item.get("enchantMods", []),
                "sockets": item.get("sockets", []),
                "links": self._count_links(item.get("sockets", [])),
                "listed_time": listing.get("indexed"),
            }

        except Exception as e:
            logger.error(f"Error parsing item: {e}")
            return None

    def _count_links(self, sockets: List[Dict]) -> int:
        """Count maximum linked sockets"""
        if not sockets:
            return 0

        max_links = 0
        for socket_group in sockets:
            group_size = socket_group.get("group", 0)
            if group_size > max_links:
                max_links = group_size

        return max_links + 1 if max_links > 0 else 0

    def _build_search_query(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Build trade API search query from filters"""
        query = {
            "query": {
                "status": {"option": "securable"},  # PoE2 uses "securable" not "online"
                "stats": [{"type": "and", "filters": []}],
            },
            "sort": {
                "price": "asc"  # Cheapest first
            }
        }

        # Text search (item name/type)
        if "term" in filters:
            query["query"]["term"] = filters["term"]

        # Item type filter (specific type like "Amulet")
        if "type" in filters:
            query["query"]["type"] = filters["type"]

        # Name filter (specific unique name)
        if "name" in filters:
            query["query"]["name"] = filters["name"]

        # Stats/mods filter
        if "stats" in filters and filters["stats"]:
            query["query"]["stats"] = self._build_stat_filters(filters["stats"])

        # Item filters (sockets, links, etc.)
        if "item_filters" in filters:
            query["query"]["filters"] = filters["item_filters"]

        return query

    def _build_stat_filters(self, stats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build stat filter groups for the query"""
        stat_filters = []

        for stat in stats:
            stat_filter = {
                "type": "and",
                "filters": []
            }

            if "id" in stat:
                stat_filter["filters"].append({
                    "id": stat["id"],
                    "value": {
                        "min": stat.get("min"),
                        "max": stat.get("max")
                    }
                })

            if stat_filter["filters"]:
                stat_filters.append(stat_filter)

        return stat_filters

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    async def search_for_upgrades(
        self,
        league: str,
        character_needs: Dict[str, Any],
        max_price_chaos: Optional[int] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search for items that address character deficiencies

        Args:
            league: League name
            character_needs: Dict with keys like:
                - missing_resistances: {"fire": 2, "cold": 8}
                - needs_life: bool
                - needs_es: bool
                - item_slots: List of slots to search (e.g., ["charm", "amulet", "helmet"])
            max_price_chaos: Maximum price filter

        Returns:
            Dict of item_type -> List of matching items
        """
        results = {}

        # Extract needs
        missing_res = character_needs.get("missing_resistances", {})
        needs_life = character_needs.get("needs_life", False)
        needs_es = character_needs.get("needs_es", False)
        item_slots = character_needs.get("item_slots", ["charm", "amulet", "helmet"])

        # Search for charms if resistances are needed
        if "charm" in item_slots and missing_res:
            logger.info("Searching for resistance charms...")
            charm_results = await self._search_resistance_charms(
                league, missing_res, max_price_chaos
            )
            if charm_results:
                results["charms"] = charm_results

        # Search for amulets if needed
        if "amulet" in item_slots:
            logger.info("Searching for amulets...")
            amulet_results = await self._search_amulets_with_stats(
                league, missing_res, needs_life, max_price_chaos
            )
            if amulet_results:
                results["amulets"] = amulet_results

        # Search for helmets if needed
        if "helmet" in item_slots and (needs_life or needs_es or missing_res):
            logger.info("Searching for helmets...")
            helmet_results = await self._search_helmets_with_defenses(
                league, missing_res, needs_life, needs_es, max_price_chaos
            )
            if helmet_results:
                results["helmets"] = helmet_results

        return results

    async def _search_resistance_charms(
        self,
        league: str,
        missing_res: Dict[str, int],
        max_price_chaos: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search for charms with resistances"""
        filters = {"term": "charm resistance"}

        items = await self.search_items(league, filters, limit=20)

        # Filter for charms with needed resistances
        filtered = []
        for item in items:
            if max_price_chaos:
                price = item.get("price", {})
                if price.get("currency") == "chaos" and price.get("amount", 999) > max_price_chaos:
                    continue

            # Check if has multiple resistances
            mods = item.get("explicit_mods", []) + item.get("implicit_mods", [])
            res_count = sum(1 for mod in mods if "Resistance" in mod)

            if res_count >= 2:
                filtered.append(item)

        return filtered[:10]

    async def _search_amulets_with_stats(
        self,
        league: str,
        missing_res: Dict[str, int],
        needs_life: bool,
        max_price_chaos: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search for amulets with spell levels and resistances"""
        filters = {"term": "amulet spell"}

        items = await self.search_items(league, filters, limit=20)

        filtered = []
        for item in items:
            if max_price_chaos:
                price = item.get("price", {})
                if price.get("currency") == "chaos" and price.get("amount", 999) > max_price_chaos:
                    continue

            mods = item.get("explicit_mods", [])

            # Check for spell levels
            has_spell_levels = any("+#" in mod and "Spell" in mod and "Level" in mod for mod in mods)

            # Check for resistances
            has_res = sum(1 for mod in mods if "Resistance" in mod) >= 2

            # Check for life if needed
            has_life = any("Life" in mod and "Maximum" in mod for mod in mods)

            if has_spell_levels and has_res and (has_life or not needs_life):
                filtered.append(item)

        return filtered[:10]

    async def _search_helmets_with_defenses(
        self,
        league: str,
        missing_res: Dict[str, int],
        needs_life: bool,
        needs_es: bool,
        max_price_chaos: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search for helmets with life/ES and resistances"""
        filters = {"term": "helmet life"}

        items = await self.search_items(league, filters, limit=20)

        filtered = []
        for item in items:
            if max_price_chaos:
                price = item.get("price", {})
                if price.get("currency") == "chaos" and price.get("amount", 999) > max_price_chaos:
                    continue

            mods = item.get("explicit_mods", [])

            # Check for life
            has_life = any("Life" in mod and "Maximum" in mod for mod in mods)

            # Check for ES
            has_es = any("Energy Shield" in mod for mod in mods)

            # Check for resistances
            res_count = sum(1 for mod in mods if "Resistance" in mod)

            meets_requirements = True
            if needs_life and not has_life:
                meets_requirements = False
            if needs_es and not has_es:
                meets_requirements = False
            if res_count < 2:
                meets_requirements = False

            if meets_requirements:
                filtered.append(item)

        return filtered[:10]

    async def search_with_analysis(
        self,
        league: str,
        character_needs: Dict[str, Any],
        current_gear: Dict[str, Any],
        base_character_stats: Dict[str, Any],
        max_price_chaos: Optional[int] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Enhanced search with upgrade value analysis.

        Wraps search_for_upgrades and adds priority scoring and
        upgrade recommendations for each item.

        Args:
            league: League name
            character_needs: Character deficiencies
            current_gear: Dict of slot -> GearStats
            base_character_stats: Base character stats
            max_price_chaos: Maximum price

        Returns:
            Dict with analyzed items sorted by priority score
        """
        # Get raw search results
        raw_results = await self.search_for_upgrades(
            league=league,
            character_needs=character_needs,
            max_price_chaos=max_price_chaos
        )

        # For now, return raw results
        # Full integration with GearEvaluator will be in next update
        logger.info("Trade search with analysis completed (basic mode)")
        return raw_results


# Helper functions for common searches

async def search_amulet_with_spell_levels_and_resistances(
    league: str,
    min_spell_levels: int = 2,
    min_life: int = 50,
    min_total_res: int = 80,
    max_price_chaos: int = 100
) -> List[Dict[str, Any]]:
    """Search for amulets with spell levels and resistances"""

    trade_api = TradeAPI()

    try:
        filters = {
            "type": "Amulet",
            "stats": [
                {
                    "id": "explicit.stat_3988349707",  # +# to Level of all Spell Skills
                    "min": min_spell_levels,
                },
            ],
            "item_filters": {
                "misc_filters": {
                    "filters": {
                        "ilvl": {"min": 75}
                    }
                }
            }
        }

        results = await trade_api.search_items(league, filters, limit=20)

        # Filter by resistances and life in code (easier than building complex query)
        filtered_results = []
        for item in results:
            # Check price
            price = item.get("price", {})
            if price.get("currency") == "chaos" and price.get("amount", 999) > max_price_chaos:
                continue

            # Check for life/ES and resistances in mods
            mods = item.get("explicit_mods", [])
            has_life = any("Life" in mod and "Maximum" in mod for mod in mods)
            has_res = sum(1 for mod in mods if "Resistance" in mod)

            if (has_life or min_life == 0) and has_res >= 2:
                filtered_results.append(item)

        return filtered_results[:10]

    finally:
        await trade_api.close()


async def search_helmet_with_life_es_resistances(
    league: str,
    min_life: int = 100,
    min_es: int = 100,
    min_total_res: int = 60,
    max_price_chaos: int = 100
) -> List[Dict[str, Any]]:
    """Search for helmets with life, ES, and resistances"""

    trade_api = TradeAPI()

    try:
        filters = {
            "type": "Helmet",
            "item_filters": {
                "misc_filters": {
                    "filters": {
                        "ilvl": {"min": 75}
                    }
                }
            }
        }

        results = await trade_api.search_items(league, filters, limit=20)

        # Filter in code
        filtered_results = []
        for item in results:
            # Check price
            price = item.get("price", {})
            if price.get("currency") == "chaos" and price.get("amount", 999) > max_price_chaos:
                continue

            mods = item.get("explicit_mods", [])
            has_life = any(str(min_life) in mod or "Life" in mod for mod in mods)
            has_es = any("Energy Shield" in mod for mod in mods)
            res_count = sum(1 for mod in mods if "Resistance" in mod)

            if has_life and has_es and res_count >= 2:
                filtered_results.append(item)

        return filtered_results[:10]

    finally:
        await trade_api.close()


async def search_resistance_charms(
    league: str,
    min_total_res: int = 30,
    max_price_chaos: int = 20
) -> List[Dict[str, Any]]:
    """Search for charms with resistances"""

    trade_api = TradeAPI()

    try:
        filters = {
            "type": "Charm",
        }

        results = await trade_api.search_items(league, filters, limit=30)

        # Filter for multi-resistance charms
        filtered_results = []
        for item in results:
            price = item.get("price", {})
            if price.get("currency") == "chaos" and price.get("amount", 999) > max_price_chaos:
                continue

            mods = item.get("explicit_mods", []) + item.get("implicit_mods", [])
            res_count = sum(1 for mod in mods if "Resistance" in mod)

            if res_count >= 2:  # At least 2 different resistances
                filtered_results.append(item)

        return filtered_results[:10]

    finally:
        await trade_api.close()
