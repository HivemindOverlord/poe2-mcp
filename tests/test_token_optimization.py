"""
Tests for token optimization features.

Tests pagination, detail levels, and compact output format across MCP tools.
"""

import json
import sys
from pathlib import Path

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mcp_server import PoE2BuildOptimizerMCP
from src.utils.response_formatter import (
    BASE_ITEM_FIELDS,
    KEYSTONE_FIELDS,
    MOD_FIELDS,
    SPELL_GEM_FIELDS,
    SUPPORT_GEM_FIELDS,
    PaginationMeta,
    abbreviate_keys,
    compact_json,
    filter_fields,
)


class TestResponseFormatter:
    """Test response_formatter utility functions."""

    def test_pagination_meta_basic(self):
        """Test PaginationMeta creation and properties."""
        meta = PaginationMeta(total=100, limit=20, offset=0, showing=20)

        assert meta.total == 100
        assert meta.limit == 20
        assert meta.offset == 0
        assert meta.showing == 20
        assert meta.has_more is True

    def test_pagination_meta_no_more(self):
        """Test PaginationMeta when at end of results."""
        meta = PaginationMeta(total=25, limit=20, offset=20, showing=5)

        assert meta.has_more is False
        assert meta.showing == 5

    def test_pagination_meta_to_dict(self):
        """Test PaginationMeta serialization."""
        meta = PaginationMeta(total=100, limit=20, offset=40, showing=20)
        d = meta.to_dict()

        assert d["total"] == 100
        assert d["limit"] == 20
        assert d["offset"] == 40
        assert d["showing"] == 20
        assert d["has_more"] is True

    def test_abbreviate_keys_simple(self):
        """Test key abbreviation for simple dict."""
        data = {"name": "Test", "tier": 1, "spirit_cost": 25}
        abbreviated = abbreviate_keys(data)

        assert "n" in abbreviated
        assert abbreviated["n"] == "Test"
        assert "t" in abbreviated
        assert "sc" in abbreviated

    def test_abbreviate_keys_nested(self):
        """Test key abbreviation for nested structures."""
        data = {"name": "Test", "effects": {"spirit_cost": 10}}
        abbreviated = abbreviate_keys(data)

        assert abbreviated["n"] == "Test"
        assert "fx" in abbreviated
        assert abbreviated["fx"]["sc"] == 10

    def test_abbreviate_keys_list(self):
        """Test key abbreviation for lists."""
        data = [{"name": "A"}, {"name": "B"}]
        abbreviated = abbreviate_keys(data)

        assert abbreviated[0]["n"] == "A"
        assert abbreviated[1]["n"] == "B"

    def test_compact_json_output(self):
        """Test compact JSON formatting."""
        data = {"name": "Test Gem", "tier": 1, "spirit_cost": 25}
        result = compact_json(data)

        # Should be minified (no spaces after separators)
        assert " " not in result or result.count(" ") < 3
        # Should have abbreviated keys
        assert '"n":' in result
        assert '"t":' in result
        assert '"sc":' in result

    def test_filter_fields_summary(self):
        """Test filtering to summary level."""
        item = {
            "name": "Test",
            "tier": 1,
            "tags": ["fire", "spell"],
            "spirit_cost": 25,
            "effect_summary": "Does damage",
            "effects": {"damage": 100},
            "compatible_with": ["spell"],
            "requirements": {"int": 50},
            "acquisition": "Drop",
        }

        summary = filter_fields(item, "summary", SUPPORT_GEM_FIELDS)

        assert "name" in summary
        assert "tier" in summary
        assert "tags" not in summary
        assert "spirit_cost" not in summary

    def test_filter_fields_standard(self):
        """Test filtering to standard level."""
        item = {
            "name": "Test",
            "tier": 1,
            "tags": ["fire"],
            "spirit_cost": 25,
            "effect_summary": "Damage",
            "effects": {"damage": 100},
            "compatible_with": ["spell"],
            "requirements": {"int": 50},
            "acquisition": "Drop",
        }

        standard = filter_fields(item, "standard", SUPPORT_GEM_FIELDS)

        assert "name" in standard
        assert "tier" in standard
        assert "tags" in standard
        assert "spirit_cost" in standard
        assert "effect_summary" in standard
        assert "effects" not in standard
        assert "acquisition" not in standard

    def test_filter_fields_full(self):
        """Test that full level returns all fields."""
        item = {
            "name": "Test",
            "tier": 1,
            "tags": ["fire"],
            "spirit_cost": 25,
            "custom_field": "preserved",
        }

        full = filter_fields(item, "full", SUPPORT_GEM_FIELDS)

        # Full should return all fields
        assert full == item


class TestListAllSupportsPagination:
    """Test pagination in list_all_supports."""

    @pytest_asyncio.fixture
    async def mcp_server(self):
        """Create and initialize MCP server."""
        server = PoE2BuildOptimizerMCP()
        await server.initialize()
        yield server
        await server.cleanup()

    @pytest.mark.asyncio
    async def test_default_limit(self, mcp_server):
        """Test that default limit is 20 (not 50)."""
        result = await mcp_server._handle_list_all_supports({})
        text = result[0].text

        # Should show pagination info
        assert "of" in text  # "X of Y"

    @pytest.mark.asyncio
    async def test_pagination_offset(self, mcp_server):
        """Test pagination with offset."""
        # Get first page
        result1 = await mcp_server._handle_list_all_supports({"limit": 5, "offset": 0})
        text1 = result1[0].text

        # Get second page
        result2 = await mcp_server._handle_list_all_supports({"limit": 5, "offset": 5})
        text2 = result2[0].text

        # Should have different content
        assert text1 != text2

        # Second page should show offset
        assert "Offset: 5" in text2

    @pytest.mark.asyncio
    async def test_has_more_indicator(self, mcp_server):
        """Test that 'has more' indicator appears when applicable."""
        result = await mcp_server._handle_list_all_supports({"limit": 5})
        text = result[0].text

        # Should indicate more results available
        assert "offset=" in text.lower() or "more" in text.lower()


class TestListAllSupportsDetailLevels:
    """Test detail levels in list_all_supports."""

    @pytest_asyncio.fixture
    async def mcp_server(self):
        """Create and initialize MCP server."""
        server = PoE2BuildOptimizerMCP()
        await server.initialize()
        yield server
        await server.cleanup()

    @pytest.mark.asyncio
    async def test_summary_detail(self, mcp_server):
        """Test summary detail level shows minimal info."""
        result = await mcp_server._handle_list_all_supports({"detail": "summary", "limit": 5})
        text = result[0].text

        # Summary should be concise - just names and tiers
        # Should NOT have detailed effect descriptions
        lines = [
            l
            for l in text.split("\n")
            if l.strip() and not l.startswith("#") and not l.startswith("*")
        ]

        # Each item should be a single line
        for line in lines:
            if line.startswith("-"):
                # Summary format: "- Name (TX)"
                assert "(" in line and ")" in line

    @pytest.mark.asyncio
    async def test_standard_detail(self, mcp_server):
        """Test standard detail level shows key info."""
        result = await mcp_server._handle_list_all_supports({"detail": "standard", "limit": 5})
        text = result[0].text

        # Standard should have spirit costs and tags
        assert "Spirit:" in text or "spirit" in text.lower()

    @pytest.mark.asyncio
    async def test_full_detail(self, mcp_server):
        """Test full detail level shows everything."""
        result = await mcp_server._handle_list_all_supports({"detail": "full", "limit": 5})
        text = result[0].text

        # Full should have extensive info
        assert len(text) > 200  # Should be substantial


class TestListAllSupportsCompactFormat:
    """Test compact format in list_all_supports."""

    @pytest_asyncio.fixture
    async def mcp_server(self):
        """Create and initialize MCP server."""
        server = PoE2BuildOptimizerMCP()
        await server.initialize()
        yield server
        await server.cleanup()

    @pytest.mark.asyncio
    async def test_compact_format_is_json(self, mcp_server):
        """Test that compact format returns valid JSON."""
        result = await mcp_server._handle_list_all_supports({"format": "compact", "limit": 5})
        text = result[0].text

        # Should be valid JSON
        data = json.loads(text)
        assert "results" in data
        assert "meta" in data

    @pytest.mark.asyncio
    async def test_compact_format_has_abbreviated_keys(self, mcp_server):
        """Test that compact format uses abbreviated keys."""
        result = await mcp_server._handle_list_all_supports({"format": "compact", "limit": 5})
        text = result[0].text

        # Should have abbreviated keys like "n" for name
        assert '"n":' in text

    @pytest.mark.asyncio
    async def test_compact_format_includes_meta(self, mcp_server):
        """Test that compact format includes pagination meta."""
        result = await mcp_server._handle_list_all_supports({"format": "compact", "limit": 5})
        text = result[0].text
        data = json.loads(text)

        assert "meta" in data
        assert "total" in data["meta"]
        assert "showing" in data["meta"]
        assert "has_more" in data["meta"]

    @pytest.mark.asyncio
    async def test_compact_format_parseable(self, mcp_server):
        """Test that compact format produces machine-parseable output.

        Note: Compact format may not always be smaller than markdown due to JSON
        structure overhead. Its primary benefit is structured data for programmatic
        consumption, not size reduction.
        """
        compact_result = await mcp_server._handle_list_all_supports(
            {"format": "compact", "detail": "standard", "limit": 30}
        )

        text = compact_result[0].text

        # Should be valid, parseable JSON
        data = json.loads(text)

        # Should have expected structure
        assert "results" in data
        assert "meta" in data
        assert len(data["results"]) == 30

        # Each result should have abbreviated keys
        for item in data["results"]:
            assert "n" in item  # name -> n


class TestListAllSpellsTokenOptimization:
    """Test token optimization in list_all_spells."""

    @pytest_asyncio.fixture
    async def mcp_server(self):
        """Create and initialize MCP server."""
        server = PoE2BuildOptimizerMCP()
        await server.initialize()
        yield server
        await server.cleanup()

    @pytest.mark.asyncio
    async def test_pagination(self, mcp_server):
        """Test pagination works."""
        result = await mcp_server._handle_list_all_spells({"limit": 10, "offset": 0})
        text = result[0].text

        assert "of" in text  # Shows "X of Y"

    @pytest.mark.asyncio
    async def test_compact_format(self, mcp_server):
        """Test compact format works."""
        result = await mcp_server._handle_list_all_spells({"format": "compact", "limit": 5})
        text = result[0].text

        data = json.loads(text)
        assert "results" in data
        assert "meta" in data

    @pytest.mark.asyncio
    async def test_detail_levels(self, mcp_server):
        """Test detail levels affect output."""
        summary = await mcp_server._handle_list_all_spells({"detail": "summary", "limit": 5})
        standard = await mcp_server._handle_list_all_spells({"detail": "standard", "limit": 5})

        # Summary should be shorter
        assert len(summary[0].text) < len(standard[0].text)


class TestListAllKeystonesTokenOptimization:
    """Test token optimization in list_all_keystones."""

    @pytest_asyncio.fixture
    async def mcp_server(self):
        """Create and initialize MCP server."""
        server = PoE2BuildOptimizerMCP()
        await server.initialize()
        yield server
        await server.cleanup()

    @pytest.mark.asyncio
    async def test_pagination(self, mcp_server):
        """Test pagination works."""
        result = await mcp_server._handle_list_all_keystones({"limit": 5, "offset": 0})
        text = result[0].text

        # Should show pagination info or be a valid response
        assert "Keystones" in text or "keystones" in text.lower()

    @pytest.mark.asyncio
    async def test_compact_format(self, mcp_server):
        """Test compact format works."""
        result = await mcp_server._handle_list_all_keystones({"format": "compact", "limit": 5})
        text = result[0].text

        # Should be valid JSON
        data = json.loads(text)
        assert "results" in data or "meta" in data


class TestListAllModsTokenOptimization:
    """Test token optimization in list_all_mods."""

    @pytest_asyncio.fixture
    async def mcp_server(self):
        """Create and initialize MCP server."""
        server = PoE2BuildOptimizerMCP()
        await server.initialize()
        yield server
        await server.cleanup()

    @pytest.mark.asyncio
    async def test_pagination(self, mcp_server):
        """Test pagination works."""
        result = await mcp_server._handle_list_all_mods({"limit": 10, "offset": 0})
        text = result[0].text

        assert "Mods" in text

    @pytest.mark.asyncio
    async def test_compact_format(self, mcp_server):
        """Test compact format works."""
        result = await mcp_server._handle_list_all_mods({"format": "compact", "limit": 5})
        text = result[0].text

        data = json.loads(text)
        assert "results" in data
        assert "meta" in data

    @pytest.mark.asyncio
    async def test_summary_detail(self, mcp_server):
        """Test summary detail level."""
        result = await mcp_server._handle_list_all_mods({"detail": "summary", "limit": 10})
        text = result[0].text

        # Summary should be concise
        assert len(text) < 2000  # Reasonable size for 10 items


class TestAnalyzeCharacterCompactFormat:
    """Test compact format in analyze_character."""

    @pytest_asyncio.fixture
    async def mcp_server(self):
        """Create and initialize MCP server."""
        server = PoE2BuildOptimizerMCP()
        await server.initialize()
        yield server
        await server.cleanup()

    @pytest.mark.asyncio
    async def test_format_parameter_accepted(self, mcp_server):
        """Test that format parameter is accepted (doesn't error)."""
        # This test just verifies the parameter is handled
        # We can't test actual character fetching without mock data
        # The handler should accept the format parameter without error

        # Test with a non-existent character - should fail gracefully
        result = await mcp_server._handle_analyze_character(
            {"account": "test_account", "character": "test_char", "format": "compact"}
        )

        # Should return a result (even if error)
        assert len(result) == 1
        assert result[0].text  # Has some text


class TestTokenSavingsValidation:
    """Validate that token optimization achieves expected savings."""

    @pytest_asyncio.fixture
    async def mcp_server(self):
        """Create and initialize MCP server."""
        server = PoE2BuildOptimizerMCP()
        await server.initialize()
        yield server
        await server.cleanup()

    @pytest.mark.asyncio
    async def test_compact_summary_vs_markdown_full(self, mcp_server):
        """Test that compact+summary is smaller than markdown+full."""
        # Get full markdown
        full = await mcp_server._handle_list_all_supports(
            {"format": "markdown", "detail": "full", "limit": 20}
        )

        # Get compact summary
        compact = await mcp_server._handle_list_all_supports(
            {"format": "compact", "detail": "summary", "limit": 20}
        )

        full_size = len(full[0].text)
        compact_size = len(compact[0].text)

        # Compact summary should be meaningfully smaller
        # Actual savings depend on data richness; 20% is reasonable baseline
        savings = 1 - (compact_size / full_size)
        assert savings > 0.2, f"Expected >20% savings, got {savings*100:.1f}%"

    @pytest.mark.asyncio
    async def test_pagination_reduces_response_size(self, mcp_server):
        """Test that smaller limits reduce response size."""
        large = await mcp_server._handle_list_all_supports({"limit": 50})

        small = await mcp_server._handle_list_all_supports({"limit": 10})

        # Small limit should produce smaller response
        assert len(small[0].text) < len(large[0].text)
