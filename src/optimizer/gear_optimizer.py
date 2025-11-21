"""
Gear optimization recommendations with intelligent analysis
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import select

try:
    from ..database.models import UniqueItem, Item
except ImportError:
    from src.database.models import UniqueItem, Item

logger = logging.getLogger(__name__)


class GearOptimizer:
    """Provides gear upgrade recommendations based on build goals and budget"""

    # Budget thresholds (in chaos orbs)
    BUDGET_RANGES = {
        "low": (0, 10),
        "medium": (10, 100),
        "high": (100, 1000),
        "unlimited": (1000, float('inf'))
    }

    # Slot mapping for different naming conventions
    SLOT_MAPPING = {
        "helmet": ["Helmet", "Helm"],
        "body_armour": ["Body Armour", "Body Armor", "Chest"],
        "gloves": ["Gloves"],
        "boots": ["Boots"],
        "weapon": ["Weapon", "One Hand Axe", "One Hand Sword", "One Hand Mace", "Bow", "Staff", "Wand"],
        "offhand": ["Shield", "Quiver", "One Hand"],
        "amulet": ["Amulet"],
        "ring": ["Ring"],
        "belt": ["Belt"]
    }

    def __init__(self, db_manager):
        self.db_manager = db_manager

    async def optimize(
        self,
        character_data: Dict[str, Any],
        budget: str = "medium",
        goal: str = "balanced"
    ) -> Dict[str, Any]:
        """
        Generate gear optimization recommendations

        Args:
            character_data: Character data with current gear
            budget: Budget tier (low/medium/high/unlimited)
            goal: Optimization goal (dps/defense/balanced/boss_damage/clear_speed)

        Returns:
            Gear recommendations with priorities and suggestions
        """
        logger.info(f"Optimizing gear with goal={goal}, budget={budget}")

        recommendations = {
            "priority_upgrades": [],
            "budget_tier": budget,
            "optimization_goal": goal,
            "total_estimated_cost": 0
        }

        # Extract current items from character data
        current_items = self._extract_current_items(character_data)

        # Analyze each gear slot
        slots = [
            "helmet", "body_armour", "gloves", "boots",
            "weapon", "offhand", "amulet", "ring", "belt"
        ]

        for slot in slots:
            upgrade = await self._analyze_slot(
                character_data,
                current_items.get(slot),
                slot,
                budget,
                goal
            )
            if upgrade:
                recommendations["priority_upgrades"].append(upgrade)
                recommendations["total_estimated_cost"] += upgrade.get("estimated_cost_chaos", 0)

        # Sort by priority
        recommendations["priority_upgrades"].sort(
            key=lambda x: self._priority_value(x["priority"]),
            reverse=True
        )

        # Add summary
        recommendations["summary"] = self._generate_summary(recommendations)

        return recommendations

    def _extract_current_items(self, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract current equipped items by slot"""
        current_items = {}

        items = character_data.get("items", [])
        if not items:
            return current_items

        for item in items:
            slot = item.get("inventoryId", "").lower()
            if slot:
                current_items[slot] = item

        return current_items

    async def _analyze_slot(
        self,
        character_data: Dict[str, Any],
        current_item: Optional[Dict[str, Any]],
        slot: str,
        budget: str,
        goal: str
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a specific gear slot and provide upgrade recommendations

        Args:
            character_data: Full character data
            current_item: Currently equipped item in this slot
            slot: Slot name
            budget: Budget tier
            goal: Optimization goal

        Returns:
            Upgrade recommendation or None
        """
        try:
            # Determine priority based on current item quality
            priority = self._determine_priority(current_item, slot, goal)

            if priority == "none":
                return None

            # Find suitable upgrade items from database
            suggested_items = await self._find_upgrade_items(
                current_item,
                slot,
                budget,
                goal,
                character_data
            )

            if not suggested_items:
                return None

            # Pick best suggestion
            best_suggestion = suggested_items[0]

            # Calculate improvement estimate
            improvement = self._estimate_improvement(current_item, best_suggestion, goal)

            return {
                "slot": slot,
                "priority": priority,
                "current_item": current_item.get("name", "Empty") if current_item else "Empty",
                "current_item_rarity": current_item.get("rarity", "unknown") if current_item else "empty",
                "suggested_item": best_suggestion["name"],
                "suggested_item_type": best_suggestion.get("item_class", "Unknown"),
                "improvement_estimate": improvement,
                "estimated_cost_chaos": best_suggestion.get("chaos_value", 0),
                "reasoning": self._generate_reasoning(current_item, best_suggestion, goal),
                "alternative_suggestions": [item["name"] for item in suggested_items[1:4]]
            }

        except Exception as e:
            logger.error(f"Error analyzing slot {slot}: {e}")
            return None

    def _determine_priority(
        self,
        current_item: Optional[Dict[str, Any]],
        slot: str,
        goal: str
    ) -> str:
        """Determine upgrade priority for a slot"""

        # Empty slot is always critical
        if not current_item:
            return "critical"

        rarity = current_item.get("rarity", "").lower()
        item_level = current_item.get("ilvl", 0)

        # Low item level is high priority
        if item_level < 50:
            return "high"

        # Normal/magic items are medium-high priority
        if rarity in ["normal", "magic"]:
            return "medium" if item_level >= 60 else "high"

        # Rare items might need upgrades depending on mods
        if rarity == "rare":
            # Check if item has good mods (simplified check)
            mods = current_item.get("mods", [])
            if len(mods) < 4:
                return "medium"
            return "low"

        # Unique items are usually good
        if rarity == "unique":
            # Check if it's a leveling unique
            level_req = current_item.get("level_requirement", 100)
            if level_req < 60:
                return "medium"
            return "low"

        return "low"

    async def _find_upgrade_items(
        self,
        current_item: Optional[Dict[str, Any]],
        slot: str,
        budget: str,
        goal: str,
        character_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Find suitable upgrade items from database"""

        min_chaos, max_chaos = self.BUDGET_RANGES.get(budget, (0, float('inf')))
        char_level = character_data.get("level", 100)

        suitable_items = []

        try:
            async with self.db_manager.async_session() as session:
                # Query unique items for this slot
                slot_classes = self.SLOT_MAPPING.get(slot, [slot.title()])

                # Query unique items
                query = select(UniqueItem).where(
                    UniqueItem.item_class.in_(slot_classes)
                )

                result = await session.execute(query)
                unique_items = result.scalars().all()

                for item in unique_items:
                    # Filter by level requirement
                    if item.level_requirement > char_level:
                        continue

                    # Filter by budget
                    chaos_value = item.stats.get("chaos_value", 0) if item.stats else 0
                    if not (min_chaos <= chaos_value <= max_chaos):
                        continue

                    # Score item based on goal
                    score = self._score_item(item, goal, character_data)

                    suitable_items.append({
                        "name": item.name,
                        "item_class": item.item_class,
                        "level_requirement": item.level_requirement,
                        "chaos_value": chaos_value,
                        "score": score,
                        "stats": item.stats or {}
                    })

                # Sort by score
                suitable_items.sort(key=lambda x: x["score"], reverse=True)

                return suitable_items[:5]  # Return top 5

        except Exception as e:
            logger.error(f"Error querying upgrade items: {e}")
            return []

    def _score_item(
        self,
        item: Any,
        goal: str,
        character_data: Dict[str, Any]
    ) -> float:
        """Score an item based on optimization goal"""

        score = 0.0
        stats = item.stats or {}

        if goal == "dps":
            # Prioritize damage stats
            score += stats.get("physical_damage", 0) * 2
            score += stats.get("elemental_damage", 0) * 2
            score += stats.get("attack_speed", 0) * 5
            score += stats.get("critical_chance", 0) * 10

        elif goal == "defense":
            # Prioritize defensive stats
            score += stats.get("life", 0) * 1
            score += stats.get("energy_shield", 0) * 0.5
            score += stats.get("armour", 0) * 0.1
            score += stats.get("evasion", 0) * 0.1
            score += stats.get("resistances", 0) * 2

        elif goal == "balanced":
            # Balance between offense and defense
            score += stats.get("physical_damage", 0) * 1
            score += stats.get("life", 0) * 0.5
            score += stats.get("resistances", 0) * 1.5

        # Base score on item level
        score += item.level_requirement * 0.1

        return score

    def _estimate_improvement(
        self,
        current_item: Optional[Dict[str, Any]],
        suggested_item: Dict[str, Any],
        goal: str
    ) -> float:
        """Estimate percentage improvement from upgrade"""

        if not current_item:
            return 1.0  # 100% improvement from empty

        current_rarity = current_item.get("rarity", "").lower()

        # Simplified improvement estimation
        if current_rarity in ["normal", "magic"]:
            return 0.5  # 50% improvement

        if current_rarity == "rare":
            return 0.2  # 20% improvement

        if current_rarity == "unique":
            # Unique to unique upgrade
            current_level = current_item.get("level_requirement", 0)
            suggested_level = suggested_item.get("level_requirement", 100)

            if suggested_level > current_level + 20:
                return 0.3
            return 0.1

        return 0.15

    def _generate_reasoning(
        self,
        current_item: Optional[Dict[str, Any]],
        suggested_item: Dict[str, Any],
        goal: str
    ) -> str:
        """Generate human-readable reasoning for the upgrade suggestion"""

        if not current_item:
            return f"Empty slot - equip {suggested_item['name']} for immediate improvement"

        current_rarity = current_item.get("rarity", "unknown")
        reasoning_parts = []

        if current_rarity in ["normal", "magic"]:
            reasoning_parts.append("Current item is low quality")

        if goal == "dps":
            reasoning_parts.append(f"{suggested_item['name']} provides better offensive stats")
        elif goal == "defense":
            reasoning_parts.append(f"{suggested_item['name']} provides better defensive stats")
        else:
            reasoning_parts.append(f"{suggested_item['name']} offers better overall stats")

        chaos_value = suggested_item.get("chaos_value", 0)
        if chaos_value > 0:
            reasoning_parts.append(f"(~{chaos_value:.1f} chaos)")

        return ". ".join(reasoning_parts)

    def _generate_summary(self, recommendations: Dict[str, Any]) -> str:
        """Generate summary of recommendations"""

        num_upgrades = len(recommendations["priority_upgrades"])
        total_cost = recommendations["total_estimated_cost"]
        goal = recommendations["optimization_goal"]

        if num_upgrades == 0:
            return "Your gear is well-optimized for your build!"

        critical_count = sum(1 for u in recommendations["priority_upgrades"] if u["priority"] == "critical")
        high_count = sum(1 for u in recommendations["priority_upgrades"] if u["priority"] == "high")

        summary = f"Found {num_upgrades} potential upgrades for {goal} optimization. "

        if critical_count > 0:
            summary += f"{critical_count} critical upgrades needed. "
        if high_count > 0:
            summary += f"{high_count} high priority upgrades. "

        summary += f"Estimated total cost: {total_cost:.1f} chaos orbs."

        return summary

    def _priority_value(self, priority: str) -> int:
        """Convert priority string to numeric value"""
        priority_map = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1,
            "none": 0
        }
        return priority_map.get(priority, 0)
