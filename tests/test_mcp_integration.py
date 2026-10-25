"""
Integration tests for MCP server enhancements.

Tests the integration of reverse-engineered extractors with MCP tools.
"""

import asyncio
import sys
from pathlib import Path

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mcp_server import PoE2BuildOptimizerMCP


class TestMCPIntegration:
    """Test MCP server with extractor integration."""

    @pytest_asyncio.fixture
    async def mcp_server(self):
        """Create and initialize MCP server."""
        server = PoE2BuildOptimizerMCP()
        await server.initialize()
        yield server
        await server.cleanup()

    @pytest.mark.asyncio
    async def test_inspect_support_gem(self, mcp_server):
        """Test inspect_support_gem output against the canonical 0.5 dataset.

        The canonical extraction (data-v0.5.0-r10) carries compatibility and
        provenance but NOT effects/requirements (empty in support_gems v1) —
        assert what the data can actually express."""
        result = await mcp_server._handle_inspect_support_gem(
            {"support_name": "Controlled Destruction"}
        )

        assert len(result) == 1
        text = result[0].text

        assert "Controlled Destruction" in text
        assert "not found" not in text.lower()
        assert "**Compatible With**:" in text
        # Provenance footer — the versioned data tag callers rely on
        assert "**Data**:" in text
        assert "**Tier**: canonical" in text
        assert "support_gems.json" in text

    @pytest.mark.asyncio
    async def test_list_all_supports(self, mcp_server):
        """Test list_all_supports listing format and pagination."""
        result = await mcp_server._handle_list_all_supports({"sort_by": "tier", "limit": 10})

        assert len(result) == 1
        text = result[0].text

        assert "Support Gems" in text
        assert "(Tier" in text
        assert "Spirit:" in text
        # Pagination hint present when more results exist (680 gems total)
        assert "offset=" in text

    @pytest.mark.asyncio
    async def test_inspect_spell_gem(self, mcp_server):
        """Test inspect_spell_gem renders the canonical per-level gem data."""
        result = await mcp_server._handle_inspect_spell_gem({"spell_name": "Fireball"})

        assert len(result) == 1
        text = result[0].text

        assert "Fireball" in text
        assert "Gem Type: Spell" in text
        assert "**Cast Time**:" in text
        assert "**Per-Level Stats**" in text
        # Base damage now surfaces as per-level scaling stats
        assert "spell_minimum_base_fire_damage" in text
        # Provenance footer
        assert "**Data**:" in text
        assert "skill_gems.json" in text

    @pytest.mark.asyncio
    async def test_list_all_spells(self, mcp_server):
        """Test list_all_spells filtered listing format."""
        result = await mcp_server._handle_list_all_spells({"filter_element": "fire", "limit": 5})

        assert len(result) == 1
        text = result[0].text

        assert "Spell Gems" in text
        assert "(Fire)" in text
        assert "Cast:" in text
        assert "Mana:" in text
        assert "Tags:" in text

    @pytest.mark.asyncio
    async def test_optimize_passives_with_extractor(self, mcp_server):
        """Test optimize_passives uses passive tree extractor."""
        result = await mcp_server._handle_optimize_passives(
            {"character_data": {"class": "Warrior"}, "available_points": 5, "goal": "damage"}
        )

        assert len(result) == 1
        text = result[0].text

        # Should have passive tree optimization response
        assert "passive" in text.lower() or "tree" in text.lower() or "allocation" in text.lower()

    @pytest.mark.asyncio
    async def test_passive_optimizer_defensive(self, mcp_server):
        """Test passive optimizer with defensive goal."""
        if not mcp_server.passive_optimizer:
            pytest.skip("Passive optimizer not initialized")

        recommendations = await mcp_server.passive_optimizer.optimize(
            character_data={"class": "Tank"}, available_points=3, goal="defense"
        )

        assert "suggested_allocations" in recommendations
        assert isinstance(recommendations["suggested_allocations"], list)

        # Should have defensive recommendations
        if recommendations["suggested_allocations"]:
            first_rec = recommendations["suggested_allocations"][0]
            assert "name" in first_rec
            assert "benefit" in first_rec or "type" in first_rec

    @pytest.mark.asyncio
    async def test_extractors_initialized(self, mcp_server):
        """Test that core data components are properly initialized.

        The standalone reverse-engineering extractors (stat/active-skill/
        text/passive-tree) were replaced by the resolver + fresh-data
        pipeline — verify the components the handlers actually use."""
        assert hasattr(mcp_server, "passive_tree_resolver")
        assert mcp_server.passive_tree_resolver is not None
        assert hasattr(mcp_server, "gem_synergy_calculator")
        assert hasattr(mcp_server, "db_manager")

    @pytest.mark.asyncio
    async def test_support_gem_json_structure(self, mcp_server):
        """Test that support gem JSON is accessed correctly.

        Uses Spell Echo — Faster Projectiles is a PoE1 gem that doesn't
        exist in the PoE2 0.5 dataset. Also locks the suffix-tolerant
        lookup ("Spell Echo" resolving "Spell Echo Support")."""
        result = await mcp_server._handle_inspect_support_gem({"support_name": "Spell Echo"})

        assert len(result) == 1
        text = result[0].text
        assert "Spell Echo" in text
        # Should not show "not found" error
        assert "not found" not in text.lower()

    @pytest.mark.asyncio
    async def test_spell_gem_json_structure(self, mcp_server):
        """Test that spell gem JSON is accessed correctly."""
        # Test with a known spell
        result = await mcp_server._handle_inspect_spell_gem({"spell_name": "Lightning Bolt"})

        assert len(result) == 1
        text = result[0].text
        # Should find the spell or return proper error
        assert "Lightning" in text or "not found" in text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
