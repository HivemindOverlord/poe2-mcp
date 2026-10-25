"""
Path of Exile 2 Damage-over-Time Calculator (issue #159)

Models the DoT layer that hit-DPS math cannot see:
  - Ailment DoT derived from hit damage: ignite, poison, bleed
  - Skill DoT with a caller-supplied base (e.g. Essence Drain)
  - Combined sustained DPS (hit + ailments + skill DoT)

Ailment constants come from the local knowledge base
(src/knowledge/poe2_mechanics.py — PoE2 values, NOT PoE1):
  - Ignite: 20% of the hit's FIRE damage per second for 4s. No stacking.
  - Poison: 20% of the hit's PHYSICAL+CHAOS damage per second for 2s.
    Default stack limit 1 (Escalating Poison etc. raise it).
  - Bleed: 15% of the hit's PHYSICAL damage per second for 5s; 100% more
    (30%/s) while the target moves or when aggravated. No stacking.

Mitigation model:
  - Ignite is fire damage -> enemy fire resistance (with exposure/pen).
  - Poison is chaos damage -> enemy chaos resistance.
  - Bleed bypasses both armor and ES -> unmitigated.
  - Shock ("20% more damage taken") applies to DoT as well as hits.
  - DoTs cannot crit; magnitude is based on the damage of the applying
    hit, so the crit-weighted expected hit is the right basis for
    expected-value DPS.

Known data gap (documented in #159): the canonical 0.5 extraction carries
DoT stat-set effectiveness scalars but not absolute base DoT values
(e.g. Essence Drain's chaos damage per second), so skill DoT takes the
base DPS from the caller and the server does the modifier math.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from .spell_dps_calculator import EnemyStats
except ImportError:
    from src.calculator.spell_dps_calculator import EnemyStats

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AilmentRule:
    """Game constants for one ailment type."""

    name: str
    hit_fraction: float  # portion of basis damage dealt per second
    base_duration: float  # seconds
    basis_types: tuple  # which hit damage types feed the ailment
    damage_type: str  # damage type the DoT itself deals
    moving_multiplier: float = 1.0  # bleed: 2.0 while target moves


AILMENT_RULES: Dict[str, AilmentRule] = {
    "ignite": AilmentRule(
        name="Ignite",
        hit_fraction=0.20,
        base_duration=4.0,
        basis_types=("fire",),
        damage_type="fire",
    ),
    "poison": AilmentRule(
        name="Poison",
        hit_fraction=0.20,
        base_duration=2.0,
        basis_types=("physical", "chaos"),
        damage_type="chaos",
    ),
    "bleed": AilmentRule(
        name="Bleed",
        hit_fraction=0.15,
        base_duration=5.0,
        basis_types=("physical",),
        damage_type="physical",
        moving_multiplier=2.0,
    ),
}


@dataclass
class AilmentInput:
    """Caller-aggregated modifiers for one ailment calculation."""

    ailment: str  # "ignite" | "poison" | "bleed"
    chance_pct: float = 100.0  # chance to apply on hit (0-100)
    increased_magnitude: float = 0.0  # sum of %increased DoT/ailment magnitude
    more_multipliers: List[float] = field(default_factory=list)
    increased_duration: float = 0.0  # sum of %increased ailment duration
    stack_limit: int = 1  # poison: raised by Escalating Poison etc.
    enemy_moving: bool = False  # bleed: 100% more while moving
    aggravated: bool = False  # bleed: always counts as moving


@dataclass
class SkillDoTInput:
    """Caller-supplied skill DoT (e.g. Essence Drain) — see module docstring
    for why base DPS comes from the caller."""

    base_dps: float  # base DoT damage per second at gem level
    damage_type: str = "chaos"
    increased: float = 0.0  # sum of %increased applicable to the DoT
    more_multipliers: List[float] = field(default_factory=list)
    uptime: float = 1.0  # 0..1 — fraction of fight the DoT is ticking


class DoTCalculator:
    """
    DoT math engine. Pure functions over caller-aggregated modifiers —
    same MCP-as-math-engine philosophy as SpellDPSCalculator.
    """

    def calculate_ailment_dot(
        self,
        ailment_input: AilmentInput,
        hit_damage_by_type: Dict[str, float],
        hits_per_second: float,
        enemy: Optional[EnemyStats] = None,
    ) -> Dict[str, Any]:
        """
        Expected sustained DPS from one ailment.

        Args:
            ailment_input: Aggregated ailment modifiers.
            hit_damage_by_type: The applying hit's damage split by type
                (crit-weighted expected hit, PRE-resistance — ailment
                magnitude is based on damage dealt before mitigation).
            hits_per_second: Application attempts per second (casts/sec
                for spells, attacks/sec for attacks).
            enemy: Enemy stats for resistance/shock; None = no mitigation.

        Returns:
            Breakdown dict; {"error": ...} for an unknown ailment.
        """
        rule = AILMENT_RULES.get(ailment_input.ailment.lower().strip())
        if rule is None:
            return {
                "error": (
                    f"Unknown ailment '{ailment_input.ailment}'. "
                    f"Supported: {', '.join(sorted(AILMENT_RULES))}"
                )
            }
        enemy = enemy or EnemyStats()

        # Base: fraction of the relevant hit damage per second
        basis_damage = sum(hit_damage_by_type.get(t, 0.0) for t in rule.basis_types)
        dps_per_stack = basis_damage * rule.hit_fraction

        # Bleed's moving/aggravated state is 100% MORE
        moving = ailment_input.enemy_moving or ailment_input.aggravated
        if moving and rule.moving_multiplier != 1.0:
            dps_per_stack *= rule.moving_multiplier

        # Increased (additive sum) then more (multiplicative)
        increased_mult = 1.0 + ailment_input.increased_magnitude / 100.0
        more_mult = 1.0
        for more in ailment_input.more_multipliers:
            more_mult *= 1.0 + more / 100.0
        dps_per_stack *= increased_mult * more_mult

        # Mitigation: the DoT's own damage type vs enemy. Bleed bypasses
        # armor/ES; physical_resistance is generic phys reduction which
        # does not apply to bleed per the PoE2 knowledge base.
        resistance_mult = 1.0
        if rule.damage_type == "fire":
            effective_res = max(
                (enemy.fire_resistance - enemy.fire_exposure) - enemy.fire_penetration,
                0.0,
            )
            resistance_mult = 1.0 - effective_res / 100.0
        elif rule.damage_type == "chaos":
            resistance_mult = 1.0 - enemy.chaos_resistance / 100.0
        dps_per_stack_final = dps_per_stack * resistance_mult

        if enemy.is_shocked:
            dps_per_stack_final *= 1.2

        # Duration and expected active stacks. Non-stacking ailments
        # (limit 1) cap at full uptime once applications x duration >= 1.
        duration = rule.base_duration * (1.0 + ailment_input.increased_duration / 100.0)
        applications_per_second = (
            hits_per_second * max(min(ailment_input.chance_pct, 100.0), 0.0) / 100.0
        )
        expected_active_stacks = min(
            applications_per_second * duration,
            float(max(ailment_input.stack_limit, 0)),
        )
        sustained_dps = dps_per_stack_final * expected_active_stacks

        return {
            "ailment": rule.name,
            "damage_type": rule.damage_type,
            "basis_damage": round(basis_damage, 2),
            "hit_fraction": rule.hit_fraction,
            "dps_per_stack": round(dps_per_stack_final, 2),
            "duration_seconds": round(duration, 2),
            "applications_per_second": round(applications_per_second, 3),
            "expected_active_stacks": round(expected_active_stacks, 3),
            "stack_limit": ailment_input.stack_limit,
            "sustained_dps": round(sustained_dps, 2),
            "multipliers": {
                "increased": round(increased_mult, 3),
                "more": round(more_mult, 3),
                "moving": rule.moving_multiplier if moving else 1.0,
                "resistance": round(resistance_mult, 3),
                "shock": 1.2 if enemy.is_shocked else 1.0,
            },
        }

    def calculate_skill_dot(
        self,
        skill_dot: SkillDoTInput,
        enemy: Optional[EnemyStats] = None,
    ) -> Dict[str, Any]:
        """
        Sustained DPS from an inherent skill DoT (Essence Drain etc.).
        Base DPS is caller-supplied — see the module docstring for the
        extraction gap; the server does the modifier/mitigation math.
        """
        enemy = enemy or EnemyStats()

        increased_mult = 1.0 + skill_dot.increased / 100.0
        more_mult = 1.0
        for more in skill_dot.more_multipliers:
            more_mult *= 1.0 + more / 100.0
        dps = skill_dot.base_dps * increased_mult * more_mult

        damage_type = skill_dot.damage_type.lower().strip()
        resistance_mult = 1.0
        if damage_type == "fire":
            effective_res = max(
                (enemy.fire_resistance - enemy.fire_exposure) - enemy.fire_penetration,
                0.0,
            )
            resistance_mult = 1.0 - effective_res / 100.0
        elif damage_type == "cold":
            effective_res = max(
                (enemy.cold_resistance - enemy.cold_exposure) - enemy.cold_penetration,
                0.0,
            )
            resistance_mult = 1.0 - effective_res / 100.0
        elif damage_type == "lightning":
            effective_res = max(
                (enemy.lightning_resistance - enemy.lightning_exposure)
                - enemy.lightning_penetration,
                0.0,
            )
            resistance_mult = 1.0 - effective_res / 100.0
        elif damage_type == "chaos":
            resistance_mult = 1.0 - enemy.chaos_resistance / 100.0
        dps *= resistance_mult

        if enemy.is_shocked:
            dps *= 1.2

        uptime = max(min(skill_dot.uptime, 1.0), 0.0)
        sustained_dps = dps * uptime

        return {
            "source": "skill_dot",
            "damage_type": damage_type,
            "base_dps": round(skill_dot.base_dps, 2),
            "dps_at_full_uptime": round(dps, 2),
            "uptime": uptime,
            "sustained_dps": round(sustained_dps, 2),
            "multipliers": {
                "increased": round(increased_mult, 3),
                "more": round(more_mult, 3),
                "resistance": round(resistance_mult, 3),
                "shock": 1.2 if enemy.is_shocked else 1.0,
            },
        }

    def combine(
        self,
        hit_dps: float,
        ailment_results: List[Dict[str, Any]],
        skill_dot_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Combine hit DPS with all DoT layers into sustained totals."""
        ailment_dps = sum(r.get("sustained_dps", 0.0) for r in ailment_results if "error" not in r)
        skill_dot_dps = (
            skill_dot_result.get("sustained_dps", 0.0)
            if skill_dot_result and "error" not in skill_dot_result
            else 0.0
        )
        dot_dps = ailment_dps + skill_dot_dps
        return {
            "hit_dps": round(hit_dps, 2),
            "ailment_dps": round(ailment_dps, 2),
            "skill_dot_dps": round(skill_dot_dps, 2),
            "dot_dps": round(dot_dps, 2),
            "total_sustained_dps": round(hit_dps + dot_dps, 2),
        }


def split_expected_hit_by_type(
    expected_hit: float,
    base_damage: float,
    primary_type: Optional[str],
    added_by_type: Dict[str, float],
    damage_effectiveness: float = 1.0,
) -> Dict[str, float]:
    """
    Attribute a crit-weighted expected hit across damage types.

    The hit pipeline applies the same increased/more/crit multipliers to
    all damage, so the type split is proportional to the pre-multiplier
    composition: spell base damage belongs to the spell's primary type;
    added flat damage belongs to its own type (scaled by effectiveness).

    Returns {} when there is nothing to attribute.
    """
    composition: Dict[str, float] = {}
    if base_damage > 0 and primary_type:
        composition[primary_type.lower()] = base_damage
    for dmg_type, amount in added_by_type.items():
        if amount > 0:
            key = dmg_type.lower()
            composition[key] = composition.get(key, 0.0) + amount * damage_effectiveness

    total = sum(composition.values())
    if total <= 0 or expected_hit <= 0:
        return {}
    scale = expected_hit / total
    return {t: v * scale for t, v in composition.items()}
