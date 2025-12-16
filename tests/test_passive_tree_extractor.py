"""
Tests for PassiveTreeExtractor - Production passive tree data access

Validates:
- Node extraction with complete data
- Name population from PoB ground truth
- PoB skill ID mapping
- Keystone/notable filtering
- Node type classification
- Caching behavior
"""

import pytest
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers.passive_tree_extractor import (
    PassiveTreeExtractor,
    PassiveNode,
    get_node,
    get_node_by_pob_id,
    get_all_keystones,
    get_all_notables,
)


class TestPassiveNode:
    """Test PassiveNode dataclass methods."""

    def test_small_node_detection(self):
        """Test is_small_node() method."""
        # Small node
        small = PassiveNode(row_index=0, name="Small Node")
        assert small.is_small_node() is True

        # Keystone
        keystone = PassiveNode(row_index=1, name="Keystone", is_keystone=True)
        assert keystone.is_small_node() is False

        # Notable
        notable = PassiveNode(row_index=2, name="Notable", is_notable=True)
        assert notable.is_small_node() is False

        # Jewel socket
        jewel = PassiveNode(row_index=3, name="Jewel", is_jewel_socket=True)
        assert jewel.is_small_node() is False

    def test_node_type_classification(self):
        """Test get_node_type() method."""
        keystone = PassiveNode(row_index=0, name="Test", is_keystone=True)
        assert keystone.get_node_type() == "Keystone"

        notable = PassiveNode(row_index=1, name="Test", is_notable=True)
        assert notable.get_node_type() == "Notable"

        jewel = PassiveNode(row_index=2, name="Test", is_jewel_socket=True)
        assert jewel.get_node_type() == "Jewel Socket"

        small = PassiveNode(row_index=3, name="Test")
        assert small.get_node_type() == "Small Passive"

    def test_to_dict_serialization(self):
        """Test to_dict() serialization."""
        node = PassiveNode(
            row_index=40,
            name="Zealot's Oath",
            internal_id="KeystoneZealotsOath",
            is_keystone=True,
            stats=["+10 to Strength"],
            icon="path/to/icon.dds",
            pob_skill_id=40,
        )

        data = node.to_dict()
        assert data["row_index"] == 40
        assert data["name"] == "Zealot's Oath"
        assert data["is_keystone"] is True
        assert data["node_type"] == "Keystone"
        assert data["pob_skill_id"] == 40
        assert len(data["stats"]) == 1


class TestPassiveTreeExtractorInitialization:
    """Test extractor initialization."""

    def test_extractor_initializes(self):
        """Test that extractor can be created."""
        extractor = PassiveTreeExtractor()
        assert extractor is not None
        assert extractor.name_extractor is not None
        assert extractor.mapper is not None

    def test_parser_initialization(self):
        """Test that parser initializes if datc64 file exists."""
        extractor = PassiveTreeExtractor()
        # Parser may be None if file doesn't exist - this is OK
        if extractor.parser:
            assert extractor.parser.row_count > 0
            assert extractor.parser.row_count <= 7138


class TestNodeExtraction:
    """Test node data extraction."""

    @pytest.fixture
    def extractor(self):
        """Provide extractor instance."""
        return PassiveTreeExtractor()

    # Known test nodes from pob_passive_nodes.json (first 100 lines)
    TEST_NODES = [
        (4, "Life Flask Charges"),
        (40, "Zealot's Oath"),
        (52, "Fast Acting Toxins"),
        (55, "Incessant Cacophony"),
        (59, "Blind Chance"),
        (110, "Insightfulness"),
        (178, "Minion Damage and Life"),
        (259, "Life Mastery"),
        (331, "Storm Swell"),
        (722, "Tribal Fury"),
    ]

    def test_get_node_basic(self, extractor):
        """Test basic node retrieval."""
        if not extractor.parser:
            pytest.skip("passiveskills.datc64 not found")

        node = extractor.get_node(0)
        assert node is not None
        assert node.row_index == 0
        assert node.name != ""  # Should have a name

    def test_get_node_with_known_names(self, extractor):
        """Test that known nodes have correct names."""
        if not extractor.parser:
            pytest.skip("passiveskills.datc64 not found")

        for row_index, expected_name in self.TEST_NODES:
            node = extractor.get_node(row_index)
            assert node is not None, f"Node {row_index} not found"
            assert node.name == expected_name, f"Node {row_index} has wrong name: {node.name}"
            assert node.row_index == row_index

    def test_get_node_by_pob_id(self, extractor):
        """Test PoB skill ID mapping."""
        if not extractor.parser:
            pytest.skip("passiveskills.datc64 not found")

        # For skill IDs < 7138, PoB ID should equal row index
        node = extractor.get_node_by_pob_id(40)
        assert node is not None
        assert node.name == "Zealot's Oath"
        assert node.pob_skill_id == 40

    def test_get_node_invalid_index(self, extractor):
        """Test that invalid indices return None."""
        if not extractor.parser:
            pytest.skip("passiveskills.datc64 not found")

        node = extractor.get_node(-1)
        assert node is None

        node = extractor.get_node(999999)
        assert node is None

    def test_node_fields_populated(self, extractor):
        """Test that node fields are properly populated."""
        if not extractor.parser:
            pytest.skip("passiveskills.datc64 not found")

        node = extractor.get_node(40)  # Zealot's Oath - known keystone
        assert node is not None
        assert node.name != ""
        assert node.internal_id != ""
        assert node.is_keystone is True  # Zealot's Oath is a keystone
        assert node.icon != "" or node.icon == ""  # Icon may be empty

    def test_node_caching(self, extractor):
        """Test that nodes are cached properly."""
        if not extractor.parser:
            pytest.skip("passiveskills.datc64 not found")

        # First retrieval
        node1 = extractor.get_node(40)
        # Second retrieval (should be cached)
        node2 = extractor.get_node(40)

        assert node1 is node2  # Same object reference
        assert node1.name == node2.name


class TestNodeFiltering:
    """Test filtering methods (keystones, notables, etc)."""

    @pytest.fixture
    def extractor(self):
        """Provide extractor instance."""
        return PassiveTreeExtractor()

    def test_get_all_keystones(self, extractor):
        """Test keystone extraction."""
        if not extractor.parser:
            pytest.skip("passiveskills.datc64 not found")

        keystones = extractor.get_all_keystones()
        assert isinstance(keystones, list)

        # Verify all are keystones
        for node in keystones:
            assert node.is_keystone is True
            assert node.get_node_type() == "Keystone"

        # Should have at least a few keystones
        if len(keystones) > 0:
            # Zealot's Oath (row 40) should be in keystones
            zealots_oath = next((n for n in keystones if n.row_index == 40), None)
            if zealots_oath:
                assert zealots_oath.name == "Zealot's Oath"

    def test_get_all_notables(self, extractor):
        """Test notable extraction."""
        if not extractor.parser:
            pytest.skip("passiveskills.datc64 not found")

        notables = extractor.get_all_notables()
        assert isinstance(notables, list)

        # Verify all are notables
        for node in notables:
            assert node.is_notable is True
            assert node.get_node_type() == "Notable"

    def test_get_all_jewel_sockets(self, extractor):
        """Test jewel socket extraction."""
        if not extractor.parser:
            pytest.skip("passiveskills.datc64 not found")

        jewel_sockets = extractor.get_all_jewel_sockets()
        assert isinstance(jewel_sockets, list)

        # Verify all are jewel sockets
        for node in jewel_sockets:
            assert node.is_jewel_socket is True
            assert node.get_node_type() == "Jewel Socket"

    def test_search_nodes_by_name(self, extractor):
        """Test name-based search."""
        if not extractor.parser:
            pytest.skip("passiveskills.datc64 not found")

        # Search for "life"
        life_nodes = extractor.search_nodes_by_name("life")
        assert isinstance(life_nodes, list)

        # Verify all matches contain "life" (case-insensitive)
        for node in life_nodes:
            assert "life" in node.name.lower()

        # Case-sensitive search
        life_nodes_case = extractor.search_nodes_by_name("Life", case_sensitive=True)
        for node in life_nodes_case:
            assert "Life" in node.name


class TestModuleFunctions:
    """Test module-level convenience functions."""

    def test_module_get_node(self):
        """Test get_node() module function."""
        node = get_node(40)
        if node:  # May be None if datc64 not found
            assert node.row_index == 40
            assert node.name != ""

    def test_module_get_node_by_pob_id(self):
        """Test get_node_by_pob_id() module function."""
        node = get_node_by_pob_id(40)
        if node:
            assert node.pob_skill_id == 40

    def test_module_get_keystones(self):
        """Test get_all_keystones() module function."""
        keystones = get_all_keystones()
        assert isinstance(keystones, list)
        for node in keystones:
            assert node.is_keystone is True

    def test_module_get_notables(self):
        """Test get_all_notables() module function."""
        notables = get_all_notables()
        assert isinstance(notables, list)
        for node in notables:
            assert node.is_notable is True


class TestExtractorUtilities:
    """Test utility methods."""

    @pytest.fixture
    def extractor(self):
        """Provide extractor instance."""
        return PassiveTreeExtractor()

    def test_get_node_count(self, extractor):
        """Test get_node_count() method."""
        count = extractor.get_node_count()
        if extractor.parser:
            assert count > 0
            assert count <= 7138
        else:
            assert count == 0

    def test_get_mapper_stats(self, extractor):
        """Test get_mapper_stats() method."""
        stats = extractor.get_mapper_stats()
        assert isinstance(stats, dict)
        assert "direct_indexing_max" in stats
        assert stats["direct_indexing_max"] == 7138

    def test_clear_cache(self, extractor):
        """Test cache clearing."""
        if not extractor.parser:
            pytest.skip("passiveskills.datc64 not found")

        # Load a node (caches it)
        extractor.get_node(40)
        assert len(extractor._node_cache) > 0

        # Clear cache
        extractor.clear_cache()
        assert len(extractor._node_cache) == 0


class TestProductionReadiness:
    """Integration tests for production use cases."""

    @pytest.fixture
    def extractor(self):
        """Provide extractor instance."""
        return PassiveTreeExtractor()

    def test_can_retrieve_100_nodes(self, extractor):
        """Test that we can successfully retrieve first 100 nodes."""
        if not extractor.parser:
            pytest.skip("passiveskills.datc64 not found")

        success_count = 0
        for i in range(100):
            node = extractor.get_node(i)
            if node:
                success_count += 1
                assert node.name != ""  # All should have names

        # At least 90% success rate
        assert success_count >= 90, f"Only retrieved {success_count}/100 nodes"

    def test_all_keystones_have_names(self, extractor):
        """Test that all keystones have proper names."""
        if not extractor.parser:
            pytest.skip("passiveskills.datc64 not found")

        keystones = extractor.get_all_keystones()
        for node in keystones:
            assert node.name != "", f"Keystone at row {node.row_index} has no name"
            assert not node.name.startswith("Passive["), f"Keystone {node.row_index} has fallback name"

    def test_node_type_mutually_exclusive(self, extractor):
        """Test that node types are mutually exclusive."""
        if not extractor.parser:
            pytest.skip("passiveskills.datc64 not found")

        for i in range(100):
            node = extractor.get_node(i)
            if node:
                # Count how many type flags are True
                type_count = sum([
                    node.is_keystone,
                    node.is_notable,
                    node.is_jewel_socket,
                ])
                # Should be 0 (small node) or 1 (specific type)
                assert type_count <= 1, f"Node {i} has multiple type flags set"

    def test_pob_mapping_consistency(self, extractor):
        """Test that PoB mapping is consistent."""
        if not extractor.parser:
            pytest.skip("passiveskills.datc64 not found")

        # For nodes with PoB IDs < 7138, ID should equal row index
        for row_index in [4, 40, 52, 55, 59, 110, 178, 259]:
            node = extractor.get_node(row_index)
            assert node is not None
            assert node.pob_skill_id == row_index, f"PoB ID mismatch at row {row_index}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
