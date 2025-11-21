"""
Character Comparison System
Compares user's character against top ladder players using similar skills
Identifies optimization opportunities based on what top players do differently
"""

import logging
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


class CharacterComparator:
    """
    Compare characters to identify optimization opportunities
    Focuses on comparing against higher-level, higher-DPS players using same skills
    """

    def __init__(self):
        pass

    def compare_to_top_players(
        self,
        user_character: Dict[str, Any],
        top_characters: List[Dict[str, Any]],
        comparison_focus: str = "dps"
    ) -> Dict[str, Any]:
        """
        Compare user's character to top ladder players

        Args:
            user_character: User's character data
            top_characters: List of top player characters (filtered by same skills)
            comparison_focus: What to optimize for (dps, defense, balanced)

        Returns:
            Comprehensive comparison with recommendations
        """
        logger.info(f"Comparing character against {len(top_characters)} top players")

        comparison = {
            "user_character": {
                "name": user_character.get("name"),
                "level": user_character.get("level", 0),
                "class": user_character.get("class")
            },
            "comparison_pool": {
                "count": len(top_characters),
                "avg_level": self._avg_level(top_characters),
                "level_range": self._level_range(top_characters)
            },
            "skill_comparison": self._compare_skills(user_character, top_characters),
            "gear_comparison": self._compare_gear(user_character, top_characters),
            "stat_comparison": self._compare_stats(user_character, top_characters),
            "passive_comparison": self._compare_passives(user_character, top_characters),
            "key_differences": [],
            "recommendations": [],
            "top_performers": self._identify_top_performers(top_characters, comparison_focus)
        }

        # Generate insights
        comparison["key_differences"] = self._identify_key_differences(user_character, top_characters)
        comparison["recommendations"] = self._generate_recommendations(comparison)

        return comparison

    def extract_main_skills(self, character: Dict[str, Any]) -> Set[str]:
        """
        Extract main skill names from character

        Returns:
            Set of main skill names (normalized)
        """
        skills = character.get("skills", [])
        main_skills = set()

        for skill_group in skills:
            # Try different data structures
            skill_data = skill_group.get("skillData", skill_group)
            all_gems = skill_group.get("allGems", [])

            # Extract from allGems
            for gem in all_gems:
                name = gem.get("name", "").strip()
                if name and not self._is_support_gem(name):
                    main_skills.add(self._normalize_skill_name(name))

            # Extract from direct skill data
            name = skill_data.get("name", skill_data.get("id", "")).strip()
            if name and not self._is_support_gem(name):
                main_skills.add(self._normalize_skill_name(name))

        return main_skills

    def _normalize_skill_name(self, name: str) -> str:
        """Normalize skill name for comparison"""
        return name.lower().strip().replace("'", "").replace("-", " ")

    def _is_support_gem(self, name: str) -> str:
        """Check if gem is a support gem"""
        support_keywords = [
            "support", "increased", "additional", "concentrated", "faster",
            "multiple", "greater", "efficacy", "controlled", "elemental",
            "awakened", "enlighten", "empower", "enhance"
        ]
        name_lower = name.lower()
        return any(keyword in name_lower for keyword in support_keywords)

    def _compare_skills(
        self,
        user_char: Dict[str, Any],
        top_chars: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Compare skill setups"""

        user_skills = self.extract_main_skills(user_char)
        user_skill_groups = user_char.get("skills", [])

        # Analyze what top players are doing
        common_support_gems = defaultdict(int)
        common_skill_links = defaultdict(int)
        avg_gem_levels = defaultdict(list)

        for char in top_chars:
            for skill_group in char.get("skills", []):
                all_gems = skill_group.get("allGems", [])

                # Count support gem usage
                for gem in all_gems:
                    name = gem.get("name", "")
                    if self._is_support_gem(name):
                        common_support_gems[name] += 1

                    # Track gem levels
                    level = self._extract_gem_level(gem)
                    if level:
                        avg_gem_levels[name].append(level)

        # Calculate averages
        for gem, levels in avg_gem_levels.items():
            avg_gem_levels[gem] = sum(levels) / len(levels) if levels else 0

        return {
            "user_main_skills": list(user_skills),
            "user_skill_count": len(user_skill_groups),
            "common_supports_in_top_players": dict(sorted(
                common_support_gems.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]),
            "avg_gem_levels": dict(avg_gem_levels),
            "recommendations": self._generate_skill_recommendations(
                user_char,
                common_support_gems,
                avg_gem_levels
            )
        }

    def _extract_gem_level(self, gem: Dict[str, Any]) -> Optional[int]:
        """Extract gem level from gem data"""
        item_data = gem.get("itemData", gem)
        properties = item_data.get("properties", [])

        for prop in properties:
            if prop.get("name") == "Level":
                values = prop.get("values", [])
                if values and values[0]:
                    level_str = str(values[0][0])
                    # Extract number from strings like "20 (Max)"
                    import re
                    match = re.search(r'(\d+)', level_str)
                    if match:
                        return int(match.group(1))
        return None

    def _compare_gear(
        self,
        user_char: Dict[str, Any],
        top_chars: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Compare gear choices"""

        user_items = user_char.get("items", [])
        user_uniques = self._extract_unique_items(user_items)

        # Track what top players use
        unique_usage = defaultdict(int)
        unique_by_slot = defaultdict(lambda: defaultdict(int))
        mod_priorities = defaultdict(int)

        for char in top_chars:
            items = char.get("items", [])
            char_uniques = self._extract_unique_items(items)

            for slot, unique_name in char_uniques.items():
                unique_usage[unique_name] += 1
                unique_by_slot[slot][unique_name] += 1

            # Track important mods
            for item in items:
                item_data = item.get("itemData", item)
                explicit_mods = item_data.get("explicitMods", [])
                for mod in explicit_mods:
                    # Simplify mod for tracking
                    simplified = self._simplify_mod(mod)
                    if simplified:
                        mod_priorities[simplified] += 1

        return {
            "user_uniques": dict(user_uniques),
            "popular_uniques": dict(sorted(
                unique_usage.items(),
                key=lambda x: x[1],
                reverse=True
            )[:15]),
            "popular_uniques_by_slot": {
                slot: dict(sorted(items.items(), key=lambda x: x[1], reverse=True)[:5])
                for slot, items in unique_by_slot.items()
            },
            "most_important_mods": dict(sorted(
                mod_priorities.items(),
                key=lambda x: x[1],
                reverse=True
            )[:20]),
            "differences": self._find_gear_differences(user_uniques, unique_usage)
        }

    def _extract_unique_items(self, items: List[Dict]) -> Dict[str, str]:
        """Extract unique items by slot"""
        uniques = {}
        for item in items:
            item_data = item.get("itemData", item)
            name = item_data.get("name", "").strip()
            type_line = item_data.get("typeLine", "").strip()
            slot = item_data.get("inventoryId", "")

            # Check if unique (has a name different from typeLine)
            if name and name != type_line:
                uniques[slot] = name
            # Or check for unique rarity indicator
            elif "Unique" in str(item_data.get("frameType", "")):
                uniques[slot] = type_line

        return uniques

    def _simplify_mod(self, mod: str) -> Optional[str]:
        """Simplify mod to track common stats"""
        mod_lower = mod.lower()

        # Map to categories
        if "life" in mod_lower and "maximum" in mod_lower:
            return "+Life"
        elif "energy shield" in mod_lower and "maximum" in mod_lower:
            return "+Energy Shield"
        elif "mana" in mod_lower and "maximum" in mod_lower:
            return "+Mana"
        elif "resistance" in mod_lower:
            if "fire" in mod_lower:
                return "+Fire Resistance"
            elif "cold" in mod_lower:
                return "+Cold Resistance"
            elif "lightning" in mod_lower:
                return "+Lightning Resistance"
            elif "chaos" in mod_lower:
                return "+Chaos Resistance"
            elif "all" in mod_lower or "elemental" in mod_lower:
                return "+All Resistances"
        elif "critical" in mod_lower and "chance" in mod_lower:
            return "+Critical Chance"
        elif "critical" in mod_lower and ("damage" in mod_lower or "multiplier" in mod_lower):
            return "+Critical Damage"
        elif "spell damage" in mod_lower or "increased spell damage" in mod_lower:
            return "+Spell Damage"
        elif "cast speed" in mod_lower:
            return "+Cast Speed"
        elif "movement speed" in mod_lower:
            return "+Movement Speed"

        return None

    def _compare_stats(
        self,
        user_char: Dict[str, Any],
        top_chars: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Compare character stats"""

        user_stats = user_char.get("stats", {})

        # Aggregate stats from top players
        stat_aggregates = defaultdict(list)

        for char in top_chars:
            stats = char.get("stats", {})
            for key, value in stats.items():
                if isinstance(value, (int, float)):
                    stat_aggregates[key].append(value)

        # Calculate averages and percentiles
        stat_comparison = {}
        for key, values in stat_aggregates.items():
            if not values:
                continue

            avg = sum(values) / len(values)
            sorted_values = sorted(values)
            p25 = sorted_values[len(sorted_values) // 4]
            p50 = sorted_values[len(sorted_values) // 2]
            p75 = sorted_values[3 * len(sorted_values) // 4]

            user_value = user_stats.get(key, 0)

            stat_comparison[key] = {
                "user": user_value,
                "average": round(avg, 2),
                "p25": p25,
                "median": p50,
                "p75": p75,
                "percentile": self._calculate_percentile(user_value, sorted_values)
            }

        return stat_comparison

    def _calculate_percentile(self, value: float, sorted_values: List[float]) -> int:
        """Calculate what percentile a value is at"""
        if not sorted_values:
            return 0

        count_below = sum(1 for v in sorted_values if v < value)
        return int((count_below / len(sorted_values)) * 100)

    def _compare_passives(
        self,
        user_char: Dict[str, Any],
        top_chars: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Compare passive tree allocations"""

        user_passives = user_char.get("passive_tree", user_char.get("passives", {}))
        user_nodes = set()

        if isinstance(user_passives, dict):
            user_nodes = set(user_passives.get("hashes", user_passives.get("nodes", [])))
        elif isinstance(user_passives, list):
            user_nodes = set(user_passives)

        # Track common nodes in top players
        node_usage = defaultdict(int)

        for char in top_chars:
            passives = char.get("passive_tree", char.get("passives", {}))
            nodes = set()

            if isinstance(passives, dict):
                nodes = set(passives.get("hashes", passives.get("nodes", [])))
            elif isinstance(passives, list):
                nodes = set(passives)

            for node in nodes:
                node_usage[node] += 1

        # Find commonly taken nodes user doesn't have
        missing_popular_nodes = []
        threshold = len(top_chars) * 0.7  # 70% of top players take this

        for node, count in node_usage.items():
            if count >= threshold and node not in user_nodes:
                missing_popular_nodes.append({
                    "node": node,
                    "usage_rate": count / len(top_chars)
                })

        return {
            "user_node_count": len(user_nodes),
            "avg_node_count": sum(
                len(char.get("passive_tree", {}).get("hashes", []))
                for char in top_chars
            ) / len(top_chars) if top_chars else 0,
            "missing_popular_nodes": sorted(
                missing_popular_nodes,
                key=lambda x: x["usage_rate"],
                reverse=True
            )[:20]
        }

    def _identify_top_performers(
        self,
        characters: List[Dict[str, Any]],
        focus: str
    ) -> List[Dict[str, Any]]:
        """Identify top performing characters based on focus"""

        # Sort by level (proxy for success)
        sorted_chars = sorted(
            characters,
            key=lambda x: x.get("level", 0),
            reverse=True
        )

        return [
            {
                "name": char.get("name"),
                "level": char.get("level"),
                "class": char.get("class"),
                "stats": {
                    "life": char.get("stats", {}).get("life", 0),
                    "es": char.get("stats", {}).get("energyShield", 0),
                }
            }
            for char in sorted_chars[:5]
        ]

    def _identify_key_differences(
        self,
        user_char: Dict[str, Any],
        top_chars: List[Dict[str, Any]]
    ) -> List[str]:
        """Identify key differences that matter"""

        differences = []

        # Level difference
        user_level = user_char.get("level", 0)
        avg_level = self._avg_level(top_chars)
        if user_level < avg_level - 5:
            differences.append(f"Level gap: You're level {user_level}, top players average {avg_level:.0f}")

        # Stats differences
        user_stats = user_char.get("stats", {})
        life = user_stats.get("life", 0)
        es = user_stats.get("energyShield", 0)

        avg_life = sum(c.get("stats", {}).get("life", 0) for c in top_chars) / len(top_chars) if top_chars else 0
        avg_es = sum(c.get("stats", {}).get("energyShield", 0) for c in top_chars) / len(top_chars) if top_chars else 0

        if life < avg_life * 0.7:
            differences.append(f"Low Life: {life} vs average {avg_life:.0f}")

        if es < avg_es * 0.7:
            differences.append(f"Low Energy Shield: {es} vs average {avg_es:.0f}")

        # Resistance check
        fire_res = user_stats.get("fireResistance", 0)
        cold_res = user_stats.get("coldResistance", 0)
        lightning_res = user_stats.get("lightningResistance", 0)

        if fire_res < 75:
            differences.append(f"Fire Resistance uncapped: {fire_res}% (should be 75%)")
        if cold_res < 75:
            differences.append(f"Cold Resistance uncapped: {cold_res}% (should be 75%)")
        if lightning_res < 75:
            differences.append(f"Lightning Resistance uncapped: {lightning_res}% (should be 75%)")

        return differences

    def _generate_recommendations(self, comparison: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate actionable recommendations from comparison"""

        recommendations = []

        # Gear recommendations
        gear_comp = comparison.get("gear_comparison", {})
        differences = gear_comp.get("differences", [])

        for diff in differences[:3]:
            recommendations.append({
                "category": "Gear",
                "priority": "High",
                "recommendation": diff
            })

        # Skill recommendations
        skill_comp = comparison.get("skill_comparison", {})
        skill_recs = skill_comp.get("recommendations", [])

        for rec in skill_recs[:2]:
            recommendations.append({
                "category": "Skills",
                "priority": "Medium",
                "recommendation": rec
            })

        # Stat recommendations from key differences
        for diff in comparison.get("key_differences", [])[:3]:
            recommendations.append({
                "category": "Stats",
                "priority": "Critical" if "Resistance" in diff else "High",
                "recommendation": diff
            })

        return recommendations

    def _find_gear_differences(
        self,
        user_uniques: Dict[str, str],
        popular_uniques: Dict[str, int]
    ) -> List[str]:
        """Find gear differences worth mentioning"""

        differences = []

        # Find popular items user doesn't have
        for unique, count in list(popular_uniques.items())[:10]:
            if unique not in user_uniques.values():
                usage_pct = (count / len(popular_uniques)) * 100 if popular_uniques else 0
                differences.append(
                    f"{unique} is used by {usage_pct:.0f}% of top players but you don't have it"
                )

        return differences

    def _generate_skill_recommendations(
        self,
        user_char: Dict[str, Any],
        common_supports: Dict[str, int],
        avg_levels: Dict[str, float]
    ) -> List[str]:
        """Generate skill setup recommendations"""

        recommendations = []

        # Find highly used supports user might be missing
        user_skills = user_char.get("skills", [])
        user_support_names = set()

        for skill_group in user_skills:
            for gem in skill_group.get("allGems", []):
                name = gem.get("name", "")
                if self._is_support_gem(name):
                    user_support_names.add(name)

        # Recommend top supports not used
        for support, count in list(common_supports.items())[:5]:
            if support not in user_support_names:
                usage_pct = (count / 10) * 100  # Assuming 10 top players
                recommendations.append(
                    f"Consider using {support} (used by {usage_pct:.0f}% of top players)"
                )

        return recommendations[:3]

    def _avg_level(self, characters: List[Dict[str, Any]]) -> float:
        """Calculate average level"""
        if not characters:
            return 0
        return sum(c.get("level", 0) for c in characters) / len(characters)

    def _level_range(self, characters: List[Dict[str, Any]]) -> tuple:
        """Get level range"""
        if not characters:
            return (0, 0)
        levels = [c.get("level", 0) for c in characters]
        return (min(levels), max(levels))
