"""
Path of Exile 2 Spell DPS Calculator
Calculates accurate spell DPS using PoE2 damage formulas

Based on comprehensive research from:
- poewiki.net
- poe2db.tw
- maxroll.gg
- mobalytics.gg
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class SpellStats:
    """Spell base statistics"""
    name: str
    base_damage_min: float
    base_damage_max: float
    damage_effectiveness: float = 1.0  # 100% by default
    base_crit_chance: float = 0.0  # 0-100%
    base_cast_time: float = 1.0  # seconds
    damage_types: List[str] = None  # ['fire', 'cold', 'lightning', etc.]

    def __post_init__(self) -> None:
        if self.damage_types is None:
            self.damage_types = []


@dataclass
class CharacterModifiers:
    """Character damage modifiers"""
    # Increased/Decreased (additive)
    increased_spell_damage: float = 0.0  # Sum of all % increased
    increased_cast_speed: float = 0.0
    increased_crit_damage: float = 0.0

    # More/Less (multiplicative)
    more_multipliers: List[float] = None  # List of more % values (e.g., [25, 30, 20])

    # Added damage (flat)
    added_fire: float = 0.0
    added_cold: float = 0.0
    added_lightning: float = 0.0
    added_chaos: float = 0.0
    added_physical: float = 0.0

    # Critical stats
    added_crit_bonus: float = 100.0  # PoE2 base: +100%
    increased_crit_chance: float = 0.0

    # Archmage
    maximum_mana: float = 0.0
    has_archmage: bool = False

    def __post_init__(self) -> None:
        if self.more_multipliers is None:
            self.more_multipliers = []


@dataclass
class EnemyStats:
    """Enemy defensive stats"""
    fire_resistance: float = 0.0  # 0-100
    cold_resistance: float = 0.0
    lightning_resistance: float = 0.0
    chaos_resistance: float = 0.0
    physical_resistance: float = 0.0

    # Debuffs (negative resistances)
    fire_exposure: float = 0.0  # e.g., 20 for -20% res
    cold_exposure: float = 0.0
    lightning_exposure: float = 0.0

    # Penetration
    fire_penetration: float = 0.0
    cold_penetration: float = 0.0
    lightning_penetration: float = 0.0

    # Modifiers
    is_shocked: bool = False  # 20% more damage taken


class SpellDPSCalculator:
    """
    Calculates spell DPS using PoE2 formulas

    Formula:
    Final Damage = (Base + Added × Effectiveness) × (1 + ΣIncreased) × Π(1 + More) × CritMultiplier × (1 - EffectiveRes)
    """

    # Spell database (expandable)
    SPELL_DATABASE = {
        "arc": SpellStats(
            name="Arc",
            base_damage_min=10.0,
            base_damage_max=100.0,  # Placeholder - varies by gem level
            damage_effectiveness=1.0,
            base_crit_chance=5.0,
            base_cast_time=0.8,
            damage_types=["lightning"]
        ),
        "spark": SpellStats(
            name="Spark",
            base_damage_min=10.0,
            base_damage_max=100.0,
            damage_effectiveness=1.0,
            base_crit_chance=9.0,
            base_cast_time=0.7,
            damage_types=["lightning"]
        ),
        "fireball": SpellStats(
            name="Fireball",
            base_damage_min=20.0,
            base_damage_max=120.0,
            damage_effectiveness=1.0,
            base_crit_chance=6.0,
            base_cast_time=0.9,
            damage_types=["fire"]
        ),
        # Add more spells as needed
    }

    def calculate_dps(
        self,
        spell: SpellStats,
        char_mods: CharacterModifiers,
        enemy: Optional[EnemyStats] = None
    ) -> Dict[str, Any]:
        """
        Calculate complete spell DPS

        Args:
            spell: Spell base statistics
            char_mods: Character modifiers
            enemy: Enemy stats (if None, assumes no resistance)

        Returns:
            Dictionary with DPS breakdown
        """
        if enemy is None:
            enemy = EnemyStats()

        try:
            # Step 1: Calculate base damage
            base_damage = (spell.base_damage_min + spell.base_damage_max) / 2

            # Step 2: Add flat damage (with damage effectiveness)
            added_damage = self._calculate_added_damage(spell, char_mods)
            total_base_damage = base_damage + added_damage

            # Step 3: Archmage scaling (if applicable)
            if char_mods.has_archmage:
                archmage_bonus = self._calculate_archmage_bonus(
                    char_mods.maximum_mana,
                    total_base_damage
                )
                total_base_damage += archmage_bonus

            # Step 4: Apply increased/decreased (single additive sum)
            increased_multiplier = 1.0 + (char_mods.increased_spell_damage / 100.0)
            damage_after_increased = total_base_damage * increased_multiplier

            # Step 5: Apply more/less (multiplicative stack)
            more_multiplier = self._calculate_more_multiplier(char_mods.more_multipliers)
            damage_after_more = damage_after_increased * more_multiplier

            # Step 6: Calculate expected damage with crits
            crit_chance = min(spell.base_crit_chance + char_mods.increased_crit_chance, 100.0) / 100.0
            crit_multiplier = self._calculate_crit_multiplier(
                char_mods.added_crit_bonus,
                char_mods.increased_crit_damage
            )

            non_crit_damage = damage_after_more * (1.0 - crit_chance)
            crit_damage = damage_after_more * crit_multiplier * crit_chance
            expected_hit_damage = non_crit_damage + crit_damage

            # Step 7: Apply resistance/penetration
            damage_after_resistance = self._apply_resistances(
                expected_hit_damage,
                spell.damage_types,
                enemy
            )

            # Step 8: Apply Shock if applicable
            if enemy.is_shocked:
                damage_after_resistance *= 1.2  # 20% more damage

            # Step 9: Calculate DPS (damage × casts per second)
            cast_speed = self._calculate_cast_speed(
                spell.base_cast_time,
                char_mods.increased_cast_speed
            )
            dps = damage_after_resistance * cast_speed

            return {
                "total_dps": round(dps, 2),
                "average_hit": round(damage_after_resistance, 2),
                "casts_per_second": round(cast_speed, 3),
                "crit_chance": round(crit_chance * 100, 2),
                "breakdown": {
                    "base_damage": round(base_damage, 2),
                    "added_damage": round(added_damage, 2),
                    "after_increased": round(damage_after_increased, 2),
                    "after_more": round(damage_after_more, 2),
                    "expected_hit": round(expected_hit_damage, 2),
                    "after_resistance": round(damage_after_resistance, 2),
                    "multipliers": {
                        "increased": round(increased_multiplier, 3),
                        "more": round(more_multiplier, 3),
                        "crit": round(crit_multiplier, 3) if crit_chance > 0 else 1.0
                    }
                }
            }

        except Exception as e:
            logger.error(f"Error calculating DPS for {spell.name}: {e}", exc_info=True)
            return {
                "total_dps": 0,
                "average_hit": 0,
                "casts_per_second": 0,
                "error": str(e)
            }

    def _calculate_added_damage(self, spell: SpellStats, char_mods: CharacterModifiers) -> float:
        """Calculate added damage with damage effectiveness applied.

        Sums all sources of added flat damage (fire, cold, lightning, chaos, physical)
        and multiplies by the spell's damage effectiveness.

        Args:
            spell: Spell statistics including damage effectiveness
            char_mods: Character modifiers with added flat damage values

        Returns:
            Total added damage after applying damage effectiveness

        Formula:
            (Added Fire + Cold + Lightning + Chaos + Physical) × Damage Effectiveness

        Examples:
            >>> spell = SpellStats(name="Test", base_damage_min=10, base_damage_max=20, damage_effectiveness=0.8)
            >>> char_mods = CharacterModifiers(added_fire=50, added_cold=30)
            >>> calc = SpellDPSCalculator()
            >>> calc._calculate_added_damage(spell, char_mods)
            64.0
        """
        total_added = (
            char_mods.added_fire +
            char_mods.added_cold +
            char_mods.added_lightning +
            char_mods.added_chaos +
            char_mods.added_physical
        )
        return total_added * spell.damage_effectiveness

    def _calculate_archmage_bonus(self, max_mana: float, base_damage: float) -> float:
        """Calculate bonus lightning damage from Archmage support.

        Archmage adds lightning damage based on maximum mana. The bonus scales
        at 4% of base damage per 100 maximum mana.

        Args:
            max_mana: Character's maximum mana pool
            base_damage: Base spell damage before modifiers

        Returns:
            Additional lightning damage from Archmage, or 0.0 if no mana

        Formula:
            Archmage Bonus = (Max Mana / 100) × 0.04 × Base Damage

        Examples:
            >>> calc = SpellDPSCalculator()
            >>> calc._calculate_archmage_bonus(2000, 100)
            80.0
            >>> calc._calculate_archmage_bonus(0, 100)
            0.0
        """
        if max_mana <= 0:
            return 0.0

        archmage_multiplier = (max_mana / 100.0) * 0.04  # 4% per 100 mana
        return base_damage * archmage_multiplier

    def _calculate_more_multiplier(self, more_multipliers: List[float]) -> float:
        """Calculate total multiplier from all 'more' damage modifiers.

        'More' modifiers stack multiplicatively, unlike 'increased' modifiers which
        stack additively. Each modifier is applied sequentially.

        Args:
            more_multipliers: List of more damage percentages (e.g., [25, 30, 20] for +25%, +30%, +20%)

        Returns:
            Total multiplicative damage multiplier

        Formula:
            Total = (1 + More1/100) × (1 + More2/100) × (1 + More3/100) × ...

        Examples:
            >>> calc = SpellDPSCalculator()
            >>> calc._calculate_more_multiplier([25, 30])
            1.625
            >>> calc._calculate_more_multiplier([])
            1.0
        """
        total = 1.0
        for more_percent in more_multipliers:
            total *= (1.0 + more_percent / 100.0)
        return total

    def _calculate_crit_multiplier(self, added_crit_bonus: float, increased_crit: float) -> float:
        """Calculate critical strike damage multiplier using PoE2 system.

        In PoE2, critical strikes have a base +100% damage bonus (200% total).
        The base bonus can be increased through modifiers.

        Args:
            added_crit_bonus: Base crit damage bonus (default 100 for PoE2) plus any flat additions
            increased_crit: Percentage of increased critical strike damage

        Returns:
            Total critical strike damage multiplier

        Formula:
            Crit Multiplier = 1 + (Added Bonus / 100) × (1 + Increased / 100)

        Examples:
            >>> calc = SpellDPSCalculator()
            >>> calc._calculate_crit_multiplier(100, 0)
            2.0
            >>> calc._calculate_crit_multiplier(100, 50)
            2.5
        """
        # PoE2 base is +100% (200% total damage on crit)
        total_bonus = added_crit_bonus / 100.0  # Convert % to decimal
        increased_mult = 1.0 + (increased_crit / 100.0)

        return 1.0 + (total_bonus * increased_mult)

    def _apply_resistances(
        self,
        damage: float,
        damage_types: List[str],
        enemy: EnemyStats
    ) -> float:
        """Apply enemy resistances, exposure, and penetration to damage.

        Calculates effective resistance after applying exposure (which can go negative)
        and penetration (which cannot reduce resistance below 0%).

        Args:
            damage: Incoming damage before resistance mitigation
            damage_types: List of damage types (uses first element as primary type)
            enemy: Enemy defensive statistics

        Returns:
            Final damage after resistance mitigation

        Formula:
            Effective Resistance = max((Base Resistance - Exposure) - Penetration, 0)
            Final Damage = Damage × (1 - Effective Resistance / 100)

        Examples:
            >>> calc = SpellDPSCalculator()
            >>> enemy = EnemyStats(fire_resistance=75, fire_exposure=20, fire_penetration=10)
            >>> calc._apply_resistances(100, ["fire"], enemy)
            55.0
        """
        if not damage_types:
            return damage

        # Get primary damage type (first in list)
        primary_type = damage_types[0].lower()

        # Get base resistance
        resistance_map = {
            "fire": (enemy.fire_resistance, enemy.fire_exposure, enemy.fire_penetration),
            "cold": (enemy.cold_resistance, enemy.cold_exposure, enemy.cold_penetration),
            "lightning": (enemy.lightning_resistance, enemy.lightning_exposure, enemy.lightning_penetration),
            "chaos": (enemy.chaos_resistance, 0, 0),
            "physical": (enemy.physical_resistance, 0, 0)
        }

        if primary_type not in resistance_map:
            return damage

        base_res, exposure, penetration = resistance_map[primary_type]

        # Step 1: Apply exposure (can go negative)
        res_after_exposure = base_res - exposure

        # Step 2: Apply penetration (cannot go below 0%)
        effective_resistance = max(res_after_exposure - penetration, 0.0)

        # Calculate damage multiplier
        damage_multiplier = 1.0 - (effective_resistance / 100.0)

        return damage * damage_multiplier

    def _calculate_cast_speed(self, base_cast_time: float, increased_cast_speed: float) -> float:
        """Calculate casts per second from base cast time and modifiers.

        Applies increased cast speed modifiers to reduce the actual cast time,
        then converts to casts per second.

        Args:
            base_cast_time: Base time per cast in seconds (from spell gem)
            increased_cast_speed: Total percentage of increased cast speed

        Returns:
            Number of casts per second

        Formula:
            Actual Cast Time = Base Cast Time / (1 + Increased Cast Speed / 100)
            Casts Per Second = 1 / Actual Cast Time

        Examples:
            >>> calc = SpellDPSCalculator()
            >>> calc._calculate_cast_speed(0.8, 50)
            1.875
            >>> calc._calculate_cast_speed(1.0, 0)
            1.0
        """
        cast_speed_multiplier = 1.0 + (increased_cast_speed / 100.0)
        actual_cast_time = base_cast_time / cast_speed_multiplier
        return 1.0 / actual_cast_time

    def get_spell_by_name(self, spell_name: str) -> Optional[SpellStats]:
        """Retrieve spell statistics from the spell database.

        Performs case-insensitive lookup of spell data from the internal database.

        Args:
            spell_name: Name of the spell to look up (case-insensitive)

        Returns:
            SpellStats object if found, None otherwise

        Examples:
            >>> calc = SpellDPSCalculator()
            >>> arc = calc.get_spell_by_name("Arc")
            >>> arc.name
            'Arc'
            >>> calc.get_spell_by_name("NonexistentSpell") is None
            True
        """
        return self.SPELL_DATABASE.get(spell_name.lower())

    def add_spell_to_database(self, spell: SpellStats) -> None:
        """Add or update a spell in the spell database.

        Stores spell statistics in the internal database for later lookup.
        If a spell with the same name exists, it will be overwritten.

        Args:
            spell: SpellStats object to add to the database

        Examples:
            >>> calc = SpellDPSCalculator()
            >>> new_spell = SpellStats(
            ...     name="CustomSpell",
            ...     base_damage_min=50,
            ...     base_damage_max=100,
            ...     damage_effectiveness=1.2
            ... )
            >>> calc.add_spell_to_database(new_spell)
            >>> calc.get_spell_by_name("CustomSpell").name
            'CustomSpell'
        """
        self.SPELL_DATABASE[spell.name.lower()] = spell
