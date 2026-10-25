"""
Tests for the calculate_character_dps MCP handler (P5 / Issue #114).

Two test modes:
  - Calculator-direct tests exercise src/calculator/spell_dps_calculator.py
    through the same wiring the handler uses, but without going through MCP
    init. Cheap, fast, lock in math contracts. These run anywhere.
  - Handler tests invoke the actual MCP handler method via the canonical
    `await mcp.initialize()` fixture pattern. These verify the response
    formatting, error paths, and provenance banner. They depend on the full
    MCP module being importable.

If you only see the calculator-direct tests run (handler tests collected but
skipped), the local environment has the pre-existing mcp_server import hang
documented in PR #113's discussion. CI runs both modes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import pytest_asyncio

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Calculator-direct mode — verifies the math contract without MCP import
# ---------------------------------------------------------------------------


def test_calculator_baseline_fireball():
    """Fireball with no modifiers, target dummy. Math anchor."""
    from src.calculator.spell_dps_calculator import (
        CharacterModifiers,
        EnemyStats,
        SpellDPSCalculator,
    )

    calc = SpellDPSCalculator()
    spell = calc.SPELL_DATABASE["fireball"]
    result = calc.calculate_dps(spell, CharacterModifiers(), EnemyStats())

    # Fireball: 20-120 = 70 avg base damage, 0.9s cast = 1.111 casts/sec.
    # No mods, 0% res, base crit chance applies.
    assert result["total_dps"] > 0
    assert result["casts_per_second"] == pytest.approx(1.111, abs=0.01)
    assert result["breakdown"]["base_damage"] == 70.0


def test_calculator_more_multipliers_stack_multiplicatively():
    """Two +25% more multipliers must give ×1.5625, not ×1.5."""
    from src.calculator.spell_dps_calculator import (
        CharacterModifiers,
        EnemyStats,
        SpellDPSCalculator,
    )

    calc = SpellDPSCalculator()
    spell = calc.SPELL_DATABASE["spark"]
    mods = CharacterModifiers(more_multipliers=[25.0, 25.0])
    result = calc.calculate_dps(spell, mods, EnemyStats())
    assert result["breakdown"]["multipliers"]["more"] == pytest.approx(1.5625, abs=0.001)


def test_calculator_resistance_reduces_damage():
    """75% fire res reduces fire damage by 75%."""
    from src.calculator.spell_dps_calculator import (
        CharacterModifiers,
        EnemyStats,
        SpellDPSCalculator,
    )

    calc = SpellDPSCalculator()
    spell = calc.SPELL_DATABASE["fireball"]
    base = calc.calculate_dps(spell, CharacterModifiers(), EnemyStats())
    resisted = calc.calculate_dps(spell, CharacterModifiers(), EnemyStats(fire_resistance=75))
    # 75% res = 25% damage taken
    assert resisted["total_dps"] == pytest.approx(base["total_dps"] * 0.25, rel=0.01)


def test_calculator_penetration_overcomes_resistance():
    """25 penetration vs 75 res = effective 50% res."""
    from src.calculator.spell_dps_calculator import (
        CharacterModifiers,
        EnemyStats,
        SpellDPSCalculator,
    )

    calc = SpellDPSCalculator()
    spell = calc.SPELL_DATABASE["fireball"]
    no_pen = calc.calculate_dps(spell, CharacterModifiers(), EnemyStats(fire_resistance=75))
    with_pen = calc.calculate_dps(
        spell, CharacterModifiers(), EnemyStats(fire_resistance=75, fire_penetration=25)
    )
    # 50% res taken = 2x damage vs 25% res taken
    assert with_pen["total_dps"] == pytest.approx(no_pen["total_dps"] * 2.0, rel=0.01)


# ---------------------------------------------------------------------------
# Handler mode — methodology-rule-compliant per docs/TESTING.md
# ---------------------------------------------------------------------------

# MCP import is LAZY (inside the fixture) so that a hung mcp_server import in
# the local environment doesn't block pytest collection of the
# calculator-direct tests above. If the fixture init fails, all handler tests
# error rather than module-load.


@pytest_asyncio.fixture(scope="module")
async def mcp():
    """Canonical fixture per docs/TESTING.md — initialize before handler use.

    Import is deferred to here so pytest collection isn't blocked by a slow
    mcp_server module-level import on some platforms.
    """
    from src.mcp_server import PoE2BuildOptimizerMCP

    instance = PoE2BuildOptimizerMCP()
    await instance.initialize()
    return instance


@pytest.mark.asyncio
async def test_handler_fireball_target_dummy(mcp):
    """Baseline: handler returns a structured response with DPS > 0."""
    r = await mcp._handle_calculate_character_dps({"spell_name": "Fireball"})
    text = r[0].text
    assert "# Fireball DPS" in text
    assert "Total DPS" in text
    assert "Breakdown" in text
    assert "Source" in text
    assert "Data version" in text  # Provenance banner — Issue #116 pattern


@pytest.mark.asyncio
async def test_handler_unknown_spell_warns(mcp):
    """Unknown spell + no override returns a helpful list of available spells."""
    r = await mcp._handle_calculate_character_dps({"spell_name": "NotARealSpell"})
    text = r[0].text
    assert "not in the built-in database" in text.lower()
    assert "spell_stats" in text  # Hints at the override mechanism


@pytest.mark.asyncio
async def test_handler_custom_spell_stats_works(mcp):
    """spell_stats override allows DPS calc for spells not in SPELL_DATABASE."""
    r = await mcp._handle_calculate_character_dps(
        {
            "spell_stats": {
                "name": "Custom Spell",
                "base_damage_min": 100,
                "base_damage_max": 200,
                "base_cast_time": 1.0,
                "damage_types": ["cold"],
            },
        }
    )
    text = r[0].text
    assert "Custom Spell DPS" in text
    assert "Total DPS" in text


@pytest.mark.asyncio
async def test_handler_no_args_returns_help(mcp):
    """No spell_name and no spell_stats returns an error pointing at the right inputs."""
    r = await mcp._handle_calculate_character_dps({})
    text = r[0].text
    assert "spell_name" in text and "spell_stats" in text
