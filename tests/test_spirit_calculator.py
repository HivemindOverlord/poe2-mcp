"""
Unit tests for Path of Exile 2 Spirit Calculator

Tests the advanced Spirit management system including:
- Spirit sources (quest, gear, passives)
- Spirit reservations with support gems
- Overflow detection and resolution
- Optimization suggestions
"""

import unittest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from calculator.spirit_calculator import (
    SpiritCalculator,
    SpiritSource,
    SpiritReservation,
    SupportGem,
    SpiritSourceType,
    SpiritReservationType,
    SpiritOptimization,
    calculate_support_gem_cost,
    find_optimal_support_combinations
)


class TestSpiritSource(unittest.TestCase):
    """Test SpiritSource dataclass."""

    def test_valid_source(self):
        source = SpiritSource(
            name="Test Quest",
            amount=30,
            source_type=SpiritSourceType.QUEST
        )
        self.assertEqual(source.name, "Test Quest")
        self.assertEqual(source.amount, 30)
        self.assertEqual(source.source_type, SpiritSourceType.QUEST)
        self.assertTrue(source.enabled)

    def test_negative_amount_raises_error(self):
        with self.assertRaises(ValueError):
            SpiritSource(
                name="Invalid",
                amount=-10,
                source_type=SpiritSourceType.QUEST
            )

    def test_disabled_source(self):
        source = SpiritSource(
            name="Test",
            amount=20,
            source_type=SpiritSourceType.GEAR,
            enabled=False
        )
        self.assertFalse(source.enabled)


class TestSupportGem(unittest.TestCase):
    """Test SupportGem dataclass."""

    def test_valid_support_gem(self):
        gem = SupportGem(name="Minion Damage", multiplier=1.5)
        self.assertEqual(gem.name, "Minion Damage")
        self.assertEqual(gem.multiplier, 1.5)

    def test_invalid_multiplier_raises_error(self):
        with self.assertRaises(ValueError):
            SupportGem(name="Invalid", multiplier=0.5)


class TestSpiritReservation(unittest.TestCase):
    """Test SpiritReservation dataclass."""

    def test_base_cost_no_supports(self):
        res = SpiritReservation(
            name="Raise Zombie",
            base_cost=25,
            reservation_type=SpiritReservationType.PERMANENT_MINION
        )
        self.assertEqual(res.calculate_cost(), 25)

    def test_cost_with_single_support(self):
        res = SpiritReservation(
            name="Raise Zombie",
            base_cost=25,
            reservation_type=SpiritReservationType.PERMANENT_MINION,
            support_gems=[SupportGem("Minion Damage", 1.5)]
        )
        # 25 * 1.5 = 37.5, rounds up to 38
        self.assertEqual(res.calculate_cost(), 38)

    def test_cost_with_multiple_supports(self):
        res = SpiritReservation(
            name="Raise Zombie",
            base_cost=25,
            reservation_type=SpiritReservationType.PERMANENT_MINION,
            support_gems=[
                SupportGem("Minion Damage", 1.5),
                SupportGem("Minion Life", 1.3)
            ]
        )
        # 25 * 1.5 * 1.3 = 48.75, rounds up to 49
        self.assertEqual(res.calculate_cost(), 49)

    def test_disabled_reservation_costs_zero(self):
        res = SpiritReservation(
            name="Raise Zombie",
            base_cost=25,
            reservation_type=SpiritReservationType.PERMANENT_MINION,
            support_gems=[SupportGem("Minion Damage", 1.5)],
            enabled=False
        )
        self.assertEqual(res.calculate_cost(), 0)

    def test_priority_validation(self):
        with self.assertRaises(ValueError):
            SpiritReservation(
                name="Test",
                base_cost=25,
                reservation_type=SpiritReservationType.AURA,
                priority=11  # Invalid: must be 1-10
            )

    def test_add_support_gem(self):
        res = SpiritReservation(
            name="Raise Zombie",
            base_cost=25,
            reservation_type=SpiritReservationType.PERMANENT_MINION
        )
        self.assertEqual(res.calculate_cost(), 25)

        res.add_support_gem("Minion Damage", 1.5)
        self.assertEqual(res.calculate_cost(), 38)

    def test_remove_support_gem(self):
        res = SpiritReservation(
            name="Raise Zombie",
            base_cost=25,
            reservation_type=SpiritReservationType.PERMANENT_MINION,
            support_gems=[SupportGem("Minion Damage", 1.5)]
        )
        self.assertEqual(res.calculate_cost(), 38)

        removed = res.remove_support_gem("Minion Damage")
        self.assertTrue(removed)
        self.assertEqual(res.calculate_cost(), 25)

    def test_remove_nonexistent_support_gem(self):
        res = SpiritReservation(
            name="Raise Zombie",
            base_cost=25,
            reservation_type=SpiritReservationType.PERMANENT_MINION
        )
        removed = res.remove_support_gem("Nonexistent")
        self.assertFalse(removed)

    def test_get_cost_breakdown(self):
        res = SpiritReservation(
            name="Raise Zombie",
            base_cost=25,
            reservation_type=SpiritReservationType.PERMANENT_MINION,
            support_gems=[
                SupportGem("Minion Damage", 1.5),
                SupportGem("Minion Life", 1.3)
            ]
        )
        breakdown = res.get_cost_breakdown()
        self.assertEqual(breakdown['base_cost'], 25)
        self.assertEqual(breakdown['final_cost'], 49)
        self.assertEqual(breakdown['total_multiplier'], 1.95)
        self.assertEqual(len(breakdown['support_gems']), 2)


class TestSpiritCalculator(unittest.TestCase):
    """Test SpiritCalculator main functionality."""

    def setUp(self):
        """Create a fresh calculator for each test."""
        self.calc = SpiritCalculator()

    def test_initialization(self):
        """Test calculator initializes with empty lists."""
        self.assertEqual(len(self.calc.sources), 0)
        self.assertEqual(len(self.calc.reservations), 0)
        self.assertEqual(self.calc.get_maximum_spirit(), 0)

    def test_add_quest_spirit(self):
        """Test adding quest Spirit sources."""
        self.calc.add_quest_spirit("First Skull", 30)
        self.calc.add_quest_spirit("Second Skull", 30)
        self.calc.add_quest_spirit("Third Skull", 40)

        self.assertEqual(self.calc.get_quest_spirit(), 100)
        self.assertEqual(self.calc.get_maximum_spirit(), 100)

    def test_add_gear_spirit(self):
        """Test adding gear Spirit sources."""
        self.calc.add_gear_spirit("Helmet", 30)
        self.calc.add_gear_spirit("Body Armour", 20)

        self.assertEqual(self.calc.get_gear_spirit(), 50)
        self.assertEqual(self.calc.get_maximum_spirit(), 50)

    def test_add_passive_spirit(self):
        """Test adding passive tree Spirit sources."""
        self.calc.add_passive_spirit("Node 1", 15)
        self.calc.add_passive_spirit("Node 2", 10)

        self.assertEqual(self.calc.get_passive_spirit(), 25)
        self.assertEqual(self.calc.get_maximum_spirit(), 25)

    def test_combined_spirit_sources(self):
        """Test combining multiple Spirit sources."""
        self.calc.add_quest_spirit("Quest", 100)
        self.calc.add_gear_spirit("Gear", 50)
        self.calc.add_passive_spirit("Passive", 25)

        self.assertEqual(self.calc.get_maximum_spirit(), 175)

    def test_remove_spirit_source(self):
        """Test removing a Spirit source."""
        self.calc.add_gear_spirit("Helmet", 30)
        self.assertEqual(self.calc.get_maximum_spirit(), 30)

        removed = self.calc.remove_spirit_source("Helmet")
        self.assertTrue(removed)
        self.assertEqual(self.calc.get_maximum_spirit(), 0)

    def test_remove_nonexistent_spirit_source(self):
        """Test removing a nonexistent Spirit source."""
        removed = self.calc.remove_spirit_source("Nonexistent")
        self.assertFalse(removed)

    def test_toggle_spirit_source(self):
        """Test toggling a Spirit source on/off."""
        self.calc.add_gear_spirit("Helmet", 30)
        self.assertEqual(self.calc.get_maximum_spirit(), 30)

        # Toggle off
        enabled = self.calc.toggle_spirit_source("Helmet")
        self.assertFalse(enabled)
        self.assertEqual(self.calc.get_maximum_spirit(), 0)

        # Toggle on
        enabled = self.calc.toggle_spirit_source("Helmet")
        self.assertTrue(enabled)
        self.assertEqual(self.calc.get_maximum_spirit(), 30)

    def test_add_reservation_no_supports(self):
        """Test adding a reservation without support gems."""
        self.calc.add_quest_spirit("Quest", 100)
        res = self.calc.add_reservation(
            "Purity of Fire",
            30,
            SpiritReservationType.AURA
        )

        self.assertEqual(self.calc.get_spirit_reserved(), 30)
        self.assertEqual(self.calc.get_spirit_available(), 70)

    def test_add_reservation_with_supports(self):
        """Test adding a reservation with support gems."""
        self.calc.add_quest_spirit("Quest", 100)
        res = self.calc.add_reservation(
            "Raise Zombie",
            25,
            SpiritReservationType.PERMANENT_MINION,
            support_gems=[("Minion Damage", 1.5), ("Minion Life", 1.3)]
        )

        # 25 * 1.5 * 1.3 = 48.75, rounds up to 49
        self.assertEqual(self.calc.get_spirit_reserved(), 49)
        self.assertEqual(self.calc.get_spirit_available(), 51)

    def test_multiple_reservations(self):
        """Test multiple reservations."""
        self.calc.add_quest_spirit("Quest", 100)

        self.calc.add_reservation("Purity of Fire", 30, SpiritReservationType.AURA)
        self.calc.add_reservation("Raise Zombie", 25, SpiritReservationType.PERMANENT_MINION,
                                 support_gems=[("Minion Damage", 1.5)])

        # 30 + 38 = 68
        self.assertEqual(self.calc.get_spirit_reserved(), 68)
        self.assertEqual(self.calc.get_spirit_available(), 32)

    def test_remove_reservation(self):
        """Test removing a reservation."""
        self.calc.add_quest_spirit("Quest", 100)
        self.calc.add_reservation("Purity of Fire", 30, SpiritReservationType.AURA)
        self.assertEqual(self.calc.get_spirit_reserved(), 30)

        removed = self.calc.remove_reservation("Purity of Fire")
        self.assertTrue(removed)
        self.assertEqual(self.calc.get_spirit_reserved(), 0)

    def test_toggle_reservation(self):
        """Test toggling a reservation on/off."""
        self.calc.add_quest_spirit("Quest", 100)
        self.calc.add_reservation("Purity of Fire", 30, SpiritReservationType.AURA)
        self.assertEqual(self.calc.get_spirit_reserved(), 30)

        # Toggle off
        enabled = self.calc.toggle_reservation("Purity of Fire")
        self.assertFalse(enabled)
        self.assertEqual(self.calc.get_spirit_reserved(), 0)

        # Toggle on
        enabled = self.calc.toggle_reservation("Purity of Fire")
        self.assertTrue(enabled)
        self.assertEqual(self.calc.get_spirit_reserved(), 30)

    def test_get_reservation(self):
        """Test getting a reservation by name."""
        self.calc.add_reservation("Purity of Fire", 30, SpiritReservationType.AURA)
        res = self.calc.get_reservation("Purity of Fire")
        self.assertIsNotNone(res)
        self.assertEqual(res.name, "Purity of Fire")

        res = self.calc.get_reservation("Nonexistent")
        self.assertIsNone(res)

    def test_overflow_detection(self):
        """Test overflow detection."""
        self.calc.add_quest_spirit("Quest", 100)
        self.calc.add_reservation("Reservation 1", 60, SpiritReservationType.AURA)
        self.calc.add_reservation("Reservation 2", 50, SpiritReservationType.AURA)

        self.assertTrue(self.calc.is_overflowing())
        self.assertEqual(self.calc.get_overflow_amount(), 10)
        self.assertEqual(self.calc.get_spirit_available(), -10)

    def test_no_overflow(self):
        """Test no overflow scenario."""
        self.calc.add_quest_spirit("Quest", 100)
        self.calc.add_reservation("Reservation 1", 40, SpiritReservationType.AURA)
        self.calc.add_reservation("Reservation 2", 50, SpiritReservationType.AURA)

        self.assertFalse(self.calc.is_overflowing())
        self.assertEqual(self.calc.get_overflow_amount(), 0)
        self.assertEqual(self.calc.get_spirit_available(), 10)

    def test_spirit_summary(self):
        """Test Spirit summary generation."""
        self.calc.add_quest_spirit("Quest", 100)
        self.calc.add_gear_spirit("Gear", 50)
        self.calc.add_reservation("Purity of Fire", 30, SpiritReservationType.AURA)

        summary = self.calc.get_spirit_summary()
        self.assertEqual(summary['maximum_spirit'], 150)
        self.assertEqual(summary['reserved_spirit'], 30)
        self.assertEqual(summary['available_spirit'], 120)
        self.assertFalse(summary['is_overflowing'])
        self.assertEqual(summary['overflow_amount'], 0)
        self.assertEqual(summary['active_reservations'], 1)

    def test_auto_resolve_overflow(self):
        """Test automatic overflow resolution."""
        self.calc.add_quest_spirit("Quest", 100)

        # Add reservations that overflow
        self.calc.add_reservation("High Priority", 30, SpiritReservationType.AURA, priority=1)
        self.calc.add_reservation("Medium Priority", 40, SpiritReservationType.AURA, priority=5)
        self.calc.add_reservation("Low Priority", 50, SpiritReservationType.AURA, priority=9)

        self.assertTrue(self.calc.is_overflowing())

        actions = self.calc.auto_resolve_overflow()
        self.assertFalse(self.calc.is_overflowing())
        self.assertGreater(len(actions), 0)

    def test_optimization_suggestions(self):
        """Test optimization suggestions."""
        self.calc.add_quest_spirit("Quest", 100)
        self.calc.add_reservation(
            "Raise Zombie",
            25,
            SpiritReservationType.PERMANENT_MINION,
            support_gems=[("Minion Damage", 1.5), ("Minion Life", 1.3)],
            priority=5
        )
        self.calc.add_reservation("Purity of Fire", 80, SpiritReservationType.AURA, priority=8)

        suggestions = self.calc.get_optimization_suggestions()
        self.assertGreater(len(suggestions), 0)

        # First suggestion should save the most Spirit
        if len(suggestions) > 1:
            self.assertGreaterEqual(
                suggestions[0].spirit_saved,
                suggestions[1].spirit_saved
            )

    def test_suggest_optimal_configuration(self):
        """Test optimal configuration suggestion."""
        self.calc.add_quest_spirit("Quest", 100)
        self.calc.add_reservation("Res1", 40, SpiritReservationType.AURA, priority=1)
        self.calc.add_reservation("Res2", 40, SpiritReservationType.AURA, priority=2)
        self.calc.add_reservation("Res3", 40, SpiritReservationType.AURA, priority=9)

        optimal = self.calc.suggest_optimal_configuration()
        self.assertEqual(optimal['maximum_spirit'], 100)
        self.assertLessEqual(optimal['optimal_spirit_used'], 100)
        self.assertGreaterEqual(len(optimal['enabled_reservations']), 2)

    def test_validate_configuration_valid(self):
        """Test validation of valid configuration."""
        self.calc.add_quest_spirit("Quest", 100)
        self.calc.add_reservation("Purity of Fire", 30, SpiritReservationType.AURA)

        is_valid, issues = self.calc.validate_configuration()
        self.assertTrue(is_valid)
        self.assertEqual(len(issues), 0)

    def test_validate_configuration_overflow(self):
        """Test validation detects overflow."""
        self.calc.add_quest_spirit("Quest", 100)
        self.calc.add_reservation("Overflow", 120, SpiritReservationType.AURA)

        is_valid, issues = self.calc.validate_configuration()
        self.assertFalse(is_valid)
        self.assertGreater(len(issues), 0)
        self.assertIn("overflow", issues[0].lower())

    def test_validate_configuration_no_sources(self):
        """Test validation detects no Spirit sources."""
        is_valid, issues = self.calc.validate_configuration()
        self.assertFalse(is_valid)
        self.assertGreater(len(issues), 0)

    def test_export_import_configuration(self):
        """Test exporting and importing configuration."""
        self.calc.add_quest_spirit("Quest", 100)
        self.calc.add_gear_spirit("Gear", 50)
        self.calc.add_reservation(
            "Raise Zombie",
            25,
            SpiritReservationType.PERMANENT_MINION,
            support_gems=[("Minion Damage", 1.5)]
        )

        # Export
        config = self.calc.export_configuration()
        self.assertIn('sources', config)
        self.assertIn('reservations', config)
        self.assertIn('summary', config)

        # Import to new calculator
        calc2 = SpiritCalculator()
        calc2.import_configuration(config)

        self.assertEqual(calc2.get_maximum_spirit(), 150)
        self.assertEqual(calc2.get_spirit_reserved(), 38)
        self.assertEqual(len(calc2.sources), 2)
        self.assertEqual(len(calc2.reservations), 1)


class TestHelperFunctions(unittest.TestCase):
    """Test helper functions."""

    def test_calculate_support_gem_cost(self):
        """Test support gem cost calculation."""
        # No supports
        self.assertEqual(calculate_support_gem_cost(25, []), 25)

        # Single support
        self.assertEqual(calculate_support_gem_cost(25, [1.5]), 38)

        # Multiple supports
        self.assertEqual(calculate_support_gem_cost(20, [1.5, 1.3]), 39)

    def test_find_optimal_support_combinations(self):
        """Test finding optimal support combinations."""
        available_supports = [
            ("Support1", 1.5),
            ("Support2", 1.3),
            ("Support3", 1.2)
        ]

        combos = find_optimal_support_combinations(20, available_supports, 40)

        # Should find multiple valid combinations
        self.assertGreater(len(combos), 0)

        # All combos should be within budget
        for names, cost in combos:
            self.assertLessEqual(cost, 40)

        # Should be sorted by cost descending
        if len(combos) > 1:
            self.assertGreaterEqual(combos[0][1], combos[1][1])


if __name__ == '__main__':
    unittest.main()
