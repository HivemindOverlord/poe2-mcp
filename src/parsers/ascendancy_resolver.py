#!/usr/bin/env python3
"""
Ascendancy Data Resolver - Resolves ascendancy node data.

Primary source (PoE 2 0.5+):
- data/game/ascendancies/ascendancies.json
  Fresh extraction (2026-05-31) from data/balance/ascendancy.datc64. Contains
  the canonical 23 active ascendancies including the 4 the legacy file misses:
  Spirit Walker (Huntress), Martial Artist (Monk), Abyssal Lich (Witch),
  Disciple of Varashta (Sorceress). Schema is a flat list of records with
  id / display_name / base_class / is_unused. NO per-node data — that's the
  domain of the passive tree.

Detailed node fallback:
- data/complete_models/druid_ascendancies.json
  Still loaded for detailed Druid node stats. The 0.5 extraction doesn't
  include notable-node level data yet; covering the other ascendancies'
  detailed nodes is deferred until passive-tree wiring (#137 follow-up).

Legacy fallback (deprecated, kept for safety):
- data/complete_models/all_ascendancies.json (Jan 2026, 19 ascendancies,
  marked "incomplete/placeholder" in its own metadata). Loaded only if the
  fresh dataset is missing; will be removed once all callers verified.

Migration scope (#137 / #135): wires ascendancy_resolver to read from
data/game/. Schema adapter normalises the new flat list into the resolver's
internal lookup tables. The hardcoded ``ASCENDANCY_TO_CLASS`` map is now
seeded from the fresh dataset, with the hand-curated map kept as a defensive
fallback so a missing data file doesn't break callers.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

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

        # Primary: data/game/ascendancies/ascendancies.json (0.5 fresh extraction)
        # Adapt the new flat list schema to the resolver's expected dict-of-dicts.
        fresh_path = self.data_dir / "game" / "ascendancies" / "ascendancies.json"
        loaded_fresh = False
        if fresh_path.exists():
            try:
                with open(fresh_path, "r", encoding="utf-8") as f:
                    fresh = json.load(f)
                self._all_ascendancies = self._adapt_fresh_schema(fresh)
                loaded_fresh = True
                active_count = len(self._all_ascendancies.get("ascendancies", {}))
                logger.info(
                    f"Loaded {active_count} active ascendancies from data/game/ "
                    f"(source: {fresh.get('metadata', {}).get('source', 'unknown')})"
                )
            except Exception as e:
                logger.error(f"Failed to load fresh ascendancies.json: {e}")

        # Node data (campaign C5, closes #137 row 1b): the .datc64 extraction
        # carries NO ascendancy node data (verified — see #137), so per-node
        # name/stats come from data/game/ascendancies/nodes.json, generated
        # from the PoB2 community 0.5 tree under the established psg+pob
        # precedent. Merged into notable_nodes so every existing consumer
        # (get_ascendancy_info, node indices) picks them up unchanged.
        nodes_path = self.data_dir / "game" / "ascendancies" / "nodes.json"
        if loaded_fresh and nodes_path.exists():
            try:
                with open(nodes_path, "r", encoding="utf-8") as f:
                    node_data = json.load(f)
                merged = 0
                ascs = self._all_ascendancies.get("ascendancies", {})
                for asc_name, nodes in node_data.get("ascendancy_nodes", {}).items():
                    if asc_name in ascs:
                        ascs[asc_name]["notable_nodes"] = nodes
                        ascs[asc_name]["node_source"] = "pob_0_5_tree"
                        merged += 1
                logger.info(
                    f"Merged node data for {merged} ascendancies from nodes.json "
                    f"({node_data.get('metadata', {}).get('node_count', '?')} nodes, "
                    f"source: PoB 0_5 tree per psg+pob precedent)"
                )
            except Exception as e:
                logger.error(f"Failed to load ascendancy nodes.json: {e}")

        # Legacy fallback (Jan 2026, marked incomplete in its own metadata).
        # Loaded only if the fresh dataset is unavailable, to keep the
        # resolver functional during transition or test contexts that mock
        # data/game/ away.
        if not loaded_fresh:
            legacy_path = self.data_dir / "complete_models" / "all_ascendancies.json"
            if legacy_path.exists():
                try:
                    with open(legacy_path, "r", encoding="utf-8") as f:
                        self._all_ascendancies = json.load(f)
                    logger.warning(
                        "Loaded legacy data/complete_models/all_ascendancies.json "
                        "(pre-0.5; missing Spirit Walker / Martial Artist / "
                        "Abyssal Lich / Disciple of Varashta). Run extraction "
                        "(#138) and re-deploy data/game/ to fix."
                    )
                except Exception as e:
                    logger.error(f"Failed to load legacy all_ascendancies.json: {e}")

        # Load druid_ascendancies.json for detailed Druid node data
        # (still authoritative; the new dataset only has metadata, not nodes)
        druid_path = self.data_dir / "complete_models" / "druid_ascendancies.json"
        if druid_path.exists():
            try:
                with open(druid_path, "r", encoding="utf-8") as f:
                    self._druid_detailed = json.load(f)
                logger.info("Loaded detailed Druid ascendancy data")
            except Exception as e:
                logger.error(f"Failed to load druid_ascendancies.json: {e}")

        # Build lookup indices
        self._build_indices()

        # Augment the hardcoded class map with fresh-data discoveries so
        # ``get_base_class`` returns correct values for the new 0.5
        # ascendancies even if a caller doesn't iterate via the data dict.
        self._augment_class_map_from_data()

        self._loaded = True

    @staticmethod
    def _adapt_fresh_schema(fresh: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert the data/game/ascendancies/ascendancies.json flat-list schema
        into the resolver's expected dict-keyed-by-display-name shape.

        Skips ``is_unused`` placeholder rows (the source datc64 has 14 of
        them — internal slots for cut/scrapped ascendancies that ship with
        ``[DNT-UNUSED]`` display names).
        """
        adapted: Dict[str, Dict[str, Any]] = {}
        for record in fresh.get("ascendancies", []):
            if record.get("is_unused"):
                continue
            display_name = record.get("display_name")
            if not display_name:
                continue
            adapted[display_name] = {
                "base_class": record.get("base_class"),
                "id": record.get("id"),
                "row_index": record.get("row_index"),
                # notable_nodes intentionally absent — fresh dataset doesn't
                # cover per-node data. Downstream code already handles this.
                "notable_nodes": {},
            }
        return {
            "metadata": fresh.get("metadata", {}),
            "ascendancies": adapted,
        }

    def _augment_class_map_from_data(self):
        """Add any ascendancies discovered in fresh data that the hardcoded
        ``ASCENDANCY_TO_CLASS`` map doesn't already cover. The hardcoded map
        is a defensive fallback so ``get_base_class`` works when callers
        don't trigger a full load."""
        for asc_name, asc_data in self._all_ascendancies.get("ascendancies", {}).items():
            base_class = asc_data.get("base_class")
            if base_class and asc_name not in self.ASCENDANCY_TO_CLASS:
                self.ASCENDANCY_TO_CLASS[asc_name] = base_class

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


if __name__ == "__main__":
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
