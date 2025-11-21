#!/usr/bin/env python3
"""
Test Gear Evaluator

Tests the gear upgrade value calculation system.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analyzer.gear_evaluator import (
    GearEvaluator,
    GearStats,
    UpgradeRecommendation
)


def test_gear_evaluator():
    """Test gear evaluator with realistic upgrade scenarios."""

    print("=" * 80)
    print("GEAR EVALUATOR TEST")
    print("=" * 80)
    print()

    # Scenario 1: Helmet upgrade for DoesFireWorkGoodNow
    print("SCENARIO 1: Helmet Upgrade (Resistance Fix)")
    print("-" * 80)
    print()

    # Current helmet (estimated)
    current_helmet = GearStats(
        item_name="Current Helmet",
        item_slot="helmet",
        armor=300,
        life=40,
        fire_res=20,
        cold_res=15,
        energy_shield=80
    )

    # Upgrade helmet with better resistances
    upgrade_helmet = GearStats(
        item_name="Upgraded Helmet +Fire/Cold Res",
        item_slot="helmet",
        armor=400,
        life=60,
        fire_res=45,  # +25 fire res!
        cold_res=40,  # +25 cold res!
        lightning_res=20,
        energy_shield=100
    )

    # Base character stats (without helmet)
    # Character has -2% fire, -8% cold TOTAL
    # So without helmet, it's even worse
    base_stats = {
        'level': 91,
        'life': 1373,  # 1413 - 40 (from helmet)
        'energy_shield': 4767,  # 4847 - 80 (from helmet)
        'armor': 1700,  # 2000 - 300 (from helmet)
        'evasion': 500,
        'fire_res': -22,  # -2 total - 20 from helmet
        'cold_res': -23,  # -8 total - 15 from helmet
        'lightning_res': 75,
        'chaos_res': -60,
        'block_chance': 25,
        'strength': 50,
        'dexterity': 120,
        'intelligence': 300
    }

    # Evaluate upgrade
    evaluator = GearEvaluator()
    value = evaluator.evaluate_upgrade(
        current_gear=current_helmet,
        upgrade_gear=upgrade_helmet,
        base_character_stats=base_stats,
        price_chaos=50.0
    )

    # Print formatted report
    report = evaluator.format_upgrade_value(upgrade_helmet, value)
    print(report)

    print()
    print(f"✓ Priority Score: {value.priority_score:.1f}/100")
    print(f"✓ Recommendation: {value.recommendation.value}")
    print(f"✓ Fixes negative resistances: {value.resistance_changes['fire'] > 0 and value.resistance_changes['cold'] > 0}")

    # Scenario 2: Charm upgrade
    print()
    print("=" * 80)
    print("SCENARIO 2: Charm Upgrade (Pure Resistance)")
    print("-" * 80)
    print()

    current_charm = GearStats(
        item_name="Small Charm",
        item_slot="charm",
        fire_res=10,
        cold_res=8
    )

    upgrade_charm = GearStats(
        item_name="Better Charm +Fire/Cold",
        item_slot="charm",
        fire_res=18,
        cold_res=15,
        life=20
    )

    # Evaluate charm upgrade
    value2 = evaluator.evaluate_upgrade(
        current_gear=current_charm,
        upgrade_gear=upgrade_charm,
        base_character_stats=base_stats,
        price_chaos=15.0
    )

    report2 = evaluator.format_upgrade_value(upgrade_charm, value2)
    print(report2)

    print()
    print(f"✓ Priority Score: {value2.priority_score:.1f}/100")
    print(f"✓ Recommendation: {value2.recommendation.value}")

    # Scenario 3: Compare two items
    print()
    print("=" * 80)
    print("SCENARIO 3: Item Comparison")
    print("-" * 80)
    print()

    item_a = GearStats(
        item_name="Amulet A: Pure Life/ES",
        item_slot="amulet",
        life=80,
        energy_shield=40,
        armor=100
    )

    item_b = GearStats(
        item_name="Amulet B: Resistances",
        item_slot="amulet",
        life=50,
        fire_res=30,
        cold_res=30,
        lightning_res=20
    )

    comparison = evaluator.compare_items(item_a, item_b, base_stats)

    print(f"Item A: {item_a.item_name}")
    print(f"  Score: {comparison['item_a_score']:.1f}/100")
    print()
    print(f"Item B: {item_b.item_name}")
    print(f"  Score: {comparison['item_b_score']:.1f}/100")
    print()
    print(f"Winner: {comparison['winner']} (by {comparison['score_difference']:.1f} points)")

    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

    # Verify results
    print()
    print("Verification:")
    print(f"✓ Helmet upgrade has high priority score: {value.priority_score >= 70}")
    print(f"✓ Helmet upgrade is recommended: {value.recommendation in [UpgradeRecommendation.UPGRADE, UpgradeRecommendation.STRONG_UPGRADE]}")
    print(f"✓ Resistance item (B) should win in current situation: {comparison['winner'] == item_b.item_name}")

    return True


if __name__ == "__main__":
    try:
        test_gear_evaluator()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
