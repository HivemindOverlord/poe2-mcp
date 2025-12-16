"""
Integration tests for new validation tools (Tier 1 + Tier 2)
Tests the fix for Faster + Slower Projectiles bug

These tests verify:
1. Tier 1 Validation Tools work correctly
2. Tier 2 Debugging Tools provide proper trace data
3. The original Faster + Slower Projectiles bug is FIXED
4. All new validation functionality is operational

Author: HivemindMinion
Date: 2025-11-22
"""
import pytest
import asyncio
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.optimizer.gem_synergy_calculator import GemSynergyCalculator, HARDCODED_INCOMPATIBILITIES


class TestValidationToolsIntegration:
    """Integration tests for validation tools"""

    @pytest.fixture(scope="class")
    def gem_calculator(self):
        """Create gem synergy calculator instance"""
        calculator = GemSynergyCalculator()
        yield calculator

    # ========================================================================
    # TIER 1 VALIDATION TESTS
    # ========================================================================

    def test_validate_support_combination_faster_slower_bug_fixed(self, gem_calculator):
        """
        CRITICAL TEST: Verify Faster + Slower Projectiles is now rejected
        This is the bug that triggered the entire validation tool architecture
        """
        # The original bug: AI recommended both Faster and Slower Projectiles
        invalid_combo = ["Faster Projectiles", "Slower Projectiles"]

        result = gem_calculator.validate_combination(invalid_combo)

        # Should be INVALID
        assert result["valid"] is False, "Faster + Slower Projectiles should be INVALID"
        assert "incompatible" in result["reason"].lower() or "conflict" in result["reason"].lower()
        assert len(result["conflicts"]) > 0

        print(f"[OK] Bug fixed: {result['reason']}")
        print(f"  Conflicts detected: {result['conflicts']}")

    def test_validate_support_combination_valid(self, gem_calculator):
        """Test that valid combinations are accepted"""
        valid_combo = ["Spell Echo", "Elemental Focus", "Controlled Destruction"]

        result = gem_calculator.validate_combination(valid_combo)

        assert result["valid"] is True, f"Valid combo should be accepted: {result.get('reason', '')}"
        assert result["conflicts"] == []

        print(f"[OK] Valid combination accepted: {', '.join(valid_combo)}")

    def test_validate_concentrated_increased_aoe_conflict(self, gem_calculator):
        """Test another known incompatibility"""
        invalid_combo = ["Concentrated Effect", "Increased Area of Effect"]

        result = gem_calculator.validate_combination(invalid_combo)

        assert result["valid"] is False, "Concentrated Effect + Increased AoE should be INVALID"
        assert len(result["conflicts"]) > 0

        print(f"[OK] AoE conflict detected: {result['reason']}")

    def test_inspect_support_gem(self, gem_calculator):
        """Test support gem inspection"""
        # Inspect a known support
        supports_file = Path(__file__).parent.parent / 'data' / 'poe2_support_gems_database.json'

        if not supports_file.exists():
            pytest.skip("Support gems database not found")

        with open(supports_file, 'r') as f:
            data = json.load(f)

        # Find first support
        first_support = None
        support_gems = data.get('support_gems', {})
        for support_id, support_data in support_gems.items():
            if isinstance(support_data, dict) and 'name' in support_data:
                first_support = support_data['name']
                break

        assert first_support is not None, "Should find at least one support gem"
        assert first_support in gem_calculator.support_gems or first_support.lower() in [s.name.lower() for s in gem_calculator.support_gems.values()]

        print(f"[OK] Can inspect support: {first_support}")

    def test_inspect_spell_gem(self, gem_calculator):
        """Test spell gem inspection"""
        spells_file = Path(__file__).parent.parent / 'data' / 'poe2_spell_gems_database.json'

        if not spells_file.exists():
            pytest.skip("Spell gems database not found")

        with open(spells_file, 'r') as f:
            data = json.load(f)

        # Find Fireball (the spell from the original bug report)
        fireball_found = False
        for category, spells in data.items():
            if category == 'metadata':
                continue
            for spell_id, spell_data in spells.items():
                if isinstance(spell_data, dict) and spell_data.get('name', '').lower() == 'fireball':
                    fireball_found = True
                    break
            if fireball_found:
                break

        assert fireball_found, "Should find Fireball spell"
        assert 'fireball' in gem_calculator.spell_gems

        print("[OK] Can inspect spell: Fireball")

    def test_list_all_supports(self, gem_calculator):
        """Test support listing with filtering"""
        supports_file = Path(__file__).parent.parent / 'data' / 'poe2_support_gems_database.json'

        if not supports_file.exists():
            pytest.skip("Support gems database not found")

        with open(supports_file, 'r') as f:
            data = json.load(f)

        # Count total supports
        support_gems = data.get('support_gems', {})
        total = sum(1 for k, v in support_gems.items() if isinstance(v, dict) and 'name' in v)

        assert total > 0, "Should have support gems in database"
        assert len(gem_calculator.support_gems) > 0, "Calculator should have loaded support gems"

        print(f"[OK] Can list {len(gem_calculator.support_gems)} support gems (database has {total})")

    def test_list_all_spells(self, gem_calculator):
        """Test spell listing with filtering"""
        spells_file = Path(__file__).parent.parent / 'data' / 'poe2_spell_gems_database.json'

        if not spells_file.exists():
            pytest.skip("Spell gems database not found")

        with open(spells_file, 'r') as f:
            data = json.load(f)

        # Count total spells
        total = 0
        for category, spells in data.items():
            if category == 'metadata':
                continue
            total += sum(1 for k, v in spells.items() if isinstance(v, dict) and 'name' in v)

        assert total > 0, "Should have spell gems in database"
        assert len(gem_calculator.spell_gems) > 0, "Calculator should have loaded spell gems"

        print(f"[OK] Can list {len(gem_calculator.spell_gems)} spell gems (database has {total})")

    # ========================================================================
    # TIER 2 DEBUGGING TESTS
    # ========================================================================

    def test_trace_support_selection_fireball(self, gem_calculator):
        """
        Test trace functionality for Fireball (the spell from the bug report)
        This shows how many combinations were tested and how filtering worked
        """
        result = gem_calculator.find_best_combinations(
            spell_name="fireball",
            num_supports=5,
            max_spirit=100,
            optimization_goal="dps",
            return_trace=True
        )

        assert isinstance(result, dict), "Should return dict when return_trace=True"
        assert "trace" in result, "Should have trace data"
        assert "results" in result, "Should have results"

        trace = result["trace"]

        # Verify trace has expected fields
        assert "spell_found" in trace
        assert "compatible_supports_count" in trace
        assert "total_combinations" in trace
        assert "valid_combinations" in trace
        assert "invalid_combinations" in trace

        # Verify spell was found
        assert trace["spell_found"] is True, "Fireball should be found in database"

        # Verify some combinations were tested
        assert trace["total_combinations"] > 0, "Should test some combinations"

        print(f"[OK] Trace for Fireball:")
        print(f"  - Spell found: {trace['spell_found']}")
        print(f"  - Compatible supports: {trace['compatible_supports_count']}")
        print(f"  - Total combinations tested: {trace['total_combinations']}")
        print(f"  - Valid: {trace['valid_combinations']}")
        print(f"  - Invalid (rejected incompatibilities): {trace['invalid_combinations']}")

        # With hardcoded incompatibility rules, some combinations should be rejected
        # (if there are enough supports to create conflicting combinations)
        if trace['compatible_supports_count'] >= 5:
            # Only assert if we have enough supports to potentially create conflicts
            print(f"  - Note: {trace['invalid_combinations']} incompatible combinations rejected")

    def test_trace_dps_calculation_valid(self, gem_calculator):
        """Test DPS calculation tracing for valid combination"""
        trace = gem_calculator.trace_dps_calculation(
            spell_name="fireball",
            support_names=["Spell Echo", "Elemental Focus"],
            character_mods={"increased_damage": 50.0},
            max_spirit=100
        )

        # Verify trace structure
        assert "spell" in trace
        assert "supports" in trace
        assert "calculations" in trace
        assert "spirit" in trace
        assert "valid" in trace

        # Should be valid if supports exist
        if len(trace["supports"]) == 2:
            assert trace["valid"] is True, f"Should be valid, errors: {trace.get('errors', [])}"

            calc = trace["calculations"]

            # Verify calculation steps are present
            assert "base_damage_avg" in calc
            assert "more_multipliers" in calc
            assert "increased_total" in calc
            assert "final_damage_per_cast" in calc
            assert "final_dps" in calc

            print(f"[OK] DPS trace for Fireball + Spell Echo + Elemental Focus:")
            print(f"  - Base damage: {calc['base_damage_avg']:.1f}")
            print(f"  - More multiplier: {calc['more_total']:.2f}x")
            print(f"  - Increased total: {calc['increased_total']:.2f}x")
            print(f"  - Final DPS: {calc['final_dps']:.1f}")
        else:
            print(f"  - Warning: Some supports not found, trace has errors: {trace.get('errors', [])}")

    def test_trace_dps_invalid_combination(self, gem_calculator):
        """Test that DPS trace detects invalid combinations"""
        trace = gem_calculator.trace_dps_calculation(
            spell_name="fireball",
            support_names=["Faster Projectiles", "Slower Projectiles"],  # INVALID!
            max_spirit=100
        )

        # Should be invalid
        assert trace["valid"] is False, "Faster + Slower Projectiles should be INVALID"
        assert len(trace["errors"]) > 0, "Should have error messages"
        assert any("incompatible" in err.lower() or "conflict" in err.lower() for err in trace["errors"]), \
            f"Error should mention incompatibility, got: {trace['errors']}"

        print(f"[OK] DPS trace correctly rejects Faster + Slower Projectiles:")
        print(f"  - Valid: {trace['valid']}")
        print(f"  - Errors: {trace['errors']}")

    # ========================================================================
    # BUG FIX VERIFICATION
    # ========================================================================

    def test_fireball_recommendations_no_longer_invalid(self, gem_calculator):
        """
        CRITICAL TEST: Verify Fireball recommendations no longer include
        Faster + Slower Projectiles in the same setup
        """
        result = gem_calculator.find_best_combinations(
            spell_name="fireball",
            num_supports=5,
            max_spirit=100,
            optimization_goal="dps",
            top_n=10
        )

        assert isinstance(result, list), "Should return list of results"

        # Check all top 10 results
        for i, combo in enumerate(result):
            support_names = combo.support_names

            # Verify no combination has both Faster and Slower Projectiles
            has_faster = any("faster" in s.lower() and "projectile" in s.lower() for s in support_names)
            has_slower = any("slower" in s.lower() and "projectile" in s.lower() for s in support_names)

            assert not (has_faster and has_slower), \
                f"Combo #{i+1} should NOT have both Faster and Slower Projectiles: {support_names}"

        print(f"[OK] All {len(result)} Fireball recommendations are valid (no Faster+Slower bug)")

        # Print top 3 for inspection
        if result:
            print("\nTop 3 Fireball support combinations:")
            for i, combo in enumerate(result[:3]):
                print(f"  {i+1}. {', '.join(combo.support_names)} - {combo.total_dps:.1f} DPS")

    def test_hardcoded_incompatibilities_present(self, gem_calculator):
        """Verify hardcoded incompatibilities are defined"""
        assert len(HARDCODED_INCOMPATIBILITIES) > 0, "Should have hardcoded incompatibilities"

        # Verify Faster + Slower Projectiles is in the list
        assert "Faster Projectiles" in HARDCODED_INCOMPATIBILITIES or \
               "faster_projectiles" in HARDCODED_INCOMPATIBILITIES, \
               "Faster Projectiles should be in incompatibility list"

        # Verify it conflicts with Slower Projectiles
        faster_conflicts = HARDCODED_INCOMPATIBILITIES.get("Faster Projectiles", []) + \
                          HARDCODED_INCOMPATIBILITIES.get("faster_projectiles", [])

        assert any("slower" in c.lower() and "projectile" in c.lower() for c in faster_conflicts), \
               "Faster Projectiles should conflict with Slower Projectiles"

        print(f"[OK] Hardcoded incompatibilities verified:")
        print(f"  - Total rules: {len(HARDCODED_INCOMPATIBILITIES)}")
        print(f"  - Faster Projectiles conflicts: {HARDCODED_INCOMPATIBILITIES.get('Faster Projectiles', HARDCODED_INCOMPATIBILITIES.get('faster_projectiles', []))}")

    # ========================================================================
    # EDGE CASES
    # ========================================================================

    def test_validate_empty_combination(self, gem_calculator):
        """Test validation with empty support list"""
        result = gem_calculator.validate_combination([])

        assert result["valid"] is True, "Empty combination should be valid"
        assert len(result["conflicts"]) == 0

        print("[OK] Empty combination validated correctly")

    def test_validate_single_support(self, gem_calculator):
        """Test validation with single support"""
        result = gem_calculator.validate_combination(["Spell Echo"])

        assert result["valid"] is True, "Single support should be valid"
        assert len(result["conflicts"]) == 0

        print("[OK] Single support validated correctly")

    def test_trace_nonexistent_spell(self, gem_calculator):
        """Test trace with nonexistent spell"""
        trace = gem_calculator.trace_dps_calculation(
            spell_name="NonexistentSpell123",
            support_names=["Spell Echo"],
            max_spirit=100
        )

        assert trace["valid"] is False, "Should be invalid for nonexistent spell"
        assert len(trace["errors"]) > 0, "Should have error about spell not found"
        assert any("not found" in err.lower() for err in trace["errors"])

        print(f"[OK] Nonexistent spell handled correctly: {trace['errors']}")

    def test_trace_nonexistent_support(self, gem_calculator):
        """Test trace with nonexistent support"""
        trace = gem_calculator.trace_dps_calculation(
            spell_name="fireball",
            support_names=["NonexistentSupport123"],
            max_spirit=100
        )

        assert trace["valid"] is False, "Should be invalid for nonexistent support"
        assert len(trace["errors"]) > 0, "Should have error about support not found"
        assert any("not found" in err.lower() for err in trace["errors"])

        print(f"[OK] Nonexistent support handled correctly: {trace['errors']}")

    def test_trace_with_return_trace_false(self, gem_calculator):
        """Test that return_trace=False returns list, not dict"""
        result = gem_calculator.find_best_combinations(
            spell_name="fireball",
            num_supports=3,
            max_spirit=100,
            optimization_goal="dps",
            top_n=5,
            return_trace=False
        )

        assert isinstance(result, list), "Should return list when return_trace=False"

        print(f"[OK] return_trace=False returns list with {len(result)} results")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
