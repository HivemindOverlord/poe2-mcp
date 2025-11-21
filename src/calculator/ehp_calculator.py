"""
Effective Health Pool (EHP) Calculator for Path of Exile 2

This module calculates layered defense effectiveness - the single most important metric
for build survivability. EHP represents the total raw damage a character can sustain
before dying, accounting for ALL defensive layers.

Key PoE2 Mechanics:
==================
1. Defense Layer Order (CRITICAL - different from PoE1):
   - Evasion (chance to avoid hit entirely)
   - Block (chance to completely block hit)
   - Armor (reduces physical damage BEFORE resistances - reversed from PoE1!)
   - Resistances (elemental/chaos damage reduction)
   - Hit taken on Life/ES pool

2. PoE2-Specific Changes:
   - Block cap: 50% (not 75% like PoE1)
   - Chaos damage: Removes 2× ES (not bypass entirely like PoE1)
   - Armor applies BEFORE resistances for physical hits
   - Hit size matters: Armor is more effective vs smaller hits

3. EHP Theory:
   EHP = Raw_HP / (1 - Total_Mitigation)

   Where Total_Mitigation layers multiplicatively:
   - Evasion: 30% evade = 0.30 mitigation
   - Block: 40% block = 0.40 mitigation
   - Together: 1 - (1 - 0.30) × (1 - 0.40) = 0.58 = 58% total mitigation

Author: Claude
Date: 2025-10-22
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

# Import existing calculators
from .defense_calculator import DefenseCalculator, DefenseConstants
from .resource_calculator import ResourceCalculator, AttributeStats

logger = logging.getLogger(__name__)


class DamageType(Enum):
    """Types of damage in Path of Exile 2."""
    PHYSICAL = "physical"
    FIRE = "fire"
    COLD = "cold"
    LIGHTNING = "lightning"
    CHAOS = "chaos"


@dataclass
class DefensiveStats:
    """
    Complete defensive statistics for EHP calculation.

    Attributes:
        life: Total life pool
        energy_shield: Total energy shield pool
        armor: Armor rating (for physical damage reduction)
        evasion: Evasion rating (for hit avoidance)
        block_chance: Block chance % (capped at 50% in PoE2)
        fire_res: Fire resistance %
        cold_res: Cold resistance %
        lightning_res: Lightning resistance %
        chaos_res: Chaos resistance %
        phys_taken_as_elemental: % of physical taken as elemental (reduces armor effectiveness)
    """
    life: float
    energy_shield: float = 0.0
    armor: float = 0.0
    evasion: float = 0.0
    block_chance: float = 0.0
    fire_res: float = 0.0
    cold_res: float = 0.0
    lightning_res: float = 0.0
    chaos_res: float = 0.0
    phys_taken_as_elemental: float = 0.0

    def __post_init__(self):
        """Validate defensive stats."""
        if self.life < 0:
            raise ValueError("Life cannot be negative")
        if self.energy_shield < 0:
            raise ValueError("Energy Shield cannot be negative")
        if self.life + self.energy_shield == 0:
            raise ValueError("Must have some life or energy shield")


@dataclass
class ThreatProfile:
    """
    Defines the incoming threat for EHP calculation.

    Hit size is CRITICAL for armor effectiveness - armor provides more DR
    against smaller hits and less against larger hits.

    Attributes:
        expected_hit_size: Expected raw damage per hit (for armor calculation)
        attacker_accuracy: Attacker accuracy (for evasion calculation)
    """
    expected_hit_size: float = 1000.0  # Default: moderate hit
    attacker_accuracy: float = 2000.0  # Default: moderate accuracy


@dataclass
class EHPResult:
    """
    Result of EHP calculation for a specific damage type.

    Attributes:
        damage_type: Type of damage
        raw_hp: Total life + ES pool
        evade_mitigation: Mitigation from evasion (0-1)
        block_mitigation: Mitigation from block (0-1)
        armor_dr: Damage reduction from armor % (physical only)
        resistance_dr: Damage reduction from resistance %
        total_mitigation: Combined mitigation from all layers (0-1)
        effective_hp: Final EHP value
        layers_breakdown: Detailed breakdown of each layer's contribution
    """
    damage_type: DamageType
    raw_hp: float
    evade_mitigation: float
    block_mitigation: float
    armor_dr: float
    resistance_dr: float
    total_mitigation: float
    effective_hp: float
    layers_breakdown: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DefenseGap:
    """
    Identifies a defensive weakness.

    Attributes:
        gap_type: Type of gap (e.g., "low_resistance", "no_evasion")
        severity: Severity rating (0-10, where 10 is critical)
        description: Human-readable description
        recommendation: Suggested fix
        current_value: Current value of the defense
        recommended_value: Recommended target value
    """
    gap_type: str
    severity: float
    description: str
    recommendation: str
    current_value: float
    recommended_value: float


class EHPCalculator:
    """
    Main EHP calculator implementing PoE2 layered defense mechanics.

    This calculator is essential for:
    1. Build evaluation - comparing defensive effectiveness
    2. Gear upgrade analysis - "is this item worth it?"
    3. Gap identification - finding defensive weaknesses
    4. Content viability - "can I survive endgame?"
    """

    def __init__(self):
        """Initialize EHP calculator with defense calculator."""
        self.defense_calc = DefenseCalculator()
        logger.info("EHPCalculator initialized for Path of Exile 2")

    # ============================================================================
    # CORE EHP CALCULATIONS
    # ============================================================================

    def calculate_ehp(
        self,
        stats: DefensiveStats,
        damage_type: DamageType,
        threat: ThreatProfile
    ) -> EHPResult:
        """
        Calculate Effective Health Pool for a specific damage type.

        This is the core function that layers all defenses according to PoE2 mechanics.

        Layer Order (PoE2):
        1. Evasion (avoidance)
        2. Block (avoidance)
        3. Armor (physical DR) - BEFORE resistances in PoE2!
        4. Resistances (elemental/chaos DR)
        5. Damage taken from Life/ES pool

        Args:
            stats: Character defensive statistics
            damage_type: Type of incoming damage
            threat: Threat profile (hit size, accuracy)

        Returns:
            EHPResult with detailed breakdown

        Example:
            >>> calc = EHPCalculator()
            >>> stats = DefensiveStats(life=5000, energy_shield=2000, armor=10000,
            ...                        fire_res=75, block_chance=40)
            >>> threat = ThreatProfile(expected_hit_size=1000, attacker_accuracy=2000)
            >>> result = calc.calculate_ehp(stats, DamageType.FIRE, threat)
            >>> print(f"Fire EHP: {result.effective_hp:.0f}")
        """
        logger.debug(f"Calculating EHP for {damage_type.value} damage")

        # Step 1: Calculate raw HP pool
        raw_hp = self._calculate_raw_hp(stats, damage_type)

        # Step 2: Calculate evasion mitigation (applies to all damage)
        evade_mitigation = self._calculate_evasion_mitigation(stats, threat)

        # Step 3: Calculate block mitigation (applies to all damage)
        block_mitigation = self._calculate_block_mitigation(stats)

        # Step 4: Calculate armor DR (physical only, BEFORE resistances)
        armor_dr = 0.0
        if damage_type == DamageType.PHYSICAL:
            armor_dr = self._calculate_armor_dr(stats, threat)

        # Step 5: Calculate resistance DR
        resistance_dr = self._calculate_resistance_dr(stats, damage_type)

        # Step 6: Layer all defenses multiplicatively
        # Formula: Total_Mitigation = 1 - (1 - evade) × (1 - block) × (1 - armor) × (1 - res)
        hit_multiplier = (1 - evade_mitigation) * (1 - block_mitigation)

        # For physical: armor applies before resistance
        if damage_type == DamageType.PHYSICAL:
            damage_multiplier = hit_multiplier * (1 - armor_dr) * (1 - resistance_dr)
        else:
            damage_multiplier = hit_multiplier * (1 - resistance_dr)

        total_mitigation = 1 - damage_multiplier

        # Step 7: Calculate EHP
        if damage_multiplier > 0:
            effective_hp = raw_hp / damage_multiplier
        else:
            effective_hp = float('inf')

        # Build detailed breakdown
        layers_breakdown = {
            'raw_hp': raw_hp,
            'evasion': {
                'mitigation_percent': evade_mitigation * 100,
                'multiplier': 1 / (1 - evade_mitigation) if evade_mitigation < 1 else float('inf')
            },
            'block': {
                'chance_percent': stats.block_chance,
                'effective_chance_percent': min(stats.block_chance, DefenseConstants.BLOCK_MAX_CHANCE),
                'mitigation_percent': block_mitigation * 100,
                'multiplier': 1 / (1 - block_mitigation) if block_mitigation < 1 else float('inf')
            },
            'armor': {
                'rating': stats.armor,
                'dr_percent': armor_dr * 100,
                'vs_hit_size': threat.expected_hit_size,
                'multiplier': 1 / (1 - armor_dr) if armor_dr < 1 else float('inf')
            } if damage_type == DamageType.PHYSICAL else None,
            'resistance': {
                'value_percent': self._get_resistance_value(stats, damage_type),
                'dr_percent': resistance_dr * 100,
                'multiplier': 1 / (1 - resistance_dr) if resistance_dr < 1 else float('inf')
            },
            'combined': {
                'total_mitigation_percent': total_mitigation * 100,
                'total_multiplier': effective_hp / raw_hp if raw_hp > 0 else 0
            }
        }

        result = EHPResult(
            damage_type=damage_type,
            raw_hp=raw_hp,
            evade_mitigation=evade_mitigation,
            block_mitigation=block_mitigation,
            armor_dr=armor_dr,
            resistance_dr=resistance_dr,
            total_mitigation=total_mitigation,
            effective_hp=effective_hp,
            layers_breakdown=layers_breakdown
        )

        logger.info(
            f"{damage_type.value.upper()} EHP: {raw_hp:.0f} raw HP -> "
            f"{effective_hp:.0f} EHP ({total_mitigation*100:.1f}% mitigation)"
        )

        return result

    def calculate_all_ehp(
        self,
        stats: DefensiveStats,
        threat: ThreatProfile
    ) -> Dict[DamageType, EHPResult]:
        """
        Calculate EHP for all damage types.

        This gives a complete picture of defensive effectiveness.

        Args:
            stats: Character defensive statistics
            threat: Threat profile

        Returns:
            Dictionary mapping damage types to EHP results

        Example:
            >>> calc = EHPCalculator()
            >>> stats = DefensiveStats(life=5000, armor=10000, fire_res=75, cold_res=75)
            >>> threat = ThreatProfile(expected_hit_size=1000)
            >>> results = calc.calculate_all_ehp(stats, threat)
            >>> for dmg_type, result in results.items():
            ...     print(f"{dmg_type.value}: {result.effective_hp:.0f} EHP")
        """
        results = {}
        for damage_type in DamageType:
            results[damage_type] = self.calculate_ehp(stats, damage_type, threat)

        logger.info("Calculated EHP for all damage types")
        return results

    # ============================================================================
    # HIT SIZE ANALYSIS
    # ============================================================================

    def analyze_armor_vs_hit_sizes(
        self,
        stats: DefensiveStats,
        hit_sizes: Optional[List[float]] = None
    ) -> Dict[float, Dict[str, float]]:
        """
        Analyze armor effectiveness against different hit sizes.

        This is CRITICAL in PoE2 because armor is more effective against
        many small hits than few large hits.

        Args:
            stats: Character defensive statistics
            hit_sizes: List of hit sizes to test (default: common values)

        Returns:
            Dictionary mapping hit sizes to armor effectiveness data

        Example:
            >>> calc = EHPCalculator()
            >>> stats = DefensiveStats(life=5000, armor=20000)
            >>> analysis = calc.analyze_armor_vs_hit_sizes(stats)
            >>> for hit_size, data in analysis.items():
            ...     print(f"{hit_size} damage: {data['dr_percent']:.1f}% DR")
        """
        if hit_sizes is None:
            # Default hit sizes: small, medium, large, huge
            hit_sizes = [500, 1000, 2000, 5000, 10000]

        analysis = {}
        for hit_size in hit_sizes:
            armor_result = self.defense_calc.calculate_armor_dr(stats.armor, hit_size)

            # Calculate EHP for this hit size
            threat = ThreatProfile(expected_hit_size=hit_size, attacker_accuracy=2000)
            ehp_result = self.calculate_ehp(
                stats,
                DamageType.PHYSICAL,
                threat
            )

            analysis[hit_size] = {
                'armor_rating': stats.armor,
                'dr_percent': armor_result.damage_reduction_percent,
                'effective_damage': armor_result.effective_damage,
                'is_capped': armor_result.is_capped,
                'physical_ehp': ehp_result.effective_hp,
                'ehp_per_1000_armor': (ehp_result.effective_hp / (stats.armor / 1000)) if stats.armor > 0 else 0
            }

        logger.info(f"Analyzed armor effectiveness against {len(hit_sizes)} hit sizes")
        return analysis

    def find_armor_breakpoints(
        self,
        stats: DefensiveStats,
        target_dr_values: Optional[List[float]] = None
    ) -> Dict[float, float]:
        """
        Find armor values needed to achieve target DR against expected hit size.

        Useful for gear planning: "How much armor do I need for 50% DR?"

        Args:
            stats: Character defensive statistics (for context)
            target_dr_values: List of target DR % values (default: 25, 50, 75)

        Returns:
            Dictionary mapping target DR to required armor

        Example:
            >>> calc = EHPCalculator()
            >>> stats = DefensiveStats(life=5000)
            >>> threat = ThreatProfile(expected_hit_size=2000)
            >>> breakpoints = calc.find_armor_breakpoints(stats)
            >>> for dr, armor in breakpoints.items():
            ...     print(f"{dr}% DR needs {armor:.0f} armor")
        """
        if target_dr_values is None:
            target_dr_values = [25.0, 50.0, 75.0, 85.0, 90.0]

        # Use default threat profile's hit size
        threat = ThreatProfile()
        hit_size = threat.expected_hit_size

        breakpoints = {}
        for target_dr in target_dr_values:
            if target_dr >= DefenseConstants.ARMOR_MAX_DR:
                breakpoints[target_dr] = float('inf')
            else:
                armor_needed = self.defense_calc.armor_needed_for_dr(target_dr, hit_size)
                breakpoints[target_dr] = armor_needed

        logger.info(f"Calculated armor breakpoints for {len(target_dr_values)} DR targets vs {hit_size} hit size")
        return breakpoints

    # ============================================================================
    # DEFENSE GAP IDENTIFICATION
    # ============================================================================

    def identify_defense_gaps(
        self,
        stats: DefensiveStats,
        threat: ThreatProfile
    ) -> List[DefenseGap]:
        """
        Identify defensive weaknesses and provide recommendations.

        This is invaluable for build improvement - shows exactly where
        your defenses are weak and how to fix them.

        Checks:
        1. Uncapped resistances (critical!)
        2. Low HP pool (< 3000 life+ES)
        3. No layered defenses (only HP)
        4. Block over-investment (>50% wasted)
        5. Armor ineffectiveness (poor vs large hits)
        6. Chaos resistance gap (common oversight)

        Args:
            stats: Character defensive statistics
            threat: Threat profile

        Returns:
            List of DefenseGap objects, sorted by severity (highest first)

        Example:
            >>> calc = EHPCalculator()
            >>> stats = DefensiveStats(life=3000, fire_res=50, chaos_res=-60)
            >>> gaps = calc.identify_defense_gaps(stats, ThreatProfile())
            >>> for gap in gaps:
            ...     print(f"[{gap.severity}/10] {gap.description}")
        """
        gaps = []

        # Check 1: Resistance caps (CRITICAL)
        resistances = {
            'fire': (stats.fire_res, DamageType.FIRE),
            'cold': (stats.cold_res, DamageType.COLD),
            'lightning': (stats.lightning_res, DamageType.LIGHTNING),
            'chaos': (stats.chaos_res, DamageType.CHAOS)
        }

        for res_name, (res_value, dmg_type) in resistances.items():
            cap = DefenseConstants.RESISTANCE_DEFAULT_CAP

            if res_value < cap:
                deficit = cap - res_value
                severity = min(10.0, (deficit / 10.0))  # 10% deficit = 1 severity

                # Chaos res is less critical
                if res_name == 'chaos':
                    severity *= 0.5

                gaps.append(DefenseGap(
                    gap_type=f"uncapped_{res_name}_resistance",
                    severity=severity,
                    description=f"{res_name.capitalize()} resistance is {deficit:.0f}% below cap",
                    recommendation=f"Increase {res_name} resistance by {deficit:.0f}% to reach {cap}% cap",
                    current_value=res_value,
                    recommended_value=cap
                ))

        # Check 2: HP pool (life + ES)
        total_hp = stats.life + stats.energy_shield
        min_hp_endgame = 3000.0

        if total_hp < min_hp_endgame:
            deficit = min_hp_endgame - total_hp
            severity = min(10.0, (deficit / 500.0))  # 500 HP deficit = 1 severity

            gaps.append(DefenseGap(
                gap_type="low_hp_pool",
                severity=severity,
                description=f"Total HP pool ({total_hp:.0f}) is below recommended minimum ({min_hp_endgame:.0f})",
                recommendation=f"Increase life and/or energy shield by {deficit:.0f} total",
                current_value=total_hp,
                recommended_value=min_hp_endgame
            ))

        # Check 3: No layered defenses
        has_armor = stats.armor >= 5000
        has_evasion = stats.evasion >= 3000
        has_block = stats.block_chance >= 20
        has_es = stats.energy_shield >= 500

        defense_layers = sum([has_armor, has_evasion, has_block, has_es])

        if defense_layers == 0:
            gaps.append(DefenseGap(
                gap_type="no_layered_defenses",
                severity=8.0,
                description="No meaningful layered defenses (only relying on resistances and HP)",
                recommendation="Invest in at least one additional defense layer: armor, evasion, block, or ES",
                current_value=0,
                recommended_value=1
            ))
        elif defense_layers == 1:
            gaps.append(DefenseGap(
                gap_type="single_defense_layer",
                severity=4.0,
                description="Only one defense layer present",
                recommendation="Consider adding a second defense layer for better survivability",
                current_value=1,
                recommended_value=2
            ))

        # Check 4: Block over-investment
        if stats.block_chance > DefenseConstants.BLOCK_MAX_CHANCE:
            waste = stats.block_chance - DefenseConstants.BLOCK_MAX_CHANCE
            severity = min(5.0, waste / 10.0)

            gaps.append(DefenseGap(
                gap_type="overcapped_block",
                severity=severity,
                description=f"Block chance ({stats.block_chance:.0f}%) exceeds cap ({DefenseConstants.BLOCK_MAX_CHANCE}%), wasting {waste:.0f}%",
                recommendation=f"Reallocate {waste:.0f}% block chance to other defenses",
                current_value=stats.block_chance,
                recommended_value=DefenseConstants.BLOCK_MAX_CHANCE
            ))

        # Check 5: Armor effectiveness vs large hits
        if stats.armor > 0:
            large_hit = 5000.0
            armor_result = self.defense_calc.calculate_armor_dr(stats.armor, large_hit)

            if armor_result.damage_reduction_percent < 30.0:
                severity = 5.0
                gaps.append(DefenseGap(
                    gap_type="armor_ineffective_vs_large_hits",
                    severity=severity,
                    description=f"Armor provides only {armor_result.damage_reduction_percent:.1f}% DR against large hits ({large_hit:.0f} damage)",
                    recommendation="Consider supplementing armor with other defenses for one-shot protection",
                    current_value=armor_result.damage_reduction_percent,
                    recommended_value=50.0
                ))

        # Check 6: Chaos resistance (special case - common oversight)
        if stats.chaos_res < 0:
            severity = min(6.0, abs(stats.chaos_res) / 20.0)

            gaps.append(DefenseGap(
                gap_type="negative_chaos_resistance",
                severity=severity,
                description=f"Negative chaos resistance ({stats.chaos_res:.0f}%) amplifies chaos damage",
                recommendation=f"Increase chaos resistance by {abs(stats.chaos_res):.0f}% to reach 0% minimum",
                current_value=stats.chaos_res,
                recommended_value=0.0
            ))

        # Check 7: Evasion with no accuracy check
        if stats.evasion > 0:
            evasion_result = self.defense_calc.calculate_evasion_chance(
                stats.evasion,
                threat.attacker_accuracy
            )

            if evasion_result.evade_chance_percent < 30.0:
                severity = 3.0
                gaps.append(DefenseGap(
                    gap_type="low_evasion_effectiveness",
                    severity=severity,
                    description=f"Evasion provides only {evasion_result.evade_chance_percent:.1f}% evade chance vs expected accuracy",
                    recommendation="Increase evasion rating or consider alternative defenses",
                    current_value=evasion_result.evade_chance_percent,
                    recommended_value=50.0
                ))

        # Sort by severity (highest first)
        gaps.sort(key=lambda g: g.severity, reverse=True)

        logger.info(f"Identified {len(gaps)} defense gaps")
        return gaps

    # ============================================================================
    # COMPARISON & OPTIMIZATION
    # ============================================================================

    def compare_upgrade(
        self,
        current_stats: DefensiveStats,
        upgraded_stats: DefensiveStats,
        threat: ThreatProfile
    ) -> Dict[str, Any]:
        """
        Compare EHP before and after a gear/passive upgrade.

        Essential for answering: "Is this upgrade worth it?"

        Args:
            current_stats: Current defensive statistics
            upgraded_stats: Statistics after upgrade
            threat: Threat profile

        Returns:
            Dictionary with comparison data for all damage types

        Example:
            >>> calc = EHPCalculator()
            >>> current = DefensiveStats(life=5000, armor=10000, fire_res=70)
            >>> upgraded = DefensiveStats(life=5000, armor=10000, fire_res=75)
            >>> comparison = calc.compare_upgrade(current, upgraded, ThreatProfile())
            >>> print(f"Fire EHP gain: +{comparison['fire']['absolute_gain']:.0f}")
        """
        current_ehp = self.calculate_all_ehp(current_stats, threat)
        upgraded_ehp = self.calculate_all_ehp(upgraded_stats, threat)

        comparison = {}
        for damage_type in DamageType:
            current = current_ehp[damage_type]
            upgraded = upgraded_ehp[damage_type]

            absolute_gain = upgraded.effective_hp - current.effective_hp

            if current.effective_hp > 0:
                percent_gain = (absolute_gain / current.effective_hp) * 100
            else:
                percent_gain = float('inf') if absolute_gain > 0 else 0

            comparison[damage_type.value] = {
                'current_ehp': current.effective_hp,
                'upgraded_ehp': upgraded.effective_hp,
                'absolute_gain': absolute_gain,
                'percent_gain': percent_gain,
                'mitigation_increase': (upgraded.total_mitigation - current.total_mitigation) * 100
            }

        # Calculate average improvement
        valid_gains = [
            data['percent_gain'] for data in comparison.values()
            if data['percent_gain'] != float('inf')
        ]

        comparison['summary'] = {
            'average_percent_gain': sum(valid_gains) / len(valid_gains) if valid_gains else 0,
            'worst_case_type': min(comparison.keys(), key=lambda k: comparison[k]['upgraded_ehp']),
            'best_case_type': max(comparison.keys(), key=lambda k: comparison[k]['upgraded_ehp'])
        }

        logger.info(
            f"Upgrade comparison: average {comparison['summary']['average_percent_gain']:.1f}% EHP gain"
        )

        return comparison

    def calculate_defense_value(
        self,
        stats: DefensiveStats,
        defense_type: str,
        increase_amount: float,
        threat: ThreatProfile,
        target_damage_type: Optional[DamageType] = None
    ) -> Dict[str, float]:
        """
        Calculate how much EHP gain you'd get from increasing a specific defense.

        Answers questions like:
        - "How much EHP would +1000 armor give me?"
        - "Is +5% fire res better than +500 life?"

        Args:
            stats: Current defensive statistics
            defense_type: Type of defense to increase ('armor', 'life', 'fire_res', etc.)
            increase_amount: Amount to increase by
            threat: Threat profile
            target_damage_type: Specific damage type to check (None = check all)

        Returns:
            Dictionary with EHP gain data

        Example:
            >>> calc = EHPCalculator()
            >>> stats = DefensiveStats(life=5000, armor=10000, fire_res=70)
            >>> value = calc.calculate_defense_value(stats, 'armor', 2000, ThreatProfile())
            >>> print(f"+2000 armor = +{value['physical_ehp_gain']:.0f} physical EHP")
        """
        # Create upgraded stats
        upgraded = DefensiveStats(
            life=stats.life,
            energy_shield=stats.energy_shield,
            armor=stats.armor,
            evasion=stats.evasion,
            block_chance=stats.block_chance,
            fire_res=stats.fire_res,
            cold_res=stats.cold_res,
            lightning_res=stats.lightning_res,
            chaos_res=stats.chaos_res
        )

        # Apply increase
        if defense_type == 'life':
            upgraded.life += increase_amount
        elif defense_type == 'energy_shield':
            upgraded.energy_shield += increase_amount
        elif defense_type == 'armor':
            upgraded.armor += increase_amount
        elif defense_type == 'evasion':
            upgraded.evasion += increase_amount
        elif defense_type == 'block_chance':
            upgraded.block_chance += increase_amount
        elif defense_type == 'fire_res':
            upgraded.fire_res += increase_amount
        elif defense_type == 'cold_res':
            upgraded.cold_res += increase_amount
        elif defense_type == 'lightning_res':
            upgraded.lightning_res += increase_amount
        elif defense_type == 'chaos_res':
            upgraded.chaos_res += increase_amount
        else:
            raise ValueError(f"Unknown defense type: {defense_type}")

        # Calculate comparison
        comparison = self.compare_upgrade(stats, upgraded, threat)

        # Format result
        result = {
            'defense_type': defense_type,
            'increase_amount': increase_amount,
        }

        if target_damage_type:
            key = target_damage_type.value
            result['ehp_gain'] = comparison[key]['absolute_gain']
            result['percent_gain'] = comparison[key]['percent_gain']
        else:
            # Include all damage types
            for damage_type in DamageType:
                key = damage_type.value
                result[f'{key}_ehp_gain'] = comparison[key]['absolute_gain']
                result[f'{key}_percent_gain'] = comparison[key]['percent_gain']

        logger.info(
            f"Defense value: +{increase_amount} {defense_type} = "
            f"+{result.get('ehp_gain', 'varies')} EHP"
        )

        return result

    # ============================================================================
    # HELPER METHODS
    # ============================================================================

    def _calculate_raw_hp(
        self,
        stats: DefensiveStats,
        damage_type: DamageType
    ) -> float:
        """
        Calculate raw HP pool accounting for PoE2 chaos mechanics.

        PoE2 Change: Chaos damage removes 2× ES (not bypass entirely)
        """
        if damage_type == DamageType.CHAOS:
            # PoE2: Chaos removes ES at 2× rate
            effective_es = stats.energy_shield / 2.0
            return stats.life + effective_es
        else:
            return stats.life + stats.energy_shield

    def _calculate_evasion_mitigation(
        self,
        stats: DefensiveStats,
        threat: ThreatProfile
    ) -> float:
        """Calculate mitigation from evasion (chance to avoid hit)."""
        if stats.evasion == 0:
            return 0.0

        evasion_result = self.defense_calc.calculate_evasion_chance(
            stats.evasion,
            threat.attacker_accuracy
        )

        return evasion_result.evade_chance_percent / 100.0

    def _calculate_block_mitigation(
        self,
        stats: DefensiveStats
    ) -> float:
        """Calculate mitigation from block (chance to avoid hit)."""
        if stats.block_chance == 0:
            return 0.0

        block_result = self.defense_calc.calculate_block_chance(stats.block_chance)
        return block_result.block_chance_percent / 100.0

    def _calculate_armor_dr(
        self,
        stats: DefensiveStats,
        threat: ThreatProfile
    ) -> float:
        """Calculate damage reduction from armor (physical only)."""
        if stats.armor == 0:
            return 0.0

        armor_result = self.defense_calc.calculate_armor_dr(
            stats.armor,
            threat.expected_hit_size
        )

        return armor_result.damage_reduction_percent / 100.0

    def _calculate_resistance_dr(
        self,
        stats: DefensiveStats,
        damage_type: DamageType
    ) -> float:
        """Calculate damage reduction from resistance."""
        resistance_value = self._get_resistance_value(stats, damage_type)

        res_result = self.defense_calc.calculate_resistance_dr(resistance_value)
        return res_result.damage_reduction_percent / 100.0

    def _get_resistance_value(
        self,
        stats: DefensiveStats,
        damage_type: DamageType
    ) -> float:
        """Get resistance value for a specific damage type."""
        resistance_map = {
            DamageType.PHYSICAL: 0.0,  # No physical resistance
            DamageType.FIRE: stats.fire_res,
            DamageType.COLD: stats.cold_res,
            DamageType.LIGHTNING: stats.lightning_res,
            DamageType.CHAOS: stats.chaos_res
        }

        return resistance_map.get(damage_type, 0.0)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def quick_physical_ehp(
    life: float,
    armor: float,
    block_chance: float = 0.0,
    hit_size: float = 1000.0
) -> float:
    """
    Quick physical EHP calculation.

    Args:
        life: Life pool
        armor: Armor rating
        block_chance: Block chance %
        hit_size: Expected hit size

    Returns:
        Physical EHP
    """
    calc = EHPCalculator()
    stats = DefensiveStats(life=life, armor=armor, block_chance=block_chance)
    threat = ThreatProfile(expected_hit_size=hit_size)
    result = calc.calculate_ehp(stats, DamageType.PHYSICAL, threat)
    return result.effective_hp


def quick_elemental_ehp(
    life: float,
    resistance: float,
    block_chance: float = 0.0
) -> float:
    """
    Quick elemental EHP calculation.

    Args:
        life: Life pool
        resistance: Elemental resistance %
        block_chance: Block chance %

    Returns:
        Elemental EHP
    """
    calc = EHPCalculator()
    stats = DefensiveStats(life=life, fire_res=resistance, block_chance=block_chance)
    threat = ThreatProfile()
    result = calc.calculate_ehp(stats, DamageType.FIRE, threat)
    return result.effective_hp


if __name__ == '__main__':
    # Example usage and testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 80)
    print("Path of Exile 2 - Effective Health Pool (EHP) Calculator")
    print("=" * 80)
    print()

    # Create calculator
    calc = EHPCalculator()

    # Example 1: Balanced defense character
    print("-" * 80)
    print("EXAMPLE 1: Balanced Defense Character")
    print("-" * 80)

    balanced_stats = DefensiveStats(
        life=5000,
        energy_shield=2000,
        armor=15000,
        evasion=3000,
        block_chance=40,
        fire_res=75,
        cold_res=75,
        lightning_res=75,
        chaos_res=20
    )

    threat = ThreatProfile(expected_hit_size=2000, attacker_accuracy=2500)

    all_ehp = calc.calculate_all_ehp(balanced_stats, threat)

    print(f"\nCharacter Stats:")
    print(f"  Life: {balanced_stats.life:.0f}")
    print(f"  Energy Shield: {balanced_stats.energy_shield:.0f}")
    print(f"  Armor: {balanced_stats.armor:.0f}")
    print(f"  Evasion: {balanced_stats.evasion:.0f}")
    print(f"  Block: {balanced_stats.block_chance:.0f}%")
    print(f"  Fire/Cold/Lightning Res: {balanced_stats.fire_res:.0f}%")
    print(f"  Chaos Res: {balanced_stats.chaos_res:.0f}%")
    print(f"\nThreat Profile:")
    print(f"  Expected Hit Size: {threat.expected_hit_size:.0f}")
    print(f"  Attacker Accuracy: {threat.attacker_accuracy:.0f}")

    print(f"\nEffective Health Pool by Damage Type:")
    for damage_type, result in all_ehp.items():
        print(f"  {damage_type.value.upper()}: {result.effective_hp:.0f} EHP "
              f"({result.total_mitigation*100:.1f}% mitigation)")

    print(f"\nPhysical Damage Breakdown:")
    phys_result = all_ehp[DamageType.PHYSICAL]
    print(f"  Raw HP: {phys_result.raw_hp:.0f}")
    print(f"  Evasion: {phys_result.evade_mitigation*100:.1f}% mitigation")
    print(f"  Block: {phys_result.block_mitigation*100:.1f}% mitigation")
    print(f"  Armor: {phys_result.armor_dr*100:.1f}% DR vs {threat.expected_hit_size:.0f} hit")
    print(f"  Total: {phys_result.effective_hp:.0f} EHP")

    # Example 2: Hit size analysis
    print("\n" + "-" * 80)
    print("EXAMPLE 2: Armor Effectiveness vs Hit Size")
    print("-" * 80)

    hit_analysis = calc.analyze_armor_vs_hit_sizes(balanced_stats)

    print(f"\nArmor Rating: {balanced_stats.armor:.0f}")
    print(f"\nEffectiveness by Hit Size:")
    for hit_size, data in hit_analysis.items():
        print(f"  {hit_size:.0f} damage: {data['dr_percent']:.1f}% DR -> "
              f"{data['physical_ehp']:.0f} Physical EHP")

    # Example 3: Defense gap identification
    print("\n" + "-" * 80)
    print("EXAMPLE 3: Defense Gap Identification")
    print("-" * 80)

    # Create a character with some issues
    flawed_stats = DefensiveStats(
        life=3500,
        energy_shield=0,
        armor=5000,
        evasion=0,
        block_chance=15,
        fire_res=60,
        cold_res=75,
        lightning_res=55,
        chaos_res=-30
    )

    gaps = calc.identify_defense_gaps(flawed_stats, threat)

    print(f"\nIdentified {len(gaps)} defense gaps:\n")
    for gap in gaps:
        print(f"[Severity: {gap.severity:.1f}/10] {gap.gap_type}")
        print(f"  Issue: {gap.description}")
        print(f"  Fix: {gap.recommendation}")
        print()

    # Example 4: Upgrade comparison
    print("-" * 80)
    print("EXAMPLE 4: Gear Upgrade Comparison")
    print("-" * 80)

    current = DefensiveStats(
        life=5000,
        energy_shield=1500,
        armor=12000,
        fire_res=70,
        cold_res=75,
        lightning_res=75,
        chaos_res=10
    )

    # Comparing two upgrade options
    option_a = DefensiveStats(
        life=5000,
        energy_shield=1500,
        armor=15000,  # +3000 armor
        fire_res=70,
        cold_res=75,
        lightning_res=75,
        chaos_res=10
    )

    option_b = DefensiveStats(
        life=5000,
        energy_shield=1500,
        armor=12000,
        fire_res=75,  # +5% fire res (capped)
        cold_res=75,
        lightning_res=75,
        chaos_res=10
    )

    print("\nOption A: +3000 Armor")
    comparison_a = calc.compare_upgrade(current, option_a, threat)
    for damage_type in ['physical', 'fire']:
        data = comparison_a[damage_type]
        print(f"  {damage_type.upper()}: {data['current_ehp']:.0f} -> {data['upgraded_ehp']:.0f} "
              f"(+{data['absolute_gain']:.0f}, +{data['percent_gain']:.1f}%)")

    print("\nOption B: Fire Res 70% -> 75%")
    comparison_b = calc.compare_upgrade(current, option_b, threat)
    for damage_type in ['physical', 'fire']:
        data = comparison_b[damage_type]
        print(f"  {damage_type.upper()}: {data['current_ehp']:.0f} -> {data['upgraded_ehp']:.0f} "
              f"(+{data['absolute_gain']:.0f}, +{data['percent_gain']:.1f}%)")

    # Example 5: Defense value calculation
    print("\n" + "-" * 80)
    print("EXAMPLE 5: Defense Value Analysis")
    print("-" * 80)

    base_stats = DefensiveStats(
        life=4500,
        armor=10000,
        block_chance=30,
        fire_res=75,
        cold_res=75,
        lightning_res=75,
        chaos_res=0
    )

    print("\nHow much EHP would various upgrades provide?")
    print("(vs 1000 damage hits)")

    upgrades = [
        ('life', 500),
        ('armor', 5000),
        ('block_chance', 10),
        ('fire_res', 5)
    ]

    for defense_type, amount in upgrades:
        value = calc.calculate_defense_value(
            base_stats,
            defense_type,
            amount,
            ThreatProfile(expected_hit_size=1000)
        )

        print(f"\n+{amount} {defense_type}:")
        if 'physical_ehp_gain' in value:
            print(f"  Physical: +{value['physical_ehp_gain']:.0f} EHP ({value['physical_percent_gain']:.1f}%)")
            print(f"  Fire: +{value['fire_ehp_gain']:.0f} EHP ({value['fire_percent_gain']:.1f}%)")
        else:
            print(f"  EHP Gain: +{value['ehp_gain']:.0f} ({value['percent_gain']:.1f}%)")

    # Example 6: Armor breakpoints
    print("\n" + "-" * 80)
    print("EXAMPLE 6: Armor Breakpoints")
    print("-" * 80)

    breakpoints = calc.find_armor_breakpoints(base_stats)

    print(f"\nArmor needed for target DR (vs {ThreatProfile().expected_hit_size:.0f} damage hits):")
    for dr, armor_needed in breakpoints.items():
        if armor_needed == float('inf'):
            print(f"  {dr:.0f}% DR: Cannot reach (exceeds 90% cap)")
        else:
            print(f"  {dr:.0f}% DR: {armor_needed:.0f} armor")

    # Example 7: Quick functions
    print("\n" + "-" * 80)
    print("EXAMPLE 7: Quick Calculations")
    print("-" * 80)

    print("\nQuick Physical EHP:")
    phys_ehp = quick_physical_ehp(life=5000, armor=20000, block_chance=40, hit_size=2000)
    print(f"  5000 life, 20000 armor, 40% block vs 2000 hit: {phys_ehp:.0f} EHP")

    print("\nQuick Elemental EHP:")
    ele_ehp = quick_elemental_ehp(life=5000, resistance=75, block_chance=40)
    print(f"  5000 life, 75% res, 40% block: {ele_ehp:.0f} EHP")

    print("\n" + "=" * 80)
    print("EHP Calculator Test Complete!")
    print("=" * 80)
