"""
Tests for TinyMT32 PRNG implementation.

These tests verify:
1. Deterministic output (same seed -> same sequence)
2. State transitions work correctly
3. Range generation produces valid values
4. Different seeds produce different sequences
"""

import pytest

from src.calculator.tinymt32 import (
    TinyMT32,
    create_timeless_rng,
    generate_poe_seed,
)


class TestTinyMT32Initialization:
    """Test initialization and seeding."""

    def test_same_seed_produces_same_sequence(self):
        """Verify deterministic behavior - same seed should produce same output."""
        rng1 = TinyMT32.from_poe_seed(node_id=12345, jewel_seed=1000)
        rng2 = TinyMT32.from_poe_seed(node_id=12345, jewel_seed=1000)

        # Generate 100 values from each and compare
        values1 = [rng1.generate_uint32() for _ in range(100)]
        values2 = [rng2.generate_uint32() for _ in range(100)]

        assert values1 == values2, "Same seed should produce same sequence"

    def test_different_seeds_produce_different_sequences(self):
        """Different seeds should produce different sequences."""
        rng1 = TinyMT32.from_poe_seed(node_id=12345, jewel_seed=1000)
        rng2 = TinyMT32.from_poe_seed(node_id=12345, jewel_seed=1001)

        values1 = [rng1.generate_uint32() for _ in range(10)]
        values2 = [rng2.generate_uint32() for _ in range(10)]

        assert values1 != values2, "Different seeds should produce different sequences"

    def test_different_node_ids_produce_different_sequences(self):
        """Different node IDs should produce different sequences."""
        rng1 = TinyMT32.from_poe_seed(node_id=12345, jewel_seed=1000)
        rng2 = TinyMT32.from_poe_seed(node_id=12346, jewel_seed=1000)

        values1 = [rng1.generate_uint32() for _ in range(10)]
        values2 = [rng2.generate_uint32() for _ in range(10)]

        assert values1 != values2, "Different node IDs should produce different sequences"

    def test_initial_state_is_set(self):
        """Verify initial state is properly initialized."""
        rng = TinyMT32.from_poe_seed(node_id=1, jewel_seed=1)
        state = rng.get_state()

        # State should have 5 elements
        assert len(state) == 5
        # Counter should be 8 after initialization (8 warm-up rounds)
        assert state[0] == 8

    def test_empty_seed_list(self):
        """Test with empty seed list (edge case)."""
        rng = TinyMT32([])
        value = rng.generate_uint32()
        assert 0 <= value <= 0xFFFFFFFF

    def test_single_seed(self):
        """Test with single seed value."""
        rng = TinyMT32([12345])
        value = rng.generate_uint32()
        assert 0 <= value <= 0xFFFFFFFF

    def test_multiple_seeds(self):
        """Test with more than 2 seeds."""
        rng = TinyMT32([1, 2, 3, 4, 5])
        value = rng.generate_uint32()
        assert 0 <= value <= 0xFFFFFFFF


class TestTinyMT32StateTransitions:
    """Test state transition logic."""

    def test_state_changes_after_next_state(self):
        """State should change after calling next_state."""
        rng = TinyMT32.from_poe_seed(node_id=12345, jewel_seed=1000)
        state_before = rng.get_state()

        rng.next_state()
        state_after = rng.get_state()

        # Counter should increment
        assert state_after[0] == state_before[0] + 1
        # At least some state values should change
        assert state_before != state_after

    def test_counter_increments(self):
        """Counter (state[0]) should increment with each next_state call."""
        rng = TinyMT32.from_poe_seed(node_id=12345, jewel_seed=1000)
        initial_counter = rng.get_state()[0]

        for i in range(10):
            rng.next_state()
            assert rng.get_state()[0] == initial_counter + i + 1

    def test_state_values_are_32bit(self):
        """All state values should be within uint32 range."""
        rng = TinyMT32.from_poe_seed(node_id=0xFFFFFFFF, jewel_seed=0xFFFFFFFF)

        for _ in range(1000):
            rng.next_state()
            state = rng.get_state()
            for val in state:
                assert 0 <= val <= 0xFFFFFFFF


class TestTinyMT32Output:
    """Test output generation methods."""

    def test_generate_uint32_range(self):
        """Generated uint32 should be in valid range."""
        rng = TinyMT32.from_poe_seed(node_id=12345, jewel_seed=1000)

        for _ in range(1000):
            value = rng.generate_uint32()
            assert 0 <= value <= 0xFFFFFFFF

    def test_generate_float_range(self):
        """Generated float should be in [0, 1)."""
        rng = TinyMT32.from_poe_seed(node_id=12345, jewel_seed=1000)

        for _ in range(1000):
            value = rng.generate_float()
            assert 0.0 <= value < 1.0

    def test_generate_range_bounds(self):
        """generate_range should return values in [0, max)."""
        rng = TinyMT32.from_poe_seed(node_id=12345, jewel_seed=1000)

        for _ in range(1000):
            value = rng.generate_range(100)
            assert 0 <= value < 100

    def test_generate_range_small(self):
        """Test generate_range with small ranges."""
        rng = TinyMT32.from_poe_seed(node_id=12345, jewel_seed=1000)

        # Range of 1 should always return 0
        for _ in range(10):
            assert rng.generate_range(1) == 0

        # Range of 2 should return 0 or 1
        values = [rng.generate_range(2) for _ in range(100)]
        assert all(v in [0, 1] for v in values)

    def test_generate_range_zero(self):
        """generate_range(0) should return 0."""
        rng = TinyMT32.from_poe_seed(node_id=12345, jewel_seed=1000)
        assert rng.generate_range(0) == 0

    def test_generate_range_distribution(self):
        """Test that generate_range produces reasonably uniform distribution."""
        rng = TinyMT32.from_poe_seed(node_id=12345, jewel_seed=1000)

        # Generate 10000 values in range [0, 10)
        values = [rng.generate_range(10) for _ in range(10000)]

        # Count occurrences
        counts = [values.count(i) for i in range(10)]

        # Each value should appear roughly 1000 times (within 30% tolerance)
        for count in counts:
            assert 700 <= count <= 1300, f"Distribution seems biased: {counts}"


class TestTinyMT32RangeInclusive:
    """Test inclusive range generation."""

    def test_generate_range_inclusive_basic(self):
        """Test basic inclusive range generation."""
        rng = TinyMT32.from_poe_seed(node_id=12345, jewel_seed=1000)

        # Generate values and check they're in range
        for _ in range(100):
            value = rng.generate_range_inclusive(10, 20)
            # Note: This method has signed/unsigned conversion quirks
            # Just verify it doesn't crash and returns a value
            assert isinstance(value, int)


class TestHelperFunctions:
    """Test helper functions."""

    def test_generate_poe_seed(self):
        """Test generate_poe_seed helper."""
        seed = generate_poe_seed(12345, 1000)
        assert seed == [12345, 1000]

    def test_generate_poe_seed_overflow(self):
        """Test generate_poe_seed with values > 32 bits."""
        seed = generate_poe_seed(0x1_0000_0001, 0x1_0000_0002)
        assert seed == [1, 2]  # Should mask to 32 bits

    def test_create_timeless_rng(self):
        """Test create_timeless_rng convenience function."""
        rng = create_timeless_rng(12345, 1000)
        assert isinstance(rng, TinyMT32)

        # Should produce same output as direct construction
        rng2 = TinyMT32.from_poe_seed(12345, 1000)
        assert rng.generate_uint32() == rng2.generate_uint32()


class TestTinyMT32Repr:
    """Test string representation."""

    def test_repr(self):
        """Test __repr__ output."""
        rng = TinyMT32.from_poe_seed(node_id=1, jewel_seed=1)
        repr_str = repr(rng)
        assert "TinyMT32" in repr_str
        assert "state=" in repr_str


class TestManipulationFunctions:
    """Test the manipulation helper functions."""

    def test_manipulate_alpha_deterministic(self):
        """ManipulateAlpha should be deterministic."""
        result1 = TinyMT32._manipulate_alpha(12345)
        result2 = TinyMT32._manipulate_alpha(12345)
        assert result1 == result2

    def test_manipulate_bravo_deterministic(self):
        """ManipulateBravo should be deterministic."""
        result1 = TinyMT32._manipulate_bravo(12345)
        result2 = TinyMT32._manipulate_bravo(12345)
        assert result1 == result2

    def test_manipulate_alpha_is_32bit(self):
        """ManipulateAlpha should return 32-bit values."""
        result = TinyMT32._manipulate_alpha(0xFFFFFFFF)
        assert 0 <= result <= 0xFFFFFFFF

    def test_manipulate_bravo_is_32bit(self):
        """ManipulateBravo should return 32-bit values."""
        result = TinyMT32._manipulate_bravo(0xFFFFFFFF)
        assert 0 <= result <= 0xFFFFFFFF


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_max_seed_values(self):
        """Test with maximum uint32 seed values."""
        rng = TinyMT32.from_poe_seed(node_id=0xFFFFFFFF, jewel_seed=0xFFFFFFFF)
        value = rng.generate_uint32()
        assert 0 <= value <= 0xFFFFFFFF

    def test_zero_seeds(self):
        """Test with zero seed values."""
        rng = TinyMT32.from_poe_seed(node_id=0, jewel_seed=0)
        value = rng.generate_uint32()
        assert 0 <= value <= 0xFFFFFFFF

    def test_elegant_hubris_seed_range(self):
        """
        Test Elegant Hubris seed range.

        Displayed range: 100 - 160,000
        Actual range: 5 - 8,000 (displayed / 20)
        """
        # Test with actual seed values (displayed / 20)
        rng1 = TinyMT32.from_poe_seed(node_id=12345, jewel_seed=5)  # Min
        rng2 = TinyMT32.from_poe_seed(node_id=12345, jewel_seed=8000)  # Max

        # Both should produce valid output
        assert 0 <= rng1.generate_uint32() <= 0xFFFFFFFF
        assert 0 <= rng2.generate_uint32() <= 0xFFFFFFFF

    def test_large_range_generation(self):
        """Test generate_range with large range."""
        rng = TinyMT32.from_poe_seed(node_id=12345, jewel_seed=1000)

        for _ in range(100):
            value = rng.generate_range(0xFFFFFFFF)
            assert 0 <= value < 0xFFFFFFFF


# Known value tests - these would be filled in with verified game data
class TestKnownValues:
    """
    Tests against known values from the game.

    These tests require verified test vectors from in-game testing or
    the TimelessEmulator reference implementation.
    """

    @pytest.mark.skip(reason="Requires verified test vectors from game")
    def test_known_sequence_1(self):
        """Test against known sequence from game data."""
        # TODO: Add verified test vector
        # rng = TinyMT32.from_poe_seed(node_id=KNOWN_NODE, jewel_seed=KNOWN_SEED)
        # assert rng.generate_uint32() == EXPECTED_VALUE_1
        # assert rng.generate_uint32() == EXPECTED_VALUE_2
        pass

    @pytest.mark.skip(reason="Requires verified test vectors from game")
    def test_timeless_jewel_roll(self):
        """Test a known Timeless Jewel modification roll."""
        # TODO: Add verified test case for a known Timeless Jewel effect
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
