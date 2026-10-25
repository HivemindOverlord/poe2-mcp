"""
Unit tests for Path of Exile 2 Damage Calculator

Tests comprehensive damage calculation functionality including:
- Base damage calculation (weapon and spell)
- Damage modifier stacking (increased/more)
- Critical strike mechanics
- Elemental conversion
- DPS calculations
- Attack/cast speed
"""

import os
import sys
import unittest

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from calculator.damage_calculator import (
    CriticalStrikeConfig,
    DamageCalculator,
    DamageComponents,
    DamageRange,
    DamageType,
    Modifier,
    ModifierType,
)


class TestDamageRange(unittest.TestCase):
    """Test DamageRange dataclass."""

    def test_valid_damage_range(self):
        """Test creating a valid damage range."""
        damage = DamageRange(10, 20)
        self.assertEqual(damage.min_damage, 10)
        self.assertEqual(damage.max_damage, 20)
        self.assertTrue(damage.is_valid())

    def test_average_calculation(self):
        """Test average damage calculation."""
        damage = DamageRange(100, 200)
        self.assertEqual(damage.average(), 150.0)

    def test_equal_min_max(self):
        """Test damage range with equal min and max."""
        damage = DamageRange(50, 50)
        self.assertEqual(damage.average(), 50.0)
        self.assertTrue(damage.is_valid())

    def test_negative_min_raises_error(self):
        """Test that negative minimum damage raises ValueError."""
        with self.assertRaises(ValueError) as context:
            DamageRange(-10, 20)
        self.assertIn("negative", str(context.exception).lower())

    def test_negative_max_raises_error(self):
        """Test that negative maximum damage raises ValueError."""
        with self.assertRaises(ValueError) as context:
            DamageRange(10, -20)
        self.assertIn("negative", str(context.exception).lower())

    def test_min_greater_than_max_raises_error(self):
        """Test that min > max raises ValueError."""
        with self.assertRaises(ValueError) as context:
            DamageRange(100, 50)
        self.assertIn("cannot exceed", str(context.exception).lower())

    def test_scale_multiplier(self):
        """Test scaling damage by a multiplier."""
        damage = DamageRange(10, 20)
        scaled = damage.scale(2.0)
        self.assertEqual(scaled.min_damage, 20)
        self.assertEqual(scaled.max_damage, 40)

    def test_scale_fractional_multiplier(self):
        """Test scaling with fractional multiplier."""
        damage = DamageRange(100, 200)
        scaled = damage.scale(0.5)
        self.assertEqual(scaled.min_damage, 50)
        self.assertEqual(scaled.max_damage, 100)


class TestModifier(unittest.TestCase):
    """Test Modifier dataclass."""

    def test_increased_modifier(self):
        """Test increased modifier multiplier calculation."""
        mod = Modifier(value=50, modifier_type=ModifierType.INCREASED)
        # get_multiplier returns decimal (0.5 for 50%), not the multiplied value (1.5)
        self.assertEqual(mod.get_multiplier(), 0.5)

    def test_more_modifier(self):
        """Test more modifier multiplier calculation."""
        mod = Modifier(value=30, modifier_type=ModifierType.MORE)
        # get_multiplier returns decimal (0.3 for 30%), not the multiplied value (1.3)
        self.assertEqual(mod.get_multiplier(), 0.3)

    def test_reduced_modifier(self):
        """Test reduced modifier (negative increased)."""
        mod = Modifier(value=25, modifier_type=ModifierType.REDUCED)
        # Reduced returns negative decimal (-0.25 for 25% reduced)
        self.assertEqual(mod.get_multiplier(), -0.25)

    def test_less_modifier(self):
        """Test less modifier (negative more)."""
        mod = Modifier(value=20, modifier_type=ModifierType.LESS)
        # Less returns negative decimal (-0.2 for 20% less)
        self.assertEqual(mod.get_multiplier(), -0.2)


class TestDamageComponents(unittest.TestCase):
    """Test DamageComponents container."""

    def test_empty_components(self):
        """Test empty damage components."""
        comp = DamageComponents()
        self.assertEqual(comp.total_average_damage(), 0.0)

    def test_single_damage_type(self):
        """Test components with single damage type."""
        comp = DamageComponents()
        comp.add_damage(DamageType.PHYSICAL, DamageRange(50, 100))
        self.assertEqual(comp.total_average_damage(), 75.0)

    def test_multiple_damage_types(self):
        """Test components with multiple damage types."""
        comp = DamageComponents()
        comp.add_damage(DamageType.PHYSICAL, DamageRange(50, 100))  # avg: 75
        comp.add_damage(DamageType.FIRE, DamageRange(20, 40))  # avg: 30
        comp.add_damage(DamageType.COLD, DamageRange(10, 20))  # avg: 15
        self.assertEqual(comp.total_average_damage(), 120.0)

    def test_get_damage_by_type(self):
        """Test retrieving specific damage type."""
        comp = DamageComponents()
        fire_damage = DamageRange(25, 50)
        comp.add_damage(DamageType.FIRE, fire_damage)

        result = comp.get_damage_by_type(DamageType.FIRE)
        self.assertIsNotNone(result)
        self.assertEqual(result.min_damage, 25)
        self.assertEqual(result.max_damage, 50)

    def test_get_nonexistent_damage_type(self):
        """Test getting damage type that doesn't exist."""
        comp = DamageComponents()
        result = comp.get_damage_by_type(DamageType.CHAOS)
        self.assertIsNone(result)


class TestBaseDamageCalculation(unittest.TestCase):
    """Test base damage calculation."""

    def setUp(self):
        """Set up test calculator."""
        self.calc = DamageCalculator()

    def test_weapon_damage_only(self):
        """Test base damage with weapon only."""
        weapon = DamageRange(50, 100)
        result = self.calc.calculate_base_damage(weapon_damage=weapon)

        # Weapon damage is physical
        phys_damage = result.get_damage_by_type(DamageType.PHYSICAL)
        self.assertIsNotNone(phys_damage)
        self.assertEqual(phys_damage.average(), 75.0)

    def test_spell_damage_only(self):
        """Test base damage with spell only."""
        spell = DamageRange(80, 120)
        result = self.calc.calculate_base_damage(spell_base_damage=spell)

        # Spell damage defaults to physical
        phys_damage = result.get_damage_by_type(DamageType.PHYSICAL)
        self.assertIsNotNone(phys_damage)
        self.assertEqual(phys_damage.average(), 100.0)

    def test_weapon_with_added_flat_damage(self):
        """Test weapon with added flat elemental damage."""
        weapon = DamageRange(50, 100)  # avg: 75
        added_damage = [
            (DamageType.FIRE, DamageRange(20, 40)),  # avg: 30
            (DamageType.LIGHTNING, DamageRange(10, 20)),  # avg: 15
        ]

        result = self.calc.calculate_base_damage(
            weapon_damage=weapon, added_flat_damage=added_damage
        )

        # Total = 75 + 30 + 15 = 120
        self.assertEqual(result.total_average_damage(), 120.0)

    def test_no_damage_source_raises_error(self):
        """Test that providing neither weapon nor spell raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.calc.calculate_base_damage()
        self.assertIn("must provide", str(context.exception).lower())


class TestIncreasedModifiers(unittest.TestCase):
    """Test increased/reduced modifier application."""

    def setUp(self):
        """Set up test calculator."""
        self.calc = DamageCalculator()

    def test_single_increased_modifier(self):
        """Test applying single increased modifier."""
        base = 100
        mods = [Modifier(value=50, modifier_type=ModifierType.INCREASED)]
        result = self.calc.apply_increased_modifiers(base, mods)

        # 100 * (1 + 0.50) = 150
        self.assertEqual(result, 150.0)

    def test_multiple_increased_modifiers_stack_additively(self):
        """Test that multiple increased modifiers stack additively."""
        base = 100
        mods = [
            Modifier(value=50, modifier_type=ModifierType.INCREASED),
            Modifier(value=30, modifier_type=ModifierType.INCREASED),
            Modifier(value=20, modifier_type=ModifierType.INCREASED),
        ]
        result = self.calc.apply_increased_modifiers(base, mods)

        # 100 * (1 + 0.50 + 0.30 + 0.20) = 100 * 2.0 = 200
        self.assertEqual(result, 200.0)

    def test_reduced_modifier(self):
        """Test reduced modifier (negative increased)."""
        base = 100
        mods = [Modifier(value=25, modifier_type=ModifierType.REDUCED)]
        result = self.calc.apply_increased_modifiers(base, mods)

        # 100 * (1 - 0.25) = 75
        self.assertEqual(result, 75.0)

    def test_increased_and_reduced_mixed(self):
        """Test mixing increased and reduced modifiers."""
        base = 100
        mods = [
            Modifier(value=100, modifier_type=ModifierType.INCREASED),  # +100%
            Modifier(value=50, modifier_type=ModifierType.REDUCED),  # -50%
        ]
        result = self.calc.apply_increased_modifiers(base, mods)

        # 100 * (1 + 1.00 - 0.50) = 100 * 1.5 = 150
        self.assertEqual(result, 150.0)

    def test_no_modifiers(self):
        """Test with empty modifier list."""
        base = 100
        result = self.calc.apply_increased_modifiers(base, [])
        self.assertEqual(result, 100.0)


class TestMoreModifiers(unittest.TestCase):
    """Test more/less modifier application."""

    def setUp(self):
        """Set up test calculator."""
        self.calc = DamageCalculator()

    def test_single_more_modifier(self):
        """Test applying single more modifier."""
        base = 100
        mods = [Modifier(value=50, modifier_type=ModifierType.MORE)]
        result = self.calc.apply_more_modifiers(base, mods)

        # 100 * 1.50 = 150
        self.assertEqual(result, 150.0)

    def test_multiple_more_modifiers_stack_multiplicatively(self):
        """Test that multiple more modifiers stack multiplicatively."""
        base = 100
        mods = [
            Modifier(value=50, modifier_type=ModifierType.MORE),  # 1.5x
            Modifier(value=30, modifier_type=ModifierType.MORE),  # 1.3x
            Modifier(value=20, modifier_type=ModifierType.MORE),  # 1.2x
        ]
        result = self.calc.apply_more_modifiers(base, mods)

        # 100 * 1.5 * 1.3 * 1.2 = 234
        self.assertAlmostEqual(result, 234.0, places=1)

    def test_less_modifier(self):
        """Test less modifier (negative more)."""
        base = 100
        mods = [Modifier(value=20, modifier_type=ModifierType.LESS)]
        result = self.calc.apply_more_modifiers(base, mods)

        # 100 * 0.80 = 80
        self.assertEqual(result, 80.0)

    def test_more_and_less_mixed(self):
        """Test mixing more and less modifiers."""
        base = 100
        mods = [
            Modifier(value=100, modifier_type=ModifierType.MORE),  # 2.0x
            Modifier(value=50, modifier_type=ModifierType.LESS),  # 0.5x
        ]
        result = self.calc.apply_more_modifiers(base, mods)

        # 100 * 2.0 * 0.5 = 100
        self.assertEqual(result, 100.0)

    def test_no_modifiers(self):
        """Test with empty modifier list."""
        base = 100
        result = self.calc.apply_more_modifiers(base, [])
        self.assertEqual(result, 100.0)


class TestMoreVsIncreased(unittest.TestCase):
    """Test critical difference between MORE and INCREASED modifiers."""

    def setUp(self):
        """Set up test calculator."""
        self.calc = DamageCalculator()

    def test_increased_modifiers_additive(self):
        """Test that INCREASED modifiers are additive."""
        base = 100
        mods = [
            Modifier(value=50, modifier_type=ModifierType.INCREASED),
            Modifier(value=50, modifier_type=ModifierType.INCREASED),
        ]
        result = self.calc.apply_increased_modifiers(base, mods)

        # 100 * (1 + 0.50 + 0.50) = 200 (NOT 225)
        self.assertEqual(result, 200.0)

    def test_more_modifiers_multiplicative(self):
        """Test that MORE modifiers are multiplicative."""
        base = 100
        mods = [
            Modifier(value=50, modifier_type=ModifierType.MORE),
            Modifier(value=50, modifier_type=ModifierType.MORE),
        ]
        result = self.calc.apply_more_modifiers(base, mods)

        # 100 * 1.50 * 1.50 = 225 (NOT 200)
        self.assertEqual(result, 225.0)


class TestCriticalStrike(unittest.TestCase):
    """Test critical strike calculation."""

    def setUp(self):
        """Set up test calculator."""
        self.calc = DamageCalculator()

    def test_poe2_base_crit_multiplier(self):
        """Test that PoE2 uses +100% base crit damage (not +150% like PoE1)."""
        config = CriticalStrikeConfig(
            crit_chance=100.0, crit_multiplier=100  # Always crit  # Base PoE2 crit
        )

        # With 100% crit chance and 100% multiplier, effective is 2.0x
        self.assertEqual(config.crit_multiplier, 100)
        self.assertEqual(config.effective_damage_multiplier(), 2.0)

    def test_crit_with_increased_multiplier(self):
        """Test critical damage with increased multiplier."""
        base_damage = DamageRange(100, 100)
        config = CriticalStrikeConfig(
            crit_chance=100.0,  # Always crit
            crit_multiplier=150,  # 100% base + 50% increased = 250% total
        )

        result = self.calc.calculate_critical_damage(base_damage, config)

        # 100 * (1 + 150/100) = 100 * 2.5 = 250
        self.assertEqual(result.average(), 250.0)

    def test_no_crit_with_effective_multiplier(self):
        """Test that 0% crit chance has 1.0x effective multiplier."""
        config = CriticalStrikeConfig(crit_chance=0.0, crit_multiplier=150)

        # With 0% crit, effective multiplier is 1.0 (no bonus)
        self.assertEqual(config.effective_damage_multiplier(), 1.0)

    def test_partial_crit_chance(self):
        """Test average damage with partial crit chance."""
        config = CriticalStrikeConfig(
            crit_chance=50.0, crit_multiplier=100  # 50% crit chance  # 2.0x damage on crit
        )

        # Effective multiplier: (0.5 * 1.0) + (0.5 * 2.0) = 0.5 + 1.0 = 1.5
        self.assertEqual(config.effective_damage_multiplier(), 1.5)


class TestDamageConversion(unittest.TestCase):
    """Test elemental conversion mechanics."""

    def setUp(self):
        """Set up test calculator."""
        self.calc = DamageCalculator()

    def test_full_physical_to_fire_conversion(self):
        """Test 100% physical to fire conversion."""
        components = DamageComponents()
        components.add_damage(DamageType.PHYSICAL, DamageRange(100, 100))

        conversion = {
            DamageType.PHYSICAL: {
                DamageType.FIRE: 100  # 100% conversion (as percentage, not decimal)
            }
        }

        result = self.calc.apply_damage_conversion(components, conversion)

        # All physical should be converted to fire
        phys = result.get_damage_by_type(DamageType.PHYSICAL)
        fire = result.get_damage_by_type(DamageType.FIRE)

        self.assertIsNone(phys)  # No physical left
        self.assertIsNotNone(fire)
        self.assertEqual(fire.average(), 100.0)

    def test_partial_physical_to_fire_conversion(self):
        """Test 50% physical to fire conversion."""
        components = DamageComponents()
        components.add_damage(DamageType.PHYSICAL, DamageRange(100, 100))

        conversion = {
            DamageType.PHYSICAL: {
                DamageType.FIRE: 50  # 50% conversion (as percentage, not decimal)
            }
        }

        result = self.calc.apply_damage_conversion(components, conversion)

        phys = result.get_damage_by_type(DamageType.PHYSICAL)
        fire = result.get_damage_by_type(DamageType.FIRE)

        # 50 physical, 50 fire
        self.assertIsNotNone(phys)
        self.assertIsNotNone(fire)
        self.assertEqual(phys.average(), 50.0)
        self.assertEqual(fire.average(), 50.0)

    def test_split_conversion(self):
        """Test converting to multiple elements."""
        components = DamageComponents()
        components.add_damage(DamageType.PHYSICAL, DamageRange(100, 100))

        conversion = {
            DamageType.PHYSICAL: {
                DamageType.FIRE: 40,  # 40% to fire (as percentage)
                DamageType.LIGHTNING: 30,  # 30% to lightning (as percentage)
            }
        }

        result = self.calc.apply_damage_conversion(components, conversion)

        phys = result.get_damage_by_type(DamageType.PHYSICAL)
        fire = result.get_damage_by_type(DamageType.FIRE)
        lightning = result.get_damage_by_type(DamageType.LIGHTNING)

        # 30 phys, 40 fire, 30 lightning
        self.assertIsNotNone(phys)
        self.assertEqual(phys.average(), 30.0)
        self.assertEqual(fire.average(), 40.0)
        self.assertEqual(lightning.average(), 30.0)

    def test_no_conversion(self):
        """Test with no conversion."""
        components = DamageComponents()
        components.add_damage(DamageType.PHYSICAL, DamageRange(100, 100))

        result = self.calc.apply_damage_conversion(components, {})

        # Should be unchanged
        phys = result.get_damage_by_type(DamageType.PHYSICAL)
        self.assertIsNotNone(phys)
        self.assertEqual(phys.average(), 100.0)


class TestAttackSpeed(unittest.TestCase):
    """Test attack speed calculation."""

    def setUp(self):
        """Set up test calculator."""
        self.calc = DamageCalculator()

    def test_base_attack_speed(self):
        """Test attack speed with no modifiers."""
        base_attack_time = 1.5  # 1.5 seconds per attack
        result = self.calc.calculate_attack_speed(base_attack_time, [])

        # 1 / 1.5 = 0.667 attacks per second
        self.assertAlmostEqual(result, 0.667, places=3)

    def test_increased_attack_speed(self):
        """Test with increased attack speed."""
        base_attack_time = 1.0  # 1 second per attack
        mods = [Modifier(50, ModifierType.INCREASED)]  # 50% increased
        result = self.calc.calculate_attack_speed(base_attack_time, mods)

        # (1 / 1.0) * (1 + 0.50) = 1.0 * 1.5 = 1.5 attacks per second
        self.assertEqual(result, 1.5)

    def test_reduced_attack_speed(self):
        """Test with reduced attack speed (negative increased)."""
        base_attack_time = 1.0  # 1 second per attack
        mods = [Modifier(25, ModifierType.REDUCED)]  # 25% reduced
        result = self.calc.calculate_attack_speed(base_attack_time, mods)

        # (1 / 1.0) * (1 - 0.25) = 1.0 * 0.75 = 0.75 attacks per second
        self.assertEqual(result, 0.75)


class TestCastSpeed(unittest.TestCase):
    """Test cast speed calculation."""

    def setUp(self):
        """Set up test calculator."""
        self.calc = DamageCalculator()

    def test_base_cast_speed(self):
        """Test cast speed with no modifiers."""
        base_cast_time = 1.0  # 1 second
        result = self.calc.calculate_cast_speed(base_cast_time, [])

        # 1 / 1.0 = 1.0 casts per second
        self.assertEqual(result, 1.0)

    def test_increased_cast_speed(self):
        """Test with increased cast speed."""
        base_cast_time = 1.0
        mods = [Modifier(100, ModifierType.INCREASED)]  # 100% increased = 2x speed
        result = self.calc.calculate_cast_speed(base_cast_time, mods)

        # (1 / 1.0) * (1 + 1.0) = 1.0 * 2.0 = 2.0 casts per second
        self.assertEqual(result, 2.0)


if __name__ == "__main__":
    unittest.main()
