"""
Gem Synergy Calculator for Path of Exile 2

Calculates optimal spell gem + support gem combinations considering:
- DPS output
- Spirit cost efficiency
- Utility effects (freeze, shock, cull, etc.)
- Quality of life (AoE, cast speed, etc.)

Author: Claude
Date: 2025-10-24
"""

import logging
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path
from itertools import combinations
import math

logger = logging.getLogger(__name__)


@dataclass
class GemStats:
    """Base gem statistics"""
    name: str
    tags: List[str] = field(default_factory=list)
    base_damage_min: float = 0.0
    base_damage_max: float = 0.0
    cast_time: float = 1.0
    crit_chance: float = 0.0
    damage_effectiveness: float = 100.0
    mana_cost: float = 0.0
    spirit_cost: int = 0


@dataclass
class SupportGemEffect:
    """Support gem effects and costs"""
    name: str
    tags: List[str] = field(default_factory=list)

    # Multipliers (More)
    more_damage: float = 0.0  # % more damage
    more_cast_speed: float = 0.0
    more_aoe: float = 0.0
    more_crit_chance: float = 0.0
    more_crit_damage: float = 0.0

    # Multipliers (Less)
    less_damage: float = 0.0  # % less damage
    less_cast_speed: float = 0.0

    # Increased (additive)
    increased_damage: float = 0.0
    increased_cast_speed: float = 0.0
    increased_aoe: float = 0.0
    increased_crit_chance: float = 0.0

    # Added flat damage
    added_damage_min: float = 0.0
    added_damage_max: float = 0.0
    damage_type: str = ""  # fire, cold, lightning, chaos, physical

    # Costs
    spirit_cost: int = 0
    mana_cost_multiplier: float = 100.0  # % of base mana

    # Utility effects
    utility_effects: List[str] = field(default_factory=list)  # ["chain", "fork", "pierce", etc.]

    # Requirements/restrictions
    required_tags: List[str] = field(default_factory=list)  # Support must have matching tags with spell
    incompatible_with: List[str] = field(default_factory=list)  # Cannot be used with these supports


@dataclass
class SynergyResult:
    """Result of a gem combination analysis"""
    spell_name: str
    support_gems: List[str]

    # DPS metrics
    total_dps: float
    average_hit: float
    casts_per_second: float

    # Costs
    total_spirit_cost: int
    total_mana_cost: float

    # Multipliers applied
    total_more_multiplier: float
    total_increased_damage: float

    # Utility
    utility_effects: List[str] = field(default_factory=list)

    # Scoring
    dps_score: float = 0.0
    efficiency_score: float = 0.0  # DPS per spirit
    overall_score: float = 0.0

    # Breakdown
    calculation_breakdown: Dict[str, Any] = field(default_factory=dict)


class GemSynergyCalculator:
    """
    Calculate optimal spell + support gem combinations

    Usage:
        >>> calc = GemSynergyCalculator()
        >>> results = calc.find_best_combinations(
        ...     spell_name="fireball",
        ...     character_mods={},
        ...     max_spirit=100,
        ...     optimization_goal="dps"
        ... )
        >>> for result in results[:5]:
        ...     print(f"{result.spell_name}: {result.total_dps:.1f} DPS")
    """

    def __init__(self, spell_db_path: Optional[Path] = None, support_db_path: Optional[Path] = None):
        """
        Initialize calculator with gem databases

        Args:
            spell_db_path: Path to spell gems JSON database
            support_db_path: Path to support gems JSON database
        """
        self.spell_gems: Dict[str, GemStats] = {}
        self.support_gems: Dict[str, SupportGemEffect] = {}

        # Default paths
        if spell_db_path is None:
            spell_db_path = Path(__file__).parent.parent.parent / "poe2_spell_gems_database.json"
        if support_db_path is None:
            support_db_path = Path(__file__).parent.parent.parent / "poe2_support_gems_database.json"

        # Load databases
        self._load_spell_database(spell_db_path)
        self._load_support_database(support_db_path)

        logger.info(f"Loaded {len(self.spell_gems)} spell gems and {len(self.support_gems)} support gems")

    def _load_spell_database(self, path: Path):
        """Load spell gems from JSON database"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Parse spell gems by category
            for category, spells in data.items():
                if category == "metadata":
                    continue

                for spell_id, spell_data in spells.items():
                    # Use level 20 stats if available, otherwise level 1
                    stats = spell_data.get('level_20', spell_data.get('level_1', {}))

                    self.spell_gems[spell_id] = GemStats(
                        name=spell_data.get('name', spell_id),
                        tags=spell_data.get('tags', []),
                        base_damage_min=stats.get('damage_min', 0) or 0,
                        base_damage_max=stats.get('damage_max', 0) or 0,
                        cast_time=stats.get('cast_time', 1.0) or 1.0,
                        crit_chance=stats.get('crit_chance', 0.0) or 0.0,
                        damage_effectiveness=stats.get('damage_effectiveness', 100) or 100,
                        mana_cost=stats.get('mana_cost', 0) or 0
                    )

            logger.info(f"Loaded {len(self.spell_gems)} spells from {path}")

        except Exception as e:
            logger.error(f"Failed to load spell database from {path}: {e}", exc_info=True)

    def _load_support_database(self, path: Path):
        """Load support gems from JSON database"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Parse support gems from "support_gems" key
            supports = data.get('support_gems', {})

            for support_id, support_data in supports.items():
                # Skip if not a dictionary
                if not isinstance(support_data, dict):
                    continue

                # Parse effects
                effects = support_data.get('effects', {})

                # Determine which tags this support needs (compatible_with)
                compatible_with = support_data.get('compatible_with', [])

                self.support_gems[support_id] = SupportGemEffect(
                    name=support_data.get('name', support_id),
                    tags=support_data.get('tags', []),
                    more_damage=effects.get('more_spell_damage', effects.get('more_damage', 0.0)),
                    more_cast_speed=effects.get('more_cast_speed', 0.0),
                    more_aoe=effects.get('more_area', 0.0),
                    more_crit_chance=effects.get('more_crit_chance', 0.0),
                    more_crit_damage=effects.get('more_crit_damage', 0.0),
                    less_damage=effects.get('less_spell_damage', effects.get('less_damage', 0.0)),
                    less_cast_speed=effects.get('less_cast_speed', 0.0),
                    increased_damage=effects.get('increased_spell_damage', effects.get('increased_damage', 0.0)),
                    increased_cast_speed=effects.get('increased_cast_speed', 0.0),
                    increased_crit_chance=effects.get('increased_crit_chance', 0.0),
                    spirit_cost=support_data.get('spirit_cost', 0) or 0,
                    mana_cost_multiplier=support_data.get('cost_multiplier', 100.0) or 100.0,
                    utility_effects=[],  # Would need to parse from effects
                    required_tags=compatible_with,
                    incompatible_with=[]
                )

            logger.info(f"Loaded {len(self.support_gems)} supports from {path}")

        except Exception as e:
            logger.error(f"Failed to load support database from {path}: {e}", exc_info=True)

    def find_best_combinations(
        self,
        spell_name: str,
        character_mods: Optional[Dict[str, float]] = None,
        max_spirit: int = 100,
        num_supports: int = 5,
        optimization_goal: str = "dps",
        top_n: int = 10
    ) -> List[SynergyResult]:
        """
        Find the best support gem combinations for a spell

        Args:
            spell_name: Name or ID of the spell gem
            character_mods: Character modifiers (increased damage, cast speed, etc.)
            max_spirit: Maximum spirit available
            num_supports: Number of support gems to use (1-5)
            optimization_goal: "dps", "efficiency", "balanced", "utility"
            top_n: Number of top combinations to return

        Returns:
            List of top N synergy results, sorted by score
        """
        if character_mods is None:
            character_mods = {}

        # Get spell
        spell = self.spell_gems.get(spell_name.lower())
        if not spell:
            logger.error(f"Spell '{spell_name}' not found in database")
            return []

        logger.info(f"Finding best {num_supports}-support combinations for {spell.name}")
        logger.info(f"Optimization goal: {optimization_goal}, Max spirit: {max_spirit}")

        # Get compatible supports
        compatible_supports = self._get_compatible_supports(spell)

        if len(compatible_supports) < num_supports:
            logger.warning(f"Only {len(compatible_supports)} compatible supports found (need {num_supports})")
            num_supports = len(compatible_supports)

        logger.info(f"Found {len(compatible_supports)} compatible support gems")

        # Generate all combinations
        all_results = []
        total_combinations = math.comb(len(compatible_supports), num_supports)
        logger.info(f"Testing {total_combinations} combinations...")

        for i, support_combo in enumerate(combinations(compatible_supports, num_supports)):
            # Check if combination is valid (no conflicts)
            if not self._is_valid_combination(support_combo):
                continue

            # Calculate DPS and metrics
            result = self._calculate_combination_dps(
                spell,
                list(support_combo),
                character_mods,
                max_spirit
            )

            if result:
                # Calculate scores based on optimization goal
                result = self._score_result(result, optimization_goal)
                all_results.append(result)

            # Log progress every 1000 combinations
            if (i + 1) % 1000 == 0:
                logger.debug(f"Tested {i+1}/{total_combinations} combinations...")

        logger.info(f"Calculated {len(all_results)} valid combinations")

        # Sort by overall score
        all_results.sort(key=lambda r: r.overall_score, reverse=True)

        return all_results[:top_n]

    def _get_compatible_supports(self, spell: GemStats) -> List[Tuple[str, SupportGemEffect]]:
        """Get all support gems compatible with this spell"""
        compatible = []

        for support_id, support in self.support_gems.items():
            # Check if support requires specific tags
            if support.required_tags:
                # Spell must have at least one matching tag
                # Check both exact matches and if "spell" tag matches
                matches = False
                for required_tag in support.required_tags:
                    # Exact match
                    if required_tag in spell.tags:
                        matches = True
                        break
                    # Case-insensitive match
                    if required_tag.lower() in [t.lower() for t in spell.tags]:
                        matches = True
                        break

                if not matches:
                    continue

            compatible.append((support_id, support))

        return compatible

    def _is_valid_combination(self, support_combo: List[Tuple[str, SupportGemEffect]]) -> bool:
        """Check if a combination of supports is valid (no conflicts)"""
        support_names = [s[0] for s in support_combo]

        for support_id, support in support_combo:
            # Check incompatibilities
            if support.incompatible_with:
                for incompatible in support.incompatible_with:
                    if incompatible in support_names:
                        return False

        return True

    def _calculate_combination_dps(
        self,
        spell: GemStats,
        supports: List[Tuple[str, SupportGemEffect]],
        character_mods: Dict[str, float],
        max_spirit: int
    ) -> Optional[SynergyResult]:
        """Calculate DPS for a specific spell + support combination"""

        # Calculate total spirit cost
        total_spirit = spell.spirit_cost + sum(s[1].spirit_cost for s in supports)

        # Skip if over spirit budget
        if total_spirit > max_spirit:
            return None

        # Start with base damage
        base_damage_avg = (spell.base_damage_min + spell.base_damage_max) / 2

        if base_damage_avg == 0:
            logger.debug(f"Skipping {spell.name} - no base damage data")
            return None

        # Accumulate modifiers
        total_more_damage = 1.0
        total_increased_damage = character_mods.get('increased_damage', 0.0)
        total_more_cast_speed = 1.0
        total_increased_cast_speed = character_mods.get('increased_cast_speed', 0.0)
        total_added_damage = 0.0
        utility_effects = []
        total_mana_cost = spell.mana_cost

        # Apply each support's effects
        for support_id, support in supports:
            # More multipliers (multiplicative)
            if support.more_damage != 0:
                total_more_damage *= (1.0 + support.more_damage / 100.0)

            if support.more_cast_speed != 0:
                total_more_cast_speed *= (1.0 + support.more_cast_speed / 100.0)

            # Less multipliers (multiplicative penalties)
            if support.less_damage != 0:
                total_more_damage *= (1.0 - support.less_damage / 100.0)

            if support.less_cast_speed != 0:
                total_more_cast_speed *= (1.0 - support.less_cast_speed / 100.0)

            # Increased (additive)
            total_increased_damage += support.increased_damage
            total_increased_cast_speed += support.increased_cast_speed

            # Added damage
            if support.added_damage_min > 0 or support.added_damage_max > 0:
                added_avg = (support.added_damage_min + support.added_damage_max) / 2
                # Apply damage effectiveness
                total_added_damage += added_avg * (spell.damage_effectiveness / 100.0)

            # Utility
            utility_effects.extend(support.utility_effects)

            # Mana cost
            total_mana_cost *= (support.mana_cost_multiplier / 100.0)

        # Calculate final damage
        damage_after_added = base_damage_avg + total_added_damage
        damage_after_increased = damage_after_added * (1.0 + total_increased_damage / 100.0)
        final_damage = damage_after_increased * total_more_damage

        # Calculate cast speed
        base_casts_per_sec = 1.0 / spell.cast_time
        casts_after_increased = base_casts_per_sec * (1.0 + total_increased_cast_speed / 100.0)
        final_casts_per_sec = casts_after_increased * total_more_cast_speed

        # Calculate DPS
        total_dps = final_damage * final_casts_per_sec

        # Create result
        result = SynergyResult(
            spell_name=spell.name,
            support_gems=[s[1].name for s in supports],
            total_dps=total_dps,
            average_hit=final_damage,
            casts_per_second=final_casts_per_sec,
            total_spirit_cost=total_spirit,
            total_mana_cost=total_mana_cost,
            total_more_multiplier=total_more_damage,
            total_increased_damage=total_increased_damage,
            utility_effects=utility_effects,
            calculation_breakdown={
                'base_damage': base_damage_avg,
                'added_damage': total_added_damage,
                'after_increased': damage_after_increased,
                'after_more': final_damage,
                'more_multiplier': total_more_damage,
                'increased_total': total_increased_damage,
                'cast_speed_multiplier': total_more_cast_speed,
                'spirit_per_support': [s[1].spirit_cost for s in supports]
            }
        )

        return result

    def _score_result(self, result: SynergyResult, optimization_goal: str) -> SynergyResult:
        """Calculate scores for a result based on optimization goal"""

        # DPS score (normalized)
        result.dps_score = result.total_dps

        # Efficiency score (DPS per spirit)
        if result.total_spirit_cost > 0:
            result.efficiency_score = result.total_dps / result.total_spirit_cost
        else:
            result.efficiency_score = result.total_dps

        # Utility score (bonus for utility effects)
        utility_score = len(result.utility_effects) * 1000  # Arbitrary bonus

        # Calculate overall score based on goal
        if optimization_goal == "dps":
            result.overall_score = result.dps_score
        elif optimization_goal == "efficiency":
            result.overall_score = result.efficiency_score
        elif optimization_goal == "utility":
            result.overall_score = result.dps_score * 0.7 + utility_score
        else:  # balanced
            result.overall_score = (
                result.dps_score * 0.6 +
                result.efficiency_score * 10.0 +  # Scale up efficiency
                utility_score * 0.1
            )

        return result

    def format_result(self, result: SynergyResult, detailed: bool = False) -> str:
        """Format a synergy result as human-readable text"""
        lines = []
        lines.append("=" * 80)
        lines.append(f"Spell: {result.spell_name}")
        lines.append(f"Support Gems: {', '.join(result.support_gems)}")
        lines.append("-" * 80)
        lines.append(f"Total DPS: {result.total_dps:,.1f}")
        lines.append(f"Average Hit: {result.average_hit:,.1f}")
        lines.append(f"Casts per Second: {result.casts_per_second:.2f}")
        lines.append(f"Spirit Cost: {result.total_spirit_cost}")
        lines.append(f"Mana Cost: {result.total_mana_cost:.1f}")
        lines.append(f"More Multiplier: {result.total_more_multiplier:.2f}x")
        lines.append(f"Increased Damage: {result.total_increased_damage:+.0f}%")

        if result.utility_effects:
            lines.append(f"Utility: {', '.join(result.utility_effects)}")

        lines.append("-" * 80)
        lines.append(f"DPS Score: {result.dps_score:,.1f}")
        lines.append(f"Efficiency (DPS/Spirit): {result.efficiency_score:,.1f}")
        lines.append(f"Overall Score: {result.overall_score:,.1f}")

        if detailed and result.calculation_breakdown:
            lines.append("-" * 80)
            lines.append("Calculation Breakdown:")
            for key, value in result.calculation_breakdown.items():
                lines.append(f"  {key}: {value}")

        lines.append("=" * 80)

        return "\n".join(lines)


# Convenience function
def find_best_supports_for_spell(
    spell_name: str,
    max_spirit: int = 100,
    num_supports: int = 5,
    goal: str = "dps"
) -> List[SynergyResult]:
    """
    Quick function to find best support combinations

    Args:
        spell_name: Name of the spell
        max_spirit: Maximum spirit available
        num_supports: Number of supports to use
        goal: "dps", "efficiency", "balanced", or "utility"

    Returns:
        List of top 10 combinations
    """
    calc = GemSynergyCalculator()
    return calc.find_best_combinations(
        spell_name=spell_name,
        max_spirit=max_spirit,
        num_supports=num_supports,
        optimization_goal=goal,
        top_n=10
    )


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 80)
    print("Path of Exile 2 Gem Synergy Calculator")
    print("=" * 80)
    print()

    # Example: Find best supports for Fireball
    print("Finding best 5-support combinations for Fireball...")
    print("Optimization goal: DPS")
    print("Max spirit: 100")
    print()

    results = find_best_supports_for_spell(
        spell_name="fireball",
        max_spirit=100,
        num_supports=5,
        goal="dps"
    )

    if results:
        print(f"Top {len(results)} combinations:")
        print()

        calc = GemSynergyCalculator()
        for i, result in enumerate(results, 1):
            print(f"#{i}")
            print(calc.format_result(result, detailed=False))
            print()
    else:
        print("No valid combinations found.")
