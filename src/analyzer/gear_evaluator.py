"""
Gear Upgrade Value Calculator for Path of Exile 2

This module quantifies the exact impact of gear upgrades on character performance.
Integrates with all calculator modules to provide precise DPS and EHP calculations.

Key Features:
- Calculate exact DPS increase/decrease from gear changes
- Calculate exact EHP changes for all damage types
- Quantify resistance changes
- Evaluate Spirit cost changes
- Generate upgrade recommendations with priority scores
- Cost/benefit analysis for trade items

Author: Claude
Date: 2025-10-22
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

# Import calculator modules
from ..calculator.defense_calculator import DefenseCalculator
from ..calculator.ehp_calculator import EHPCalculator, DefensiveStats, ThreatProfile
from ..calculator.damage_calculator import DamageCalculator, DamageRange, Modifier, ModifierType, CriticalStrikeConfig

logger = logging.getLogger(__name__)


class UpgradeRecommendation(Enum):
    """Upgrade recommendation levels."""
    STRONG_UPGRADE = "strong_upgrade"  # Significant improvement
    UPGRADE = "upgrade"  # Moderate improvement
    SIDEGRADE = "sidegrade"  # Mixed changes
    SKIP = "skip"  # No improvement or downgrade
    DOWNGRADE = "downgrade"  # Worse than current


@dataclass
class GearStats:
    """
    Statistics provided by a piece of gear.

    This represents the stat bonuses from a single gear piece.
    """
    # Defense stats
    armor: float = 0.0
    evasion: float = 0.0
    energy_shield: float = 0.0

    # Life/mana
    life: float = 0.0
    mana: float = 0.0

    # Resistances
    fire_res: float = 0.0
    cold_res: float = 0.0
    lightning_res: float = 0.0
    chaos_res: float = 0.0

    # Attributes
    strength: int = 0
    dexterity: int = 0
    intelligence: int = 0

    # Damage mods (simplified)
    increased_damage: float = 0.0
    more_damage: float = 0.0
    added_flat_damage: float = 0.0
    crit_chance: float = 0.0
    crit_multi: float = 0.0

    # Special
    spirit: int = 0
    block_chance: float = 0.0

    # Item metadata
    item_name: str = ""
    item_slot: str = ""
    item_level: int = 0


@dataclass
class UpgradeValue:
    """
    Calculated value of a gear upgrade.

    Attributes:
        ehp_changes: EHP changes for each damage type
        dps_change: DPS change (absolute and percent)
        resistance_changes: Resistance changes
        stat_changes: Raw stat changes
        priority_score: Overall priority score (0-100)
        recommendation: Upgrade recommendation
        trade_value: Estimated value in chaos orbs (if applicable)
    """
    ehp_changes: Dict[str, Dict[str, float]]
    dps_change: Dict[str, float]
    resistance_changes: Dict[str, float]
    stat_changes: Dict[str, float]
    priority_score: float
    recommendation: UpgradeRecommendation
    trade_value: Optional[float] = None
    warnings: List[str] = field(default_factory=list)


class GearEvaluator:
    """
    Main gear evaluation engine.

    Uses all calculator modules to precisely quantify gear upgrade value.

    Example:
        >>> evaluator = GearEvaluator()
        >>> current_helmet = GearStats(armor=500, life=50, fire_res=40)
        >>> upgrade_helmet = GearStats(armor=600, life=80, fire_res=45, cold_res=30)
        >>> value = evaluator.evaluate_upgrade(
        ...     current_gear=current_helmet,
        ...     upgrade_gear=upgrade_helmet,
        ...     base_character_stats={...}
        ... )
        >>> print(f"Priority Score: {value.priority_score}")
        >>> print(f"Recommendation: {value.recommendation.value}")
    """

    def __init__(self) -> None:
        """Initialize gear evaluator with calculator modules."""
        self.defense_calc = DefenseCalculator()
        self.ehp_calc = EHPCalculator()
        self.damage_calc = DamageCalculator()
        # Note: ResourceCalculator requires parameters, so it's created on-demand when needed

        logger.info("GearEvaluator initialized")

    # ============================================================================
    # MAIN EVALUATION METHODS
    # ============================================================================

    def evaluate_upgrade(
        self,
        current_gear: GearStats,
        upgrade_gear: GearStats,
        base_character_stats: Dict[str, Any],
        threat_profile: Optional[ThreatProfile] = None,
        price_chaos: Optional[float] = None
    ) -> UpgradeValue:
        """
        Evaluate a gear upgrade by calculating exact stat changes.

        Args:
            current_gear: Currently equipped gear
            upgrade_gear: Potential upgrade gear
            base_character_stats: Base character stats (without this gear piece)
            threat_profile: Threat profile for EHP calculations
            price_chaos: Price of upgrade in chaos orbs (for value analysis)

        Returns:
            UpgradeValue with detailed analysis
        """
        logger.info(
            f"Evaluating upgrade: {current_gear.item_name} -> {upgrade_gear.item_name}"
        )

        threat_profile = threat_profile or ThreatProfile()
        warnings = []

        # Calculate total stats with current gear
        current_total = self._combine_stats(base_character_stats, current_gear)

        # Calculate total stats with upgrade gear
        upgrade_total = self._combine_stats(base_character_stats, upgrade_gear)

        # Calculate EHP changes
        ehp_changes = self._calculate_ehp_changes(
            current_total,
            upgrade_total,
            threat_profile
        )

        # Calculate DPS changes (if skill data available)
        dps_change = self._calculate_dps_changes(
            current_total,
            upgrade_total,
            None  # skill_config - to be implemented later
        )

        # Calculate resistance changes
        resistance_changes = {
            'fire': upgrade_gear.fire_res - current_gear.fire_res,
            'cold': upgrade_gear.cold_res - current_gear.cold_res,
            'lightning': upgrade_gear.lightning_res - current_gear.lightning_res,
            'chaos': upgrade_gear.chaos_res - current_gear.chaos_res
        }

        # Calculate raw stat changes
        stat_changes = {
            'life': upgrade_gear.life - current_gear.life,
            'mana': upgrade_gear.mana - current_gear.mana,
            'armor': upgrade_gear.armor - current_gear.armor,
            'evasion': upgrade_gear.evasion - current_gear.evasion,
            'energy_shield': upgrade_gear.energy_shield - current_gear.energy_shield,
            'spirit': upgrade_gear.spirit - current_gear.spirit,
            'strength': upgrade_gear.strength - current_gear.strength,
            'dexterity': upgrade_gear.dexterity - current_gear.dexterity,
            'intelligence': upgrade_gear.intelligence - current_gear.intelligence
        }

        # Check for warnings
        warnings.extend(self._check_upgrade_warnings(
            current_total,
            upgrade_total,
            resistance_changes
        ))

        # Calculate priority score
        priority_score = self._calculate_priority_score(
            ehp_changes,
            dps_change,
            resistance_changes,
            stat_changes,
            current_total,
            price_chaos
        )

        # Generate recommendation
        recommendation = self._generate_recommendation(
            priority_score,
            ehp_changes,
            dps_change,
            warnings
        )

        result = UpgradeValue(
            ehp_changes=ehp_changes,
            dps_change=dps_change,
            resistance_changes=resistance_changes,
            stat_changes=stat_changes,
            priority_score=priority_score,
            recommendation=recommendation,
            trade_value=price_chaos,
            warnings=warnings
        )

        logger.info(
            f"Upgrade evaluation complete: {recommendation.value} "
            f"(priority: {priority_score:.1f})"
        )

        return result

    def evaluate_multiple_upgrades(
        self,
        current_gear: GearStats,
        potential_upgrades: List[Tuple[GearStats, Optional[float]]],
        base_character_stats: Dict[str, Any],
        top_n: int = 5
    ) -> List[Tuple[GearStats, UpgradeValue]]:
        """
        Evaluate multiple upgrade options and rank them.

        Args:
            current_gear: Currently equipped gear
            potential_upgrades: List of (upgrade_gear, price_chaos) tuples
            base_character_stats: Base character stats
            top_n: Number of top upgrades to return

        Returns:
            List of (upgrade_gear, upgrade_value) tuples, sorted by priority
        """
        logger.info(f"Evaluating {len(potential_upgrades)} upgrade options")

        results = []
        for upgrade_gear, price_chaos in potential_upgrades:
            value = self.evaluate_upgrade(
                current_gear=current_gear,
                upgrade_gear=upgrade_gear,
                base_character_stats=base_character_stats,
                price_chaos=price_chaos
            )
            results.append((upgrade_gear, value))

        # Sort by priority score (descending)
        results.sort(key=lambda x: x[1].priority_score, reverse=True)

        # Return top N
        top_results = results[:top_n]

        logger.info(
            f"Top {len(top_results)} upgrades identified "
            f"(best score: {top_results[0][1].priority_score:.1f})"
        )

        return top_results

    def compare_items(
        self,
        item_a: GearStats,
        item_b: GearStats,
        base_character_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Direct comparison of two items.

        Args:
            item_a: First item
            item_b: Second item
            base_character_stats: Base character stats

        Returns:
            Comparison results showing which is better
        """
        # Evaluate both as upgrades from a "null" item
        null_item = GearStats(item_name="None", item_slot=item_a.item_slot)

        value_a = self.evaluate_upgrade(null_item, item_a, base_character_stats)
        value_b = self.evaluate_upgrade(null_item, item_b, base_character_stats)

        # Determine winner
        if value_a.priority_score > value_b.priority_score:
            winner = item_a.item_name
            score_diff = value_a.priority_score - value_b.priority_score
        elif value_b.priority_score > value_a.priority_score:
            winner = item_b.item_name
            score_diff = value_b.priority_score - value_a.priority_score
        else:
            winner = "Tie"
            score_diff = 0.0

        return {
            'item_a': item_a.item_name,
            'item_a_score': value_a.priority_score,
            'item_a_value': value_a,
            'item_b': item_b.item_name,
            'item_b_score': value_b.priority_score,
            'item_b_value': value_b,
            'winner': winner,
            'score_difference': score_diff
        }

    # ============================================================================
    # HELPER METHODS
    # ============================================================================

    def _combine_stats(
        self,
        base_stats: Dict[str, Any],
        gear: GearStats
    ) -> Dict[str, Any]:
        """
        Combine base character stats with gear stats.

        Args:
            base_stats: Base character stats (without this gear piece)
            gear: Gear stats to add

        Returns:
            Combined stats dictionary
        """
        combined = base_stats.copy()

        # Add gear bonuses
        combined['armor'] = base_stats.get('armor', 0) + gear.armor
        combined['evasion'] = base_stats.get('evasion', 0) + gear.evasion
        combined['energy_shield'] = base_stats.get('energy_shield', 0) + gear.energy_shield
        combined['life'] = base_stats.get('life', 0) + gear.life
        combined['mana'] = base_stats.get('mana', 0) + gear.mana
        combined['fire_res'] = base_stats.get('fire_res', 0) + gear.fire_res
        combined['cold_res'] = base_stats.get('cold_res', 0) + gear.cold_res
        combined['lightning_res'] = base_stats.get('lightning_res', 0) + gear.lightning_res
        combined['chaos_res'] = base_stats.get('chaos_res', 0) + gear.chaos_res
        combined['block_chance'] = base_stats.get('block_chance', 0) + gear.block_chance

        # Attributes
        combined['strength'] = base_stats.get('strength', 0) + gear.strength
        combined['dexterity'] = base_stats.get('dexterity', 0) + gear.dexterity
        combined['intelligence'] = base_stats.get('intelligence', 0) + gear.intelligence

        # Damage mods
        combined['increased_damage'] = base_stats.get('increased_damage', 0) + gear.increased_damage
        combined['more_damage'] = base_stats.get('more_damage', 1.0) * gear.more_damage if gear.more_damage > 0 else base_stats.get('more_damage', 1.0)
        combined['added_flat_damage'] = base_stats.get('added_flat_damage', 0) + gear.added_flat_damage
        combined['crit_chance'] = base_stats.get('crit_chance', 0) + gear.crit_chance
        combined['crit_multi'] = base_stats.get('crit_multi', 0) + gear.crit_multi

        # Spirit
        combined['spirit'] = base_stats.get('spirit', 0) + gear.spirit

        return combined

    def _calculate_ehp_changes(
        self,
        current_stats: Dict[str, Any],
        upgrade_stats: Dict[str, Any],
        threat_profile: ThreatProfile
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate EHP changes for all damage types.

        Returns:
            Dictionary mapping damage types to {absolute, percent} changes
        """
        # Build DefensiveStats for current
        current_defensive = DefensiveStats(
            life=current_stats.get('life', 1),
            energy_shield=current_stats.get('energy_shield', 0),
            armor=current_stats.get('armor', 0),
            evasion=current_stats.get('evasion', 0),
            block_chance=current_stats.get('block_chance', 0),
            fire_res=current_stats.get('fire_res', 0),
            cold_res=current_stats.get('cold_res', 0),
            lightning_res=current_stats.get('lightning_res', 0),
            chaos_res=current_stats.get('chaos_res', 0)
        )

        # Build DefensiveStats for upgrade
        upgrade_defensive = DefensiveStats(
            life=upgrade_stats.get('life', 1),
            energy_shield=upgrade_stats.get('energy_shield', 0),
            armor=upgrade_stats.get('armor', 0),
            evasion=upgrade_stats.get('evasion', 0),
            block_chance=upgrade_stats.get('block_chance', 0),
            fire_res=upgrade_stats.get('fire_res', 0),
            cold_res=upgrade_stats.get('cold_res', 0),
            lightning_res=upgrade_stats.get('lightning_res', 0),
            chaos_res=upgrade_stats.get('chaos_res', 0)
        )

        # Use EHP calculator's compare_upgrade method
        comparison = self.ehp_calc.compare_upgrade(
            current_stats=current_defensive,
            upgraded_stats=upgrade_defensive,
            threat=threat_profile
        )

        return comparison

    def _calculate_dps_changes(
        self,
        current_stats: Dict[str, Any],
        upgrade_stats: Dict[str, Any],
        skill_config: Optional[Any]
    ) -> Dict[str, float]:
        """
        Calculate DPS changes.

        Returns:
            Dictionary with {absolute, percent} DPS changes
        """
        # If no skill config, we can still calculate relative DPS using gear stats
        # We use normalized base damage to calculate the DPS multiplier
        try:
            current_dps = self._calculate_relative_dps(current_stats)
            upgrade_dps = self._calculate_relative_dps(upgrade_stats)

            absolute_change = upgrade_dps - current_dps
            percent_change = (
                ((upgrade_dps / current_dps) - 1.0) * 100.0
                if current_dps > 0 else 0.0
            )

            return {
                'absolute': absolute_change,
                'percent': percent_change,
                'available': True,
                'current_dps': current_dps,
                'upgrade_dps': upgrade_dps
            }
        except Exception as e:
            logger.warning(f"Error calculating DPS changes: {e}")
            return {
                'absolute': 0.0,
                'percent': 0.0,
                'available': False,
                'error': str(e)
            }

    def _calculate_relative_dps(self, stats: Dict[str, Any]) -> float:
        """
        Calculate relative DPS using normalized base damage.

        Uses a normalized base damage of 100 to calculate the DPS multiplier
        that this set of stats would provide. This allows for relative comparison
        without needing exact skill data.

        Args:
            stats: Gear stats dictionary

        Returns:
            Relative DPS value (higher is better)
        """
        # Use normalized base damage for comparison
        base_damage = DamageRange(min_damage=100.0, max_damage=100.0)

        # Extract modifiers from stats
        increased_damage = stats.get('increased_damage', 0.0)
        more_damage = stats.get('more_damage', 0.0)
        added_flat = stats.get('added_flat_damage', 0.0)

        # Build modifier lists
        increased_mods = (
            [Modifier(value=increased_damage, modifier_type=ModifierType.INCREASED, source="Gear")]
            if increased_damage != 0 else []
        )
        more_mods = (
            [Modifier(value=more_damage, modifier_type=ModifierType.MORE, source="Gear")]
            if more_damage != 0 else []
        )

        # Calculate modified damage
        modified_damage = self.damage_calc.calculate_final_damage(
            base_damage,
            increased_mods,
            more_mods
        )

        # Add flat damage
        avg_damage = modified_damage.average() + added_flat

        # Apply critical strike multiplier
        crit_config = CriticalStrikeConfig(
            crit_chance=min(stats.get('crit_chance', 0.0), 100.0),
            crit_multiplier=stats.get('crit_multi', 100.0)
        )
        crit_multiplier = crit_config.effective_damage_multiplier()

        # Final DPS = avg_damage × crit_multiplier × attack_speed
        # Using 1.0 attack speed as baseline
        return avg_damage * crit_multiplier * 1.0

    def _check_upgrade_warnings(
        self,
        current_stats: Dict[str, Any],
        upgrade_stats: Dict[str, Any],
        resistance_changes: Dict[str, float]
    ) -> List[str]:
        """
        Check for potential issues with the upgrade.

        Returns:
            List of warning messages
        """
        warnings = []

        # Warning: Losing resistances
        for res_name, change in resistance_changes.items():
            if change < -5:  # Losing more than 5% resistance
                current_res = current_stats.get(f'{res_name}_res', 0)
                if current_res < 75:  # And not already capped
                    warnings.append(
                        f"Loses {abs(change):.0f}% {res_name} resistance "
                        f"(uncapped: {current_res:.0f}%)"
                    )

        # Warning: Losing life
        life_change = upgrade_stats.get('life', 0) - current_stats.get('life', 0)
        if life_change < -50:
            warnings.append(f"Loses {abs(life_change):.0f} life")

        # Warning: Losing ES
        es_change = upgrade_stats.get('energy_shield', 0) - current_stats.get('energy_shield', 0)
        if es_change < -100:
            warnings.append(f"Loses {abs(es_change):.0f} energy shield")

        return warnings

    def _calculate_priority_score(
        self,
        ehp_changes: Dict[str, Dict[str, float]],
        dps_change: Dict[str, float],
        resistance_changes: Dict[str, float],
        stat_changes: Dict[str, float],
        current_stats: Dict[str, Any],
        price_chaos: Optional[float]
    ) -> float:
        """
        Calculate priority score (0-100).

        Higher score = better upgrade.

        Factors:
        - EHP improvements (weighted heavily)
        - Resistance fixes (CRITICAL if uncapped)
        - Life/ES gains
        - DPS improvements
        - Price efficiency (if price provided)
        """
        score = 50.0  # Start at neutral

        # Factor 1: Resistance fixes (CRITICAL)
        for res_name, change in resistance_changes.items():
            current_res = current_stats.get(f'{res_name}_res', 0)

            # Negative resistances
            if current_res < 0:
                # Fixing negative res is HIGHEST priority
                if change > 0:
                    score += min(change * 2.0, 30.0)  # Up to +30 for fixing negative res

            # Below cap
            elif current_res < 75:
                if change > 0:
                    score += min(change * 0.5, 10.0)  # Up to +10 for improving uncapped res

            # Already capped
            else:
                if change < 0:
                    score -= abs(change) * 0.3  # Penalize losing capped res

        # Factor 2: EHP improvements
        if 'summary' in ehp_changes:
            avg_ehp_gain = ehp_changes['summary'].get('average_percent_gain', 0)
            if avg_ehp_gain > 0:
                score += min(avg_ehp_gain * 0.3, 20.0)  # Up to +20 for EHP gains
            else:
                score += avg_ehp_gain * 0.5  # Penalize EHP loss

        # Factor 3: Life/ES gains
        life_change = stat_changes.get('life', 0)
        if life_change != 0:
            current_life = current_stats.get('life', 1)
            life_percent = (life_change / current_life) * 100
            score += min(life_percent * 0.2, 10.0)  # Up to +10 for life

        es_change = stat_changes.get('energy_shield', 0)
        if es_change != 0:
            current_es = current_stats.get('energy_shield', 1)
            if current_es > 0:
                es_percent = (es_change / current_es) * 100
                score += min(es_percent * 0.2, 10.0)  # Up to +10 for ES

        # Factor 4: DPS improvements
        if dps_change.get('available', False):
            dps_percent = dps_change.get('percent', 0)
            score += min(dps_percent * 0.2, 15.0)  # Up to +15 for DPS

        # Factor 5: Price efficiency
        if price_chaos is not None and price_chaos > 0:
            # Penalize expensive upgrades slightly
            if price_chaos > 100:
                score -= min((price_chaos - 100) / 20, 10)  # Up to -10 for very expensive

        # Clamp to 0-100 range
        score = max(0.0, min(100.0, score))

        return score

    def _generate_recommendation(
        self,
        priority_score: float,
        ehp_changes: Dict[str, Dict[str, float]],
        dps_change: Dict[str, float],
        warnings: List[str]
    ) -> UpgradeRecommendation:
        """
        Generate upgrade recommendation based on analysis.

        Args:
            priority_score: Calculated priority score
            ehp_changes: EHP changes
            dps_change: DPS changes
            warnings: List of warnings

        Returns:
            UpgradeRecommendation
        """
        # Critical warnings -> SKIP
        if any('Loses' in w and 'resistance' in w for w in warnings):
            if priority_score < 55:
                return UpgradeRecommendation.SKIP

        # Strong upgrade
        if priority_score >= 70:
            return UpgradeRecommendation.STRONG_UPGRADE

        # Upgrade
        elif priority_score >= 55:
            return UpgradeRecommendation.UPGRADE

        # Sidegrade
        elif priority_score >= 45:
            return UpgradeRecommendation.SIDEGRADE

        # Downgrade
        elif priority_score < 40:
            return UpgradeRecommendation.DOWNGRADE

        # Skip
        else:
            return UpgradeRecommendation.SKIP

    # ============================================================================
    # FORMATTING AND DISPLAY
    # ============================================================================

    def format_upgrade_value(
        self,
        upgrade_gear: GearStats,
        upgrade_value: UpgradeValue
    ) -> str:
        """
        Format upgrade value into human-readable report.

        Args:
            upgrade_gear: The upgrade gear
            upgrade_value: Calculated upgrade value

        Returns:
            Formatted string report
        """
        lines = []
        lines.append("=" * 80)
        lines.append(f"GEAR UPGRADE EVALUATION: {upgrade_gear.item_name}")
        lines.append("=" * 80)
        lines.append("")

        # Recommendation
        rec_emoji = {
            UpgradeRecommendation.STRONG_UPGRADE: "✅",
            UpgradeRecommendation.UPGRADE: "👍",
            UpgradeRecommendation.SIDEGRADE: "↔️",
            UpgradeRecommendation.SKIP: "⏭️",
            UpgradeRecommendation.DOWNGRADE: "❌"
        }
        emoji = rec_emoji.get(upgrade_value.recommendation, "")
        lines.append(f"{emoji} Recommendation: {upgrade_value.recommendation.value.upper()}")
        lines.append(f"Priority Score: {upgrade_value.priority_score:.1f}/100")

        if upgrade_value.trade_value:
            lines.append(f"Price: {upgrade_value.trade_value:.1f} chaos")

        lines.append("")

        # EHP Changes
        if upgrade_value.ehp_changes:
            lines.append("EHP Changes:")
            for dmg_type, changes in upgrade_value.ehp_changes.items():
                if dmg_type == 'summary':
                    continue
                absolute = changes.get('absolute_gain', 0)
                percent = changes.get('percent_gain', 0)
                if absolute != 0:
                    sign = "+" if absolute > 0 else ""
                    lines.append(f"  {dmg_type.upper()}: {sign}{absolute:.0f} ({sign}{percent:.1f}%)")

        # Resistance Changes
        if any(v != 0 for v in upgrade_value.resistance_changes.values()):
            lines.append("")
            lines.append("Resistance Changes:")
            for res_name, change in upgrade_value.resistance_changes.items():
                if change != 0:
                    sign = "+" if change > 0 else ""
                    lines.append(f"  {res_name.capitalize()}: {sign}{change:.0f}%")

        # Stat Changes
        if any(v != 0 for v in upgrade_value.stat_changes.values()):
            lines.append("")
            lines.append("Stat Changes:")
            for stat_name, change in upgrade_value.stat_changes.items():
                if change != 0:
                    sign = "+" if change > 0 else ""
                    lines.append(f"  {stat_name.capitalize()}: {sign}{change:.0f}")

        # Warnings
        if upgrade_value.warnings:
            lines.append("")
            lines.append("⚠️  Warnings:")
            for warning in upgrade_value.warnings:
                lines.append(f"  • {warning}")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def quick_upgrade_check(
    current_gear: GearStats,
    upgrade_gear: GearStats,
    base_stats: Dict[str, Any]
) -> str:
    """
    Quick upgrade check returning recommendation.

    Args:
        current_gear: Current gear
        upgrade_gear: Upgrade gear
        base_stats: Base character stats

    Returns:
        String recommendation (UPGRADE/SKIP/etc.)
    """
    evaluator = GearEvaluator()
    value = evaluator.evaluate_upgrade(current_gear, upgrade_gear, base_stats)
    return value.recommendation.value


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 80)
    print("Path of Exile 2 Gear Evaluator - Test")
    print("=" * 80)
    print()

    # Example: Evaluate helmet upgrade
    current_helmet = GearStats(
        item_name="Old Helmet",
        item_slot="helmet",
        armor=400,
        life=50,
        fire_res=40,
        cold_res=30
    )

    upgrade_helmet = GearStats(
        item_name="New Fancy Helmet",
        item_slot="helmet",
        armor=600,
        life=80,
        fire_res=45,
        cold_res=35,
        lightning_res=25,
        energy_shield=50
    )

    # Base character stats (without helmet)
    base_stats = {
        'level': 91,
        'life': 1400,
        'energy_shield': 4800,
        'armor': 2000,
        'evasion': 500,
        'fire_res': -42,  # Missing the helmet's 40, so negative
        'cold_res': -38,
        'lightning_res': 75,
        'chaos_res': -60,
        'block_chance': 25,
        'strength': 50,
        'dexterity': 120,
        'intelligence': 300
    }

    # Evaluate upgrade
    evaluator = GearEvaluator()
    value = evaluator.evaluate_upgrade(
        current_gear=current_helmet,
        upgrade_gear=upgrade_helmet,
        base_character_stats=base_stats,
        price_chaos=50.0
    )

    # Print formatted report
    report = evaluator.format_upgrade_value(upgrade_helmet, value)
    print(report)

    print()
    print("=" * 80)
    print("Test Complete!")
    print("=" * 80)
