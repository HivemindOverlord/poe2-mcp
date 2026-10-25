"""
Tests for the DoT calculator (issue #159).

Formula anchors come straight from the local knowledge base
(src/knowledge/poe2_mechanics.py worked examples):
  - Ignite: 20%/s of fire hit, 4s ("1500 fire hit -> 300/s")
  - Poison: 20%/s of phys+chaos, 2s, stack limit ("1500 -> 300/s/stack")
  - Bleed: 15%/s of phys, 5s; 30%/s moving ("2000 phys -> 300 / 600")
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.calculator.dot_calculator import (
    AILMENT_RULES,
    AilmentInput,
    DoTCalculator,
    SkillDoTInput,
    split_expected_hit_by_type,
)
from src.calculator.spell_dps_calculator import EnemyStats

calc = DoTCalculator()


# ---------------------------------------------------------------------------
# Knowledge-base anchor values
# ---------------------------------------------------------------------------


def test_ignite_knowledge_base_example():
    """1500 fire hit -> 300/s ignite (20%), 4s duration."""
    r = calc.calculate_ailment_dot(
        AilmentInput(ailment="ignite"),
        hit_damage_by_type={"fire": 1500.0},
        hits_per_second=1.0,
    )
    assert r["dps_per_stack"] == 300.0
    assert r["duration_seconds"] == 4.0
    # 1 hit/s x 4s duration >> stack limit 1 -> full uptime
    assert r["expected_active_stacks"] == 1.0
    assert r["sustained_dps"] == 300.0


def test_poison_knowledge_base_example():
    """1000 phys + 500 chaos hit -> 300/s poison (20% of 1500), 2s."""
    r = calc.calculate_ailment_dot(
        AilmentInput(ailment="poison"),
        hit_damage_by_type={"physical": 1000.0, "chaos": 500.0},
        hits_per_second=1.0,
    )
    assert r["basis_damage"] == 1500.0
    assert r["dps_per_stack"] == 300.0
    assert r["duration_seconds"] == 2.0
    assert r["sustained_dps"] == 300.0  # stack limit 1


def test_poison_stack_limit_scales_dps():
    """Escalating-Poison-style stack limit 2 doubles sustained DPS when
    application rate saturates both stacks."""
    r = calc.calculate_ailment_dot(
        AilmentInput(ailment="poison", stack_limit=2),
        hit_damage_by_type={"physical": 1000.0, "chaos": 500.0},
        hits_per_second=2.0,  # 2 apps/s x 2s = 4 concurrent >> limit 2
    )
    assert r["expected_active_stacks"] == 2.0
    assert r["sustained_dps"] == 600.0


def test_bleed_knowledge_base_example_stationary_and_moving():
    """2000 phys hit -> 300/s stationary, 600/s moving."""
    stationary = calc.calculate_ailment_dot(
        AilmentInput(ailment="bleed"),
        hit_damage_by_type={"physical": 2000.0},
        hits_per_second=1.0,
    )
    moving = calc.calculate_ailment_dot(
        AilmentInput(ailment="bleed", enemy_moving=True),
        hit_damage_by_type={"physical": 2000.0},
        hits_per_second=1.0,
    )
    assert stationary["sustained_dps"] == 300.0
    assert moving["sustained_dps"] == 600.0


def test_bleed_aggravated_counts_as_moving():
    r = calc.calculate_ailment_dot(
        AilmentInput(ailment="bleed", aggravated=True),
        hit_damage_by_type={"physical": 2000.0},
        hits_per_second=1.0,
    )
    assert r["sustained_dps"] == 600.0


# ---------------------------------------------------------------------------
# Modifier and mitigation layers
# ---------------------------------------------------------------------------


def test_increased_and_more_stack_correctly():
    """+50% increased and [20, 25] more: 300 x 1.5 x 1.2 x 1.25 = 675."""
    r = calc.calculate_ailment_dot(
        AilmentInput(
            ailment="ignite",
            increased_magnitude=50,
            more_multipliers=[20, 25],
        ),
        hit_damage_by_type={"fire": 1500.0},
        hits_per_second=1.0,
    )
    assert r["dps_per_stack"] == 675.0


def test_ignite_respects_fire_resistance_exposure_penetration():
    """75 res - 20 exposure - 10 pen = 45% effective -> 300 x 0.55 = 165."""
    r = calc.calculate_ailment_dot(
        AilmentInput(ailment="ignite"),
        hit_damage_by_type={"fire": 1500.0},
        hits_per_second=1.0,
        enemy=EnemyStats(fire_resistance=75, fire_exposure=20, fire_penetration=10),
    )
    assert r["dps_per_stack"] == 165.0


def test_poison_respects_chaos_resistance():
    r = calc.calculate_ailment_dot(
        AilmentInput(ailment="poison"),
        hit_damage_by_type={"physical": 1500.0},
        hits_per_second=1.0,
        enemy=EnemyStats(chaos_resistance=50),
    )
    assert r["dps_per_stack"] == 150.0


def test_bleed_is_unmitigated():
    """Bleed bypasses armor/ES — physical_resistance must not reduce it."""
    r = calc.calculate_ailment_dot(
        AilmentInput(ailment="bleed"),
        hit_damage_by_type={"physical": 2000.0},
        hits_per_second=1.0,
        enemy=EnemyStats(physical_resistance=50),
    )
    assert r["dps_per_stack"] == 300.0


def test_shock_applies_to_dot():
    r = calc.calculate_ailment_dot(
        AilmentInput(ailment="ignite"),
        hit_damage_by_type={"fire": 1500.0},
        hits_per_second=1.0,
        enemy=EnemyStats(is_shocked=True),
    )
    assert r["dps_per_stack"] == 360.0  # 300 x 1.2


def test_duration_modifier_extends_uptime_window():
    """Low application rate: 0.2 apps/s x 4s = 0.8 stacks; +50% duration
    -> 0.2 x 6s = 1.2, capped at stack limit 1."""
    short = calc.calculate_ailment_dot(
        AilmentInput(ailment="ignite", chance_pct=20),
        hit_damage_by_type={"fire": 1500.0},
        hits_per_second=1.0,
    )
    extended = calc.calculate_ailment_dot(
        AilmentInput(ailment="ignite", chance_pct=20, increased_duration=50),
        hit_damage_by_type={"fire": 1500.0},
        hits_per_second=1.0,
    )
    assert short["expected_active_stacks"] == 0.8
    assert short["sustained_dps"] == 240.0  # 300 x 0.8
    assert extended["expected_active_stacks"] == 1.0  # capped
    assert extended["sustained_dps"] == 300.0


def test_chance_below_100_scales_applications():
    r = calc.calculate_ailment_dot(
        AilmentInput(ailment="poison", chance_pct=25),
        hit_damage_by_type={"physical": 1500.0},
        hits_per_second=1.0,
    )
    assert r["applications_per_second"] == 0.25
    # 0.25 apps/s x 2s = 0.5 expected stacks
    assert r["expected_active_stacks"] == 0.5
    assert r["sustained_dps"] == 150.0


def test_irrelevant_damage_types_dont_feed_ailment():
    """Cold/lightning hit damage never feeds an ignite."""
    r = calc.calculate_ailment_dot(
        AilmentInput(ailment="ignite"),
        hit_damage_by_type={"cold": 1000.0, "lightning": 1000.0},
        hits_per_second=1.0,
    )
    assert r["basis_damage"] == 0.0
    assert r["sustained_dps"] == 0.0


def test_unknown_ailment_returns_error():
    r = calc.calculate_ailment_dot(
        AilmentInput(ailment="frostburn"),
        hit_damage_by_type={"fire": 100.0},
        hits_per_second=1.0,
    )
    assert "error" in r
    assert "frostburn" in r["error"]


# ---------------------------------------------------------------------------
# Skill DoT (Essence Drain style)
# ---------------------------------------------------------------------------


def test_skill_dot_basic():
    r = calc.calculate_skill_dot(SkillDoTInput(base_dps=500.0))
    assert r["sustained_dps"] == 500.0
    assert r["damage_type"] == "chaos"


def test_skill_dot_modifiers_and_resistance():
    """500 base x 1.8 increased x 1.3 more x 0.7 chaos res = 819."""
    r = calc.calculate_skill_dot(
        SkillDoTInput(
            base_dps=500.0,
            increased=80,
            more_multipliers=[30],
        ),
        enemy=EnemyStats(chaos_resistance=30),
    )
    assert r["dps_at_full_uptime"] == 819.0


def test_skill_dot_uptime_scales_sustained():
    r = calc.calculate_skill_dot(SkillDoTInput(base_dps=500.0, uptime=0.6))
    assert r["dps_at_full_uptime"] == 500.0
    assert r["sustained_dps"] == 300.0


def test_skill_dot_fire_uses_fire_resistance():
    r = calc.calculate_skill_dot(
        SkillDoTInput(base_dps=1000.0, damage_type="fire"),
        enemy=EnemyStats(fire_resistance=75, fire_penetration=25),
    )
    assert r["dps_at_full_uptime"] == 500.0  # 50% effective res


# ---------------------------------------------------------------------------
# Combination
# ---------------------------------------------------------------------------


def test_combine_totals():
    ailments = [
        calc.calculate_ailment_dot(
            AilmentInput(ailment="ignite"),
            hit_damage_by_type={"fire": 1500.0},
            hits_per_second=1.0,
        ),
        {"error": "Unknown ailment 'x'"},  # errors must not contribute
    ]
    skill_dot = calc.calculate_skill_dot(SkillDoTInput(base_dps=500.0))
    totals = calc.combine(1000.0, ailments, skill_dot)
    assert totals["hit_dps"] == 1000.0
    assert totals["ailment_dps"] == 300.0
    assert totals["skill_dot_dps"] == 500.0
    assert totals["dot_dps"] == 800.0
    assert totals["total_sustained_dps"] == 1800.0


def test_combine_without_skill_dot():
    totals = calc.combine(1000.0, [], None)
    assert totals["total_sustained_dps"] == 1000.0


# ---------------------------------------------------------------------------
# Hit-by-type attribution helper
# ---------------------------------------------------------------------------


def test_split_attributes_base_to_primary_and_added_to_own_types():
    """Base 100 fire + added 50 chaos (eff 1.0), expected hit 300 ->
    fire 200, chaos 100 (2x scale)."""
    split = split_expected_hit_by_type(
        expected_hit=300.0,
        base_damage=100.0,
        primary_type="fire",
        added_by_type={"chaos": 50.0},
        damage_effectiveness=1.0,
    )
    assert split["fire"] == 200.0
    assert split["chaos"] == 100.0


def test_split_applies_damage_effectiveness_to_added():
    split = split_expected_hit_by_type(
        expected_hit=150.0,
        base_damage=100.0,
        primary_type="fire",
        added_by_type={"chaos": 100.0},
        damage_effectiveness=0.5,
    )
    # composition: fire 100, chaos 50 -> scale 1.0
    assert split["fire"] == 100.0
    assert split["chaos"] == 50.0


def test_split_empty_when_nothing_to_attribute():
    assert split_expected_hit_by_type(0.0, 0.0, None, {}) == {}


# ---------------------------------------------------------------------------
# Rules sanity — lock the PoE2 constants against accidental edits
# ---------------------------------------------------------------------------


def test_ailment_rule_constants_match_knowledge_base():
    assert AILMENT_RULES["ignite"].hit_fraction == 0.20
    assert AILMENT_RULES["ignite"].base_duration == 4.0
    assert AILMENT_RULES["poison"].hit_fraction == 0.20
    assert AILMENT_RULES["poison"].base_duration == 2.0
    assert AILMENT_RULES["poison"].basis_types == ("physical", "chaos")
    assert AILMENT_RULES["bleed"].hit_fraction == 0.15
    assert AILMENT_RULES["bleed"].base_duration == 5.0
    assert AILMENT_RULES["bleed"].moving_multiplier == 2.0


# ---------------------------------------------------------------------------
# Handler integration — the `dot` block on calculate_character_dps
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handler_dot_block_end_to_end():
    """calculate_character_dps with a dot block renders the DoT section
    and the combined sustained total."""
    from src.mcp_server import PoE2BuildOptimizerMCP

    server = PoE2BuildOptimizerMCP()
    result = await server._handle_calculate_character_dps(
        {
            "spell_stats": {
                "name": "DoT Test Spell",
                "base_damage_min": 100,
                "base_damage_max": 200,
                "base_cast_time": 1.0,
                "damage_types": ["fire"],
            },
            "dot": {
                "ailments": [{"type": "ignite", "chance": 100}],
                "skill_dot": {"base_dps": 250, "damage_type": "chaos"},
            },
        }
    )
    text = result[0].text
    assert "Damage over Time" in text
    assert "Ignite" in text
    assert "Skill DoT" in text
    assert "total sustained DPS" in text


@pytest.mark.asyncio
async def test_handler_without_dot_block_unchanged():
    """No dot block -> no DoT section; existing output intact."""
    from src.mcp_server import PoE2BuildOptimizerMCP

    server = PoE2BuildOptimizerMCP()
    result = await server._handle_calculate_character_dps(
        {
            "spell_stats": {
                "name": "Plain Spell",
                "base_damage_min": 100,
                "base_damage_max": 200,
                "base_cast_time": 1.0,
                "damage_types": ["fire"],
            },
        }
    )
    text = result[0].text
    assert "Damage over Time" not in text
    assert "Total DPS" in text
