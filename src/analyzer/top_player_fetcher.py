"""
Top Player Fetcher
Finds top ladder players using similar skills for comparison
"""

import asyncio
import logging
from typing import Dict, List, Any, Set, Optional

try:
    from ..api.poe_ninja_api import PoeNinjaAPI
    from ..api.character_fetcher import CharacterFetcher
    from ..api.cache_manager import CacheManager
    from ..api.rate_limiter import RateLimiter
    from .character_comparator import CharacterComparator
except ImportError:
    from src.api.poe_ninja_api import PoeNinjaAPI
    from src.api.character_fetcher import CharacterFetcher
    from src.api.cache_manager import CacheManager
    from src.api.rate_limiter import RateLimiter
    from src.analyzer.character_comparator import CharacterComparator

logger = logging.getLogger(__name__)


class TopPlayerFetcher:
    """
    Fetch top ladder players using similar skills for comparison
    """

    def __init__(
        self,
        cache_manager: Optional[CacheManager] = None,
        rate_limiter: Optional[RateLimiter] = None
    ):
        self.cache_manager = cache_manager
        self.rate_limiter = rate_limiter or RateLimiter(rate_limit=5)
        self.ninja_api = PoeNinjaAPI(
            rate_limiter=self.rate_limiter,
            cache_manager=self.cache_manager
        )
        self.char_fetcher = CharacterFetcher(
            cache_manager=self.cache_manager,
            rate_limiter=self.rate_limiter
        )
        self.comparator = CharacterComparator()

    async def find_similar_top_players(
        self,
        user_character: Dict[str, Any],
        league: str = "Standard",
        min_level: int = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find top players using similar skills

        Args:
            user_character: User's character data
            league: League to search in
            min_level: Minimum level filter (defaults to user level)
            limit: Maximum number of characters to return

        Returns:
            List of similar character data
        """
        logger.info("Finding similar top players...")

        # Extract user's main skills
        user_skills = self.comparator.extract_main_skills(user_character)
        user_level = user_character.get("level", 0)
        user_class = user_character.get("class", "")

        if not min_level:
            min_level = user_level

        logger.info(f"User skills: {user_skills}")
        logger.info(f"Searching for players level {min_level}+ in {league}")

        # Get top characters from official ladder API
        ladder_characters = await self.char_fetcher.get_top_ladder_characters(
            league=league,
            limit=limit * 5,  # Get more to filter by skills
            min_level=min_level,
            class_filter=user_class if user_class not in ["Unknown", ""] else None
        )

        logger.info(f"Found {len(ladder_characters)} characters from ladder")

        if not ladder_characters:
            logger.warning("No characters found on ladder for this league")
            return []

        # Filter and fetch full character data
        similar_characters = []

        for ladder_entry in ladder_characters:
            # Skip dead characters in hardcore
            if ladder_entry.get("dead", False):
                continue

            account = ladder_entry.get("account", "")
            character = ladder_entry.get("character", "")
            level = ladder_entry.get("level", 0)

            if not account or not character:
                continue

            try:
                # Fetch full character data
                char_data = await self.char_fetcher.get_character(
                    account,
                    character,
                    league
                )

                if char_data:
                    # Check if skills match
                    char_skills = self.comparator.extract_main_skills(char_data)

                    # Calculate skill overlap
                    overlap = len(user_skills & char_skills)

                    # Accept if:
                    # 1. We have skill overlap
                    # 2. OR we couldn't extract user skills (compare all top players)
                    if overlap > 0 or not user_skills:
                        similar_characters.append(char_data)
                        logger.info(f"Added {character} (Level {level}, Rank #{ladder_entry.get('rank', '?')}, {overlap} matching skills)")

                        if len(similar_characters) >= limit:
                            break

            except Exception as e:
                logger.debug(f"Failed to fetch {character}: {e}")
                continue

            # Rate limiting between character fetches
            await asyncio.sleep(0.5)

        logger.info(f"Found {len(similar_characters)} similar characters")
        return similar_characters

    async def compare_with_top_players(
        self,
        user_character: Dict[str, Any],
        league: str = "Standard",
        min_level: int = None,
        comparison_focus: str = "dps",
        top_player_limit: int = 10
    ) -> Dict[str, Any]:
        """
        Complete workflow: Find similar players and compare

        Args:
            user_character: User's character data
            league: League to search
            min_level: Minimum level (defaults to user level)
            comparison_focus: What to optimize for
            top_player_limit: How many top players to compare against

        Returns:
            Complete comparison report
        """
        logger.info("Starting comparison with top players...")

        # Find similar players
        top_players = await self.find_similar_top_players(
            user_character,
            league=league,
            min_level=min_level,
            limit=top_player_limit
        )

        if not top_players:
            logger.warning("No similar top players found")
            return {
                "success": False,
                "message": "Could not find similar top players for comparison",
                "suggestions": [
                    "Try a different league",
                    "Lower the minimum level requirement",
                    "Make sure your profile is public so skills can be detected"
                ]
            }

        # Perform comparison
        comparison = self.comparator.compare_to_top_players(
            user_character,
            top_players,
            comparison_focus=comparison_focus
        )

        comparison["success"] = True
        comparison["message"] = f"Compared against {len(top_players)} top players"

        return comparison

    async def get_skill_based_recommendations(
        self,
        user_character: Dict[str, Any],
        league: str = "Standard"
    ) -> Dict[str, Any]:
        """
        Get recommendations based on what top players using same skills do

        Simplified interface for MCP tool

        Returns:
            Actionable recommendations
        """
        comparison = await self.compare_with_top_players(
            user_character,
            league=league,
            comparison_focus="balanced"
        )

        if not comparison.get("success"):
            return comparison

        # Extract key insights for easy consumption
        insights = {
            "success": True,
            "comparison_summary": {
                "players_analyzed": comparison["comparison_pool"]["count"],
                "avg_level": comparison["comparison_pool"]["avg_level"],
                "your_level": comparison["user_character"]["level"]
            },
            "key_differences": comparison["key_differences"],
            "top_recommendations": comparison["recommendations"][:5],
            "gear_insights": {
                "popular_uniques": list(
                    comparison["gear_comparison"]["popular_uniques"].keys()
                )[:10],
                "your_uniques": list(
                    comparison["gear_comparison"]["user_uniques"].values()
                )
            },
            "skill_insights": {
                "popular_supports": list(
                    comparison["skill_comparison"]["common_supports_in_top_players"].keys()
                )[:8],
                "recommendations": comparison["skill_comparison"]["recommendations"][:3]
            },
            "stat_highlights": self._extract_stat_highlights(
                comparison.get("stat_comparison", {})
            )
        }

        return insights

    def _extract_stat_highlights(self, stat_comparison: Dict) -> List[Dict[str, Any]]:
        """Extract the most important stat differences"""

        highlights = []

        # Focus on key stats
        important_stats = [
            "life", "energyShield", "mana",
            "fireResistance", "coldResistance", "lightningResistance",
            "movementSpeed"
        ]

        for stat in important_stats:
            if stat in stat_comparison:
                data = stat_comparison[stat]
                user_val = data["user"]
                avg_val = data["average"]
                percentile = data["percentile"]

                if percentile < 25:  # Below 25th percentile
                    highlights.append({
                        "stat": stat,
                        "your_value": user_val,
                        "average": avg_val,
                        "percentile": percentile,
                        "status": "low",
                        "message": f"Your {stat} ({user_val}) is below average ({avg_val:.0f})"
                    })
                elif percentile > 75:  # Above 75th percentile
                    highlights.append({
                        "stat": stat,
                        "your_value": user_val,
                        "average": avg_val,
                        "percentile": percentile,
                        "status": "high",
                        "message": f"Your {stat} ({user_val}) is above average ({avg_val:.0f})"
                    })

        return highlights

    async def close(self):
        """Cleanup resources"""
        await self.ninja_api.close()
        await self.char_fetcher.close()
