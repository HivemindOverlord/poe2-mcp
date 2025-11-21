"""
Path of Exile 2 Damage Calculator Module

This module provides comprehensive damage calculation functionality for Path of Exile 2,
including base damage, modifiers, critical strikes, attack/cast speed, and DPS calculations.

Key PoE2 Mechanics:
- Increased modifiers stack additively
- More modifiers stack multiplicatively
- Critical strikes have a base +100% damage bonus (not +150% like PoE1)
- Damage conversion is applied before modifiers
- Multiple damage types can coexist

Author: Claude Code
Version: 1.0.0
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum
from functools import reduce
import operator

# Configure logging
logger = logging.getLogger(__name__)


class DamageType(Enum):
    """Enumeration of damage types in Path of Exile 2."""
    PHYSICAL = "physical"
    FIRE = "fire"
    COLD = "cold"
    LIGHTNING = "lightning"
    CHAOS = "chaos"


class ModifierType(Enum):
    """Enumeration of modifier types."""
    INCREASED = "increased"  # Additive
    MORE = "more"  # Multiplicative
    REDUCED = "reduced"  # Negative increased (additive)
    LESS = "less"  # Negative more (multiplicative)


@dataclass
class DamageRange:
    """
    Represents a damage range with minimum and maximum values.

    Attributes:
        min_damage: Minimum damage value
        max_damage: Maximum damage value

    Examples:
        >>> damage = DamageRange(10, 20)
        >>> damage.average()
        15.0
        >>> damage.is_valid()
        True
    """
    min_damage: float
    max_damage: float

    def __post_init__(self):
        """Validate damage range after initialization."""
        if self.min_damage < 0:
            raise ValueError(f"Minimum damage cannot be negative: {self.min_damage}")
        if self.max_damage < 0:
            raise ValueError(f"Maximum damage cannot be negative: {self.max_damage}")
        if self.min_damage > self.max_damage:
            raise ValueError(
                f"Minimum damage ({self.min_damage}) cannot exceed maximum damage ({self.max_damage})"
            )

    def average(self) -> float:
        """
        Calculate the average damage.

        Returns:
            Average of min and max damage

        Examples:
            >>> DamageRange(100, 200).average()
            150.0
        """
        return (self.min_damage + self.max_damage) / 2

    def is_valid(self) -> bool:
        """
        Check if the damage range is valid.

        Returns:
            True if valid, False otherwise
        """
        return (
            self.min_damage >= 0 and
            self.max_damage >= 0 and
            self.min_damage <= self.max_damage
        )

    def scale(self, multiplier: float) -> 'DamageRange':
        """
        Scale the damage range by a multiplier.

        Args:
            multiplier: Scaling factor

        Returns:
            New DamageRange with scaled values

        Examples:
            >>> DamageRange(10, 20).scale(2.0)
            DamageRange(min_damage=20.0, max_damage=40.0)
        """
        return DamageRange(
            min_damage=self.min_damage * multiplier,
            max_damage=self.max_damage * multiplier
        )


@dataclass
class Modifier:
    """
    Represents a damage modifier.

    Attributes:
        value: Modifier value (as percentage, e.g., 50 for 50%)
        modifier_type: Type of modifier (increased/more/reduced/less)
        source: Optional source description for debugging

    Examples:
        >>> mod = Modifier(50, ModifierType.INCREASED, "Passive Tree")
        >>> mod.get_multiplier()
        0.5
    """
    value: float
    modifier_type: ModifierType
    source: Optional[str] = None

    def get_multiplier(self) -> float:
        """
        Get the modifier as a decimal multiplier.

        Returns:
            Modifier value as decimal (e.g., 50% -> 0.5)

        Examples:
            >>> Modifier(50, ModifierType.INCREASED).get_multiplier()
            0.5
            >>> Modifier(30, ModifierType.REDUCED).get_multiplier()
            -0.3
        """
        multiplier = self.value / 100
        if self.modifier_type in (ModifierType.REDUCED, ModifierType.LESS):
            multiplier = -multiplier
        return multiplier


@dataclass
class DamageComponents:
    """
    Represents damage broken down by type.

    Attributes:
        damage_by_type: Dictionary mapping damage types to damage ranges

    Examples:
        >>> components = DamageComponents({
        ...     DamageType.PHYSICAL: DamageRange(100, 150),
        ...     DamageType.FIRE: DamageRange(50, 75)
        ... })
        >>> components.total_average_damage()
        187.5
    """
    damage_by_type: Dict[DamageType, DamageRange] = field(default_factory=dict)

    def total_average_damage(self) -> float:
        """
        Calculate total average damage across all types.

        Returns:
            Sum of average damage for all damage types

        Examples:
            >>> components = DamageComponents({
            ...     DamageType.PHYSICAL: DamageRange(100, 200),
            ...     DamageType.FIRE: DamageRange(50, 100)
            ... })
            >>> components.total_average_damage()
            225.0
        """
        return sum(damage_range.average() for damage_range in self.damage_by_type.values())

    def get_damage_by_type(self, damage_type: DamageType) -> Optional[DamageRange]:
        """
        Get damage range for a specific damage type.

        Args:
            damage_type: Type of damage to retrieve

        Returns:
            DamageRange for the specified type, or None if not present
        """
        return self.damage_by_type.get(damage_type)

    def add_damage(self, damage_type: DamageType, damage_range: DamageRange) -> None:
        """
        Add or update damage for a specific type.

        Args:
            damage_type: Type of damage to add
            damage_range: Damage range to add
        """
        if damage_type in self.damage_by_type:
            existing = self.damage_by_type[damage_type]
            self.damage_by_type[damage_type] = DamageRange(
                min_damage=existing.min_damage + damage_range.min_damage,
                max_damage=existing.max_damage + damage_range.max_damage
            )
        else:
            self.damage_by_type[damage_type] = damage_range


@dataclass
class CriticalStrikeConfig:
    """
    Configuration for critical strike calculations.

    Attributes:
        crit_chance: Critical strike chance (0-100)
        crit_multiplier: Critical strike damage multiplier (100 = +100% in PoE2)

    Examples:
        >>> config = CriticalStrikeConfig(crit_chance=50, crit_multiplier=150)
        >>> config.effective_damage_multiplier()
        1.75
    """
    crit_chance: float = 0.0
    crit_multiplier: float = 100.0  # PoE2 default: +100% damage on crit

    def __post_init__(self):
        """Validate critical strike configuration."""
        if not 0 <= self.crit_chance <= 100:
            raise ValueError(f"Critical chance must be between 0 and 100: {self.crit_chance}")
        if self.crit_multiplier < 0:
            raise ValueError(f"Critical multiplier cannot be negative: {self.crit_multiplier}")

    def effective_damage_multiplier(self) -> float:
        """
        Calculate the effective damage multiplier from critical strikes.

        This accounts for the chance to crit and the damage bonus when critting.

        Returns:
            Effective damage multiplier

        Formula:
            (1 - crit_chance) * 1.0 + crit_chance * (1 + crit_multiplier/100)

        Examples:
            >>> CriticalStrikeConfig(50, 100).effective_damage_multiplier()
            1.5
            >>> CriticalStrikeConfig(25, 150).effective_damage_multiplier()
            1.1875
        """
        crit_chance_decimal = self.crit_chance / 100
        crit_damage_multiplier = 1 + (self.crit_multiplier / 100)

        # Expected value calculation
        non_crit_damage = (1 - crit_chance_decimal) * 1.0
        crit_damage = crit_chance_decimal * crit_damage_multiplier

        return non_crit_damage + crit_damage


class DamageCalculator:
    """
    Main damage calculator for Path of Exile 2.

    This class handles all damage calculations including base damage, modifiers,
    critical strikes, attack speed, and DPS calculations.

    Examples:
        >>> calc = DamageCalculator()
        >>> base = DamageRange(100, 200)
        >>> increased_mods = [Modifier(50, ModifierType.INCREASED)]
        >>> more_mods = [Modifier(30, ModifierType.MORE)]
        >>> result = calc.calculate_final_damage(base, increased_mods, more_mods)
        >>> result.average()
        195.0
    """

    def __init__(self):
        """Initialize the damage calculator."""
        logger.info("DamageCalculator initialized")

    def calculate_base_damage(
        self,
        weapon_damage: Optional[DamageRange] = None,
        spell_base_damage: Optional[DamageRange] = None,
        added_flat_damage: Optional[List[Tuple[DamageType, DamageRange]]] = None
    ) -> DamageComponents:
        """
        Calculate base damage from weapon or spell with added flat damage.

        Args:
            weapon_damage: Weapon damage range (for attacks)
            spell_base_damage: Spell base damage (for spells)
            added_flat_damage: List of (damage_type, damage_range) tuples for flat additions

        Returns:
            DamageComponents with base damage by type

        Raises:
            ValueError: If neither weapon nor spell damage is provided

        Examples:
            >>> calc = DamageCalculator()
            >>> weapon = DamageRange(50, 100)
            >>> added = [(DamageType.FIRE, DamageRange(10, 20))]
            >>> result = calc.calculate_base_damage(weapon_damage=weapon, added_flat_damage=added)
            >>> result.total_average_damage()
            90.0
        """
        if weapon_damage is None and spell_base_damage is None:
            raise ValueError("Must provide either weapon_damage or spell_base_damage")

        components = DamageComponents()

        # Start with weapon or spell base damage (assumed physical for weapons)
        if weapon_damage:
            components.add_damage(DamageType.PHYSICAL, weapon_damage)
            logger.debug(f"Base weapon damage: {weapon_damage}")
        elif spell_base_damage:
            # Spells can specify their damage type separately
            components.add_damage(DamageType.PHYSICAL, spell_base_damage)
            logger.debug(f"Base spell damage: {spell_base_damage}")

        # Add flat damage bonuses
        if added_flat_damage:
            for damage_type, damage_range in added_flat_damage:
                components.add_damage(damage_type, damage_range)
                logger.debug(f"Added {damage_type.value} damage: {damage_range}")

        return components

    def apply_increased_modifiers(
        self,
        base_value: float,
        modifiers: List[Modifier]
    ) -> float:
        """
        Apply increased/reduced modifiers (additive).

        All increased and reduced modifiers are summed together, then applied
        as a single multiplicative factor.

        Args:
            base_value: Base value to modify
            modifiers: List of increased/reduced modifiers

        Returns:
            Modified value after applying increased modifiers

        Formula:
            final = base * (1 + sum(increased) - sum(reduced))

        Examples:
            >>> calc = DamageCalculator()
            >>> mods = [
            ...     Modifier(50, ModifierType.INCREASED),
            ...     Modifier(30, ModifierType.INCREASED),
            ...     Modifier(10, ModifierType.REDUCED)
            ... ]
            >>> calc.apply_increased_modifiers(100, mods)
            170.0
        """
        # Filter only increased/reduced modifiers
        relevant_mods = [
            m for m in modifiers
            if m.modifier_type in (ModifierType.INCREASED, ModifierType.REDUCED)
        ]

        # Sum all increased/reduced modifiers
        total_increased = sum(mod.get_multiplier() for mod in relevant_mods)

        result = base_value * (1 + total_increased)

        if relevant_mods:
            logger.debug(
                f"Applied {len(relevant_mods)} increased modifiers: "
                f"{base_value} * (1 + {total_increased:.2f}) = {result:.2f}"
            )

        return result

    def apply_more_modifiers(
        self,
        base_value: float,
        modifiers: List[Modifier]
    ) -> float:
        """
        Apply more/less modifiers (multiplicative).

        Each more/less modifier is applied multiplicatively in sequence.

        Args:
            base_value: Base value to modify
            modifiers: List of more/less modifiers

        Returns:
            Modified value after applying more modifiers

        Formula:
            final = base * (1 + more1/100) * (1 + more2/100) * ...

        Examples:
            >>> calc = DamageCalculator()
            >>> mods = [
            ...     Modifier(30, ModifierType.MORE),
            ...     Modifier(20, ModifierType.MORE),
            ...     Modifier(10, ModifierType.LESS)
            ... ]
            >>> calc.apply_more_modifiers(100, mods)
            140.4
        """
        # Filter only more/less modifiers
        relevant_mods = [
            m for m in modifiers
            if m.modifier_type in (ModifierType.MORE, ModifierType.LESS)
        ]

        # Apply each more/less modifier multiplicatively
        result = base_value
        multipliers = []

        for mod in relevant_mods:
            multiplier = 1 + mod.get_multiplier()
            result *= multiplier
            multipliers.append(multiplier)

        if relevant_mods:
            logger.debug(
                f"Applied {len(relevant_mods)} more modifiers: "
                f"{base_value} * {' * '.join(f'{m:.2f}' for m in multipliers)} = {result:.2f}"
            )

        return result

    def apply_damage_conversion(
        self,
        components: DamageComponents,
        conversions: Dict[DamageType, Dict[DamageType, float]]
    ) -> DamageComponents:
        """
        Apply damage conversion between types.

        Conversions are applied before modifiers. Each conversion is specified as
        a percentage (0-100) of the source damage type.

        Args:
            components: Original damage components
            conversions: Dict mapping source type to dict of (target type, percentage)

        Returns:
            New DamageComponents with conversions applied

        Examples:
            >>> calc = DamageCalculator()
            >>> components = DamageComponents({
            ...     DamageType.PHYSICAL: DamageRange(100, 200)
            ... })
            >>> conversions = {
            ...     DamageType.PHYSICAL: {DamageType.FIRE: 50}
            ... }
            >>> result = calc.apply_damage_conversion(components, conversions)
            >>> result.get_damage_by_type(DamageType.PHYSICAL).average()
            75.0
            >>> result.get_damage_by_type(DamageType.FIRE).average()
            75.0
        """
        result = DamageComponents()

        # Process each damage type
        for source_type, damage_range in components.damage_by_type.items():
            remaining_percentage = 100.0

            # Apply conversions from this source type
            if source_type in conversions:
                for target_type, conversion_pct in conversions[source_type].items():
                    if conversion_pct > 0:
                        # Convert portion to target type
                        converted_damage = damage_range.scale(conversion_pct / 100)
                        result.add_damage(target_type, converted_damage)
                        remaining_percentage -= conversion_pct

                        logger.debug(
                            f"Converted {conversion_pct}% of {source_type.value} "
                            f"to {target_type.value}"
                        )

            # Add remaining unconverted damage
            if remaining_percentage > 0:
                remaining_damage = damage_range.scale(remaining_percentage / 100)
                result.add_damage(source_type, remaining_damage)

        return result

    def calculate_final_damage(
        self,
        base_damage: DamageRange,
        increased_modifiers: Optional[List[Modifier]] = None,
        more_modifiers: Optional[List[Modifier]] = None
    ) -> DamageRange:
        """
        Calculate final damage after applying all modifiers.

        Args:
            base_damage: Base damage range
            increased_modifiers: List of increased/reduced modifiers
            more_modifiers: List of more/less modifiers

        Returns:
            Final damage range after all modifiers

        Formula:
            final = base * (1 + sum(increased)) * product(1 + more)

        Examples:
            >>> calc = DamageCalculator()
            >>> base = DamageRange(100, 200)
            >>> increased = [Modifier(50, ModifierType.INCREASED)]
            >>> more = [Modifier(30, ModifierType.MORE)]
            >>> result = calc.calculate_final_damage(base, increased, more)
            >>> result.min_damage
            195.0
            >>> result.max_damage
            390.0
        """
        increased_modifiers = increased_modifiers or []
        more_modifiers = more_modifiers or []

        # Apply increased modifiers to min and max
        min_after_increased = self.apply_increased_modifiers(
            base_damage.min_damage,
            increased_modifiers
        )
        max_after_increased = self.apply_increased_modifiers(
            base_damage.max_damage,
            increased_modifiers
        )

        # Apply more modifiers to min and max
        final_min = self.apply_more_modifiers(min_after_increased, more_modifiers)
        final_max = self.apply_more_modifiers(max_after_increased, more_modifiers)

        return DamageRange(min_damage=final_min, max_damage=final_max)

    def calculate_critical_damage(
        self,
        base_damage: DamageRange,
        crit_config: CriticalStrikeConfig
    ) -> DamageRange:
        """
        Calculate damage with critical strike multiplier applied.

        In PoE2, critical strikes have a default +100% damage bonus.

        Args:
            base_damage: Base damage range before crit
            crit_config: Critical strike configuration

        Returns:
            Damage range with critical strike multiplier

        Formula:
            crit_damage = base * (1 + crit_multiplier/100)

        Examples:
            >>> calc = DamageCalculator()
            >>> base = DamageRange(100, 200)
            >>> crit = CriticalStrikeConfig(crit_chance=0, crit_multiplier=100)
            >>> result = calc.calculate_critical_damage(base, crit)
            >>> result.min_damage
            200.0
        """
        multiplier = 1 + (crit_config.crit_multiplier / 100)

        logger.debug(
            f"Critical strike multiplier: {crit_config.crit_multiplier}% "
            f"(total: {multiplier:.2f}x)"
        )

        return base_damage.scale(multiplier)

    def calculate_attack_speed(
        self,
        base_attack_time: float,
        increased_speed_modifiers: List[Modifier]
    ) -> float:
        """
        Calculate attacks per second from base attack time and modifiers.

        Args:
            base_attack_time: Base time per attack in seconds
            increased_speed_modifiers: List of increased attack speed modifiers

        Returns:
            Attacks per second

        Raises:
            ValueError: If base_attack_time is not positive

        Formula:
            attacks_per_second = (1 / base_attack_time) * (1 + sum(increased_speed))

        Examples:
            >>> calc = DamageCalculator()
            >>> mods = [Modifier(20, ModifierType.INCREASED)]
            >>> calc.calculate_attack_speed(1.5, mods)
            0.8
        """
        if base_attack_time <= 0:
            raise ValueError(f"Base attack time must be positive: {base_attack_time}")

        # Calculate base attacks per second
        base_aps = 1 / base_attack_time

        # Apply increased attack speed modifiers
        final_aps = self.apply_increased_modifiers(base_aps, increased_speed_modifiers)

        logger.debug(
            f"Attack speed: {base_attack_time}s base -> {final_aps:.2f} attacks/sec"
        )

        return final_aps

    def calculate_cast_speed(
        self,
        base_cast_time: float,
        increased_speed_modifiers: List[Modifier]
    ) -> float:
        """
        Calculate casts per second from base cast time and modifiers.

        Args:
            base_cast_time: Base time per cast in seconds
            increased_speed_modifiers: List of increased cast speed modifiers

        Returns:
            Casts per second

        Raises:
            ValueError: If base_cast_time is not positive

        Formula:
            casts_per_second = (1 / base_cast_time) * (1 + sum(increased_speed))

        Examples:
            >>> calc = DamageCalculator()
            >>> mods = [Modifier(30, ModifierType.INCREASED)]
            >>> calc.calculate_cast_speed(0.8, mods)
            1.625
        """
        if base_cast_time <= 0:
            raise ValueError(f"Base cast time must be positive: {base_cast_time}")

        # Calculate base casts per second
        base_cps = 1 / base_cast_time

        # Apply increased cast speed modifiers
        final_cps = self.apply_increased_modifiers(base_cps, increased_speed_modifiers)

        logger.debug(
            f"Cast speed: {base_cast_time}s base -> {final_cps:.2f} casts/sec"
        )

        return final_cps

    def calculate_dps(
        self,
        damage_per_hit: DamageRange,
        actions_per_second: float,
        crit_config: Optional[CriticalStrikeConfig] = None
    ) -> float:
        """
        Calculate damage per second (DPS).

        Args:
            damage_per_hit: Damage range per hit
            actions_per_second: Attacks or casts per second
            crit_config: Optional critical strike configuration

        Returns:
            Average DPS

        Formula:
            dps = average_damage * actions_per_second * crit_multiplier

        Examples:
            >>> calc = DamageCalculator()
            >>> damage = DamageRange(100, 200)
            >>> crit = CriticalStrikeConfig(50, 100)
            >>> calc.calculate_dps(damage, 2.0, crit)
            450.0
        """
        avg_damage = damage_per_hit.average()

        # Apply critical strike multiplier if provided
        if crit_config:
            crit_multiplier = crit_config.effective_damage_multiplier()
            avg_damage *= crit_multiplier
            logger.debug(f"Applied crit multiplier: {crit_multiplier:.2f}x")

        dps = avg_damage * actions_per_second

        logger.info(
            f"DPS calculation: {damage_per_hit.average():.2f} avg damage * "
            f"{actions_per_second:.2f} aps = {dps:.2f} DPS"
        )

        return dps

    def calculate_full_dps(
        self,
        base_damage_components: DamageComponents,
        increased_damage_modifiers: Optional[List[Modifier]] = None,
        more_damage_modifiers: Optional[List[Modifier]] = None,
        base_action_time: float = 1.0,
        increased_speed_modifiers: Optional[List[Modifier]] = None,
        crit_config: Optional[CriticalStrikeConfig] = None,
        is_spell: bool = False
    ) -> Dict[str, Union[float, DamageComponents]]:
        """
        Calculate complete DPS with all modifiers for all damage types.

        This is the main entry point for comprehensive DPS calculations.

        Args:
            base_damage_components: Base damage by type
            increased_damage_modifiers: Increased damage modifiers
            more_damage_modifiers: More damage modifiers
            base_action_time: Base attack/cast time in seconds
            increased_speed_modifiers: Increased speed modifiers
            crit_config: Critical strike configuration
            is_spell: True for spells (cast speed), False for attacks (attack speed)

        Returns:
            Dictionary containing:
                - 'total_dps': Total DPS across all damage types
                - 'dps_by_type': DPS broken down by damage type
                - 'final_damage': Final damage components after modifiers
                - 'actions_per_second': Attack or cast speed

        Examples:
            >>> calc = DamageCalculator()
            >>> components = DamageComponents({
            ...     DamageType.PHYSICAL: DamageRange(100, 200)
            ... })
            >>> result = calc.calculate_full_dps(
            ...     components,
            ...     increased_damage_modifiers=[Modifier(50, ModifierType.INCREASED)],
            ...     base_action_time=1.5,
            ...     crit_config=CriticalStrikeConfig(50, 100)
            ... )
            >>> result['total_dps']
            150.0
        """
        increased_damage_modifiers = increased_damage_modifiers or []
        more_damage_modifiers = more_damage_modifiers or []
        increased_speed_modifiers = increased_speed_modifiers or []

        # Calculate action speed
        if is_spell:
            actions_per_second = self.calculate_cast_speed(
                base_action_time,
                increased_speed_modifiers
            )
        else:
            actions_per_second = self.calculate_attack_speed(
                base_action_time,
                increased_speed_modifiers
            )

        # Process each damage type
        final_components = DamageComponents()
        dps_by_type = {}
        total_dps = 0.0

        for damage_type, damage_range in base_damage_components.damage_by_type.items():
            # Apply damage modifiers
            final_damage = self.calculate_final_damage(
                damage_range,
                increased_damage_modifiers,
                more_damage_modifiers
            )

            final_components.add_damage(damage_type, final_damage)

            # Calculate DPS for this damage type
            type_dps = self.calculate_dps(final_damage, actions_per_second, crit_config)
            dps_by_type[damage_type.value] = type_dps
            total_dps += type_dps

            logger.debug(
                f"{damage_type.value.capitalize()} DPS: {type_dps:.2f}"
            )

        result = {
            'total_dps': total_dps,
            'dps_by_type': dps_by_type,
            'final_damage': final_components,
            'actions_per_second': actions_per_second
        }

        logger.info(f"Total DPS: {total_dps:.2f}")

        return result


# Convenience functions for quick calculations

def quick_dps_calculation(
    min_damage: float,
    max_damage: float,
    attacks_per_second: float,
    crit_chance: float = 0.0,
    crit_multiplier: float = 100.0
) -> float:
    """
    Quick DPS calculation without creating full objects.

    Args:
        min_damage: Minimum damage
        max_damage: Maximum damage
        attacks_per_second: Attacks/casts per second
        crit_chance: Critical strike chance (0-100)
        crit_multiplier: Critical strike damage multiplier (default 100 for PoE2)

    Returns:
        Total DPS

    Examples:
        >>> quick_dps_calculation(100, 200, 2.0, 50, 100)
        450.0
    """
    calc = DamageCalculator()
    damage = DamageRange(min_damage, max_damage)
    crit_config = CriticalStrikeConfig(crit_chance, crit_multiplier)

    return calc.calculate_dps(damage, attacks_per_second, crit_config)


def calculate_modifier_total(modifiers: List[Modifier]) -> float:
    """
    Calculate the total multiplier from a list of modifiers.

    Increased/reduced modifiers are summed, then more/less are applied multiplicatively.

    Args:
        modifiers: List of modifiers to calculate

    Returns:
        Total multiplier (e.g., 2.0 means 2x damage)

    Examples:
        >>> mods = [
        ...     Modifier(50, ModifierType.INCREASED),
        ...     Modifier(30, ModifierType.MORE)
        ... ]
        >>> calculate_modifier_total(mods)
        1.95
    """
    calc = DamageCalculator()

    # Start with 100 base, apply modifiers, see what we get
    result = calc.apply_increased_modifiers(100.0, modifiers)
    result = calc.apply_more_modifiers(result, modifiers)

    return result / 100.0


if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(level=logging.INFO)

    print("=== Path of Exile 2 Damage Calculator Example ===\n")

    # Create calculator
    calc = DamageCalculator()

    # Example 1: Basic weapon attack with modifiers
    print("Example 1: Basic Weapon Attack")
    weapon_damage = DamageRange(50, 100)
    increased_mods = [
        Modifier(50, ModifierType.INCREASED, "Passive Tree"),
        Modifier(30, ModifierType.INCREASED, "Gear")
    ]
    more_mods = [
        Modifier(40, ModifierType.MORE, "Support Gem")
    ]

    final_damage = calc.calculate_final_damage(weapon_damage, increased_mods, more_mods)
    print(f"Base damage: {weapon_damage.min_damage}-{weapon_damage.max_damage}")
    print(f"Final damage: {final_damage.min_damage:.1f}-{final_damage.max_damage:.1f}")
    print(f"Average: {final_damage.average():.1f}\n")

    # Example 2: DPS with critical strikes
    print("Example 2: DPS with Critical Strikes")
    crit_config = CriticalStrikeConfig(crit_chance=50, crit_multiplier=150)
    attack_speed = 1.5  # attacks per second

    dps = calc.calculate_dps(final_damage, attack_speed, crit_config)
    print(f"Attack speed: {attack_speed} APS")
    print(f"Crit chance: {crit_config.crit_chance}%")
    print(f"Crit multiplier: +{crit_config.crit_multiplier}%")
    print(f"DPS: {dps:.2f}\n")

    # Example 3: Multi-damage type with conversion
    print("Example 3: Damage Conversion")
    base_components = DamageComponents({
        DamageType.PHYSICAL: DamageRange(100, 200)
    })

    conversions = {
        DamageType.PHYSICAL: {
            DamageType.FIRE: 50  # Convert 50% physical to fire
        }
    }

    converted = calc.apply_damage_conversion(base_components, conversions)
    print("After 50% physical to fire conversion:")
    for damage_type, damage_range in converted.damage_by_type.items():
        print(f"  {damage_type.value.capitalize()}: {damage_range.average():.1f} avg")
    print()

    # Example 4: Complete DPS calculation
    print("Example 4: Complete DPS Calculation")
    base_components = calc.calculate_base_damage(
        weapon_damage=DamageRange(80, 150),
        added_flat_damage=[
            (DamageType.FIRE, DamageRange(20, 30)),
            (DamageType.LIGHTNING, DamageRange(10, 40))
        ]
    )

    result = calc.calculate_full_dps(
        base_damage_components=base_components,
        increased_damage_modifiers=[
            Modifier(100, ModifierType.INCREASED, "Tree + Gear")
        ],
        more_damage_modifiers=[
            Modifier(50, ModifierType.MORE, "Support Gems")
        ],
        base_action_time=1.2,
        increased_speed_modifiers=[
            Modifier(40, ModifierType.INCREASED, "Attack Speed")
        ],
        crit_config=CriticalStrikeConfig(60, 120),
        is_spell=False
    )

    print(f"Total DPS: {result['total_dps']:.2f}")
    print(f"Actions per second: {result['actions_per_second']:.2f}")
    print("DPS by type:")
    for damage_type, dps_value in result['dps_by_type'].items():
        print(f"  {damage_type.capitalize()}: {dps_value:.2f}")
