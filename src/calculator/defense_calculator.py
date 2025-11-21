"""
Defense Calculator Module for Path of Exile 2

This module provides comprehensive defense calculations including:
- Armor damage reduction (PoE2-specific formula)
- Evasion chance calculations (PoE2-specific formula)
- Energy Shield recharge mechanics (PoE2: 12.5%/sec, 4s delay)
- Resistance damage reduction
- Block chance calculations (PoE2: 50% cap)

All formulas are specific to Path of Exile 2 and differ from PoE1 in key areas.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# PoE2 Constants
class DefenseConstants:
    """Path of Exile 2 defense constants and caps."""

    # Armor
    ARMOR_MAX_DR = 90.0  # Maximum damage reduction from armor (%)
    ARMOR_MULTIPLIER = 10  # Armor formula multiplier

    # Evasion
    EVASION_MIN_HIT_CHANCE = 5.0  # Minimum hit chance (%)
    EVASION_MAX_HIT_CHANCE = 100.0  # Maximum hit chance (%)
    EVASION_ACCURACY_MULTIPLIER = 1.25  # Accuracy multiplier in formula
    EVASION_DIVISOR = 0.3  # Evasion divisor in formula

    # Energy Shield
    ES_BASE_RECHARGE_RATE = 12.5  # Base recharge rate (%/second) - PoE2 specific
    ES_BASE_DELAY = 4.0  # Base delay before recharge starts (seconds) - PoE2 specific
    ES_DELAY_BASE_VALUE = 400  # Base value for delay calculation
    ES_DELAY_DIVISOR_BASE = 100  # Base divisor for delay calculation

    # Resistances
    RESISTANCE_DEFAULT_CAP = 75.0  # Default resistance cap (%)
    RESISTANCE_HARD_CAP = 90.0  # Hard resistance cap (%)
    RESISTANCE_MIN = -200.0  # Practical minimum resistance (%)

    # Block
    BLOCK_MAX_CHANCE = 50.0  # Maximum block chance (%) - PoE2 specific (not 75% like PoE1)
    BLOCK_MIN_CHANCE = 0.0  # Minimum block chance (%)


@dataclass
class ArmorResult:
    """Result of armor damage reduction calculation."""
    armor: float
    raw_damage: float
    damage_reduction_percent: float
    effective_damage: float
    is_capped: bool


@dataclass
class EvasionResult:
    """Result of evasion chance calculation."""
    evasion: float
    accuracy: float
    hit_chance_percent: float
    evade_chance_percent: float
    is_hit_capped: bool


@dataclass
class EnergyShieldResult:
    """Result of energy shield recharge calculation."""
    max_es: float
    recharge_rate_percent: float
    recharge_per_second: float
    delay_seconds: float
    time_to_full_seconds: float


@dataclass
class ResistanceResult:
    """Result of resistance damage reduction calculation."""
    resistance_percent: float
    damage_taken_multiplier: float
    damage_reduction_percent: float
    is_capped: bool
    is_over_cap: bool


@dataclass
class BlockResult:
    """Result of block chance calculation."""
    block_chance_percent: float
    is_capped: bool


class DefenseCalculator:
    """
    Main defense calculator for Path of Exile 2.

    Implements all PoE2-specific defense formulas with proper caps,
    validation, and detailed result objects.
    """

    def __init__(self):
        """Initialize the defense calculator."""
        logger.info("DefenseCalculator initialized for Path of Exile 2")

    # ============================================================================
    # ARMOR CALCULATIONS (PoE2)
    # ============================================================================

    def calculate_armor_dr(
        self,
        armor: float,
        raw_damage: float
    ) -> ArmorResult:
        """
        Calculate damage reduction from armor using PoE2 formula.

        PoE2 Formula:
            DR = A / (A + 10 × D_raw)
            Max DR: 90%

        Args:
            armor: Total armor value
            raw_damage: Raw incoming physical damage

        Returns:
            ArmorResult containing damage reduction and effective damage

        Example:
            >>> calc = DefenseCalculator()
            >>> result = calc.calculate_armor_dr(5000, 1000)
            >>> print(f"DR: {result.damage_reduction_percent:.2f}%")
            DR: 33.33%
        """
        if armor < 0:
            logger.warning(f"Negative armor value: {armor}, treating as 0")
            armor = 0

        if raw_damage <= 0:
            logger.warning(f"Invalid raw damage: {raw_damage}, treating as 0")
            return ArmorResult(
                armor=armor,
                raw_damage=raw_damage,
                damage_reduction_percent=0.0,
                effective_damage=0.0,
                is_capped=False
            )

        # PoE2 armor formula: DR = A / (A + 10 × D_raw)
        denominator = armor + (DefenseConstants.ARMOR_MULTIPLIER * raw_damage)
        dr_percent = (armor / denominator) * 100 if denominator > 0 else 0.0

        # Apply cap
        is_capped = dr_percent > DefenseConstants.ARMOR_MAX_DR
        if is_capped:
            dr_percent = DefenseConstants.ARMOR_MAX_DR
            logger.debug(f"Armor DR capped at {DefenseConstants.ARMOR_MAX_DR}%")

        # Calculate effective damage
        effective_damage = raw_damage * (1 - dr_percent / 100)

        logger.debug(
            f"Armor DR: {armor} armor vs {raw_damage} damage = "
            f"{dr_percent:.2f}% DR, {effective_damage:.2f} effective damage"
        )

        return ArmorResult(
            armor=armor,
            raw_damage=raw_damage,
            damage_reduction_percent=dr_percent,
            effective_damage=effective_damage,
            is_capped=is_capped
        )

    def armor_needed_for_dr(
        self,
        target_dr_percent: float,
        raw_damage: float
    ) -> float:
        """
        Calculate armor needed to achieve target damage reduction.

        Rearranged PoE2 formula:
            A = (DR × 10 × D_raw) / (1 - DR)

        Args:
            target_dr_percent: Target damage reduction (%)
            raw_damage: Raw incoming physical damage

        Returns:
            Armor value needed

        Example:
            >>> calc = DefenseCalculator()
            >>> armor = calc.armor_needed_for_dr(50, 1000)
            >>> print(f"Need {armor:.0f} armor for 50% DR vs 1000 damage")
        """
        if target_dr_percent <= 0:
            return 0.0

        if target_dr_percent >= DefenseConstants.ARMOR_MAX_DR:
            logger.warning(
                f"Target DR {target_dr_percent}% >= cap {DefenseConstants.ARMOR_MAX_DR}%, "
                "returning armor for max DR"
            )
            target_dr_percent = DefenseConstants.ARMOR_MAX_DR - 0.01

        if raw_damage <= 0:
            logger.warning("Raw damage <= 0, cannot calculate armor needed")
            return 0.0

        # Rearrange: DR = A / (A + 10D) -> A = (DR × 10D) / (1 - DR)
        dr_decimal = target_dr_percent / 100
        armor_needed = (dr_decimal * DefenseConstants.ARMOR_MULTIPLIER * raw_damage) / (1 - dr_decimal)

        logger.debug(
            f"Armor needed: {armor_needed:.0f} for {target_dr_percent}% DR vs {raw_damage} damage"
        )

        return armor_needed

    def armor_comparison(
        self,
        armor: float,
        damage_values: list[float]
    ) -> Dict[float, ArmorResult]:
        """
        Calculate armor effectiveness against multiple damage values.

        Args:
            armor: Total armor value
            damage_values: List of damage values to test

        Returns:
            Dictionary mapping damage values to ArmorResult objects

        Example:
            >>> calc = DefenseCalculator()
            >>> results = calc.armor_comparison(5000, [500, 1000, 2000, 5000])
            >>> for dmg, result in results.items():
            ...     print(f"{dmg} damage: {result.damage_reduction_percent:.2f}% DR")
        """
        results = {}
        for damage in damage_values:
            results[damage] = self.calculate_armor_dr(armor, damage)

        logger.info(f"Armor comparison completed for {len(damage_values)} damage values")
        return results

    # ============================================================================
    # EVASION CALCULATIONS (PoE2)
    # ============================================================================

    def calculate_evasion_chance(
        self,
        evasion: float,
        attacker_accuracy: float
    ) -> EvasionResult:
        """
        Calculate chance to evade using PoE2 formula.

        PoE2 Formula:
            Hit_Chance = (Accuracy × 1.25 × 100) / (Accuracy + Evasion × 0.3)
            Caps: 5% min, 100% max

        Args:
            evasion: Total evasion rating
            attacker_accuracy: Attacker's accuracy rating

        Returns:
            EvasionResult containing hit and evade chances

        Example:
            >>> calc = DefenseCalculator()
            >>> result = calc.calculate_evasion_chance(5000, 2000)
            >>> print(f"Evade chance: {result.evade_chance_percent:.2f}%")
        """
        if evasion < 0:
            logger.warning(f"Negative evasion value: {evasion}, treating as 0")
            evasion = 0

        if attacker_accuracy < 0:
            logger.warning(f"Negative accuracy value: {attacker_accuracy}, treating as 0")
            attacker_accuracy = 0

        if attacker_accuracy == 0:
            # No accuracy means no hit
            return EvasionResult(
                evasion=evasion,
                accuracy=attacker_accuracy,
                hit_chance_percent=0.0,
                evade_chance_percent=100.0,
                is_hit_capped=False
            )

        # PoE2 formula: Hit_Chance = (Accuracy × 1.25 × 100) / (Accuracy + Evasion × 0.3)
        numerator = attacker_accuracy * DefenseConstants.EVASION_ACCURACY_MULTIPLIER * 100
        denominator = attacker_accuracy + (evasion * DefenseConstants.EVASION_DIVISOR)

        hit_chance_percent = numerator / denominator if denominator > 0 else 100.0

        # Apply caps
        is_hit_capped = False
        if hit_chance_percent < DefenseConstants.EVASION_MIN_HIT_CHANCE:
            hit_chance_percent = DefenseConstants.EVASION_MIN_HIT_CHANCE
            is_hit_capped = True
        elif hit_chance_percent > DefenseConstants.EVASION_MAX_HIT_CHANCE:
            hit_chance_percent = DefenseConstants.EVASION_MAX_HIT_CHANCE
            is_hit_capped = True

        evade_chance_percent = 100.0 - hit_chance_percent

        logger.debug(
            f"Evasion: {evasion} vs {attacker_accuracy} accuracy = "
            f"{evade_chance_percent:.2f}% evade chance"
        )

        return EvasionResult(
            evasion=evasion,
            accuracy=attacker_accuracy,
            hit_chance_percent=hit_chance_percent,
            evade_chance_percent=evade_chance_percent,
            is_hit_capped=is_hit_capped
        )

    def evasion_needed_for_hit_chance(
        self,
        target_hit_chance_percent: float,
        attacker_accuracy: float
    ) -> float:
        """
        Calculate evasion needed to reduce hit chance to target value.

        Rearranged PoE2 formula:
            E = (Accuracy × 1.25 × 100 - Hit_Chance × Accuracy) / (Hit_Chance × 0.3)

        Args:
            target_hit_chance_percent: Target hit chance (%)
            attacker_accuracy: Attacker's accuracy rating

        Returns:
            Evasion value needed

        Example:
            >>> calc = DefenseCalculator()
            >>> evasion = calc.evasion_needed_for_hit_chance(50, 2000)
            >>> print(f"Need {evasion:.0f} evasion for 50% hit chance")
        """
        if target_hit_chance_percent <= DefenseConstants.EVASION_MIN_HIT_CHANCE:
            logger.warning(
                f"Target hit chance {target_hit_chance_percent}% <= min "
                f"{DefenseConstants.EVASION_MIN_HIT_CHANCE}%, using min"
            )
            target_hit_chance_percent = DefenseConstants.EVASION_MIN_HIT_CHANCE + 0.01

        if target_hit_chance_percent >= DefenseConstants.EVASION_MAX_HIT_CHANCE:
            return 0.0

        if attacker_accuracy <= 0:
            logger.warning("Attacker accuracy <= 0, cannot calculate evasion needed")
            return 0.0

        # Rearrange: Hit = (Acc × 1.25 × 100) / (Acc + Eva × 0.3)
        # -> E = (Acc × 1.25 × 100 - Hit × Acc) / (Hit × 0.3)
        numerator = (
            attacker_accuracy * DefenseConstants.EVASION_ACCURACY_MULTIPLIER * 100
            - target_hit_chance_percent * attacker_accuracy
        )
        denominator = target_hit_chance_percent * DefenseConstants.EVASION_DIVISOR

        evasion_needed = numerator / denominator if denominator > 0 else 0.0
        evasion_needed = max(0.0, evasion_needed)

        logger.debug(
            f"Evasion needed: {evasion_needed:.0f} for {target_hit_chance_percent}% "
            f"hit chance vs {attacker_accuracy} accuracy"
        )

        return evasion_needed

    # ============================================================================
    # ENERGY SHIELD CALCULATIONS (PoE2)
    # ============================================================================

    def calculate_es_recharge(
        self,
        max_es: float,
        increased_recharge_rate_percent: float = 0.0,
        faster_start_percent: float = 0.0
    ) -> EnergyShieldResult:
        """
        Calculate Energy Shield recharge mechanics using PoE2 values.

        PoE2 Mechanics:
            - Base recharge rate: 12.5% per second (not 20% like PoE1)
            - Base delay: 4 seconds (not 2 seconds like PoE1)
            - Delay formula: 400 / (100 + faster_start_%)

        Args:
            max_es: Maximum energy shield value
            increased_recharge_rate_percent: Increased ES recharge rate (%)
            faster_start_percent: Faster start of ES recharge (%)

        Returns:
            EnergyShieldResult containing recharge rate and timing

        Example:
            >>> calc = DefenseCalculator()
            >>> result = calc.calculate_es_recharge(1000, 50, 25)
            >>> print(f"Recharges {result.recharge_per_second:.1f} ES/sec")
        """
        if max_es < 0:
            logger.warning(f"Negative max ES value: {max_es}, treating as 0")
            max_es = 0

        # Calculate recharge rate (PoE2: 12.5% base)
        base_rate = DefenseConstants.ES_BASE_RECHARGE_RATE
        actual_rate_percent = base_rate * (1 + increased_recharge_rate_percent / 100)
        recharge_per_second = max_es * (actual_rate_percent / 100)

        # Calculate delay (PoE2: 4 second base, formula: 400 / (100 + faster_start_%))
        delay_divisor = DefenseConstants.ES_DELAY_DIVISOR_BASE + faster_start_percent
        delay_seconds = DefenseConstants.ES_DELAY_BASE_VALUE / delay_divisor if delay_divisor > 0 else DefenseConstants.ES_BASE_DELAY

        # Calculate time to full
        if recharge_per_second > 0:
            time_to_full = (max_es / recharge_per_second) + delay_seconds
        else:
            time_to_full = float('inf')

        logger.debug(
            f"ES Recharge: {max_es} max ES, {actual_rate_percent:.2f}% rate "
            f"({recharge_per_second:.1f}/sec), {delay_seconds:.2f}s delay"
        )

        return EnergyShieldResult(
            max_es=max_es,
            recharge_rate_percent=actual_rate_percent,
            recharge_per_second=recharge_per_second,
            delay_seconds=delay_seconds,
            time_to_full_seconds=time_to_full
        )

    # ============================================================================
    # RESISTANCE CALCULATIONS
    # ============================================================================

    def calculate_resistance_dr(
        self,
        resistance_percent: float,
        cap: float = DefenseConstants.RESISTANCE_DEFAULT_CAP
    ) -> ResistanceResult:
        """
        Calculate damage reduction from resistance.

        Formula:
            Damage_Taken = (100 - Resistance%) / 100

        Caps:
            - Default cap: 75%
            - Hard cap: 90%

        Args:
            resistance_percent: Total resistance value (%)
            cap: Effective resistance cap (%, default 75%)

        Returns:
            ResistanceResult containing damage multiplier and reduction

        Example:
            >>> calc = DefenseCalculator()
            >>> result = calc.calculate_resistance_dr(80, 75)
            >>> print(f"Taking {result.damage_taken_multiplier:.2%} damage")
        """
        # Validate cap
        if cap > DefenseConstants.RESISTANCE_HARD_CAP:
            logger.warning(
                f"Cap {cap}% exceeds hard cap {DefenseConstants.RESISTANCE_HARD_CAP}%, "
                "using hard cap"
            )
            cap = DefenseConstants.RESISTANCE_HARD_CAP

        # Apply cap
        is_over_cap = resistance_percent > cap
        is_capped = False
        effective_resistance = resistance_percent

        if resistance_percent > cap:
            effective_resistance = cap
            is_capped = True
            logger.debug(
                f"Resistance {resistance_percent}% capped at {cap}% "
                f"(over-cap: {resistance_percent - cap}%)"
            )

        # Clamp to reasonable minimum
        if effective_resistance < DefenseConstants.RESISTANCE_MIN:
            logger.warning(
                f"Resistance {effective_resistance}% below minimum "
                f"{DefenseConstants.RESISTANCE_MIN}%, clamping"
            )
            effective_resistance = DefenseConstants.RESISTANCE_MIN

        # Calculate damage multiplier
        damage_taken_multiplier = (100 - effective_resistance) / 100
        damage_reduction_percent = 100 - damage_taken_multiplier * 100

        logger.debug(
            f"Resistance: {resistance_percent}% (effective: {effective_resistance}%) = "
            f"{damage_reduction_percent:.2f}% DR"
        )

        return ResistanceResult(
            resistance_percent=effective_resistance,
            damage_taken_multiplier=damage_taken_multiplier,
            damage_reduction_percent=damage_reduction_percent,
            is_capped=is_capped,
            is_over_cap=is_over_cap
        )

    def calculate_all_resistances(
        self,
        fire_res: float = 0.0,
        cold_res: float = 0.0,
        lightning_res: float = 0.0,
        chaos_res: float = 0.0,
        fire_cap: float = DefenseConstants.RESISTANCE_DEFAULT_CAP,
        cold_cap: float = DefenseConstants.RESISTANCE_DEFAULT_CAP,
        lightning_cap: float = DefenseConstants.RESISTANCE_DEFAULT_CAP,
        chaos_cap: float = DefenseConstants.RESISTANCE_DEFAULT_CAP
    ) -> Dict[str, ResistanceResult]:
        """
        Calculate damage reduction for all resistance types.

        Args:
            fire_res: Fire resistance (%)
            cold_res: Cold resistance (%)
            lightning_res: Lightning resistance (%)
            chaos_res: Chaos resistance (%)
            fire_cap: Fire resistance cap (%)
            cold_cap: Cold resistance cap (%)
            lightning_cap: Lightning resistance cap (%)
            chaos_cap: Chaos resistance cap (%)

        Returns:
            Dictionary mapping resistance types to ResistanceResult objects

        Example:
            >>> calc = DefenseCalculator()
            >>> results = calc.calculate_all_resistances(75, 80, 70, 50)
            >>> for res_type, result in results.items():
            ...     print(f"{res_type}: {result.damage_reduction_percent:.0f}% DR")
        """
        resistances = {
            'fire': (fire_res, fire_cap),
            'cold': (cold_res, cold_cap),
            'lightning': (lightning_res, lightning_cap),
            'chaos': (chaos_res, chaos_cap)
        }

        results = {}
        for res_type, (res_value, res_cap) in resistances.items():
            results[res_type] = self.calculate_resistance_dr(res_value, res_cap)

        logger.info("All resistance calculations completed")
        return results

    # ============================================================================
    # BLOCK CALCULATIONS (PoE2)
    # ============================================================================

    def calculate_block_chance(
        self,
        block_chance_percent: float
    ) -> BlockResult:
        """
        Calculate effective block chance with PoE2 cap.

        PoE2 Cap:
            - Maximum block chance: 50% (not 75% like PoE1)

        Args:
            block_chance_percent: Total block chance (%)

        Returns:
            BlockResult containing effective block chance

        Example:
            >>> calc = DefenseCalculator()
            >>> result = calc.calculate_block_chance(60)
            >>> print(f"Block: {result.block_chance_percent}% (capped: {result.is_capped})")
        """
        if block_chance_percent < DefenseConstants.BLOCK_MIN_CHANCE:
            logger.warning(
                f"Block chance {block_chance_percent}% < 0%, treating as 0%"
            )
            block_chance_percent = DefenseConstants.BLOCK_MIN_CHANCE

        is_capped = block_chance_percent > DefenseConstants.BLOCK_MAX_CHANCE
        effective_block = min(block_chance_percent, DefenseConstants.BLOCK_MAX_CHANCE)

        if is_capped:
            logger.debug(
                f"Block chance {block_chance_percent}% capped at "
                f"{DefenseConstants.BLOCK_MAX_CHANCE}%"
            )

        return BlockResult(
            block_chance_percent=effective_block,
            is_capped=is_capped
        )

    # ============================================================================
    # COMBINED DEFENSE CALCULATIONS
    # ============================================================================

    def calculate_effective_hp(
        self,
        life: float,
        energy_shield: float = 0.0,
        armor_dr_percent: float = 0.0,
        resistance_percent: float = 0.0,
        block_chance_percent: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculate effective HP considering all defense layers.

        Args:
            life: Total life pool
            energy_shield: Total energy shield
            armor_dr_percent: Damage reduction from armor (%)
            resistance_percent: Resistance (%)
            block_chance_percent: Block chance (%)

        Returns:
            Dictionary containing effective HP calculations

        Example:
            >>> calc = DefenseCalculator()
            >>> result = calc.calculate_effective_hp(
            ...     life=5000, energy_shield=2000, armor_dr_percent=40,
            ...     resistance_percent=75, block_chance_percent=40
            ... )
            >>> print(f"EHP: {result['effective_hp']:.0f}")
        """
        # Calculate total raw HP (life + ES)
        total_hp = life + energy_shield

        # Apply resistance
        res_result = self.calculate_resistance_dr(resistance_percent)
        hp_after_res = total_hp / res_result.damage_taken_multiplier if res_result.damage_taken_multiplier > 0 else float('inf')

        # Apply armor DR
        armor_multiplier = 1 / (1 - min(armor_dr_percent, DefenseConstants.ARMOR_MAX_DR) / 100)
        hp_after_armor = hp_after_res * armor_multiplier

        # Apply block (expected value)
        block_result = self.calculate_block_chance(block_chance_percent)
        block_multiplier = 1 / (1 - block_result.block_chance_percent / 100)
        effective_hp = hp_after_armor * block_multiplier

        result = {
            'life': life,
            'energy_shield': energy_shield,
            'total_hp': total_hp,
            'resistance_multiplier': 1 / res_result.damage_taken_multiplier if res_result.damage_taken_multiplier > 0 else float('inf'),
            'armor_multiplier': armor_multiplier,
            'block_multiplier': block_multiplier,
            'effective_hp': effective_hp
        }

        logger.info(
            f"EHP calculation: {total_hp:.0f} HP -> {effective_hp:.0f} EHP "
            f"(res: {resistance_percent}%, armor DR: {armor_dr_percent}%, "
            f"block: {block_chance_percent}%)"
        )

        return result

    def calculate_damage_taken(
        self,
        raw_damage: float,
        armor: float = 0.0,
        resistance_percent: float = 0.0,
        block_chance_percent: float = 0.0,
        damage_type: str = 'physical'
    ) -> Dict[str, Any]:
        """
        Calculate actual damage taken after all mitigation.

        Args:
            raw_damage: Raw incoming damage
            armor: Armor value (only for physical damage)
            resistance_percent: Resistance (%)
            block_chance_percent: Block chance (%)
            damage_type: Type of damage ('physical', 'elemental', etc.)

        Returns:
            Dictionary containing damage breakdown

        Example:
            >>> calc = DefenseCalculator()
            >>> result = calc.calculate_damage_taken(
            ...     raw_damage=1000, armor=5000, resistance_percent=75,
            ...     block_chance_percent=40, damage_type='physical'
            ... )
            >>> print(f"Take {result['expected_damage']:.0f} damage on average")
        """
        damage_after_armor = raw_damage
        armor_dr_percent = 0.0

        # Apply armor only for physical damage
        if damage_type.lower() == 'physical' and armor > 0:
            armor_result = self.calculate_armor_dr(armor, raw_damage)
            damage_after_armor = armor_result.effective_damage
            armor_dr_percent = armor_result.damage_reduction_percent

        # Apply resistance
        res_result = self.calculate_resistance_dr(resistance_percent)
        damage_after_res = damage_after_armor * res_result.damage_taken_multiplier

        # Calculate expected damage with block
        block_result = self.calculate_block_chance(block_chance_percent)
        expected_damage = damage_after_res * (1 - block_result.block_chance_percent / 100)

        result = {
            'raw_damage': raw_damage,
            'armor_dr_percent': armor_dr_percent,
            'damage_after_armor': damage_after_armor,
            'resistance_percent': res_result.resistance_percent,
            'damage_after_resistance': damage_after_res,
            'block_chance_percent': block_result.block_chance_percent,
            'expected_damage': expected_damage,
            'damage_reduction_total_percent': (1 - expected_damage / raw_damage) * 100 if raw_damage > 0 else 0
        }

        logger.info(
            f"Damage calculation: {raw_damage:.0f} raw -> {expected_damage:.0f} expected "
            f"({result['damage_reduction_total_percent']:.1f}% total DR)"
        )

        return result


# Convenience functions for quick calculations

def armor_dr(armor: float, damage: float) -> float:
    """Quick armor damage reduction calculation."""
    calc = DefenseCalculator()
    result = calc.calculate_armor_dr(armor, damage)
    return result.damage_reduction_percent


def evasion_chance(evasion: float, accuracy: float) -> float:
    """Quick evasion chance calculation."""
    calc = DefenseCalculator()
    result = calc.calculate_evasion_chance(evasion, accuracy)
    return result.evade_chance_percent


def resistance_dr(resistance: float, cap: float = DefenseConstants.RESISTANCE_DEFAULT_CAP) -> float:
    """Quick resistance damage reduction calculation."""
    calc = DefenseCalculator()
    result = calc.calculate_resistance_dr(resistance, cap)
    return result.damage_reduction_percent


def block_effective(block_chance: float) -> float:
    """Quick block chance calculation with cap."""
    calc = DefenseCalculator()
    result = calc.calculate_block_chance(block_chance)
    return result.block_chance_percent


if __name__ == '__main__':
    # Example usage and testing
    logging.basicConfig(level=logging.INFO)

    calc = DefenseCalculator()

    print("=== Path of Exile 2 Defense Calculator ===\n")

    # Armor examples
    print("--- Armor (PoE2) ---")
    armor_test = calc.calculate_armor_dr(5000, 1000)
    print(f"5000 armor vs 1000 damage: {armor_test.damage_reduction_percent:.2f}% DR")
    print(f"Effective damage: {armor_test.effective_damage:.0f}")

    armor_needed = calc.armor_needed_for_dr(50, 1000)
    print(f"Armor needed for 50% DR vs 1000 damage: {armor_needed:.0f}\n")

    # Evasion examples
    print("--- Evasion (PoE2) ---")
    evasion_test = calc.calculate_evasion_chance(5000, 2000)
    print(f"5000 evasion vs 2000 accuracy: {evasion_test.evade_chance_percent:.2f}% evade")
    print(f"Hit chance: {evasion_test.hit_chance_percent:.2f}%\n")

    # Energy Shield examples
    print("--- Energy Shield (PoE2) ---")
    es_test = calc.calculate_es_recharge(1000, 50, 25)
    print(f"1000 ES with 50% increased rate, 25% faster start:")
    print(f"Recharge rate: {es_test.recharge_rate_percent:.2f}%/sec ({es_test.recharge_per_second:.1f}/sec)")
    print(f"Delay: {es_test.delay_seconds:.2f}s")
    print(f"Time to full: {es_test.time_to_full_seconds:.2f}s\n")

    # Resistance examples
    print("--- Resistances ---")
    all_res = calc.calculate_all_resistances(75, 80, 70, 50)
    for res_type, result in all_res.items():
        print(f"{res_type.capitalize()}: {result.resistance_percent:.0f}% "
              f"({result.damage_reduction_percent:.0f}% DR, capped: {result.is_capped})")
    print()

    # Block examples
    print("--- Block (PoE2 - 50% cap) ---")
    block_test = calc.calculate_block_chance(60)
    print(f"60% block chance: {block_test.block_chance_percent:.0f}% (capped: {block_test.is_capped})\n")

    # Combined defense
    print("--- Effective HP ---")
    ehp = calc.calculate_effective_hp(
        life=5000,
        energy_shield=2000,
        armor_dr_percent=40,
        resistance_percent=75,
        block_chance_percent=40
    )
    print(f"5000 life, 2000 ES, 40% armor DR, 75% res, 40% block:")
    print(f"Total HP: {ehp['total_hp']:.0f}")
    print(f"Effective HP: {ehp['effective_hp']:.0f}\n")

    # Damage taken
    print("--- Damage Taken ---")
    damage = calc.calculate_damage_taken(
        raw_damage=1000,
        armor=5000,
        resistance_percent=75,
        block_chance_percent=40,
        damage_type='physical'
    )
    print(f"1000 physical damage, 5000 armor, 75% res, 40% block:")
    print(f"After armor: {damage['damage_after_armor']:.0f}")
    print(f"After resistance: {damage['damage_after_resistance']:.0f}")
    print(f"Expected (with block): {damage['expected_damage']:.0f}")
    print(f"Total DR: {damage['damage_reduction_total_percent']:.1f}%")
