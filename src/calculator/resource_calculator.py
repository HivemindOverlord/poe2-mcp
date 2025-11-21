"""
Resource Calculator for Path of Exile 2

This module handles all resource calculations for PoE2 including the NEW Spirit system.
Spirit is a new resource in PoE2 that limits the number of permanent minions, auras,
and meta-gems a character can use simultaneously.

Key PoE2 Changes:
- Spirit: New resource for permanent summons and auras (replaces mana reservation for some)
- Life: Base changed to 28 + 12/level (was 38 + 12/level in PoE1)
- Mana: Base changed to 34 + 4/level (was 34 + 6/level in PoE1)
- Accuracy: Formula adjusted to 6 × level + 6 × dex

Author: Claude
Date: 2025-10-22
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


# Configure logging
logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Enumeration of resource types in PoE2."""
    LIFE = "life"
    MANA = "mana"
    ENERGY_SHIELD = "energy_shield"
    SPIRIT = "spirit"  # NEW in PoE2


class ReservationType(Enum):
    """Enumeration of reservation types in PoE2."""
    MANA_FLAT = "mana_flat"
    MANA_PERCENT = "mana_percent"
    LIFE_FLAT = "life_flat"
    LIFE_PERCENT = "life_percent"
    SPIRIT_FLAT = "spirit_flat"  # NEW in PoE2


@dataclass
class AttributeStats:
    """Character attribute statistics."""
    strength: int = 0
    dexterity: int = 0
    intelligence: int = 0

    def __post_init__(self):
        """Validate attributes are non-negative."""
        if self.strength < 0 or self.dexterity < 0 or self.intelligence < 0:
            raise ValueError("Attributes cannot be negative")


@dataclass
class ResourceModifiers:
    """
    Modifiers that affect resource calculations.

    Attributes:
        flat_bonus: Flat amount added to base (e.g., +50 life)
        increased_percent: Additive increased % (e.g., 120% increased life)
        more_multipliers: List of multiplicative more % (e.g., [1.15, 1.10] for 15% more and 10% more)
    """
    flat_bonus: float = 0.0
    increased_percent: float = 0.0
    more_multipliers: List[float] = field(default_factory=list)

    def calculate_total_more(self) -> float:
        """Calculate combined more multiplier."""
        total = 1.0
        for multiplier in self.more_multipliers:
            total *= multiplier
        return total


@dataclass
class SpiritReservation:
    """
    Represents a single Spirit reservation (gem/aura/minion).

    NEW in PoE2: Spirit is used for permanent effects like:
    - Permanent minions (zombies, spectres, golems)
    - Auras and buffs
    - Meta-gems that persist
    """
    name: str
    base_cost: int
    support_multipliers: List[float] = field(default_factory=list)
    enabled: bool = True

    def calculate_cost(self) -> int:
        """
        Calculate actual Spirit cost with support gem multipliers.

        Returns:
            Final Spirit cost (rounded up)
        """
        if not self.enabled:
            return 0

        cost = float(self.base_cost)
        for multiplier in self.support_multipliers:
            cost *= multiplier

        # Spirit costs are rounded up in PoE2
        return int(cost + 0.999999)  # Ceiling function


@dataclass
class ResourcePool:
    """Represents a character's resource pool (Life/Mana/ES/Spirit)."""
    maximum: float = 0.0
    current: float = 0.0
    reserved_flat: float = 0.0
    reserved_percent: float = 0.0

    def __post_init__(self):
        """Initialize current to maximum if not set."""
        if self.current == 0.0:
            self.current = self.maximum

    @property
    def unreserved_maximum(self) -> float:
        """Calculate unreserved maximum (maximum available for spending)."""
        reserved_amount = self.reserved_flat + (self.maximum * self.reserved_percent / 100.0)
        return max(0.0, self.maximum - reserved_amount)

    @property
    def reserved_amount(self) -> float:
        """Calculate total reserved amount."""
        return self.maximum - self.unreserved_maximum

    @property
    def percent_available(self) -> float:
        """Calculate percentage of unreserved pool available."""
        if self.unreserved_maximum <= 0:
            return 0.0
        return (self.current / self.unreserved_maximum) * 100.0


class ResourceCalculator:
    """
    Main calculator for all PoE2 resource calculations.

    Handles:
    - Life, Mana, Energy Shield (traditional)
    - Spirit (NEW in PoE2)
    - Accuracy
    - Attribute bonuses
    """

    # PoE2 Constants
    BASE_LIFE_AT_LEVEL_1 = 28  # Changed from 38 in PoE1
    LIFE_PER_LEVEL = 12
    LIFE_PER_STRENGTH = 2

    BASE_MANA_AT_LEVEL_1 = 34
    MANA_PER_LEVEL = 4  # Changed from 6 in PoE1
    MANA_PER_INTELLIGENCE = 2
    BASE_MANA_REGEN_PERCENT = 4.0  # 4% per second

    BASE_SPIRIT_FROM_QUESTS = 100  # PoE2: Base Spirit from quest rewards

    ACCURACY_PER_LEVEL = 6
    ACCURACY_PER_DEXTERITY = 6

    def __init__(self, character_level: int, attributes: AttributeStats):
        """
        Initialize resource calculator.

        Args:
            character_level: Character level (1-100)
            attributes: Character attributes (Str/Dex/Int)

        Raises:
            ValueError: If level is out of valid range
        """
        if not 1 <= character_level <= 100:
            raise ValueError("Character level must be between 1 and 100")

        self.level = character_level
        self.attributes = attributes
        self.spirit_reservations: List[SpiritReservation] = []

        logger.info(f"Initialized ResourceCalculator for level {character_level}")

    def calculate_maximum_life(
        self,
        modifiers: Optional[ResourceModifiers] = None
    ) -> float:
        """
        Calculate maximum Life using PoE2 formula.

        Formula:
            Base = 28 + (12 × level) + (2 × strength) + flat_bonuses
            Final = Base × (1 + increased%) × more_multipliers

        Args:
            modifiers: Life modifiers (flat, increased, more)

        Returns:
            Maximum Life value
        """
        if modifiers is None:
            modifiers = ResourceModifiers()

        # Calculate base life
        base_life = (
            self.BASE_LIFE_AT_LEVEL_1 +
            (self.LIFE_PER_LEVEL * self.level) +
            (self.LIFE_PER_STRENGTH * self.attributes.strength)
        )

        # Add flat bonuses
        base_life += modifiers.flat_bonus

        # Apply increased %
        increased_multiplier = 1.0 + (modifiers.increased_percent / 100.0)
        life_after_increased = base_life * increased_multiplier

        # Apply more multipliers
        final_life = life_after_increased * modifiers.calculate_total_more()

        logger.debug(
            f"Life calculation: base={base_life}, "
            f"increased%={modifiers.increased_percent}, "
            f"final={final_life}"
        )

        return round(final_life, 1)

    def calculate_maximum_mana(
        self,
        modifiers: Optional[ResourceModifiers] = None
    ) -> float:
        """
        Calculate maximum Mana using PoE2 formula.

        Formula:
            Base = 34 + (4 × level) + (2 × intelligence) + flat_bonuses
            Final = Base × (1 + increased%) × more_multipliers

        Args:
            modifiers: Mana modifiers (flat, increased, more)

        Returns:
            Maximum Mana value
        """
        if modifiers is None:
            modifiers = ResourceModifiers()

        # Calculate base mana
        base_mana = (
            self.BASE_MANA_AT_LEVEL_1 +
            (self.MANA_PER_LEVEL * self.level) +
            (self.MANA_PER_INTELLIGENCE * self.attributes.intelligence)
        )

        # Add flat bonuses
        base_mana += modifiers.flat_bonus

        # Apply increased %
        increased_multiplier = 1.0 + (modifiers.increased_percent / 100.0)
        mana_after_increased = base_mana * increased_multiplier

        # Apply more multipliers
        final_mana = mana_after_increased * modifiers.calculate_total_more()

        logger.debug(
            f"Mana calculation: base={base_mana}, "
            f"increased%={modifiers.increased_percent}, "
            f"final={final_mana}"
        )

        return round(final_mana, 1)

    def calculate_mana_regeneration(
        self,
        maximum_mana: float,
        increased_regen_percent: float = 0.0,
        flat_regen_per_second: float = 0.0
    ) -> float:
        """
        Calculate mana regeneration per second.

        Formula:
            Base_Regen = maximum_mana × 0.04 (4% per second)
            Increased_Regen = Base_Regen × (1 + increased%)
            Final = Increased_Regen + flat_regen

        Args:
            maximum_mana: Maximum mana pool
            increased_regen_percent: Increased mana regen % (additive)
            flat_regen_per_second: Flat mana regen per second

        Returns:
            Mana regeneration per second
        """
        base_regen = maximum_mana * (self.BASE_MANA_REGEN_PERCENT / 100.0)
        increased_multiplier = 1.0 + (increased_regen_percent / 100.0)
        final_regen = (base_regen * increased_multiplier) + flat_regen_per_second

        return round(final_regen, 2)

    def calculate_maximum_energy_shield(
        self,
        modifiers: Optional[ResourceModifiers] = None
    ) -> float:
        """
        Calculate maximum Energy Shield.

        Formula:
            Base = flat_bonuses (from gear/passives)
            Final = Base × (1 + increased%) × more_multipliers

        Note: ES has no inherent base value, only from gear/passives

        Args:
            modifiers: ES modifiers (flat, increased, more)

        Returns:
            Maximum Energy Shield value
        """
        if modifiers is None:
            modifiers = ResourceModifiers()

        # ES has no base from level or attributes, only flat bonuses
        base_es = modifiers.flat_bonus

        # Apply increased %
        increased_multiplier = 1.0 + (modifiers.increased_percent / 100.0)
        es_after_increased = base_es * increased_multiplier

        # Apply more multipliers
        final_es = es_after_increased * modifiers.calculate_total_more()

        logger.debug(
            f"ES calculation: base={base_es}, "
            f"increased%={modifiers.increased_percent}, "
            f"final={final_es}"
        )

        return round(final_es, 1)

    def calculate_maximum_spirit(
        self,
        modifiers: Optional[ResourceModifiers] = None
    ) -> int:
        """
        Calculate maximum Spirit (NEW in PoE2).

        Spirit is a new resource that limits permanent effects:
        - Permanent minions (zombies, spectres, golems)
        - Persistent auras
        - Meta-gems

        Formula:
            Base = 100 (from quests) + flat_bonuses (from gear/passives)
            Final = Base × (1 + increased%) × more_multipliers

        Note: Spirit increased% modifiers are rare and valuable

        Args:
            modifiers: Spirit modifiers (flat from gear, increased %)

        Returns:
            Maximum Spirit value (integer)
        """
        if modifiers is None:
            modifiers = ResourceModifiers()

        # Base Spirit from quest rewards
        base_spirit = self.BASE_SPIRIT_FROM_QUESTS

        # Add flat bonuses (primarily from gear and passives)
        base_spirit += modifiers.flat_bonus

        # Apply increased % (rare in PoE2)
        increased_multiplier = 1.0 + (modifiers.increased_percent / 100.0)
        spirit_after_increased = base_spirit * increased_multiplier

        # Apply more multipliers (very rare)
        final_spirit = spirit_after_increased * modifiers.calculate_total_more()

        # Spirit is always an integer
        final_spirit_int = int(final_spirit)

        logger.debug(
            f"Spirit calculation: base={base_spirit}, "
            f"increased%={modifiers.increased_percent}, "
            f"final={final_spirit_int}"
        )

        return final_spirit_int

    def add_spirit_reservation(
        self,
        name: str,
        base_cost: int,
        support_multipliers: Optional[List[float]] = None
    ) -> None:
        """
        Add a Spirit reservation (minion/aura/meta-gem).

        Args:
            name: Name of the reservation (e.g., "Raise Zombie", "Purity of Fire")
            base_cost: Base Spirit cost
            support_multipliers: Support gem multipliers (e.g., [1.5, 1.3] for two supports)
        """
        if support_multipliers is None:
            support_multipliers = []

        reservation = SpiritReservation(
            name=name,
            base_cost=base_cost,
            support_multipliers=support_multipliers
        )

        self.spirit_reservations.append(reservation)
        logger.info(
            f"Added Spirit reservation: {name} "
            f"(base={base_cost}, final={reservation.calculate_cost()})"
        )

    def remove_spirit_reservation(self, name: str) -> bool:
        """
        Remove a Spirit reservation by name.

        Args:
            name: Name of the reservation to remove

        Returns:
            True if removed, False if not found
        """
        initial_length = len(self.spirit_reservations)
        self.spirit_reservations = [
            r for r in self.spirit_reservations if r.name != name
        ]

        removed = len(self.spirit_reservations) < initial_length
        if removed:
            logger.info(f"Removed Spirit reservation: {name}")
        else:
            logger.warning(f"Spirit reservation not found: {name}")

        return removed

    def toggle_spirit_reservation(self, name: str) -> bool:
        """
        Toggle a Spirit reservation on/off.

        Args:
            name: Name of the reservation to toggle

        Returns:
            New enabled state, or False if not found
        """
        for reservation in self.spirit_reservations:
            if reservation.name == name:
                reservation.enabled = not reservation.enabled
                logger.info(
                    f"Toggled Spirit reservation {name}: "
                    f"{'enabled' if reservation.enabled else 'disabled'}"
                )
                return reservation.enabled

        logger.warning(f"Spirit reservation not found: {name}")
        return False

    def calculate_spirit_reserved(self) -> int:
        """
        Calculate total Spirit reserved by all active reservations.

        Returns:
            Total Spirit reserved
        """
        total_reserved = sum(
            reservation.calculate_cost()
            for reservation in self.spirit_reservations
        )

        logger.debug(f"Total Spirit reserved: {total_reserved}")
        return total_reserved

    def calculate_spirit_available(
        self,
        maximum_spirit: int
    ) -> int:
        """
        Calculate available Spirit after reservations.

        Args:
            maximum_spirit: Maximum Spirit pool

        Returns:
            Available Spirit (can be negative if over-reserved)
        """
        reserved = self.calculate_spirit_reserved()
        available = maximum_spirit - reserved

        logger.debug(
            f"Spirit: max={maximum_spirit}, "
            f"reserved={reserved}, "
            f"available={available}"
        )

        return available

    def check_spirit_overflow(
        self,
        maximum_spirit: int
    ) -> Tuple[bool, int, List[str]]:
        """
        Check if Spirit reservations exceed maximum (overflow).

        Args:
            maximum_spirit: Maximum Spirit pool

        Returns:
            Tuple of (is_overflowing, overflow_amount, active_reservations)
        """
        available = self.calculate_spirit_available(maximum_spirit)
        is_overflowing = available < 0
        overflow_amount = abs(available) if is_overflowing else 0

        active_reservations = [
            f"{r.name} ({r.calculate_cost()})"
            for r in self.spirit_reservations
            if r.enabled
        ]

        if is_overflowing:
            logger.warning(
                f"Spirit overflow detected! Over by {overflow_amount}. "
                f"Active: {active_reservations}"
            )

        return is_overflowing, overflow_amount, active_reservations

    def get_spirit_reservation_details(self) -> List[Dict[str, any]]:
        """
        Get detailed information about all Spirit reservations.

        Returns:
            List of dictionaries with reservation details
        """
        details = []
        for reservation in self.spirit_reservations:
            details.append({
                'name': reservation.name,
                'base_cost': reservation.base_cost,
                'final_cost': reservation.calculate_cost(),
                'support_multipliers': reservation.support_multipliers,
                'enabled': reservation.enabled
            })

        return details

    def calculate_accuracy(
        self,
        flat_bonus: float = 0.0,
        increased_percent: float = 0.0
    ) -> int:
        """
        Calculate Accuracy rating using PoE2 formula.

        Formula:
            Base = (6 × level) + (6 × dexterity) + flat_bonuses
            Final = Base × (1 + increased%)

        Args:
            flat_bonus: Flat accuracy from gear/passives
            increased_percent: Increased accuracy %

        Returns:
            Accuracy rating (integer)
        """
        # Calculate base accuracy
        base_accuracy = (
            (self.ACCURACY_PER_LEVEL * self.level) +
            (self.ACCURACY_PER_DEXTERITY * self.attributes.dexterity)
        )

        # Add flat bonus
        base_accuracy += flat_bonus

        # Apply increased %
        increased_multiplier = 1.0 + (increased_percent / 100.0)
        final_accuracy = base_accuracy * increased_multiplier

        logger.debug(
            f"Accuracy calculation: base={base_accuracy}, "
            f"increased%={increased_percent}, "
            f"final={int(final_accuracy)}"
        )

        return int(final_accuracy)

    def get_attribute_bonuses(self) -> Dict[str, float]:
        """
        Get all bonuses derived from attributes.

        Returns:
            Dictionary of attribute bonuses
        """
        return {
            'life_from_strength': self.LIFE_PER_STRENGTH * self.attributes.strength,
            'mana_from_intelligence': self.MANA_PER_INTELLIGENCE * self.attributes.intelligence,
            'accuracy_from_dexterity': self.ACCURACY_PER_DEXTERITY * self.attributes.dexterity,
            'strength': self.attributes.strength,
            'dexterity': self.attributes.dexterity,
            'intelligence': self.attributes.intelligence
        }

    def create_resource_pool(
        self,
        resource_type: ResourceType,
        modifiers: Optional[ResourceModifiers] = None
    ) -> ResourcePool:
        """
        Create a complete resource pool with calculated maximum.

        Args:
            resource_type: Type of resource pool to create
            modifiers: Modifiers to apply to the resource

        Returns:
            ResourcePool object with calculated maximum

        Raises:
            ValueError: If resource_type is not supported
        """
        if resource_type == ResourceType.LIFE:
            maximum = self.calculate_maximum_life(modifiers)
        elif resource_type == ResourceType.MANA:
            maximum = self.calculate_maximum_mana(modifiers)
        elif resource_type == ResourceType.ENERGY_SHIELD:
            maximum = self.calculate_maximum_energy_shield(modifiers)
        elif resource_type == ResourceType.SPIRIT:
            maximum = float(self.calculate_maximum_spirit(modifiers))
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")

        pool = ResourcePool(maximum=maximum, current=maximum)
        logger.info(f"Created {resource_type.value} pool: {maximum}")

        return pool

    def calculate_all_resources(
        self,
        life_mods: Optional[ResourceModifiers] = None,
        mana_mods: Optional[ResourceModifiers] = None,
        es_mods: Optional[ResourceModifiers] = None,
        spirit_mods: Optional[ResourceModifiers] = None
    ) -> Dict[str, any]:
        """
        Calculate all resources and return a comprehensive summary.

        Args:
            life_mods: Life modifiers
            mana_mods: Mana modifiers
            es_mods: Energy Shield modifiers
            spirit_mods: Spirit modifiers

        Returns:
            Dictionary containing all resource calculations
        """
        max_life = self.calculate_maximum_life(life_mods)
        max_mana = self.calculate_maximum_mana(mana_mods)
        max_es = self.calculate_maximum_energy_shield(es_mods)
        max_spirit = self.calculate_maximum_spirit(spirit_mods)

        spirit_reserved = self.calculate_spirit_reserved()
        spirit_available = self.calculate_spirit_available(max_spirit)
        spirit_overflow, overflow_amount, active_reservations = self.check_spirit_overflow(max_spirit)

        mana_regen = self.calculate_mana_regeneration(max_mana)
        accuracy = self.calculate_accuracy()
        attribute_bonuses = self.get_attribute_bonuses()

        summary = {
            'level': self.level,
            'attributes': {
                'strength': self.attributes.strength,
                'dexterity': self.attributes.dexterity,
                'intelligence': self.attributes.intelligence
            },
            'resources': {
                'life': {
                    'maximum': max_life,
                    'from_strength': attribute_bonuses['life_from_strength']
                },
                'mana': {
                    'maximum': max_mana,
                    'regeneration_per_second': mana_regen,
                    'from_intelligence': attribute_bonuses['mana_from_intelligence']
                },
                'energy_shield': {
                    'maximum': max_es
                },
                'spirit': {
                    'maximum': max_spirit,
                    'reserved': spirit_reserved,
                    'available': spirit_available,
                    'is_overflowing': spirit_overflow,
                    'overflow_amount': overflow_amount,
                    'active_reservations': active_reservations,
                    'reservation_details': self.get_spirit_reservation_details()
                }
            },
            'accuracy': {
                'rating': accuracy,
                'from_dexterity': attribute_bonuses['accuracy_from_dexterity']
            }
        }

        logger.info("Calculated all resources")
        return summary


def calculate_hit_chance(attacker_accuracy: int, defender_evasion: int) -> float:
    """
    Calculate chance to hit based on accuracy vs evasion.

    PoE2 Formula (approximate):
        Chance = Accuracy / (Accuracy + (Evasion / 4))

    Args:
        attacker_accuracy: Attacker's accuracy rating
        defender_evasion: Defender's evasion rating

    Returns:
        Hit chance as percentage (0-100)
    """
    if attacker_accuracy <= 0:
        return 0.0

    if defender_evasion <= 0:
        return 100.0

    # PoE2 formula (simplified)
    chance = attacker_accuracy / (attacker_accuracy + (defender_evasion / 4.0))
    chance_percent = chance * 100.0

    # Clamp between 5% and 100%
    chance_percent = max(5.0, min(100.0, chance_percent))

    return round(chance_percent, 2)


# Example usage and testing
if __name__ == "__main__":
    # Configure logging for testing
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 80)
    print("Path of Exile 2 Resource Calculator - Test Suite")
    print("=" * 80)
    print()

    # Create a test character
    print("Creating level 50 character with 150 Str, 100 Dex, 120 Int...")
    attributes = AttributeStats(strength=150, dexterity=100, intelligence=120)
    calculator = ResourceCalculator(character_level=50, attributes=attributes)
    print()

    # Test Life calculation
    print("-" * 80)
    print("LIFE CALCULATION")
    print("-" * 80)
    life_mods = ResourceModifiers(
        flat_bonus=50,  # +50 from gear
        increased_percent=120,  # 120% increased
        more_multipliers=[1.15]  # 15% more
    )
    max_life = calculator.calculate_maximum_life(life_mods)
    print(f"Maximum Life: {max_life}")
    print()

    # Test Mana calculation
    print("-" * 80)
    print("MANA CALCULATION")
    print("-" * 80)
    mana_mods = ResourceModifiers(
        flat_bonus=30,
        increased_percent=80
    )
    max_mana = calculator.calculate_maximum_mana(mana_mods)
    mana_regen = calculator.calculate_mana_regeneration(
        max_mana,
        increased_regen_percent=50
    )
    print(f"Maximum Mana: {max_mana}")
    print(f"Mana Regen: {mana_regen}/s")
    print()

    # Test Energy Shield calculation
    print("-" * 80)
    print("ENERGY SHIELD CALCULATION")
    print("-" * 80)
    es_mods = ResourceModifiers(
        flat_bonus=200,  # ES only from gear
        increased_percent=150
    )
    max_es = calculator.calculate_maximum_energy_shield(es_mods)
    print(f"Maximum Energy Shield: {max_es}")
    print()

    # Test Spirit calculation (NEW in PoE2)
    print("-" * 80)
    print("SPIRIT CALCULATION (NEW IN POE2)")
    print("-" * 80)
    spirit_mods = ResourceModifiers(
        flat_bonus=50,  # +50 from gear
        increased_percent=20  # 20% increased (rare!)
    )
    max_spirit = calculator.calculate_maximum_spirit(spirit_mods)
    print(f"Maximum Spirit: {max_spirit}")
    print()

    # Test Spirit reservations
    print("-" * 80)
    print("SPIRIT RESERVATIONS")
    print("-" * 80)
    calculator.add_spirit_reservation("Raise Zombie", 25, [1.5])  # 25 * 1.5 = 38
    calculator.add_spirit_reservation("Summon Skeleton", 20, [1.4, 1.3])  # 20 * 1.4 * 1.3 = 37
    calculator.add_spirit_reservation("Purity of Fire", 30)  # 30

    spirit_reserved = calculator.calculate_spirit_reserved()
    spirit_available = calculator.calculate_spirit_available(max_spirit)
    overflow, overflow_amt, active = calculator.check_spirit_overflow(max_spirit)

    print(f"Total Reserved: {spirit_reserved}")
    print(f"Available: {spirit_available}")
    print(f"Overflowing: {overflow} (by {overflow_amt})")
    print(f"Active Reservations: {active}")
    print()

    # Test reservation details
    print("Reservation Details:")
    for detail in calculator.get_spirit_reservation_details():
        print(f"  - {detail['name']}: {detail['base_cost']} -> {detail['final_cost']} "
              f"(multipliers: {detail['support_multipliers']}) "
              f"[{'ON' if detail['enabled'] else 'OFF'}]")
    print()

    # Test Accuracy
    print("-" * 80)
    print("ACCURACY CALCULATION")
    print("-" * 80)
    accuracy = calculator.calculate_accuracy(
        flat_bonus=200,
        increased_percent=50
    )
    hit_chance = calculate_hit_chance(accuracy, 1500)
    print(f"Accuracy Rating: {accuracy}")
    print(f"Hit Chance vs 1500 Evasion: {hit_chance}%")
    print()

    # Test attribute bonuses
    print("-" * 80)
    print("ATTRIBUTE BONUSES")
    print("-" * 80)
    bonuses = calculator.get_attribute_bonuses()
    for key, value in bonuses.items():
        print(f"{key}: {value}")
    print()

    # Full summary
    print("=" * 80)
    print("COMPLETE CHARACTER SUMMARY")
    print("=" * 80)
    summary = calculator.calculate_all_resources(
        life_mods=life_mods,
        mana_mods=mana_mods,
        es_mods=es_mods,
        spirit_mods=spirit_mods
    )

    import json
    print(json.dumps(summary, indent=2))
    print()

    print("=" * 80)
    print("Test suite complete!")
    print("=" * 80)
