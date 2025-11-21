"""
Unit tests for EHP Calculator

Tests cover:
1. Basic EHP calculations for all damage types
2. PoE2-specific mechanics (chaos vs ES, armor before res, 50% block cap)
3. Hit size analysis and armor breakpoints
4. Defense gap identification
5. Upgrade comparisons
6. Edge cases and validation
"""

import pytest
import logging
from src.calculator.ehp_calculator import (
    EHPCalculator,
    DefensiveStats,
    ThreatProfile,
    DamageType,
    DefenseGap,
    quick_physical_ehp,
    quick_elemental_ehp
)
from src.calculator.defense_calculator import DefenseConstants


class TestDefensiveStats:
    """Test DefensiveStats dataclass."""

    def test_valid_stats(self):
        """Test creating valid defensive stats."""
        stats = DefensiveStats(
            life=5000,
            energy_shield=2000,
            armor=10000,
            fire_res=75
        )

        assert stats.life == 5000
        assert stats.energy_shield == 2000
        assert stats.armor == 10000
        assert stats.fire_res == 75

    def test_minimal_stats(self):
        """Test creating stats with minimal values."""
        stats = DefensiveStats(life=1)
        assert stats.life == 1
        assert stats.energy_shield == 0

    def test_negative_life(self):
        """Test that negative life raises error."""
        with pytest.raises(ValueError, match="Life cannot be negative"):
            DefensiveStats(life=-100)

    def test_negative_es(self):
        """Test that negative ES raises error."""
        with pytest.raises(ValueError, match="Energy Shield cannot be negative"):
            DefensiveStats(life=1000, energy_shield=-500)

    def test_no_hp_pool(self):
        """Test that zero life and ES raises error."""
        with pytest.raises(ValueError, match="Must have some life or energy shield"):
            DefensiveStats(life=0, energy_shield=0)


class TestThreatProfile:
    """Test ThreatProfile dataclass."""

    def test_default_values(self):
        """Test default threat profile."""
        threat = ThreatProfile()
        assert threat.expected_hit_size == 1000.0
        assert threat.attacker_accuracy == 2000.0

    def test_custom_values(self):
        """Test custom threat profile."""
        threat = ThreatProfile(expected_hit_size=5000, attacker_accuracy=3000)
        assert threat.expected_hit_size == 5000
        assert threat.attacker_accuracy == 3000


class TestBasicEHP:
    """Test basic EHP calculations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calc = EHPCalculator()
        self.threat = ThreatProfile(expected_hit_size=1000, attacker_accuracy=2000)

    def test_life_only_no_mitigation(self):
        """Test EHP with only life and no mitigation."""
        stats = DefensiveStats(life=5000)
        result = self.calc.calculate_ehp(stats, DamageType.PHYSICAL, self.threat)

        # With no mitigation, EHP should equal raw HP
        assert result.raw_hp == 5000
        assert result.effective_hp == pytest.approx(5000, rel=1e-2)
        assert result.total_mitigation == pytest.approx(0, abs=1e-2)

    def test_life_with_resistance(self):
        """Test EHP with life and capped resistance."""
        stats = DefensiveStats(life=5000, fire_res=75)
        result = self.calc.calculate_ehp(stats, DamageType.FIRE, self.threat)

        # 75% res = 4× EHP multiplier
        # EHP = 5000 / (1 - 0.75) = 20000
        assert result.raw_hp == 5000
        assert result.effective_hp == pytest.approx(20000, rel=1e-2)
        assert result.total_mitigation == pytest.approx(0.75, abs=1e-2)

    def test_life_es_combined(self):
        """Test EHP with combined life and ES."""
        stats = DefensiveStats(life=4000, energy_shield=2000, fire_res=75)
        result = self.calc.calculate_ehp(stats, DamageType.FIRE, self.threat)

        # Total pool: 6000
        # 75% res = 4× multiplier
        # EHP = 6000 / 0.25 = 24000
        assert result.raw_hp == 6000
        assert result.effective_hp == pytest.approx(24000, rel=1e-2)

    def test_physical_with_armor(self):
        """Test physical EHP with armor."""
        stats = DefensiveStats(life=5000, armor=10000)
        result = self.calc.calculate_ehp(stats, DamageType.PHYSICAL, self.threat)

        # Armor DR vs 1000 damage: 10000 / (10000 + 10*1000) = 50%
        # EHP = 5000 / 0.5 = 10000
        assert result.armor_dr == pytest.approx(0.5, rel=1e-2)
        assert result.effective_hp == pytest.approx(10000, rel=1e-2)

    def test_block_chance(self):
        """Test EHP with block chance."""
        stats = DefensiveStats(life=5000, block_chance=40, fire_res=75)
        result = self.calc.calculate_ehp(stats, DamageType.FIRE, self.threat)

        # Block: 40% avoidance = 1 / 0.6 = 1.667× multiplier
        # Resistance: 75% = 4× multiplier
        # Combined: 1.667 × 4 = 6.667× total
        # EHP = 5000 × 6.667 = 33333
        expected_ehp = 5000 / ((1 - 0.40) * (1 - 0.75))
        assert result.effective_hp == pytest.approx(expected_ehp, rel=1e-2)

    def test_evasion_chance(self):
        """Test EHP with evasion."""
        stats = DefensiveStats(life=5000, evasion=5000, fire_res=75)
        result = self.calc.calculate_ehp(stats, DamageType.FIRE, self.threat)

        # Evasion provides some avoidance
        assert result.evade_mitigation > 0
        # EHP should be higher than resistance alone
        assert result.effective_hp > 20000


class TestPoE2Mechanics:
    """Test PoE2-specific mechanics."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calc = EHPCalculator()
        self.threat = ThreatProfile()

    def test_chaos_es_double_damage(self):
        """Test PoE2 mechanic: chaos removes 2× ES."""
        stats = DefensiveStats(life=3000, energy_shield=2000, chaos_res=0)

        # Vs non-chaos: full ES
        fire_result = self.calc.calculate_ehp(stats, DamageType.FIRE, self.threat)
        assert fire_result.raw_hp == 5000

        # Vs chaos: ES counts as half
        chaos_result = self.calc.calculate_ehp(stats, DamageType.CHAOS, self.threat)
        assert chaos_result.raw_hp == 4000  # 3000 life + 2000/2 ES

    def test_block_cap_50_percent(self):
        """Test PoE2 block cap of 50%."""
        # Block over cap
        stats_over = DefensiveStats(life=5000, block_chance=75, fire_res=75)
        result_over = self.calc.calculate_ehp(stats_over, DamageType.FIRE, self.threat)

        # Block at cap
        stats_cap = DefensiveStats(life=5000, block_chance=50, fire_res=75)
        result_cap = self.calc.calculate_ehp(stats_cap, DamageType.FIRE, self.threat)

        # Both should have same EHP (capped at 50%)
        assert result_over.block_mitigation == pytest.approx(0.5, rel=1e-2)
        assert result_cap.block_mitigation == pytest.approx(0.5, rel=1e-2)
        assert result_over.effective_hp == pytest.approx(result_cap.effective_hp, rel=1e-2)

    def test_armor_before_resistance(self):
        """Test PoE2 mechanic: armor applies before resistance for physical."""
        stats = DefensiveStats(life=5000, armor=10000, fire_res=75)

        # Physical: armor reduces BEFORE resistance (but phys has no res)
        phys_result = self.calc.calculate_ehp(stats, DamageType.PHYSICAL, self.threat)

        # Fire: only resistance applies
        fire_result = self.calc.calculate_ehp(stats, DamageType.FIRE, self.threat)

        # Fire should have higher EHP (75% res vs ~50% armor)
        assert fire_result.effective_hp > phys_result.effective_hp

    def test_armor_scales_with_hit_size(self):
        """Test that armor effectiveness decreases with hit size."""
        stats = DefensiveStats(life=5000, armor=10000)

        # Small hit
        small_threat = ThreatProfile(expected_hit_size=500)
        small_result = self.calc.calculate_ehp(stats, DamageType.PHYSICAL, small_threat)

        # Large hit
        large_threat = ThreatProfile(expected_hit_size=5000)
        large_result = self.calc.calculate_ehp(stats, DamageType.PHYSICAL, large_threat)

        # Armor should be more effective vs small hits
        assert small_result.armor_dr > large_result.armor_dr
        assert small_result.effective_hp > large_result.effective_hp

    def test_resistance_90_hard_cap(self):
        """Test that resistance is capped at 90%."""
        stats = DefensiveStats(life=5000, fire_res=95)  # Over cap
        result = self.calc.calculate_ehp(stats, DamageType.FIRE, self.threat)

        # Should be capped at 90%
        assert result.resistance_dr <= 0.90


class TestLayeredDefenses:
    """Test multiple defense layers working together."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calc = EHPCalculator()
        self.threat = ThreatProfile(expected_hit_size=1000)

    def test_all_layers_physical(self):
        """Test all defense layers for physical damage."""
        stats = DefensiveStats(
            life=5000,
            armor=10000,
            evasion=5000,
            block_chance=40
        )

        result = self.calc.calculate_ehp(stats, DamageType.PHYSICAL, self.threat)

        # All layers should contribute
        assert result.evade_mitigation > 0
        assert result.block_mitigation > 0
        assert result.armor_dr > 0
        assert result.total_mitigation > 0.5  # Should have good total mitigation

    def test_all_layers_elemental(self):
        """Test all defense layers for elemental damage."""
        stats = DefensiveStats(
            life=5000,
            energy_shield=2000,
            evasion=5000,
            block_chance=40,
            fire_res=75
        )

        result = self.calc.calculate_ehp(stats, DamageType.FIRE, self.threat)

        # Evasion, block, and resistance should all contribute
        assert result.evade_mitigation > 0
        assert result.block_mitigation > 0
        assert result.resistance_dr == pytest.approx(0.75)

    def test_multiplicative_layering(self):
        """Test that defense layers multiply (not add)."""
        stats = DefensiveStats(life=5000, block_chance=40, fire_res=50)

        result = self.calc.calculate_ehp(stats, DamageType.FIRE, self.threat)

        # 40% block + 50% res ≠ 90% mitigation
        # Correct: 1 - (0.6 × 0.5) = 70% mitigation
        expected_mitigation = 1 - (0.6 * 0.5)
        assert result.total_mitigation == pytest.approx(expected_mitigation, rel=1e-2)


class TestHitSizeAnalysis:
    """Test hit size analysis features."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calc = EHPCalculator()
        self.stats = DefensiveStats(life=5000, armor=20000)

    def test_analyze_armor_vs_hit_sizes(self):
        """Test armor analysis against multiple hit sizes."""
        analysis = self.calc.analyze_armor_vs_hit_sizes(self.stats)

        # Should have multiple hit sizes
        assert len(analysis) > 0

        # DR should decrease as hit size increases
        hit_sizes = sorted(analysis.keys())
        drs = [analysis[h]['dr_percent'] for h in hit_sizes]

        for i in range(len(drs) - 1):
            assert drs[i] >= drs[i + 1]  # DR decreases or stays same

    def test_custom_hit_sizes(self):
        """Test armor analysis with custom hit sizes."""
        custom_sizes = [100, 500, 2000]
        analysis = self.calc.analyze_armor_vs_hit_sizes(self.stats, custom_sizes)

        assert len(analysis) == 3
        assert 100 in analysis
        assert 500 in analysis
        assert 2000 in analysis

    def test_find_armor_breakpoints(self):
        """Test finding armor breakpoints."""
        breakpoints = self.calc.find_armor_breakpoints(self.stats)

        # Should have multiple breakpoints
        assert len(breakpoints) > 0

        # Required armor should increase with target DR
        drs = sorted(breakpoints.keys())
        armors = [breakpoints[dr] for dr in drs]

        for i in range(len(armors) - 1):
            # Each higher DR should need more armor (or be infinite)
            if armors[i] != float('inf') and armors[i + 1] != float('inf'):
                assert armors[i] <= armors[i + 1]

    def test_armor_breakpoint_90_percent_unreachable(self):
        """Test that 90% DR breakpoint is recognized as cap."""
        breakpoints = self.calc.find_armor_breakpoints(self.stats, [90.0])

        # 90% is at the cap, should be possible but very high
        assert 90.0 in breakpoints


class TestDefenseGaps:
    """Test defense gap identification."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calc = EHPCalculator()
        self.threat = ThreatProfile()

    def test_uncapped_resistance_gap(self):
        """Test identification of uncapped resistances."""
        stats = DefensiveStats(
            life=5000,
            fire_res=50,  # 25% below cap
            cold_res=75,
            lightning_res=75,
            chaos_res=0
        )

        gaps = self.calc.identify_defense_gaps(stats, self.threat)

        # Should identify fire res gap
        fire_gaps = [g for g in gaps if 'fire' in g.gap_type]
        assert len(fire_gaps) > 0

        fire_gap = fire_gaps[0]
        assert fire_gap.current_value == 50
        assert fire_gap.recommended_value == 75

    def test_low_hp_pool_gap(self):
        """Test identification of low HP pool."""
        stats = DefensiveStats(
            life=2000,  # Very low
            fire_res=75,
            cold_res=75,
            lightning_res=75
        )

        gaps = self.calc.identify_defense_gaps(stats, self.threat)

        # Should identify low HP
        hp_gaps = [g for g in gaps if 'low_hp' in g.gap_type]
        assert len(hp_gaps) > 0

    def test_no_layered_defenses_gap(self):
        """Test identification of missing defense layers."""
        stats = DefensiveStats(
            life=5000,
            armor=0,
            evasion=0,
            block_chance=0,
            energy_shield=0,
            fire_res=75,
            cold_res=75,
            lightning_res=75
        )

        gaps = self.calc.identify_defense_gaps(stats, self.threat)

        # Should identify lack of layers
        layer_gaps = [g for g in gaps if 'layered' in g.gap_type or 'layer' in g.gap_type]
        assert len(layer_gaps) > 0

    def test_overcapped_block_gap(self):
        """Test identification of wasted block chance."""
        stats = DefensiveStats(
            life=5000,
            block_chance=70,  # 20% over cap
            fire_res=75,
            cold_res=75,
            lightning_res=75
        )

        gaps = self.calc.identify_defense_gaps(stats, self.threat)

        # Should identify overcapped block
        block_gaps = [g for g in gaps if 'block' in g.gap_type]
        assert len(block_gaps) > 0

        block_gap = block_gaps[0]
        assert block_gap.current_value == 70
        assert block_gap.recommended_value == 50

    def test_negative_chaos_res_gap(self):
        """Test identification of negative chaos resistance."""
        stats = DefensiveStats(
            life=5000,
            fire_res=75,
            cold_res=75,
            lightning_res=75,
            chaos_res=-60  # Very negative
        )

        gaps = self.calc.identify_defense_gaps(stats, self.threat)

        # Should identify negative chaos res
        chaos_gaps = [g for g in gaps if 'chaos' in g.gap_type]
        assert len(chaos_gaps) > 0

    def test_gaps_sorted_by_severity(self):
        """Test that gaps are sorted by severity."""
        stats = DefensiveStats(
            life=2000,  # Low HP (high severity)
            fire_res=70,  # Slightly low (lower severity)
            cold_res=75,
            lightning_res=75,
            chaos_res=-20
        )

        gaps = self.calc.identify_defense_gaps(stats, self.threat)

        # Gaps should be sorted by severity (descending)
        for i in range(len(gaps) - 1):
            assert gaps[i].severity >= gaps[i + 1].severity

    def test_good_build_minimal_gaps(self):
        """Test that a good build has minimal gaps."""
        stats = DefensiveStats(
            life=5500,
            energy_shield=1500,
            armor=12000,
            block_chance=45,
            fire_res=75,
            cold_res=75,
            lightning_res=75,
            chaos_res=20
        )

        gaps = self.calc.identify_defense_gaps(stats, self.threat)

        # Should have few or no high-severity gaps
        critical_gaps = [g for g in gaps if g.severity >= 7]
        assert len(critical_gaps) == 0


class TestComparisons:
    """Test upgrade comparison features."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calc = EHPCalculator()
        self.threat = ThreatProfile()

    def test_compare_armor_upgrade(self):
        """Test comparing armor upgrade."""
        current = DefensiveStats(life=5000, armor=10000)
        upgraded = DefensiveStats(life=5000, armor=15000)

        comparison = self.calc.compare_upgrade(current, upgraded, self.threat)

        # Physical EHP should increase
        assert comparison['physical']['absolute_gain'] > 0
        assert comparison['physical']['percent_gain'] > 0

    def test_compare_resistance_upgrade(self):
        """Test comparing resistance upgrade."""
        current = DefensiveStats(life=5000, fire_res=70)
        upgraded = DefensiveStats(life=5000, fire_res=75)

        comparison = self.calc.compare_upgrade(current, upgraded, self.threat)

        # Fire EHP should increase significantly (capping res is powerful)
        assert comparison['fire']['absolute_gain'] > 0
        assert comparison['fire']['percent_gain'] > 10  # Should be meaningful gain

    def test_compare_life_upgrade(self):
        """Test comparing life upgrade."""
        current = DefensiveStats(life=4500, fire_res=75)
        upgraded = DefensiveStats(life=5000, fire_res=75)

        comparison = self.calc.compare_upgrade(current, upgraded, self.threat)

        # All damage types should benefit equally from life
        phys_gain = comparison['physical']['percent_gain']
        fire_gain = comparison['fire']['percent_gain']

        # Gains should be similar (within 1% due to rounding)
        assert abs(phys_gain - fire_gain) < 1

    def test_calculate_defense_value(self):
        """Test calculating value of defense increase."""
        stats = DefensiveStats(life=5000, armor=10000, fire_res=75)

        # Test armor value
        armor_value = self.calc.calculate_defense_value(
            stats, 'armor', 5000, self.threat
        )

        assert 'physical_ehp_gain' in armor_value
        assert armor_value['physical_ehp_gain'] > 0

        # Test resistance value
        res_value = self.calc.calculate_defense_value(
            stats, 'fire_res', 5, self.threat
        )

        assert 'fire_ehp_gain' in res_value

    def test_invalid_defense_type(self):
        """Test that invalid defense type raises error."""
        stats = DefensiveStats(life=5000)

        with pytest.raises(ValueError, match="Unknown defense type"):
            self.calc.calculate_defense_value(
                stats, 'invalid_type', 100, self.threat
            )


class TestAllEHP:
    """Test calculating EHP for all damage types."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calc = EHPCalculator()
        self.threat = ThreatProfile()

    def test_calculate_all_ehp(self):
        """Test calculating EHP for all damage types."""
        stats = DefensiveStats(
            life=5000,
            armor=10000,
            fire_res=75,
            cold_res=75,
            lightning_res=75,
            chaos_res=0
        )

        results = self.calc.calculate_all_ehp(stats, self.threat)

        # Should have result for each damage type
        assert len(results) == len(DamageType)
        for damage_type in DamageType:
            assert damage_type in results

    def test_elemental_ehp_similar(self):
        """Test that elemental EHP is similar when resistances are equal."""
        stats = DefensiveStats(
            life=5000,
            fire_res=75,
            cold_res=75,
            lightning_res=75
        )

        results = self.calc.calculate_all_ehp(stats, self.threat)

        fire_ehp = results[DamageType.FIRE].effective_hp
        cold_ehp = results[DamageType.COLD].effective_hp
        lightning_ehp = results[DamageType.LIGHTNING].effective_hp

        # All three should be very similar
        assert fire_ehp == pytest.approx(cold_ehp, rel=1e-2)
        assert fire_ehp == pytest.approx(lightning_ehp, rel=1e-2)

    def test_chaos_lower_with_es(self):
        """Test that chaos EHP is lower when relying on ES."""
        stats = DefensiveStats(
            life=3000,
            energy_shield=2000,
            fire_res=75,
            chaos_res=0
        )

        results = self.calc.calculate_all_ehp(stats, self.threat)

        # Chaos should have lower raw HP due to 2× ES damage
        chaos_result = results[DamageType.CHAOS]
        fire_result = results[DamageType.FIRE]

        assert chaos_result.raw_hp < fire_result.raw_hp


class TestQuickFunctions:
    """Test convenience quick calculation functions."""

    def test_quick_physical_ehp(self):
        """Test quick physical EHP calculation."""
        ehp = quick_physical_ehp(life=5000, armor=10000, block_chance=40, hit_size=1000)

        assert ehp > 0
        assert ehp > 5000  # Should be higher than raw HP

    def test_quick_elemental_ehp(self):
        """Test quick elemental EHP calculation."""
        ehp = quick_elemental_ehp(life=5000, resistance=75, block_chance=40)

        assert ehp > 0
        assert ehp > 20000  # 75% res = ~4× multiplier, block adds more

    def test_quick_functions_match_full_calc(self):
        """Test that quick functions match full calculation."""
        calc = EHPCalculator()

        # Test physical
        stats = DefensiveStats(life=5000, armor=10000, block_chance=40)
        threat = ThreatProfile(expected_hit_size=1000)

        full_result = calc.calculate_ehp(stats, DamageType.PHYSICAL, threat)
        quick_result = quick_physical_ehp(5000, 10000, 40, 1000)

        assert full_result.effective_hp == pytest.approx(quick_result, rel=1e-2)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calc = EHPCalculator()
        self.threat = ThreatProfile()

    def test_zero_armor_vs_physical(self):
        """Test physical EHP with zero armor."""
        stats = DefensiveStats(life=5000, armor=0)
        result = self.calc.calculate_ehp(stats, DamageType.PHYSICAL, self.threat)

        assert result.armor_dr == 0
        assert result.effective_hp == 5000

    def test_zero_evasion(self):
        """Test EHP with zero evasion."""
        stats = DefensiveStats(life=5000, evasion=0)
        result = self.calc.calculate_ehp(stats, DamageType.PHYSICAL, self.threat)

        assert result.evade_mitigation == 0

    def test_maximum_mitigation(self):
        """Test near-maximum mitigation doesn't cause overflow."""
        stats = DefensiveStats(
            life=5000,
            armor=100000,  # Very high armor
            block_chance=50,
            fire_res=90  # At hard cap
        )

        threat = ThreatProfile(expected_hit_size=100)  # Small hit (high armor DR)

        result = self.calc.calculate_ehp(stats, DamageType.FIRE, threat)

        # Should have very high EHP but not infinite
        assert result.effective_hp > 100000
        assert result.effective_hp != float('inf')

    def test_negative_resistance(self):
        """Test EHP with negative resistance."""
        stats = DefensiveStats(life=5000, fire_res=-60)
        result = self.calc.calculate_ehp(stats, DamageType.FIRE, self.threat)

        # Negative res means taking more damage, so EHP < raw HP
        assert result.effective_hp < result.raw_hp

    def test_very_large_hit(self):
        """Test armor effectiveness against very large hits."""
        stats = DefensiveStats(life=5000, armor=50000)
        threat = ThreatProfile(expected_hit_size=50000)  # Enormous hit

        result = self.calc.calculate_ehp(stats, DamageType.PHYSICAL, threat)

        # Armor should provide minimal DR vs huge hits
        assert result.armor_dr < 0.6  # Less than 60% DR


class TestLayersBreakdown:
    """Test detailed breakdown in EHP results."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calc = EHPCalculator()
        self.threat = ThreatProfile()

    def test_breakdown_structure(self):
        """Test that breakdown has correct structure."""
        stats = DefensiveStats(
            life=5000,
            armor=10000,
            evasion=5000,
            block_chance=40,
            fire_res=75
        )

        result = self.calc.calculate_ehp(stats, DamageType.PHYSICAL, self.threat)

        # Check breakdown exists
        assert 'raw_hp' in result.layers_breakdown
        assert 'evasion' in result.layers_breakdown
        assert 'block' in result.layers_breakdown
        assert 'armor' in result.layers_breakdown
        assert 'resistance' in result.layers_breakdown
        assert 'combined' in result.layers_breakdown

    def test_breakdown_multipliers(self):
        """Test that breakdown multipliers are calculated correctly."""
        stats = DefensiveStats(life=5000, fire_res=75)
        result = self.calc.calculate_ehp(stats, DamageType.FIRE, self.threat)

        # 75% res should give 4× multiplier
        res_multiplier = result.layers_breakdown['resistance']['multiplier']
        assert res_multiplier == pytest.approx(4.0, rel=1e-2)


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v', '--tb=short'])
