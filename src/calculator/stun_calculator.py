"""
Path of Exile 2 Stun Calculator Module

This module implements PoE2's redesigned stun system featuring:
- Light Stun: Chance-based interruption on hit
- Heavy Stun: Buildup-based extended stun (3 seconds)
- Primed State: 50-99% Heavy Stun meter grants Crushing Blow potential
- Damage type bonuses: Physical (+50% more), Melee (+50% more)

Author: Claude Code
Version: 1.0.0
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Tuple


# Configure module logger
logger = logging.getLogger(__name__)


class DamageType(Enum):
    """Damage type enumeration for stun bonus calculation."""
    PHYSICAL = "physical"
    FIRE = "fire"
    COLD = "cold"
    LIGHTNING = "lightning"
    CHAOS = "chaos"


class AttackType(Enum):
    """Attack type enumeration for stun bonus calculation."""
    MELEE = "melee"
    RANGED = "ranged"
    SPELL = "spell"


class StunState(Enum):
    """Current stun state of an entity."""
    NORMAL = "normal"
    PRIMED = "primed"  # 50-99% Heavy Stun meter
    HEAVY_STUNNED = "heavy_stunned"


@dataclass
class StunModifiers:
    """
    Modifiers affecting stun calculations.

    Attributes:
        increased_stun_chance: Additive increased stun chance (e.g., 50 for +50%)
        more_stun_chance: Multiplicative more stun chance (e.g., 1.5 for 50% more)
        increased_stun_threshold: Enemy stun threshold multiplier (e.g., 1.2 for 20% increased)
        reduced_stun_threshold: Enemy stun threshold reduction (e.g., 0.8 for 20% reduced)
        stun_buildup_multiplier: Multiplier for Heavy Stun buildup rate
        minimum_stun_chance: Minimum chance to stun (overrides 15% default)
        immune_to_stun: Complete immunity to stuns
    """
    increased_stun_chance: float = 0.0
    more_stun_chance: float = 1.0
    increased_stun_threshold: float = 1.0
    reduced_stun_threshold: float = 1.0
    stun_buildup_multiplier: float = 1.0
    minimum_stun_chance: Optional[float] = None
    immune_to_stun: bool = False


@dataclass
class LightStunResult:
    """
    Result of a Light Stun chance calculation.

    Attributes:
        base_chance: Base stun chance before modifiers (%)
        damage_type_bonus: Bonus from damage type (e.g., 1.5 for physical)
        attack_type_bonus: Bonus from attack type (e.g., 1.5 for melee)
        final_chance: Final chance after all modifiers (%)
        will_stun: Whether the stun will occur (after threshold check)
        damage: Damage dealt for this calculation
        target_max_life: Target's maximum life
    """
    base_chance: float
    damage_type_bonus: float
    attack_type_bonus: float
    final_chance: float
    will_stun: bool
    damage: float
    target_max_life: float

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"Light Stun: {self.final_chance:.1f}% chance "
            f"({'STUN' if self.will_stun else 'no stun'}) - "
            f"Base: {self.base_chance:.1f}% × "
            f"DmgType: {self.damage_type_bonus:.2f}× × "
            f"AtkType: {self.attack_type_bonus:.2f}×"
        )


@dataclass
class HeavyStunMeter:
    """
    Heavy Stun buildup meter tracking.

    Attributes:
        current_buildup: Current buildup amount
        max_buildup: Maximum buildup (equals target max life)
        buildup_percentage: Current buildup as percentage (0-100)
        state: Current stun state (normal, primed, heavy_stunned)
        hits_received: Number of hits contributing to buildup
        hit_history: History of hits and their buildup contributions
    """
    current_buildup: float = 0.0
    max_buildup: float = 0.0
    buildup_percentage: float = 0.0
    state: StunState = StunState.NORMAL
    hits_received: int = 0
    hit_history: List[Dict[str, float]] = field(default_factory=list)

    def update_state(self) -> None:
        """Update the stun state based on current buildup percentage."""
        if self.buildup_percentage >= 100.0:
            self.state = StunState.HEAVY_STUNNED
        elif self.buildup_percentage >= 50.0:
            self.state = StunState.PRIMED
        else:
            self.state = StunState.NORMAL

    def is_primed(self) -> bool:
        """Check if the entity is in Primed state (50-99% meter)."""
        return self.state == StunState.PRIMED

    def is_heavy_stunned(self) -> bool:
        """Check if the entity is Heavy Stunned."""
        return self.state == StunState.HEAVY_STUNNED

    def reset(self) -> None:
        """Reset the Heavy Stun meter (e.g., after stun expires)."""
        self.current_buildup = 0.0
        self.buildup_percentage = 0.0
        self.state = StunState.NORMAL
        self.hits_received = 0
        self.hit_history.clear()
        logger.debug("Heavy Stun meter reset")

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"Heavy Stun Meter: {self.buildup_percentage:.1f}% "
            f"({self.current_buildup:.0f}/{self.max_buildup:.0f}) - "
            f"State: {self.state.value.upper()}"
        )


@dataclass
class HeavyStunResult:
    """
    Result of a Heavy Stun buildup calculation.

    Attributes:
        buildup_added: Amount of buildup added by this hit
        total_buildup: Total buildup after this hit
        meter: Current Heavy Stun meter state
        triggered_heavy_stun: Whether this hit triggered Heavy Stun
        triggered_crushing_blow: Whether this hit triggered Crushing Blow (primed + would stun)
        hits_to_heavy_stun: Estimated hits needed to reach Heavy Stun with similar damage
    """
    buildup_added: float
    total_buildup: float
    meter: HeavyStunMeter
    triggered_heavy_stun: bool
    triggered_crushing_blow: bool
    hits_to_heavy_stun: float

    def __str__(self) -> str:
        """Human-readable string representation."""
        status = []
        if self.triggered_heavy_stun:
            status.append("HEAVY STUN TRIGGERED")
        if self.triggered_crushing_blow:
            status.append("CRUSHING BLOW")

        status_str = " | ".join(status) if status else "Building..."

        return (
            f"Heavy Stun: +{self.buildup_added:.0f} buildup "
            f"({self.meter.buildup_percentage:.1f}%) - {status_str} - "
            f"~{self.hits_to_heavy_stun:.1f} hits to Heavy Stun"
        )


@dataclass
class CompleteStunResult:
    """
    Complete stun calculation result including both Light and Heavy stun.

    Attributes:
        light_stun: Light Stun calculation result
        heavy_stun: Heavy Stun calculation result
        damage: Damage dealt
        target_max_life: Target's maximum life
        damage_type: Type of damage dealt
        attack_type: Type of attack used
    """
    light_stun: LightStunResult
    heavy_stun: HeavyStunResult
    damage: float
    target_max_life: float
    damage_type: DamageType
    attack_type: AttackType

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.light_stun}\n{self.heavy_stun}"


class StunCalculator:
    """
    Calculator for Path of Exile 2 stun mechanics.

    Handles both Light Stun (chance-based) and Heavy Stun (buildup-based)
    calculations with support for damage type and attack type bonuses.
    """

    # Constants
    LIGHT_STUN_MINIMUM_THRESHOLD: float = 15.0  # Minimum 15% chance required
    PHYSICAL_DAMAGE_BONUS: float = 1.5  # 50% more stun for physical damage
    MELEE_ATTACK_BONUS: float = 1.5  # 50% more stun for melee attacks
    PRIMED_STATE_THRESHOLD: float = 50.0  # Primed at 50% meter
    HEAVY_STUN_THRESHOLD: float = 100.0  # Heavy Stun at 100% meter
    HEAVY_STUN_DURATION: float = 3.0  # 3 seconds Heavy Stun duration

    def __init__(self):
        """Initialize the Stun Calculator."""
        self._entity_meters: Dict[str, HeavyStunMeter] = {}
        logger.info("StunCalculator initialized")

    def calculate_light_stun_chance(
        self,
        damage: float,
        target_max_life: float,
        damage_type: DamageType,
        attack_type: AttackType,
        modifiers: Optional[StunModifiers] = None
    ) -> LightStunResult:
        """
        Calculate Light Stun chance for a hit.

        Formula:
        - Base chance = (damage / target_max_life) × 100
        - Apply damage type bonus (×1.5 for physical)
        - Apply attack type bonus (×1.5 for melee)
        - Apply increased/more modifiers
        - Check minimum threshold (15% default)

        Args:
            damage: Damage dealt by the hit
            target_max_life: Target's maximum life
            damage_type: Type of damage dealt
            attack_type: Type of attack used
            modifiers: Optional modifiers to stun calculations

        Returns:
            LightStunResult with calculation details

        Raises:
            ValueError: If damage or target_max_life are invalid
        """
        if damage < 0:
            raise ValueError(f"Damage cannot be negative: {damage}")
        if target_max_life <= 0:
            raise ValueError(f"Target max life must be positive: {target_max_life}")

        modifiers = modifiers or StunModifiers()

        # Immunity check
        if modifiers.immune_to_stun:
            logger.debug("Target is immune to stun")
            return LightStunResult(
                base_chance=0.0,
                damage_type_bonus=1.0,
                attack_type_bonus=1.0,
                final_chance=0.0,
                will_stun=False,
                damage=damage,
                target_max_life=target_max_life
            )

        # Calculate base chance
        base_chance = (damage / target_max_life) * 100.0

        # Apply damage type bonus
        damage_type_bonus = (
            self.PHYSICAL_DAMAGE_BONUS
            if damage_type == DamageType.PHYSICAL
            else 1.0
        )

        # Apply attack type bonus
        attack_type_bonus = (
            self.MELEE_ATTACK_BONUS
            if attack_type == AttackType.MELEE
            else 1.0
        )

        # Calculate chance with bonuses
        chance = base_chance * damage_type_bonus * attack_type_bonus

        # Apply increased modifier (additive)
        if modifiers.increased_stun_chance != 0:
            chance *= (1.0 + modifiers.increased_stun_chance / 100.0)

        # Apply more modifier (multiplicative)
        chance *= modifiers.more_stun_chance

        # Apply stun threshold modifiers (affects the "effective damage")
        # Reduced threshold = easier to stun = higher effective chance
        threshold_multiplier = (
            modifiers.increased_stun_threshold *
            modifiers.reduced_stun_threshold
        )
        if threshold_multiplier != 1.0:
            # Inverse relationship: lower threshold = higher chance
            chance /= threshold_multiplier

        # Cap at 100%
        final_chance = min(chance, 100.0)

        # Check minimum threshold
        minimum_threshold = (
            modifiers.minimum_stun_chance
            if modifiers.minimum_stun_chance is not None
            else self.LIGHT_STUN_MINIMUM_THRESHOLD
        )

        will_stun = final_chance >= minimum_threshold
        if not will_stun:
            final_chance = 0.0

        result = LightStunResult(
            base_chance=base_chance,
            damage_type_bonus=damage_type_bonus,
            attack_type_bonus=attack_type_bonus,
            final_chance=final_chance,
            will_stun=will_stun,
            damage=damage,
            target_max_life=target_max_life
        )

        logger.debug(f"Light Stun calculated: {result}")
        return result

    def calculate_heavy_stun_buildup(
        self,
        damage: float,
        target_max_life: float,
        damage_type: DamageType,
        attack_type: AttackType,
        entity_id: str = "default",
        modifiers: Optional[StunModifiers] = None,
        light_stun_would_occur: bool = False
    ) -> HeavyStunResult:
        """
        Calculate Heavy Stun buildup for a hit and update the entity's meter.

        Heavy Stun buildup uses the same bonuses as Light Stun chance.
        When the meter reaches 100%, a 3-second Heavy Stun is triggered.
        Primed state (50-99%) + Light Stun = Crushing Blow.

        Args:
            damage: Damage dealt by the hit
            target_max_life: Target's maximum life (= max buildup)
            damage_type: Type of damage dealt
            attack_type: Type of attack used
            entity_id: Unique identifier for the entity (for tracking multiple entities)
            modifiers: Optional modifiers to stun calculations
            light_stun_would_occur: Whether Light Stun would occur (for Crushing Blow)

        Returns:
            HeavyStunResult with calculation details and meter state

        Raises:
            ValueError: If damage or target_max_life are invalid
        """
        if damage < 0:
            raise ValueError(f"Damage cannot be negative: {damage}")
        if target_max_life <= 0:
            raise ValueError(f"Target max life must be positive: {target_max_life}")

        modifiers = modifiers or StunModifiers()

        # Get or create meter for this entity
        if entity_id not in self._entity_meters:
            self._entity_meters[entity_id] = HeavyStunMeter(
                max_buildup=target_max_life
            )
            logger.debug(f"Created Heavy Stun meter for entity: {entity_id}")

        meter = self._entity_meters[entity_id]

        # Update max buildup if target life changed
        if meter.max_buildup != target_max_life:
            old_percentage = meter.buildup_percentage
            meter.max_buildup = target_max_life
            meter.buildup_percentage = (
                (meter.current_buildup / meter.max_buildup * 100.0)
                if meter.max_buildup > 0 else 0.0
            )
            logger.debug(
                f"Updated max buildup for {entity_id}: "
                f"{old_percentage:.1f}% -> {meter.buildup_percentage:.1f}%"
            )

        # Check if currently Heavy Stunned
        was_heavy_stunned = meter.is_heavy_stunned()

        # Immunity check
        if modifiers.immune_to_stun:
            logger.debug(f"Entity {entity_id} is immune to stun")
            return HeavyStunResult(
                buildup_added=0.0,
                total_buildup=meter.current_buildup,
                meter=meter,
                triggered_heavy_stun=False,
                triggered_crushing_blow=False,
                hits_to_heavy_stun=float('inf')
            )

        # Check Primed state before adding buildup (for Crushing Blow)
        was_primed = meter.is_primed()

        # Calculate buildup (same formula as Light Stun chance, but as raw value)
        base_buildup = damage

        # Apply damage type bonus
        damage_type_bonus = (
            self.PHYSICAL_DAMAGE_BONUS
            if damage_type == DamageType.PHYSICAL
            else 1.0
        )

        # Apply attack type bonus
        attack_type_bonus = (
            self.MELEE_ATTACK_BONUS
            if attack_type == AttackType.MELEE
            else 1.0
        )

        # Calculate buildup with bonuses
        buildup = base_buildup * damage_type_bonus * attack_type_bonus

        # Apply increased modifier (additive)
        if modifiers.increased_stun_chance != 0:
            buildup *= (1.0 + modifiers.increased_stun_chance / 100.0)

        # Apply more modifier (multiplicative)
        buildup *= modifiers.more_stun_chance

        # Apply buildup multiplier
        buildup *= modifiers.stun_buildup_multiplier

        # Apply stun threshold modifiers
        threshold_multiplier = (
            modifiers.increased_stun_threshold *
            modifiers.reduced_stun_threshold
        )
        if threshold_multiplier != 1.0:
            buildup /= threshold_multiplier

        # Add to meter
        meter.current_buildup += buildup
        meter.buildup_percentage = (
            (meter.current_buildup / meter.max_buildup * 100.0)
            if meter.max_buildup > 0 else 0.0
        )
        meter.hits_received += 1
        meter.hit_history.append({
            'damage': damage,
            'buildup': buildup,
            'total_buildup': meter.current_buildup,
            'percentage': meter.buildup_percentage
        })

        # Update state
        meter.update_state()

        # Check for Heavy Stun trigger
        triggered_heavy_stun = not was_heavy_stunned and meter.is_heavy_stunned()

        # Check for Crushing Blow (was primed, Light Stun would occur)
        triggered_crushing_blow = was_primed and light_stun_would_occur

        # Calculate hits needed to Heavy Stun
        remaining_buildup = meter.max_buildup - meter.current_buildup
        if buildup > 0 and remaining_buildup > 0:
            hits_to_heavy_stun = remaining_buildup / buildup
        elif meter.is_heavy_stunned():
            hits_to_heavy_stun = 0.0
        else:
            hits_to_heavy_stun = float('inf')

        result = HeavyStunResult(
            buildup_added=buildup,
            total_buildup=meter.current_buildup,
            meter=meter,
            triggered_heavy_stun=triggered_heavy_stun,
            triggered_crushing_blow=triggered_crushing_blow,
            hits_to_heavy_stun=hits_to_heavy_stun
        )

        if triggered_heavy_stun:
            logger.info(f"Heavy Stun triggered on entity {entity_id}!")
        if triggered_crushing_blow:
            logger.info(f"Crushing Blow triggered on entity {entity_id}!")

        logger.debug(f"Heavy Stun buildup calculated: {result}")
        return result

    def calculate_complete_stun(
        self,
        damage: float,
        target_max_life: float,
        damage_type: DamageType,
        attack_type: AttackType,
        entity_id: str = "default",
        modifiers: Optional[StunModifiers] = None
    ) -> CompleteStunResult:
        """
        Calculate both Light Stun and Heavy Stun for a single hit.

        This is the primary method for complete stun calculations,
        combining both Light and Heavy stun mechanics.

        Args:
            damage: Damage dealt by the hit
            target_max_life: Target's maximum life
            damage_type: Type of damage dealt
            attack_type: Type of attack used
            entity_id: Unique identifier for the entity
            modifiers: Optional modifiers to stun calculations

        Returns:
            CompleteStunResult with both Light and Heavy stun details
        """
        # Calculate Light Stun
        light_stun = self.calculate_light_stun_chance(
            damage=damage,
            target_max_life=target_max_life,
            damage_type=damage_type,
            attack_type=attack_type,
            modifiers=modifiers
        )

        # Calculate Heavy Stun with Light Stun result
        heavy_stun = self.calculate_heavy_stun_buildup(
            damage=damage,
            target_max_life=target_max_life,
            damage_type=damage_type,
            attack_type=attack_type,
            entity_id=entity_id,
            modifiers=modifiers,
            light_stun_would_occur=light_stun.will_stun
        )

        result = CompleteStunResult(
            light_stun=light_stun,
            heavy_stun=heavy_stun,
            damage=damage,
            target_max_life=target_max_life,
            damage_type=damage_type,
            attack_type=attack_type
        )

        logger.debug(f"Complete stun calculated for entity {entity_id}")
        return result

    def get_heavy_stun_meter(self, entity_id: str = "default") -> Optional[HeavyStunMeter]:
        """
        Get the Heavy Stun meter for an entity.

        Args:
            entity_id: Unique identifier for the entity

        Returns:
            HeavyStunMeter if it exists, None otherwise
        """
        return self._entity_meters.get(entity_id)

    def reset_heavy_stun_meter(self, entity_id: str = "default") -> None:
        """
        Reset the Heavy Stun meter for an entity.

        Useful for when a Heavy Stun expires or entity is no longer tracked.

        Args:
            entity_id: Unique identifier for the entity
        """
        if entity_id in self._entity_meters:
            self._entity_meters[entity_id].reset()
            logger.info(f"Reset Heavy Stun meter for entity: {entity_id}")
        else:
            logger.warning(f"No meter found for entity: {entity_id}")

    def remove_entity(self, entity_id: str) -> None:
        """
        Remove an entity's Heavy Stun meter from tracking.

        Args:
            entity_id: Unique identifier for the entity
        """
        if entity_id in self._entity_meters:
            del self._entity_meters[entity_id]
            logger.info(f"Removed entity from tracking: {entity_id}")
        else:
            logger.warning(f"No meter found for entity: {entity_id}")

    def get_all_tracked_entities(self) -> List[str]:
        """
        Get a list of all entities currently being tracked.

        Returns:
            List of entity IDs
        """
        return list(self._entity_meters.keys())

    def calculate_hits_to_stun(
        self,
        damage_per_hit: float,
        target_max_life: float,
        damage_type: DamageType,
        attack_type: AttackType,
        modifiers: Optional[StunModifiers] = None
    ) -> Tuple[float, float]:
        """
        Calculate theoretical hits needed for both Light and Heavy stun.

        Args:
            damage_per_hit: Damage dealt per hit
            target_max_life: Target's maximum life
            damage_type: Type of damage dealt
            attack_type: Type of attack used
            modifiers: Optional modifiers to stun calculations

        Returns:
            Tuple of (hits_for_light_stun_threshold, hits_for_heavy_stun)
        """
        modifiers = modifiers or StunModifiers()

        # Calculate Light Stun chance for one hit
        light_result = self.calculate_light_stun_chance(
            damage=damage_per_hit,
            target_max_life=target_max_life,
            damage_type=damage_type,
            attack_type=attack_type,
            modifiers=modifiers
        )

        # Calculate hits needed to reach 15% threshold
        if light_result.base_chance == 0:
            hits_for_light = float('inf')
        else:
            # We need final_chance to be >= 15%
            # final_chance = base_chance × bonuses
            # base_chance = (damage / life) × 100
            # We need: (damage × hits / life) × 100 × bonuses >= 15
            # hits = (15 / (base_per_hit × bonuses))
            chance_per_hit = (
                light_result.base_chance *
                light_result.damage_type_bonus *
                light_result.attack_type_bonus
            )
            if modifiers.increased_stun_chance != 0:
                chance_per_hit *= (1.0 + modifiers.increased_stun_chance / 100.0)
            chance_per_hit *= modifiers.more_stun_chance

            minimum_threshold = (
                modifiers.minimum_stun_chance
                if modifiers.minimum_stun_chance is not None
                else self.LIGHT_STUN_MINIMUM_THRESHOLD
            )

            if chance_per_hit >= minimum_threshold:
                hits_for_light = 1.0
            elif light_result.base_chance > 0:
                hits_for_light = minimum_threshold / chance_per_hit
            else:
                hits_for_light = float('inf')

        # Calculate Heavy Stun buildup per hit
        base_buildup = damage_per_hit
        damage_type_bonus = (
            self.PHYSICAL_DAMAGE_BONUS
            if damage_type == DamageType.PHYSICAL
            else 1.0
        )
        attack_type_bonus = (
            self.MELEE_ATTACK_BONUS
            if attack_type == AttackType.MELEE
            else 1.0
        )

        buildup_per_hit = base_buildup * damage_type_bonus * attack_type_bonus

        if modifiers.increased_stun_chance != 0:
            buildup_per_hit *= (1.0 + modifiers.increased_stun_chance / 100.0)
        buildup_per_hit *= modifiers.more_stun_chance
        buildup_per_hit *= modifiers.stun_buildup_multiplier

        threshold_multiplier = (
            modifiers.increased_stun_threshold *
            modifiers.reduced_stun_threshold
        )
        if threshold_multiplier != 1.0:
            buildup_per_hit /= threshold_multiplier

        # Calculate hits for Heavy Stun
        if buildup_per_hit > 0:
            hits_for_heavy = target_max_life / buildup_per_hit
        else:
            hits_for_heavy = float('inf')

        logger.debug(
            f"Hits to stun: Light={hits_for_light:.2f}, Heavy={hits_for_heavy:.2f}"
        )

        return (hits_for_light, hits_for_heavy)


# Convenience function for quick calculations
def quick_stun_calculation(
    damage: float,
    target_max_life: float,
    is_physical: bool = False,
    is_melee: bool = False
) -> str:
    """
    Quick stun calculation with simplified parameters.

    Args:
        damage: Damage dealt
        target_max_life: Target's maximum life
        is_physical: Whether damage is physical
        is_melee: Whether attack is melee

    Returns:
        Formatted string with stun calculation results
    """
    calculator = StunCalculator()

    damage_type = DamageType.PHYSICAL if is_physical else DamageType.FIRE
    attack_type = AttackType.MELEE if is_melee else AttackType.RANGED

    result = calculator.calculate_complete_stun(
        damage=damage,
        target_max_life=target_max_life,
        damage_type=damage_type,
        attack_type=attack_type
    )

    return str(result)


if __name__ == "__main__":
    # Configure logging for demonstration
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 80)
    print("Path of Exile 2 Stun Calculator - Demonstration")
    print("=" * 80)

    calculator = StunCalculator()

    # Example 1: Physical melee attack
    print("\n--- Example 1: Physical Melee Attack ---")
    print("Scenario: 1000 damage to enemy with 5000 life")
    result1 = calculator.calculate_complete_stun(
        damage=1000,
        target_max_life=5000,
        damage_type=DamageType.PHYSICAL,
        attack_type=AttackType.MELEE,
        entity_id="enemy1"
    )
    print(result1)

    # Example 2: Multiple hits building Heavy Stun
    print("\n--- Example 2: Multiple Hits Building Heavy Stun ---")
    print("Scenario: 5 consecutive 800 damage hits (physical melee)")
    for i in range(5):
        result = calculator.calculate_complete_stun(
            damage=800,
            target_max_life=5000,
            damage_type=DamageType.PHYSICAL,
            attack_type=AttackType.MELEE,
            entity_id="enemy2"
        )
        print(f"\nHit {i+1}:")
        print(result)

    # Example 3: Fire spell (no bonuses)
    print("\n--- Example 3: Fire Spell (No Bonuses) ---")
    print("Scenario: 1500 damage to enemy with 5000 life")
    result3 = calculator.calculate_complete_stun(
        damage=1500,
        target_max_life=5000,
        damage_type=DamageType.FIRE,
        attack_type=AttackType.SPELL,
        entity_id="enemy3"
    )
    print(result3)

    # Example 4: With modifiers
    print("\n--- Example 4: With Stun Modifiers ---")
    print("Scenario: 1000 damage with +50% increased stun chance")
    modifiers = StunModifiers(increased_stun_chance=50.0)
    result4 = calculator.calculate_complete_stun(
        damage=1000,
        target_max_life=5000,
        damage_type=DamageType.PHYSICAL,
        attack_type=AttackType.MELEE,
        entity_id="enemy4",
        modifiers=modifiers
    )
    print(result4)

    # Example 5: Hits to stun calculation
    print("\n--- Example 5: Hits Needed to Stun ---")
    print("Scenario: 500 damage per hit (physical melee)")
    hits_light, hits_heavy = calculator.calculate_hits_to_stun(
        damage_per_hit=500,
        target_max_life=5000,
        damage_type=DamageType.PHYSICAL,
        attack_type=AttackType.MELEE
    )
    print(f"Hits for Light Stun threshold: {hits_light:.2f}")
    print(f"Hits for Heavy Stun: {hits_heavy:.2f}")

    print("\n" + "=" * 80)
    print("Demonstration complete!")
    print("=" * 80)
