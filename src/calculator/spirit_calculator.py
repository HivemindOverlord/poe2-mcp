"""
Spirit Calculator for Path of Exile 2

This module provides advanced Spirit management for PoE2's unique Spirit system.
Spirit is a NEW resource in PoE2 that limits permanent minions, auras, and meta-gems.

This extends the basic Spirit tracking in resource_calculator.py with:
- Advanced reservation management
- Support gem cost optimization
- Overflow detection and resolution
- Smart suggestions for reducing Spirit usage
- Quest vs Gear tracking
- Integration with build planning

Key PoE2 Mechanics:
- Base Spirit: 100 (from 3 quest skulls: 30 + 30 + 40)
- Additional Spirit: From gear, passives, ascendancy
- Spirit Costs: Base cost × support_multiplier_1 × support_multiplier_2 × ...
- Rounding: Always rounds UP (ceiling)

Author: Claude
Date: 2025-10-22
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum
import math

# Configure logging
logger = logging.getLogger(__name__)


class SpiritSourceType(Enum):
    """Types of Spirit sources in PoE2."""
    QUEST = "quest"  # From skull quests (30, 30, 40)
    GEAR = "gear"  # From equipment
    PASSIVE_TREE = "passive_tree"  # From passive tree nodes
    ASCENDANCY = "ascendancy"  # From ascendancy nodes
    BUFF = "buff"  # Temporary Spirit buffs
    OTHER = "other"  # Other sources


class SpiritReservationType(Enum):
    """Types of Spirit reservations in PoE2."""
    PERMANENT_MINION = "permanent_minion"  # Zombies, Spectres, Golems
    AURA = "aura"  # Auras and buffs
    META_GEM = "meta_gem"  # Meta-gems that persist
    OTHER = "other"  # Other Spirit-consuming effects


@dataclass
class SpiritSource:
    """
    Represents a source of maximum Spirit.

    Attributes:
        name: Source name (e.g., "First Skull Quest", "Helmet +30 Spirit")
        amount: Amount of Spirit provided
        source_type: Type of source
        enabled: Whether this source is active
    """
    name: str
    amount: int
    source_type: SpiritSourceType
    enabled: bool = True

    def __post_init__(self):
        """Validate source."""
        if self.amount < 0:
            raise ValueError("Spirit amount cannot be negative")


@dataclass
class SupportGem:
    """
    Represents a support gem with its cost multiplier.

    Attributes:
        name: Support gem name
        multiplier: Cost multiplier (e.g., 1.5 for 150%, 1.3 for 130%)
    """
    name: str
    multiplier: float

    def __post_init__(self):
        """Validate multiplier."""
        if self.multiplier < 1.0:
            raise ValueError("Support multiplier must be >= 1.0")


@dataclass
class SpiritReservation:
    """
    Represents a single Spirit reservation (minion/aura/meta-gem).

    Attributes:
        name: Reservation name
        base_cost: Base Spirit cost
        reservation_type: Type of reservation
        support_gems: List of support gems affecting this reservation
        enabled: Whether this reservation is active
        priority: Priority for auto-disable (lower = higher priority to keep)
    """
    name: str
    base_cost: int
    reservation_type: SpiritReservationType
    support_gems: List[SupportGem] = field(default_factory=list)
    enabled: bool = True
    priority: int = 5  # 1-10 scale (1 = essential, 10 = least important)

    def __post_init__(self):
        """Validate reservation."""
        if self.base_cost < 0:
            raise ValueError("Base cost cannot be negative")
        if not 1 <= self.priority <= 10:
            raise ValueError("Priority must be between 1 and 10")

    def calculate_cost(self) -> int:
        """
        Calculate actual Spirit cost with support gem multipliers.

        Returns:
            Final Spirit cost (rounded UP)

        Examples:
            >>> gem = SpiritReservation("Test", 20, SpiritReservationType.AURA)
            >>> gem.calculate_cost()
            20
            >>> gem.support_gems = [SupportGem("Support1", 1.5), SupportGem("Support2", 1.3)]
            >>> gem.calculate_cost()
            39
        """
        if not self.enabled:
            return 0

        cost = float(self.base_cost)
        for support_gem in self.support_gems:
            cost *= support_gem.multiplier

        # Spirit costs always round UP in PoE2
        return math.ceil(cost)

    def get_cost_breakdown(self) -> Dict[str, any]:
        """
        Get detailed breakdown of cost calculation.

        Returns:
            Dictionary with cost calculation details
        """
        breakdown = {
            'base_cost': self.base_cost,
            'support_gems': [
                {'name': sg.name, 'multiplier': sg.multiplier}
                for sg in self.support_gems
            ],
            'total_multiplier': self._calculate_total_multiplier(),
            'raw_cost': self.base_cost * self._calculate_total_multiplier(),
            'final_cost': self.calculate_cost(),
            'enabled': self.enabled
        }
        return breakdown

    def _calculate_total_multiplier(self) -> float:
        """Calculate combined support gem multiplier."""
        multiplier = 1.0
        for support_gem in self.support_gems:
            multiplier *= support_gem.multiplier
        return multiplier

    def add_support_gem(self, name: str, multiplier: float) -> None:
        """
        Add a support gem to this reservation.

        Args:
            name: Support gem name
            multiplier: Cost multiplier
        """
        support_gem = SupportGem(name=name, multiplier=multiplier)
        self.support_gems.append(support_gem)
        logger.info(
            f"Added support gem '{name}' ({multiplier}x) to '{self.name}'. "
            f"New cost: {self.calculate_cost()}"
        )

    def remove_support_gem(self, name: str) -> bool:
        """
        Remove a support gem by name.

        Args:
            name: Support gem name to remove

        Returns:
            True if removed, False if not found
        """
        initial_length = len(self.support_gems)
        self.support_gems = [sg for sg in self.support_gems if sg.name != name]

        removed = len(self.support_gems) < initial_length
        if removed:
            logger.info(f"Removed support gem '{name}' from '{self.name}'")
        return removed

    def get_optimization_suggestions(self) -> List[str]:
        """
        Suggest ways to reduce Spirit cost for this reservation.

        Returns:
            List of optimization suggestions
        """
        suggestions = []

        if not self.support_gems:
            suggestions.append("No support gems - cost is optimal")
            return suggestions

        # Find most expensive support gem
        if self.support_gems:
            most_expensive = max(self.support_gems, key=lambda sg: sg.multiplier)
            savings = self.calculate_cost() - math.ceil(
                self.base_cost * (self._calculate_total_multiplier() / most_expensive.multiplier)
            )
            suggestions.append(
                f"Remove '{most_expensive.name}' ({most_expensive.multiplier}x) "
                f"to save {savings} Spirit"
            )

        # Suggest replacing high multiplier supports
        high_multiplier_supports = [
            sg for sg in self.support_gems if sg.multiplier >= 1.5
        ]
        if high_multiplier_supports:
            suggestions.append(
                f"Consider replacing high-multiplier supports: "
                f"{', '.join([sg.name for sg in high_multiplier_supports])}"
            )

        return suggestions


@dataclass
class SpiritOptimization:
    """
    Represents an optimization suggestion for Spirit management.

    Attributes:
        description: Human-readable description
        spirit_saved: Amount of Spirit that would be saved
        action_type: Type of action (disable, remove_support, etc.)
        target: Target reservation/support name
    """
    description: str
    spirit_saved: int
    action_type: str
    target: str


class SpiritCalculator:
    """
    Advanced Spirit calculator for Path of Exile 2.

    Provides comprehensive Spirit management including:
    - Multiple Spirit sources (quests, gear, passives)
    - Detailed reservation tracking
    - Support gem optimization
    - Overflow detection and resolution
    - Smart suggestions for Spirit optimization

    Examples:
        >>> calc = SpiritCalculator()
        >>> calc.add_quest_spirit("First Skull", 30)
        >>> calc.add_quest_spirit("Second Skull", 30)
        >>> calc.add_quest_spirit("Third Skull", 40)
        >>> calc.get_maximum_spirit()
        100
        >>> calc.add_reservation("Raise Zombie", 25, SpiritReservationType.PERMANENT_MINION)
        >>> calc.get_spirit_reserved()
        25
        >>> calc.get_spirit_available()
        75
    """

    def __init__(self):
        """Initialize Spirit calculator."""
        self.sources: List[SpiritSource] = []
        self.reservations: List[SpiritReservation] = []

        logger.info("Initialized SpiritCalculator")

    # === Spirit Sources Management ===

    def add_quest_spirit(self, quest_name: str, amount: int) -> None:
        """
        Add Spirit from a quest reward.

        Args:
            quest_name: Name of the quest
            amount: Spirit amount (typically 30, 30, or 40)
        """
        source = SpiritSource(
            name=quest_name,
            amount=amount,
            source_type=SpiritSourceType.QUEST
        )
        self.sources.append(source)
        logger.info(f"Added quest Spirit: {quest_name} (+{amount})")

    def add_gear_spirit(self, item_name: str, amount: int) -> None:
        """
        Add Spirit from gear.

        Args:
            item_name: Name of the item
            amount: Spirit bonus from item
        """
        source = SpiritSource(
            name=item_name,
            amount=amount,
            source_type=SpiritSourceType.GEAR
        )
        self.sources.append(source)
        logger.info(f"Added gear Spirit: {item_name} (+{amount})")

    def add_passive_spirit(self, node_name: str, amount: int) -> None:
        """
        Add Spirit from passive tree.

        Args:
            node_name: Name of the passive node
            amount: Spirit bonus from node
        """
        source = SpiritSource(
            name=node_name,
            amount=amount,
            source_type=SpiritSourceType.PASSIVE_TREE
        )
        self.sources.append(source)
        logger.info(f"Added passive Spirit: {node_name} (+{amount})")

    def add_spirit_source(
        self,
        name: str,
        amount: int,
        source_type: SpiritSourceType
    ) -> None:
        """
        Add a generic Spirit source.

        Args:
            name: Source name
            amount: Spirit amount
            source_type: Type of source
        """
        source = SpiritSource(
            name=name,
            amount=amount,
            source_type=source_type
        )
        self.sources.append(source)
        logger.info(f"Added Spirit source: {name} (+{amount}) [{source_type.value}]")

    def remove_spirit_source(self, name: str) -> bool:
        """
        Remove a Spirit source by name.

        Args:
            name: Source name to remove

        Returns:
            True if removed, False if not found
        """
        initial_length = len(self.sources)
        self.sources = [s for s in self.sources if s.name != name]

        removed = len(self.sources) < initial_length
        if removed:
            logger.info(f"Removed Spirit source: {name}")
        else:
            logger.warning(f"Spirit source not found: {name}")
        return removed

    def toggle_spirit_source(self, name: str) -> bool:
        """
        Toggle a Spirit source on/off.

        Args:
            name: Source name to toggle

        Returns:
            New enabled state, or False if not found
        """
        for source in self.sources:
            if source.name == name:
                source.enabled = not source.enabled
                logger.info(
                    f"Toggled Spirit source '{name}': "
                    f"{'enabled' if source.enabled else 'disabled'}"
                )
                return source.enabled

        logger.warning(f"Spirit source not found: {name}")
        return False

    def get_maximum_spirit(self) -> int:
        """
        Calculate maximum Spirit from all active sources.

        Returns:
            Total maximum Spirit
        """
        total = sum(
            source.amount
            for source in self.sources
            if source.enabled
        )
        return total

    def get_spirit_by_source_type(self, source_type: SpiritSourceType) -> int:
        """
        Get Spirit from a specific source type.

        Args:
            source_type: Type of source to sum

        Returns:
            Total Spirit from that source type
        """
        total = sum(
            source.amount
            for source in self.sources
            if source.enabled and source.source_type == source_type
        )
        return total

    def get_quest_spirit(self) -> int:
        """Get total Spirit from quests."""
        return self.get_spirit_by_source_type(SpiritSourceType.QUEST)

    def get_gear_spirit(self) -> int:
        """Get total Spirit from gear."""
        return self.get_spirit_by_source_type(SpiritSourceType.GEAR)

    def get_passive_spirit(self) -> int:
        """Get total Spirit from passive tree."""
        return self.get_spirit_by_source_type(SpiritSourceType.PASSIVE_TREE)

    # === Reservation Management ===

    def add_reservation(
        self,
        name: str,
        base_cost: int,
        reservation_type: SpiritReservationType,
        support_gems: Optional[List[Tuple[str, float]]] = None,
        priority: int = 5
    ) -> SpiritReservation:
        """
        Add a Spirit reservation.

        Args:
            name: Reservation name
            base_cost: Base Spirit cost
            reservation_type: Type of reservation
            support_gems: List of (name, multiplier) tuples
            priority: Priority (1-10, lower = more important)

        Returns:
            The created SpiritReservation
        """
        # Create support gem objects
        support_gem_objs = []
        if support_gems:
            for gem_name, multiplier in support_gems:
                support_gem_objs.append(SupportGem(name=gem_name, multiplier=multiplier))

        reservation = SpiritReservation(
            name=name,
            base_cost=base_cost,
            reservation_type=reservation_type,
            support_gems=support_gem_objs,
            priority=priority
        )

        self.reservations.append(reservation)
        logger.info(
            f"Added Spirit reservation: {name} "
            f"(base={base_cost}, final={reservation.calculate_cost()}, priority={priority})"
        )

        return reservation

    def remove_reservation(self, name: str) -> bool:
        """
        Remove a Spirit reservation by name.

        Args:
            name: Reservation name to remove

        Returns:
            True if removed, False if not found
        """
        initial_length = len(self.reservations)
        self.reservations = [r for r in self.reservations if r.name != name]

        removed = len(self.reservations) < initial_length
        if removed:
            logger.info(f"Removed Spirit reservation: {name}")
        else:
            logger.warning(f"Spirit reservation not found: {name}")
        return removed

    def toggle_reservation(self, name: str) -> bool:
        """
        Toggle a Spirit reservation on/off.

        Args:
            name: Reservation name to toggle

        Returns:
            New enabled state, or False if not found
        """
        for reservation in self.reservations:
            if reservation.name == name:
                reservation.enabled = not reservation.enabled
                logger.info(
                    f"Toggled Spirit reservation '{name}': "
                    f"{'enabled' if reservation.enabled else 'disabled'}"
                )
                return reservation.enabled

        logger.warning(f"Spirit reservation not found: {name}")
        return False

    def get_reservation(self, name: str) -> Optional[SpiritReservation]:
        """
        Get a reservation by name.

        Args:
            name: Reservation name

        Returns:
            SpiritReservation if found, None otherwise
        """
        for reservation in self.reservations:
            if reservation.name == name:
                return reservation
        return None

    def get_spirit_reserved(self) -> int:
        """
        Calculate total Spirit reserved by all active reservations.

        Returns:
            Total Spirit reserved
        """
        total = sum(
            reservation.calculate_cost()
            for reservation in self.reservations
        )
        return total

    def get_spirit_available(self) -> int:
        """
        Calculate available Spirit after reservations.

        Returns:
            Available Spirit (can be negative if over-reserved)
        """
        maximum = self.get_maximum_spirit()
        reserved = self.get_spirit_reserved()
        return maximum - reserved

    def is_overflowing(self) -> bool:
        """
        Check if Spirit reservations exceed maximum.

        Returns:
            True if over-reserved, False otherwise
        """
        return self.get_spirit_available() < 0

    def get_overflow_amount(self) -> int:
        """
        Get amount of Spirit overflow (if any).

        Returns:
            Overflow amount (0 if not overflowing)
        """
        available = self.get_spirit_available()
        return abs(available) if available < 0 else 0

    # === Analysis and Reporting ===

    def get_reservation_details(self) -> List[Dict[str, any]]:
        """
        Get detailed information about all Spirit reservations.

        Returns:
            List of dictionaries with reservation details
        """
        details = []
        for reservation in self.reservations:
            details.append({
                'name': reservation.name,
                'type': reservation.reservation_type.value,
                'base_cost': reservation.base_cost,
                'final_cost': reservation.calculate_cost(),
                'support_gems': [
                    {'name': sg.name, 'multiplier': sg.multiplier}
                    for sg in reservation.support_gems
                ],
                'enabled': reservation.enabled,
                'priority': reservation.priority,
                'cost_breakdown': reservation.get_cost_breakdown()
            })
        return details

    def get_source_details(self) -> List[Dict[str, any]]:
        """
        Get detailed information about all Spirit sources.

        Returns:
            List of dictionaries with source details
        """
        details = []
        for source in self.sources:
            details.append({
                'name': source.name,
                'amount': source.amount,
                'type': source.source_type.value,
                'enabled': source.enabled
            })
        return details

    def get_spirit_summary(self) -> Dict[str, any]:
        """
        Get comprehensive Spirit summary.

        Returns:
            Dictionary with complete Spirit status
        """
        maximum = self.get_maximum_spirit()
        reserved = self.get_spirit_reserved()
        available = self.get_spirit_available()
        overflowing = self.is_overflowing()
        overflow_amount = self.get_overflow_amount()

        # Count reservations by type
        reservation_counts = {}
        for res_type in SpiritReservationType:
            count = sum(
                1 for r in self.reservations
                if r.enabled and r.reservation_type == res_type
            )
            reservation_counts[res_type.value] = count

        # Count sources by type
        source_breakdown = {}
        for src_type in SpiritSourceType:
            amount = self.get_spirit_by_source_type(src_type)
            source_breakdown[src_type.value] = amount

        summary = {
            'maximum_spirit': maximum,
            'reserved_spirit': reserved,
            'available_spirit': available,
            'is_overflowing': overflowing,
            'overflow_amount': overflow_amount,
            'utilization_percent': (reserved / maximum * 100) if maximum > 0 else 0,
            'source_breakdown': source_breakdown,
            'reservation_counts': reservation_counts,
            'active_reservations': len([r for r in self.reservations if r.enabled]),
            'total_reservations': len(self.reservations)
        }

        return summary

    def get_active_reservations(self) -> List[str]:
        """
        Get list of active reservation names.

        Returns:
            List of active reservation names with costs
        """
        return [
            f"{r.name} ({r.calculate_cost()})"
            for r in self.reservations
            if r.enabled
        ]

    # === Optimization ===

    def get_optimization_suggestions(
        self,
        target_spirit_to_free: Optional[int] = None
    ) -> List[SpiritOptimization]:
        """
        Get suggestions for optimizing Spirit usage.

        Args:
            target_spirit_to_free: How much Spirit needs to be freed (None = all overflow)

        Returns:
            List of optimization suggestions sorted by effectiveness
        """
        suggestions = []

        # If no target specified, use overflow amount
        if target_spirit_to_free is None:
            target_spirit_to_free = self.get_overflow_amount()

        if target_spirit_to_free <= 0:
            return suggestions

        # Option 1: Disable entire reservations (sorted by priority, then cost)
        for reservation in sorted(
            self.reservations,
            key=lambda r: (-r.priority, -r.calculate_cost())
        ):
            if not reservation.enabled:
                continue

            suggestions.append(SpiritOptimization(
                description=f"Disable '{reservation.name}' (priority {reservation.priority})",
                spirit_saved=reservation.calculate_cost(),
                action_type="disable_reservation",
                target=reservation.name
            ))

        # Option 2: Remove support gems from reservations
        for reservation in self.reservations:
            if not reservation.enabled or not reservation.support_gems:
                continue

            # For each support gem, calculate savings
            for support_gem in sorted(
                reservation.support_gems,
                key=lambda sg: -sg.multiplier
            ):
                cost_with = reservation.calculate_cost()

                # Calculate cost without this support
                temp_multiplier = 1.0
                for sg in reservation.support_gems:
                    if sg.name != support_gem.name:
                        temp_multiplier *= sg.multiplier
                cost_without = math.ceil(reservation.base_cost * temp_multiplier)

                savings = cost_with - cost_without
                if savings > 0:
                    suggestions.append(SpiritOptimization(
                        description=f"Remove '{support_gem.name}' from '{reservation.name}'",
                        spirit_saved=savings,
                        action_type="remove_support",
                        target=f"{reservation.name}::{support_gem.name}"
                    ))

        # Sort by spirit saved (descending)
        suggestions.sort(key=lambda s: -s.spirit_saved)

        return suggestions

    def auto_resolve_overflow(self) -> List[str]:
        """
        Automatically resolve Spirit overflow by disabling lowest priority reservations.

        Returns:
            List of actions taken
        """
        actions = []
        overflow = self.get_overflow_amount()

        if overflow <= 0:
            logger.info("No overflow to resolve")
            return actions

        logger.info(f"Auto-resolving {overflow} Spirit overflow")

        # Sort reservations by priority (highest priority value = least important)
        sorted_reservations = sorted(
            [r for r in self.reservations if r.enabled],
            key=lambda r: (-r.priority, -r.calculate_cost())
        )

        spirit_freed = 0
        for reservation in sorted_reservations:
            if spirit_freed >= overflow:
                break

            cost = reservation.calculate_cost()
            reservation.enabled = False
            spirit_freed += cost

            action = f"Disabled '{reservation.name}' (priority {reservation.priority}, freed {cost} Spirit)"
            actions.append(action)
            logger.info(action)

        final_overflow = self.get_overflow_amount()
        if final_overflow > 0:
            logger.warning(
                f"Could not fully resolve overflow. Remaining: {final_overflow} Spirit"
            )
        else:
            logger.info("Successfully resolved Spirit overflow")

        return actions

    def suggest_optimal_configuration(self) -> Dict[str, any]:
        """
        Suggest optimal Spirit configuration to maximize usage without overflow.

        Returns:
            Dictionary with suggestions and configuration
        """
        max_spirit = self.get_maximum_spirit()

        # Sort reservations by priority (lower = more important)
        sorted_reservations = sorted(
            self.reservations,
            key=lambda r: (r.priority, -r.calculate_cost())
        )

        # Build optimal configuration
        enabled_reservations = []
        disabled_reservations = []
        spirit_used = 0

        for reservation in sorted_reservations:
            cost = reservation.calculate_cost()
            if spirit_used + cost <= max_spirit:
                enabled_reservations.append(reservation.name)
                spirit_used += cost
            else:
                disabled_reservations.append(reservation.name)

        suggestion = {
            'maximum_spirit': max_spirit,
            'optimal_spirit_used': spirit_used,
            'optimal_spirit_remaining': max_spirit - spirit_used,
            'enabled_reservations': enabled_reservations,
            'disabled_reservations': disabled_reservations,
            'efficiency_percent': (spirit_used / max_spirit * 100) if max_spirit > 0 else 0
        }

        return suggestion

    # === Validation ===

    def validate_configuration(self) -> Tuple[bool, List[str]]:
        """
        Validate current Spirit configuration.

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Check for overflow
        if self.is_overflowing():
            overflow = self.get_overflow_amount()
            issues.append(f"Spirit overflow: {overflow} Spirit over maximum")

        # Check for duplicate names
        reservation_names = [r.name for r in self.reservations]
        duplicates = set([name for name in reservation_names if reservation_names.count(name) > 1])
        if duplicates:
            issues.append(f"Duplicate reservation names: {', '.join(duplicates)}")

        source_names = [s.name for s in self.sources]
        duplicates = set([name for name in source_names if source_names.count(name) > 1])
        if duplicates:
            issues.append(f"Duplicate source names: {', '.join(duplicates)}")

        # Check for zero maximum Spirit
        if self.get_maximum_spirit() == 0:
            issues.append("No Spirit sources configured (maximum Spirit is 0)")

        # Check for reservations with no support gems but high costs
        for reservation in self.reservations:
            if reservation.base_cost > 50 and not reservation.support_gems:
                issues.append(
                    f"'{reservation.name}' has high base cost ({reservation.base_cost}) "
                    "but no support gems - verify this is correct"
                )

        is_valid = len(issues) == 0
        return is_valid, issues

    # === Export/Import ===

    def export_configuration(self) -> Dict[str, any]:
        """
        Export complete Spirit configuration.

        Returns:
            Dictionary with all configuration data
        """
        return {
            'sources': self.get_source_details(),
            'reservations': self.get_reservation_details(),
            'summary': self.get_spirit_summary()
        }

    def import_configuration(self, config: Dict[str, any]) -> None:
        """
        Import Spirit configuration.

        Args:
            config: Configuration dictionary (from export_configuration)
        """
        # Clear existing configuration
        self.sources.clear()
        self.reservations.clear()

        # Import sources
        for source_data in config.get('sources', []):
            source = SpiritSource(
                name=source_data['name'],
                amount=source_data['amount'],
                source_type=SpiritSourceType(source_data['type']),
                enabled=source_data.get('enabled', True)
            )
            self.sources.append(source)

        # Import reservations
        for res_data in config.get('reservations', []):
            support_gems = [
                SupportGem(name=sg['name'], multiplier=sg['multiplier'])
                for sg in res_data.get('support_gems', [])
            ]

            reservation = SpiritReservation(
                name=res_data['name'],
                base_cost=res_data['base_cost'],
                reservation_type=SpiritReservationType(res_data['type']),
                support_gems=support_gems,
                enabled=res_data.get('enabled', True),
                priority=res_data.get('priority', 5)
            )
            self.reservations.append(reservation)

        logger.info("Imported Spirit configuration")


# === Helper Functions ===

def calculate_support_gem_cost(
    base_cost: int,
    support_multipliers: List[float]
) -> int:
    """
    Calculate final Spirit cost with support gem multipliers.

    Args:
        base_cost: Base Spirit cost
        support_multipliers: List of support multipliers

    Returns:
        Final cost (rounded UP)

    Examples:
        >>> calculate_support_gem_cost(20, [1.5, 1.3])
        39
        >>> calculate_support_gem_cost(25, [1.4])
        35
    """
    cost = float(base_cost)
    for multiplier in support_multipliers:
        cost *= multiplier
    return math.ceil(cost)


def find_optimal_support_combinations(
    base_cost: int,
    available_supports: List[Tuple[str, float]],
    max_spirit: int
) -> List[Tuple[List[str], int]]:
    """
    Find all valid support gem combinations that fit within Spirit budget.

    Args:
        base_cost: Base Spirit cost
        available_supports: List of (name, multiplier) tuples
        max_spirit: Maximum Spirit budget for this reservation

    Returns:
        List of (support_names, total_cost) tuples, sorted by cost descending
    """
    from itertools import combinations

    valid_combos = []

    # Try all combinations of supports (including empty)
    for r in range(len(available_supports) + 1):
        for combo in combinations(available_supports, r):
            if not combo:
                cost = base_cost
                names = []
            else:
                names = [name for name, _ in combo]
                multipliers = [mult for _, mult in combo]
                cost = calculate_support_gem_cost(base_cost, multipliers)

            if cost <= max_spirit:
                valid_combos.append((names, cost))

    # Sort by cost descending (most powerful first)
    valid_combos.sort(key=lambda x: -x[1])

    return valid_combos


# === Example Usage and Testing ===

if __name__ == "__main__":
    # Configure logging for testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 80)
    print("Path of Exile 2 Spirit Calculator - Test Suite")
    print("=" * 80)
    print()

    # Create Spirit calculator
    print("Creating Spirit calculator...")
    calc = SpiritCalculator()
    print()

    # === Test 1: Quest Spirit ===
    print("-" * 80)
    print("TEST 1: Quest Spirit Setup")
    print("-" * 80)
    calc.add_quest_spirit("First Skull Quest", 30)
    calc.add_quest_spirit("Second Skull Quest", 30)
    calc.add_quest_spirit("Third Skull Quest", 40)
    print(f"Quest Spirit: {calc.get_quest_spirit()}")
    print(f"Maximum Spirit: {calc.get_maximum_spirit()}")
    print()

    # === Test 2: Add Gear Spirit ===
    print("-" * 80)
    print("TEST 2: Gear Spirit")
    print("-" * 80)
    calc.add_gear_spirit("Helmet - +30 Spirit", 30)
    calc.add_gear_spirit("Body Armour - +20 Spirit", 20)
    print(f"Gear Spirit: {calc.get_gear_spirit()}")
    print(f"Maximum Spirit: {calc.get_maximum_spirit()}")
    print()

    # === Test 3: Add Passive Spirit ===
    print("-" * 80)
    print("TEST 3: Passive Tree Spirit")
    print("-" * 80)
    calc.add_passive_spirit("Minion Master Node", 15)
    calc.add_passive_spirit("Spirit Reserve Node", 10)
    print(f"Passive Spirit: {calc.get_passive_spirit()}")
    print(f"Maximum Spirit: {calc.get_maximum_spirit()}")
    print()

    # === Test 4: Add Reservations ===
    print("-" * 80)
    print("TEST 4: Spirit Reservations")
    print("-" * 80)

    # Add Raise Zombie with support gems
    calc.add_reservation(
        "Raise Zombie",
        25,
        SpiritReservationType.PERMANENT_MINION,
        support_gems=[("Minion Damage", 1.5), ("Minion Life", 1.3)],
        priority=2  # High priority (important)
    )

    # Add Summon Skeleton with support gems
    calc.add_reservation(
        "Summon Skeleton",
        20,
        SpiritReservationType.PERMANENT_MINION,
        support_gems=[("Minion Damage", 1.5), ("Melee Splash", 1.4)],
        priority=3
    )

    # Add Purity of Fire aura (no supports)
    calc.add_reservation(
        "Purity of Fire",
        30,
        SpiritReservationType.AURA,
        priority=5
    )

    # Add Summon Golem
    calc.add_reservation(
        "Summon Golem",
        35,
        SpiritReservationType.PERMANENT_MINION,
        support_gems=[("Minion Speed", 1.3)],
        priority=7  # Lower priority
    )

    print(f"Total Reservations: {len(calc.reservations)}")
    print(f"Spirit Reserved: {calc.get_spirit_reserved()}")
    print(f"Spirit Available: {calc.get_spirit_available()}")
    print(f"Is Overflowing: {calc.is_overflowing()}")
    if calc.is_overflowing():
        print(f"Overflow Amount: {calc.get_overflow_amount()}")
    print()

    # === Test 5: Reservation Details ===
    print("-" * 80)
    print("TEST 5: Reservation Details")
    print("-" * 80)
    for detail in calc.get_reservation_details():
        print(f"\n{detail['name']}:")
        print(f"  Type: {detail['type']}")
        print(f"  Base Cost: {detail['base_cost']}")
        print(f"  Final Cost: {detail['final_cost']}")
        print(f"  Priority: {detail['priority']}")
        print(f"  Support Gems: {', '.join([sg['name'] for sg in detail['support_gems']]) or 'None'}")
        print(f"  Enabled: {detail['enabled']}")
    print()

    # === Test 6: Spirit Summary ===
    print("-" * 80)
    print("TEST 6: Spirit Summary")
    print("-" * 80)
    summary = calc.get_spirit_summary()
    import json
    print(json.dumps(summary, indent=2))
    print()

    # === Test 7: Optimization Suggestions ===
    print("-" * 80)
    print("TEST 7: Optimization Suggestions")
    print("-" * 80)
    if calc.is_overflowing():
        suggestions = calc.get_optimization_suggestions()
        print(f"Found {len(suggestions)} optimization suggestions:")
        for i, suggestion in enumerate(suggestions[:5], 1):  # Show top 5
            print(f"{i}. {suggestion.description} (saves {suggestion.spirit_saved} Spirit)")
    else:
        print("No overflow - no optimization needed!")
    print()

    # === Test 8: Validation ===
    print("-" * 80)
    print("TEST 8: Configuration Validation")
    print("-" * 80)
    is_valid, issues = calc.validate_configuration()
    print(f"Configuration Valid: {is_valid}")
    if issues:
        print("Issues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("No issues found!")
    print()

    # === Test 9: Auto-Resolve Overflow ===
    if calc.is_overflowing():
        print("-" * 80)
        print("TEST 9: Auto-Resolve Overflow")
        print("-" * 80)
        print(f"Before: Available Spirit = {calc.get_spirit_available()}")
        actions = calc.auto_resolve_overflow()
        print(f"After: Available Spirit = {calc.get_spirit_available()}")
        print("Actions taken:")
        for action in actions:
            print(f"  - {action}")
        print()

    # === Test 10: Optimal Configuration ===
    print("-" * 80)
    print("TEST 10: Optimal Configuration Suggestion")
    print("-" * 80)
    optimal = calc.suggest_optimal_configuration()
    print(json.dumps(optimal, indent=2))
    print()

    # === Test 11: Support Gem Cost Calculation ===
    print("-" * 80)
    print("TEST 11: Support Gem Cost Calculation")
    print("-" * 80)
    print(f"Base cost 20 with [1.5, 1.3]: {calculate_support_gem_cost(20, [1.5, 1.3])}")
    print(f"Base cost 25 with [1.4]: {calculate_support_gem_cost(25, [1.4])}")
    print(f"Base cost 30 with [1.5, 1.4, 1.3]: {calculate_support_gem_cost(30, [1.5, 1.4, 1.3])}")
    print()

    # === Test 12: Find Optimal Support Combinations ===
    print("-" * 80)
    print("TEST 12: Find Optimal Support Combinations")
    print("-" * 80)
    available_supports = [
        ("Minion Damage", 1.5),
        ("Minion Life", 1.3),
        ("Minion Speed", 1.3),
        ("Melee Splash", 1.4)
    ]
    combos = find_optimal_support_combinations(20, available_supports, 50)
    print(f"Valid combinations for base cost 20 with max 50 Spirit:")
    for i, (names, cost) in enumerate(combos[:5], 1):  # Show top 5
        print(f"{i}. {names if names else 'No supports'}: {cost} Spirit")
    print()

    # === Test 13: Export/Import Configuration ===
    print("-" * 80)
    print("TEST 13: Export/Import Configuration")
    print("-" * 80)
    exported = calc.export_configuration()
    print("Exported configuration successfully")

    # Create new calculator and import
    calc2 = SpiritCalculator()
    calc2.import_configuration(exported)
    print(f"Imported into new calculator:")
    print(f"  Maximum Spirit: {calc2.get_maximum_spirit()}")
    print(f"  Reserved Spirit: {calc2.get_spirit_reserved()}")
    print(f"  Available Spirit: {calc2.get_spirit_available()}")
    print()

    print("=" * 80)
    print("Test suite complete!")
    print("=" * 80)
