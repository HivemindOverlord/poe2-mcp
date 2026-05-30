#!/usr/bin/env python3
"""
Ascendancy Data Resolver - Resolves ascendancy node data from complete_models.

Provides high-level API for:
- Looking up ascendancy nodes by name or ID
- Getting all nodes for a specific ascendancy
- Resolving unresolved node IDs that might be ascendancy nodes

Uses data from:
- data/complete_models/all_ascendancies.json
- data/complete_models/druid_ascendancies.json (detailed Druid data)
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class AscendancyNode:
    """A resolved ascendancy node."""
    id: str
    name: str
    ascendancy: str
    base_class: str
    stats: List[str] = field(default_factory=list)
    stat_effects: Dict[str, Any] = field(default_factory=dict)
    is_notable: bool = False
    is_keystone: bool = False


class AscendancyResolver:
    """
    Resolves ascendancy node data from complete_models.

    Usage:
        resolver = AscendancyResolver()

        # Get all nodes for an ascendancy
        shaman_nodes = resolver.get_ascendancy_nodes("Shaman")

        # Look up a specific node
        node = resolver.get_node("Sacred Flow")

        # Get ascendancy info
        info = resolver.get_ascendancy_info("Shaman")
    """

    # Mapping of ascendancy names to their base class
    ASCENDANCY_TO_CLASS = {
        # Warrior (STR)
        "Titan": "Warrior",
        "Warbringer": "Warrior",
        "Smith of Kitava": "Warrior",
        # Ranger (DEX)
        "Deadeye": "Ranger",
        "Pathfinder": "Ranger",
        # Huntress (DEX)
        "Amazon": "Huntress",
        "Ritualist": "Huntress",
        "Spirit Walker": "Huntress",  # 0.5 (new) - node data pending local extraction
        # Witch (INT)
        "Infernalist": "Witch",
        "Blood Mage": "Witch",
        "Bloodmage": "Witch",
        "Lich": "Witch",
        # Sorceress (INT)
        "Stormweaver": "Sorceress",
        "Chronomancer": "Sorceress",
        # Mercenary (STR/DEX)
        "Tactician": "Mercenary",
        "Witchhunter": "Mercenary",
        "Gemling Legionnaire": "Mercenary",
        # Druid (STR/INT)
        "Shaman": "Druid",
        "Oracle": "Druid",
        # Monk (DEX/INT)
        "Invoker": "Monk",
        "Acolyte of Chayula": "Monk",
        "Martial Artist": "Monk",  # 0.5 (new) - node data pending local extraction
    }

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize the resolver.

        Args:
            data_dir: Path to data directory containing complete_models
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data"

        self.data_dir = Path(data_dir)
        self._all_ascendancies: Dict = {}
        self._druid_detailed: Dict = {}
        self._nodes_by_name: Dict[str, AscendancyNode] = {}
        self._nodes_by_id: Dict[str, AscendancyNode] = {}
        self._loaded = False

    def _ensure_loaded(self):
        """Load ascendancy databases if not already loaded."""
        if self._loaded:
            return

        # Load all_ascendancies.json
        all_asc_path = self.data_dir / "complete_models" / "all_ascendancies.json"
        if all_asc_path.exists():
            try:
                with open(all_asc_path, 'r', encoding='utf-8') as f:
                    self._all_ascendancies = json.load(f)
                logger.info(f"Loaded {len(self._all_ascendancies.get('ascendancies', {}))} ascendancies")
            except Exception as e:
                logger.error(f"Failed to load all_ascendancies.json: {e}")

        # Load druid_ascendancies.json for detailed Druid data
        druid_path = self.data_dir / "complete_models" / "druid_ascendancies.json"
        if druid_path.exists():
            try:
                with open(druid_path, 'r', encoding='utf-8') as f:
                    self._druid_detailed = json.load(f)
                logger.info("Loaded detailed Druid ascendancy data")
            except Exception as e:
                logger.error(f"Failed to load druid_ascendancies.json: {e}")

        # Build lookup indices
        self._build_indices()
        self._loaded = True

    def _build_indices(self):
        """Build lookup indices for nodes."""
        # Index detailed Druid nodes first (highest priority)
        if self._druid_detailed:
            for asc_name, asc_data in self._druid_detailed.get("ascendancies", {}).items():
                base_class = asc_data.get("base_class", "Druid")
                for node_id, node_data in asc_data.get("nodes", {}).items():
                    node = AscendancyNode(
                        id=node_id,
                        name=node_data.get("name", node_id),
                        ascendancy=asc_name,
                        base_class=base_class,
                        stats=node_data.get("stats", []),
                        stat_effects=node_data.get("stat_effects", {}),
                        is_notable=node_data.get("is_notable", False),
                        is_keystone=node_data.get("is_keystone", False),
                    )
                    self._nodes_by_id[node_id] = node
                    self._nodes_by_name[node.name.lower()] = node

        # Index all ascendancy nodes
        if self._all_ascendancies:
            for asc_name, asc_data in self._all_ascendancies.get("ascendancies", {}).items():
                base_class = asc_data.get("base_class", "Unknown")
                for node_id, node_data in asc_data.get("notable_nodes", {}).items():
                    # Skip if already indexed from detailed data
                    if node_id in self._nodes_by_id:
                        continue

                    node = AscendancyNode(
                        id=node_id,
                        name=node_data.get("name", node_id),
                        ascendancy=asc_name,
                        base_class=base_class,
                        stats=node_data.get("stats", []),
                        is_notable=True,
                        is_keystone=False,
                    )
                    self._nodes_by_id[node_id] = node
                    self._nodes_by_name[node.name.lower()] = node

        logger.info(f"Indexed {len(self._nodes_by_id)} ascendancy nodes")

    def get_ascendancy_info(self, ascendancy_name: str) -> Optional[Dict]:
        """
        Get information about an ascendancy class.

        Args:
            ascendancy_name: Name of the ascendancy (e.g., "Shaman")

        Returns:
            Dict with ascendancy info or None if not found
        """
        self._ensure_loaded()

        # Check detailed Druid data first
        if ascendancy_name in self._druid_detailed.get("ascendancies", {}):
            return self._druid_detailed["ascendancies"][ascendancy_name]

        # Check all_ascendancies
        if ascendancy_name in self._all_ascendancies.get("ascendancies", {}):
            return self._all_ascendancies["ascendancies"][ascendancy_name]

        return None

    def get_ascendancy_nodes(self, ascendancy_name: str) -> List[AscendancyNode]:
        """
        Get all nodes for a specific ascendancy.

        Args:
            ascendancy_name: Name of the ascendancy (e.g., "Shaman")

        Returns:
            List of AscendancyNode objects
        """
        self._ensure_loaded()

        nodes = []
        for node in self._nodes_by_id.values():
            if node.ascendancy == ascendancy_name:
                nodes.append(node)

        return nodes

    def get_node(self, name_or_id: str) -> Optional[AscendancyNode]:
        """
        Look up an ascendancy node by name or ID.

        Args:
            name_or_id: Node name (e.g., "Sacred Flow") or ID

        Returns:
            AscendancyNode or None if not found
        """
        self._ensure_loaded()

        # Try ID lookup first
        if name_or_id in self._nodes_by_id:
            return self._nodes_by_id[name_or_id]

        # Try name lookup (case-insensitive)
        return self._nodes_by_name.get(name_or_id.lower())

    def get_base_class(self, ascendancy_name: str) -> Optional[str]:
        """
        Get the base class for an ascendancy.

        Args:
            ascendancy_name: Name of the ascendancy

        Returns:
            Base class name or None if unknown
        """
        return self.ASCENDANCY_TO_CLASS.get(ascendancy_name)

    def list_all_ascendancies(self) -> List[str]:
        """Return list of all known ascendancy names."""
        self._ensure_loaded()

        ascendancies = set(self.ASCENDANCY_TO_CLASS.keys())

        # Add any from data files
        for asc_name in self._all_ascendancies.get("ascendancies", {}).keys():
            ascendancies.add(asc_name)
        for asc_name in self._druid_detailed.get("ascendancies", {}).keys():
            ascendancies.add(asc_name)

        return sorted(ascendancies)

    def format_ascendancy_summary(self, ascendancy_name: str) -> str:
        """
        Format a summary of an ascendancy for display.

        Args:
            ascendancy_name: Name of the ascendancy

        Returns:
            Formatted string summary
        """
        self._ensure_loaded()

        info = self.get_ascendancy_info(ascendancy_name)
        nodes = self.get_ascendancy_nodes(ascendancy_name)
        base_class = self.get_base_class(ascendancy_name)

        if not info and not nodes:
            return f"No data found for ascendancy: {ascendancy_name}"

        output = f"# {ascendancy_name} Ascendancy\n\n"
        output += f"**Base Class:** {base_class or 'Unknown'}\n\n"

        if info:
            if "description" in info:
                output += f"**Description:** {info['description']}\n\n"
            if "key_mechanics" in info:
                output += f"**Key Mechanics:** {', '.join(info['key_mechanics'])}\n\n"

        if nodes:
            notables = [n for n in nodes if n.is_notable]
            small = [n for n in nodes if not n.is_notable and not n.is_keystone]

            output += f"## Notable Nodes ({len(notables)})\n\n"
            for node in notables:
                output += f"### {node.name}\n"
                for stat in node.stats:
                    output += f"- {stat}\n"
                output += "\n"

            if small:
                output += f"## Small Nodes ({len(small)})\n\n"
                for node in small:
                    output += f"**{node.name}:** {node.stats[0] if node.stats else 'No stats'}\n"

        return output


# Singleton instance for convenience
_resolver: Optional[AscendancyResolver] = None

def get_ascendancy_resolver() -> AscendancyResolver:
    """Get the singleton AscendancyResolver instance."""
    global _resolver
    if _resolver is None:
        _resolver = AscendancyResolver()
    return _resolver


if __name__ == '__main__':
    # Demo usage
    resolver = AscendancyResolver()

    print("=== ASCENDANCY RESOLVER DEMO ===\n")

    # List all ascendancies
    print("Known Ascendancies:")
    for asc in resolver.list_all_ascendancies():
        base = resolver.get_base_class(asc)
        print(f"  - {asc} ({base})")

    # Get Shaman summary
    print("\n" + "=" * 60)
    print(resolver.format_ascendancy_summary("Shaman"))

    # Look up a specific node
    print("\n" + "=" * 60)
    node = resolver.get_node("Sacred Flow")
    if node:
        print(f"Node: {node.name}")
        print(f"Ascendancy: {node.ascendancy}")
        print(f"Stats: {node.stats}")
