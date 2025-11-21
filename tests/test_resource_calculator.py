"""
Unit tests for Path of Exile 2 Resource Calculator

Tests all resource calculations including the new Spirit system.
"""

import unittest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from calculator.resource_calculator import (
    ResourceCalculator,
    AttributeStats,
    ResourceModifiers,
    SpiritReservation,
    ResourcePool,
    ResourceType,
    calculate_hit_chance
)


class TestAttributeStats(unittest.TestCase):
    """Test AttributeStats dataclass."""

    def test_valid_attributes(self):
        attrs = AttributeStats(strength=100, dexterity=80, intelligence=120)
        self.assertEqual(attrs.strength, 100)
        self.assertEqual(attrs.dexterity, 80)
        self.assertEqual(attrs.intelligence, 120)

    def test_negative_attributes_raise_error(self):
        with self.assertRaises(ValueError):
            AttributeStats(strength=-10, dexterity=50, intelligence=50)

    def test_zero_attributes(self):
        attrs = AttributeStats(strength=0, dexterity=0, intelligence=0)
        self.assertEqual(attrs.strength, 0)


class TestResourceModifiers(unittest.TestCase):
    """Test ResourceModifiers dataclass."""

    def test_no_more_multipliers(self):
        mods = ResourceModifiers()
        self.assertEqual(mods.calculate_total_more(), 1.0)

    def test_single_more_multiplier(self):
        mods = ResourceModifiers(more_multipliers=[1.5])
        self.assertEqual(mods.calculate_total_more(), 1.5)

    def test_multiple_more_multipliers(self):
        mods = ResourceModifiers(more_multipliers=[1.5, 1.2])
        self.assertAlmostEqual(mods.calculate_total_more(), 1.8, places=5)


class TestSpiritReservation(unittest.TestCase):
    """Test Spirit reservation calculations."""

    def test_base_cost_no_supports(self):
        reservation = SpiritReservation(name="Test", base_cost=25)
        self.assertEqual(reservation.calculate_cost(), 25)

    def test_cost_with_single_support(self):
        reservation = SpiritReservation(name="Test", base_cost=25, support_multipliers=[1.5])
        self.assertEqual(reservation.calculate_cost(), 38)  # 25 * 1.5 = 37.5, rounded up

    def test_cost_with_multiple_supports(self):
        reservation = SpiritReservation(name="Test", base_cost=20, support_multipliers=[1.4, 1.3])
        self.assertEqual(reservation.calculate_cost(), 37)  # 20 * 1.4 * 1.3 = 36.4, rounded up

    def test_disabled_reservation(self):
        reservation = SpiritReservation(name="Test", base_cost=25, enabled=False)
        self.assertEqual(reservation.calculate_cost(), 0)


class TestResourcePool(unittest.TestCase):
    """Test ResourcePool calculations."""

    def test_unreserved_with_flat_reservation(self):
        pool = ResourcePool(maximum=1000, reserved_flat=200)
        self.assertEqual(pool.unreserved_maximum, 800)

    def test_unreserved_with_percent_reservation(self):
        pool = ResourcePool(maximum=1000, reserved_percent=50)
        self.assertEqual(pool.unreserved_maximum, 500)

    def test_unreserved_with_both_reservations(self):
        pool = ResourcePool(maximum=1000, reserved_flat=100, reserved_percent=50)
        self.assertEqual(pool.unreserved_maximum, 400)  # 1000 - 100 - 500

    def test_percent_available(self):
        pool = ResourcePool(maximum=1000, current=500, reserved_percent=50)
        self.assertEqual(pool.percent_available, 100.0)  # 500/500 unreserved


class TestResourceCalculator(unittest.TestCase):
    """Test main ResourceCalculator functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.attributes = AttributeStats(strength=100, dexterity=80, intelligence=120)
        self.calculator = ResourceCalculator(character_level=50, attributes=self.attributes)

    def test_invalid_level_raises_error(self):
        with self.assertRaises(ValueError):
            ResourceCalculator(character_level=0, attributes=self.attributes)

        with self.assertRaises(ValueError):
            ResourceCalculator(character_level=101, attributes=self.attributes)

    def test_calculate_maximum_life_base(self):
        """Test base life calculation without modifiers."""
        # Formula: 28 + (12 * 50) + (2 * 100) = 28 + 600 + 200 = 828
        max_life = self.calculator.calculate_maximum_life()
        self.assertEqual(max_life, 828.0)

    def test_calculate_maximum_life_with_modifiers(self):
        """Test life calculation with modifiers."""
        mods = ResourceModifiers(
            flat_bonus=50,
            increased_percent=100,
            more_multipliers=[1.15]
        )
        # Base: 828 + 50 = 878
        # Increased: 878 * 2.0 = 1756
        # More: 1756 * 1.15 = 2019.4
        max_life = self.calculator.calculate_maximum_life(mods)
        self.assertAlmostEqual(max_life, 2019.4, places=1)

    def test_calculate_maximum_mana_base(self):
        """Test base mana calculation without modifiers."""
        # Formula: 34 + (4 * 50) + (2 * 120) = 34 + 200 + 240 = 474
        max_mana = self.calculator.calculate_maximum_mana()
        self.assertEqual(max_mana, 474.0)

    def test_calculate_maximum_mana_with_modifiers(self):
        """Test mana calculation with modifiers."""
        mods = ResourceModifiers(
            flat_bonus=30,
            increased_percent=50
        )
        # Base: 474 + 30 = 504
        # Increased: 504 * 1.5 = 756
        max_mana = self.calculator.calculate_maximum_mana(mods)
        self.assertEqual(max_mana, 756.0)

    def test_calculate_mana_regeneration(self):
        """Test mana regeneration calculation."""
        max_mana = 1000
        # Base regen: 1000 * 0.04 = 40
        # Increased: 40 * 1.5 = 60
        # Flat: 60 + 10 = 70
        regen = self.calculator.calculate_mana_regeneration(
            maximum_mana=max_mana,
            increased_regen_percent=50,
            flat_regen_per_second=10
        )
        self.assertEqual(regen, 70.0)

    def test_calculate_maximum_energy_shield(self):
        """Test energy shield calculation."""
        mods = ResourceModifiers(
            flat_bonus=200,
            increased_percent=150
        )
        # Base: 200
        # Increased: 200 * 2.5 = 500
        max_es = self.calculator.calculate_maximum_energy_shield(mods)
        self.assertEqual(max_es, 500.0)

    def test_calculate_maximum_spirit_base(self):
        """Test base Spirit calculation (NEW in PoE2)."""
        # Base: 100 (from quests)
        max_spirit = self.calculator.calculate_maximum_spirit()
        self.assertEqual(max_spirit, 100)

    def test_calculate_maximum_spirit_with_modifiers(self):
        """Test Spirit calculation with modifiers (NEW in PoE2)."""
        mods = ResourceModifiers(
            flat_bonus=50,
            increased_percent=20
        )
        # Base: 100 + 50 = 150
        # Increased: 150 * 1.2 = 180
        max_spirit = self.calculator.calculate_maximum_spirit(mods)
        self.assertEqual(max_spirit, 180)

    def test_add_spirit_reservation(self):
        """Test adding Spirit reservations (NEW in PoE2)."""
        self.calculator.add_spirit_reservation("Raise Zombie", 25, [1.5])
        self.assertEqual(len(self.calculator.spirit_reservations), 1)
        self.assertEqual(self.calculator.spirit_reservations[0].name, "Raise Zombie")

    def test_remove_spirit_reservation(self):
        """Test removing Spirit reservations."""
        self.calculator.add_spirit_reservation("Test", 25)
        removed = self.calculator.remove_spirit_reservation("Test")
        self.assertTrue(removed)
        self.assertEqual(len(self.calculator.spirit_reservations), 0)

    def test_remove_nonexistent_reservation(self):
        """Test removing non-existent reservation."""
        removed = self.calculator.remove_spirit_reservation("NonExistent")
        self.assertFalse(removed)

    def test_toggle_spirit_reservation(self):
        """Test toggling Spirit reservations."""
        self.calculator.add_spirit_reservation("Test", 25)
        # Toggle off
        enabled = self.calculator.toggle_spirit_reservation("Test")
        self.assertFalse(enabled)
        # Toggle on
        enabled = self.calculator.toggle_spirit_reservation("Test")
        self.assertTrue(enabled)

    def test_calculate_spirit_reserved(self):
        """Test Spirit reservation calculation."""
        self.calculator.add_spirit_reservation("Zombie", 25, [1.5])  # 38
        self.calculator.add_spirit_reservation("Skeleton", 20, [1.4, 1.3])  # 37
        self.calculator.add_spirit_reservation("Golem", 30)  # 30

        total_reserved = self.calculator.calculate_spirit_reserved()
        self.assertEqual(total_reserved, 105)  # 38 + 37 + 30

    def test_calculate_spirit_available(self):
        """Test available Spirit calculation."""
        self.calculator.add_spirit_reservation("Test", 30)
        available = self.calculator.calculate_spirit_available(maximum_spirit=100)
        self.assertEqual(available, 70)

    def test_check_spirit_overflow_no_overflow(self):
        """Test Spirit overflow check with enough Spirit."""
        self.calculator.add_spirit_reservation("Test", 30)
        overflow, amt, active = self.calculator.check_spirit_overflow(maximum_spirit=100)
        self.assertFalse(overflow)
        self.assertEqual(amt, 0)

    def test_check_spirit_overflow_with_overflow(self):
        """Test Spirit overflow check with insufficient Spirit."""
        self.calculator.add_spirit_reservation("Test1", 60)
        self.calculator.add_spirit_reservation("Test2", 60)
        overflow, amt, active = self.calculator.check_spirit_overflow(maximum_spirit=100)
        self.assertTrue(overflow)
        self.assertEqual(amt, 20)  # Over by 20
        self.assertEqual(len(active), 2)

    def test_calculate_accuracy(self):
        """Test accuracy calculation."""
        # Base: (6 * 50) + (6 * 80) = 300 + 480 = 780
        # Flat: 780 + 200 = 980
        # Increased: 980 * 1.5 = 1470
        accuracy = self.calculator.calculate_accuracy(
            flat_bonus=200,
            increased_percent=50
        )
        self.assertEqual(accuracy, 1470)

    def test_get_attribute_bonuses(self):
        """Test attribute bonus calculation."""
        bonuses = self.calculator.get_attribute_bonuses()
        self.assertEqual(bonuses['life_from_strength'], 200)  # 100 * 2
        self.assertEqual(bonuses['mana_from_intelligence'], 240)  # 120 * 2
        self.assertEqual(bonuses['accuracy_from_dexterity'], 480)  # 80 * 6

    def test_create_resource_pool(self):
        """Test resource pool creation."""
        pool = self.calculator.create_resource_pool(ResourceType.LIFE)
        self.assertIsInstance(pool, ResourcePool)
        self.assertGreater(pool.maximum, 0)

    def test_calculate_all_resources(self):
        """Test comprehensive resource calculation."""
        self.calculator.add_spirit_reservation("Test", 30)

        summary = self.calculator.calculate_all_resources()

        self.assertIn('level', summary)
        self.assertIn('attributes', summary)
        self.assertIn('resources', summary)
        self.assertIn('accuracy', summary)

        # Check Spirit section
        spirit = summary['resources']['spirit']
        self.assertEqual(spirit['maximum'], 100)
        self.assertEqual(spirit['reserved'], 30)
        self.assertEqual(spirit['available'], 70)
        self.assertFalse(spirit['is_overflowing'])


class TestHitChanceCalculation(unittest.TestCase):
    """Test hit chance calculation."""

    def test_hit_chance_equal_stats(self):
        """Test hit chance with equal accuracy and evasion."""
        chance = calculate_hit_chance(1000, 1000)
        self.assertAlmostEqual(chance, 80.0, places=1)

    def test_hit_chance_high_accuracy(self):
        """Test hit chance with high accuracy."""
        chance = calculate_hit_chance(5000, 1000)
        self.assertGreater(chance, 90.0)

    def test_hit_chance_low_accuracy(self):
        """Test hit chance with low accuracy."""
        chance = calculate_hit_chance(500, 5000)
        self.assertLess(chance, 50.0)

    def test_hit_chance_minimum(self):
        """Test hit chance minimum cap."""
        chance = calculate_hit_chance(1, 100000)
        self.assertGreaterEqual(chance, 5.0)  # Min cap

    def test_hit_chance_maximum(self):
        """Test hit chance maximum cap."""
        chance = calculate_hit_chance(100000, 1)
        self.assertLessEqual(chance, 100.0)  # Max cap


class TestPoE2Formulas(unittest.TestCase):
    """Test that PoE2 formulas are correctly implemented."""

    def test_life_formula_constants(self):
        """Verify PoE2 life formula constants."""
        self.assertEqual(ResourceCalculator.BASE_LIFE_AT_LEVEL_1, 28)
        self.assertEqual(ResourceCalculator.LIFE_PER_LEVEL, 12)
        self.assertEqual(ResourceCalculator.LIFE_PER_STRENGTH, 2)

    def test_mana_formula_constants(self):
        """Verify PoE2 mana formula constants."""
        self.assertEqual(ResourceCalculator.BASE_MANA_AT_LEVEL_1, 34)
        self.assertEqual(ResourceCalculator.MANA_PER_LEVEL, 4)
        self.assertEqual(ResourceCalculator.MANA_PER_INTELLIGENCE, 2)

    def test_spirit_formula_constants(self):
        """Verify PoE2 Spirit formula constants (NEW)."""
        self.assertEqual(ResourceCalculator.BASE_SPIRIT_FROM_QUESTS, 100)

    def test_accuracy_formula_constants(self):
        """Verify PoE2 accuracy formula constants."""
        self.assertEqual(ResourceCalculator.ACCURACY_PER_LEVEL, 6)
        self.assertEqual(ResourceCalculator.ACCURACY_PER_DEXTERITY, 6)


if __name__ == '__main__':
    unittest.main(verbosity=2)
