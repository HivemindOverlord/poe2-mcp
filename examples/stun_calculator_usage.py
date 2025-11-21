"""
Path of Exile 2 Stun Calculator - Usage Examples

This file demonstrates various use cases for the stun calculator module.

Author: Claude Code
Version: 1.0.0
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.calculator.stun_calculator import (
    StunCalculator,
    DamageType,
    AttackType,
    StunModifiers,
    StunState,
    quick_stun_calculation
)


def example_1_basic_usage():
    """Example 1: Basic usage - single hit calculation."""
    print("=" * 80)
    print("Example 1: Basic Usage - Single Hit")
    print("=" * 80)

    calculator = StunCalculator()

    # Physical melee attack dealing 1500 damage to enemy with 6000 life
    result = calculator.calculate_complete_stun(
        damage=1500,
        target_max_life=6000,
        damage_type=DamageType.PHYSICAL,
        attack_type=AttackType.MELEE,
        entity_id="boss1"
    )

    print(f"\nDamage: {result.damage}")
    print(f"Target Life: {result.target_max_life}")
    print(f"Damage Type: {result.damage_type.value}")
    print(f"Attack Type: {result.attack_type.value}")
    print(f"\nLight Stun Chance: {result.light_stun.final_chance:.1f}%")
    print(f"Will Light Stun: {'Yes' if result.light_stun.will_stun else 'No'}")
    print(f"\nHeavy Stun Buildup: {result.heavy_stun.meter.buildup_percentage:.1f}%")
    print(f"Hits to Heavy Stun: {result.heavy_stun.hits_to_heavy_stun:.2f}")
    print(f"State: {result.heavy_stun.meter.state.value}")


def example_2_combat_sequence():
    """Example 2: Simulating a combat sequence with multiple hits."""
    print("\n" + "=" * 80)
    print("Example 2: Combat Sequence - Multiple Hits on Boss")
    print("=" * 80)

    calculator = StunCalculator()
    boss_id = "titan_boss"
    boss_life = 10000

    # Simulate a player attacking a boss with varying damage
    attacks = [
        (1200, DamageType.PHYSICAL, AttackType.MELEE, "Heavy Strike"),
        (800, DamageType.PHYSICAL, AttackType.MELEE, "Follow-up Attack"),
        (1500, DamageType.PHYSICAL, AttackType.MELEE, "Critical Hit"),
        (900, DamageType.PHYSICAL, AttackType.MELEE, "Normal Attack"),
        (2000, DamageType.PHYSICAL, AttackType.MELEE, "Heavy Strike"),
    ]

    print(f"\nBoss Life: {boss_life}")
    print(f"Boss ID: {boss_id}\n")

    for i, (damage, dmg_type, atk_type, skill_name) in enumerate(attacks, 1):
        result = calculator.calculate_complete_stun(
            damage=damage,
            target_max_life=boss_life,
            damage_type=dmg_type,
            attack_type=atk_type,
            entity_id=boss_id
        )

        print(f"Attack {i}: {skill_name} ({damage} damage)")
        print(f"  Light Stun: {result.light_stun.final_chance:.1f}% chance "
              f"({'STUN!' if result.light_stun.will_stun else 'no stun'})")
        print(f"  Heavy Meter: {result.heavy_stun.meter.buildup_percentage:.1f}% "
              f"({result.heavy_stun.meter.state.value.upper()})")

        if result.heavy_stun.triggered_heavy_stun:
            print(f"  *** HEAVY STUN TRIGGERED! ***")
        if result.heavy_stun.triggered_crushing_blow:
            print(f"  *** CRUSHING BLOW! ***")

        print()


def example_3_different_damage_types():
    """Example 3: Comparing different damage types."""
    print("=" * 80)
    print("Example 3: Damage Type Comparison")
    print("=" * 80)

    calculator = StunCalculator()
    damage = 1000
    target_life = 5000

    damage_types = [
        (DamageType.PHYSICAL, "Physical"),
        (DamageType.FIRE, "Fire"),
        (DamageType.COLD, "Cold"),
        (DamageType.LIGHTNING, "Lightning"),
        (DamageType.CHAOS, "Chaos")
    ]

    print(f"\nComparing {damage} damage to target with {target_life} life")
    print("All attacks are melee\n")

    print(f"{'Damage Type':<15} {'Light Stun %':<15} {'Heavy Buildup':<15} {'Hits to Heavy'}")
    print("-" * 65)

    for dmg_type, name in damage_types:
        result = calculator.calculate_complete_stun(
            damage=damage,
            target_max_life=target_life,
            damage_type=dmg_type,
            attack_type=AttackType.MELEE,
            entity_id=f"test_{name}"
        )

        print(f"{name:<15} {result.light_stun.final_chance:<15.1f} "
              f"{result.heavy_stun.buildup_added:<15.0f} "
              f"{result.heavy_stun.hits_to_heavy_stun:.2f}")


def example_4_melee_vs_ranged():
    """Example 4: Comparing melee vs ranged attacks."""
    print("\n" + "=" * 80)
    print("Example 4: Melee vs Ranged vs Spell")
    print("=" * 80)

    calculator = StunCalculator()
    damage = 1000
    target_life = 5000

    attack_types = [
        (AttackType.MELEE, "Melee"),
        (AttackType.RANGED, "Ranged"),
        (AttackType.SPELL, "Spell")
    ]

    print(f"\nComparing {damage} physical damage to target with {target_life} life\n")

    print(f"{'Attack Type':<15} {'Light Stun %':<15} {'Heavy Buildup':<15} {'Hits to Heavy'}")
    print("-" * 65)

    for atk_type, name in attack_types:
        result = calculator.calculate_complete_stun(
            damage=damage,
            target_max_life=target_life,
            damage_type=DamageType.PHYSICAL,
            attack_type=atk_type,
            entity_id=f"test_{name}"
        )

        print(f"{name:<15} {result.light_stun.final_chance:<15.1f} "
              f"{result.heavy_stun.buildup_added:<15.0f} "
              f"{result.heavy_stun.hits_to_heavy_stun:.2f}")


def example_5_with_modifiers():
    """Example 5: Using stun modifiers from gear/passives."""
    print("\n" + "=" * 80)
    print("Example 5: Character with Stun Modifiers")
    print("=" * 80)

    calculator = StunCalculator()

    # Character with stun-focused build
    stun_modifiers = StunModifiers(
        increased_stun_chance=75.0,  # +75% increased from passive tree
        more_stun_chance=1.4,         # 40% more from support gem
        stun_buildup_multiplier=1.2,  # 20% faster buildup
        reduced_stun_threshold=0.85   # Enemies have 15% reduced stun threshold
    )

    damage = 1000
    target_life = 8000

    print("\nCharacter Modifiers:")
    print(f"  +{stun_modifiers.increased_stun_chance:.0f}% increased stun chance")
    print(f"  {(stun_modifiers.more_stun_chance - 1) * 100:.0f}% more stun chance")
    print(f"  {(stun_modifiers.stun_buildup_multiplier - 1) * 100:.0f}% increased buildup")
    print(f"  Enemies have {(1 - stun_modifiers.reduced_stun_threshold) * 100:.0f}% reduced threshold")

    print(f"\nAttack: {damage} physical melee damage vs {target_life} life boss\n")

    # Without modifiers
    result_no_mods = calculator.calculate_complete_stun(
        damage=damage,
        target_max_life=target_life,
        damage_type=DamageType.PHYSICAL,
        attack_type=AttackType.MELEE,
        entity_id="boss_no_mods"
    )

    # With modifiers
    result_with_mods = calculator.calculate_complete_stun(
        damage=damage,
        target_max_life=target_life,
        damage_type=DamageType.PHYSICAL,
        attack_type=AttackType.MELEE,
        entity_id="boss_with_mods",
        modifiers=stun_modifiers
    )

    print(f"{'Metric':<25} {'No Modifiers':<20} {'With Modifiers':<20}")
    print("-" * 70)
    print(f"{'Light Stun Chance':<25} {result_no_mods.light_stun.final_chance:<20.1f} "
          f"{result_with_mods.light_stun.final_chance:<20.1f}")
    print(f"{'Heavy Buildup':<25} {result_no_mods.heavy_stun.buildup_added:<20.0f} "
          f"{result_with_mods.heavy_stun.buildup_added:<20.0f}")
    print(f"{'Hits to Heavy Stun':<25} {result_no_mods.heavy_stun.hits_to_heavy_stun:<20.2f} "
          f"{result_with_mods.heavy_stun.hits_to_heavy_stun:<20.2f}")


def example_6_primed_state_detection():
    """Example 6: Detecting and utilizing Primed state."""
    print("\n" + "=" * 80)
    print("Example 6: Primed State and Crushing Blow")
    print("=" * 80)

    calculator = StunCalculator()
    boss_id = "primed_test_boss"
    boss_life = 5000

    print(f"\nBoss Life: {boss_life}")
    print("Strategy: Build to Primed state, then trigger Crushing Blow\n")

    # First attack: Get to 50% (Primed)
    result1 = calculator.calculate_complete_stun(
        damage=2500,
        target_max_life=boss_life,
        damage_type=DamageType.FIRE,
        attack_type=AttackType.SPELL,
        entity_id=boss_id
    )

    print(f"Attack 1: 2500 fire spell damage")
    print(f"  Heavy Meter: {result1.heavy_stun.meter.buildup_percentage:.1f}%")
    print(f"  State: {result1.heavy_stun.meter.state.value.upper()}")
    print(f"  Is Primed: {result1.heavy_stun.meter.is_primed()}")

    # Check if primed
    meter = calculator.get_heavy_stun_meter(boss_id)
    if meter.is_primed():
        print("\n  *** BOSS IS PRIMED! Next stun will trigger Crushing Blow! ***")

    # Second attack: Should trigger Crushing Blow
    result2 = calculator.calculate_complete_stun(
        damage=1000,
        target_max_life=boss_life,
        damage_type=DamageType.FIRE,
        attack_type=AttackType.SPELL,
        entity_id=boss_id
    )

    print(f"\nAttack 2: 1000 fire spell damage")
    print(f"  Light Stun: {result2.light_stun.final_chance:.1f}% "
          f"({'STUN!' if result2.light_stun.will_stun else 'no stun'})")
    print(f"  Heavy Meter: {result2.heavy_stun.meter.buildup_percentage:.1f}%")

    if result2.heavy_stun.triggered_crushing_blow:
        print("\n  *** CRUSHING BLOW TRIGGERED! ***")
        print("  (Extra damage/stun duration from Primed state)")


def example_7_planning_attacks():
    """Example 7: Planning optimal attack sequence."""
    print("\n" + "=" * 80)
    print("Example 7: Attack Planning - Hits to Stun Analysis")
    print("=" * 80)

    calculator = StunCalculator()

    # Different skill damage values
    skills = [
        (500, "Basic Attack"),
        (1000, "Power Attack"),
        (1500, "Heavy Strike"),
        (2500, "Ultimate Ability")
    ]

    boss_life = 10000

    print(f"\nBoss Life: {boss_life}")
    print("All attacks are Physical Melee\n")

    print(f"{'Skill':<20} {'Damage':<10} {'Light Stun':<15} {'Heavy Stun'}")
    print(f"{'':20} {'':10} {'(Hits Needed)':<15} {'(Hits Needed)'}")
    print("-" * 70)

    for damage, skill_name in skills:
        hits_light, hits_heavy = calculator.calculate_hits_to_stun(
            damage_per_hit=damage,
            target_max_life=boss_life,
            damage_type=DamageType.PHYSICAL,
            attack_type=AttackType.MELEE
        )

        print(f"{skill_name:<20} {damage:<10} {hits_light:<15.2f} {hits_heavy:.2f}")

    print("\nAnalysis:")
    print("  - All skills reach Light Stun threshold in 1 hit")
    print("  - Heavy Strike (1500) can Heavy Stun in ~3 hits")
    print("  - Ultimate (2500) can Heavy Stun in ~2 hits")


def example_8_quick_calculation():
    """Example 8: Using the quick calculation convenience function."""
    print("\n" + "=" * 80)
    print("Example 8: Quick Calculation (Convenience Function)")
    print("=" * 80)

    print("\nFor rapid calculations, use the quick_stun_calculation function:\n")

    # Fire spell
    result1 = quick_stun_calculation(
        damage=1200,
        target_max_life=6000,
        is_physical=False,
        is_melee=False
    )
    print("Fire Spell (1200 damage vs 6000 life):")
    print(result1)

    # Physical melee
    print("\n" + "-" * 60 + "\n")
    result2 = quick_stun_calculation(
        damage=1200,
        target_max_life=6000,
        is_physical=True,
        is_melee=True
    )
    print("Physical Melee (1200 damage vs 6000 life):")
    print(result2)


def example_9_multiple_enemies():
    """Example 9: Tracking multiple enemies simultaneously."""
    print("\n" + "=" * 80)
    print("Example 9: Multiple Enemy Tracking")
    print("=" * 80)

    calculator = StunCalculator()

    enemies = [
        ("rare_elite", 8000),
        ("magic_mob1", 3000),
        ("magic_mob2", 3000),
        ("normal_mob", 1500)
    ]

    print("\nAttacking multiple enemies with 1000 physical melee damage:\n")

    for enemy_id, enemy_life in enemies:
        result = calculator.calculate_complete_stun(
            damage=1000,
            target_max_life=enemy_life,
            damage_type=DamageType.PHYSICAL,
            attack_type=AttackType.MELEE,
            entity_id=enemy_id
        )

        print(f"{enemy_id} (Life: {enemy_life}):")
        print(f"  Light Stun: {result.light_stun.final_chance:.1f}% "
              f"({'STUN' if result.light_stun.will_stun else 'no stun'})")
        print(f"  Heavy Meter: {result.heavy_stun.meter.buildup_percentage:.1f}%")
        print()

    print(f"Currently tracking {len(calculator.get_all_tracked_entities())} enemies:")
    for entity_id in calculator.get_all_tracked_entities():
        meter = calculator.get_heavy_stun_meter(entity_id)
        print(f"  - {entity_id}: {meter.buildup_percentage:.1f}% ({meter.state.value})")


def main():
    """Run all examples."""
    print("\n")
    print("*" * 80)
    print("*" + " " * 78 + "*")
    print("*" + "  Path of Exile 2 Stun Calculator - Usage Examples".center(78) + "*")
    print("*" + " " * 78 + "*")
    print("*" * 80)
    print("\n")

    example_1_basic_usage()
    example_2_combat_sequence()
    example_3_different_damage_types()
    example_4_melee_vs_ranged()
    example_5_with_modifiers()
    example_6_primed_state_detection()
    example_7_planning_attacks()
    example_8_quick_calculation()
    example_9_multiple_enemies()

    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
