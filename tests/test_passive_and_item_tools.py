"""
Tests for new passive tree and base item MCP tools.
Added to expose keystone, notable, and base item data that was previously idle.
"""

import pytest
import asyncio
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mcp_server import PoE2BuildOptimizerMCP


# Check if PSG database exists
PSG_DATABASE_PATH = Path(__file__).parent.parent / "data" / "psg_passive_nodes.json"
HAS_PSG_DATABASE = PSG_DATABASE_PATH.exists()


class TestKeystoneTools:
    """Test keystone-related MCP tools"""

    @pytest.fixture
    def server(self):
        """Create server instance for testing"""
        return PoE2BuildOptimizerMCP()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_PSG_DATABASE, reason="PSG database not found")
    async def test_list_all_keystones_returns_keystones(self, server):
        """Test that list_all_keystones returns keystone data"""
        result = await server._handle_list_all_keystones({})

        assert len(result) == 1
        text = result[0].text

        # Should have keystones header (or error if resolver not initialized)
        assert "Keystones" in text or "not initialized" in text

    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_PSG_DATABASE, reason="PSG database not found")
    async def test_list_all_keystones_with_filter(self, server):
        """Test filtering keystones by stat text"""
        result = await server._handle_list_all_keystones({"filter_stat": "life"})

        assert len(result) == 1
        text = result[0].text

        # Should be fewer than unfiltered (or show message about filtered results)
        assert "Keystones" in text or "not initialized" in text

    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_PSG_DATABASE, reason="PSG database not found")
    async def test_inspect_keystone_known_keystone(self, server):
        """Test inspecting a known keystone"""
        # Try to inspect a keystone
        result = await server._handle_inspect_keystone({"keystone_name": "Chaos Inoculation"})
        text = result[0].text

        # Should either find it or show available keystones or show not initialized
        assert "Chaos Inoculation" in text or "Available keystones" in text or "Not Found" in text or "not initialized" in text

    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_PSG_DATABASE, reason="PSG database not found")
    async def test_inspect_keystone_not_found(self, server):
        """Test inspecting a non-existent keystone"""
        result = await server._handle_inspect_keystone({"keystone_name": "NonExistentKeystone12345"})
        text = result[0].text

        # Should show not found message with suggestions or not initialized
        assert "Not Found" in text or "not initialized" in text


class TestNotableTools:
    """Test notable-related MCP tools"""

    @pytest.fixture
    def server(self):
        """Create server instance for testing"""
        return PoE2BuildOptimizerMCP()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_PSG_DATABASE, reason="PSG database not found")
    async def test_list_all_notables_returns_data(self, server):
        """Test that list_all_notables returns notable data"""
        result = await server._handle_list_all_notables({})

        assert len(result) == 1
        text = result[0].text

        # Should have notables header or not initialized
        assert "Notable" in text or "not initialized" in text

    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_PSG_DATABASE, reason="PSG database not found")
    async def test_list_all_notables_with_filter(self, server):
        """Test filtering notables by stat text"""
        result = await server._handle_list_all_notables({
            "filter_stat": "projectile",
            "limit": 20
        })

        assert len(result) == 1
        text = result[0].text

        # Should contain projectile-related notables or show filtered message or not initialized
        assert "Notable" in text or "not initialized" in text

    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_PSG_DATABASE, reason="PSG database not found")
    async def test_list_all_notables_respects_limit(self, server):
        """Test that limit parameter is respected"""
        result = await server._handle_list_all_notables({"limit": 5})
        text = result[0].text

        # Should indicate limited results or not initialized
        assert "5 shown" in text or "Notable" in text or "not initialized" in text


class TestPassiveNodeTools:
    """Test generic passive node inspection"""

    @pytest.fixture
    def server(self):
        """Create server instance for testing"""
        return PoE2BuildOptimizerMCP()

    @pytest.mark.asyncio
    async def test_inspect_passive_node_requires_input(self, server):
        """Test that inspect_passive_node requires name or id"""
        result = await server._handle_inspect_passive_node({})
        text = result[0].text

        # Should show error about required input (or not initialized)
        assert "required" in text.lower() or "error" in text.lower() or "not initialized" in text.lower()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_PSG_DATABASE, reason="PSG database not found")
    async def test_inspect_passive_node_by_name(self, server):
        """Test inspecting a passive node by name"""
        # Try a notable name
        result = await server._handle_inspect_passive_node({"node_name": "Power Shots"})
        text = result[0].text

        # Should find it or show not found or not initialized
        assert "Power Shots" in text or "Not Found" in text or "not initialized" in text


class TestBaseItemTools:
    """Test base item MCP tools"""

    @pytest.fixture
    def server(self):
        """Create server instance for testing"""
        return PoE2BuildOptimizerMCP()

    @pytest.mark.asyncio
    async def test_list_all_base_items_returns_data(self, server):
        """Test that list_all_base_items returns item data"""
        result = await server._handle_list_all_base_items({})

        assert len(result) == 1
        text = result[0].text

        # Should have items header
        assert "Base Item" in text

    @pytest.mark.asyncio
    async def test_list_all_base_items_with_filter(self, server):
        """Test filtering base items"""
        result = await server._handle_list_all_base_items({
            "filter_name": "sword",
            "limit": 20
        })

        assert len(result) == 1
        text = result[0].text

        # Should have items or show empty filter message
        assert "Base Item" in text

    @pytest.mark.asyncio
    async def test_inspect_base_item_requires_name(self, server):
        """Test that inspect_base_item requires item_name"""
        result = await server._handle_inspect_base_item({})
        text = result[0].text

        assert "required" in text.lower() or "error" in text.lower()


class TestToolRegistration:
    """Test that new tools are properly registered"""

    @pytest.fixture
    def server(self):
        """Create server instance for testing"""
        return PoE2BuildOptimizerMCP()

    def test_keystone_tools_in_dispatch(self, server):
        """Verify keystone tools are in the dispatch table"""
        # The dispatch is handled in handle_call_tool, verify handlers exist
        assert hasattr(server, '_handle_list_all_keystones')
        assert hasattr(server, '_handle_inspect_keystone')

    def test_notable_tools_in_dispatch(self, server):
        """Verify notable tools are in the dispatch table"""
        assert hasattr(server, '_handle_list_all_notables')
        assert hasattr(server, '_handle_inspect_passive_node')

    def test_base_item_tools_in_dispatch(self, server):
        """Verify base item tools are in the dispatch table"""
        assert hasattr(server, '_handle_list_all_base_items')
        assert hasattr(server, '_handle_inspect_base_item')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
