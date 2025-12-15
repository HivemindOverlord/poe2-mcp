#!/usr/bin/env python3
"""
Passive Tree Resolver - Resolves poe.ninja node IDs to full passive data.

Provides high-level API for:
- Resolving node IDs to names, stats, and metadata
- Pathfinding between nodes
- Finding nearest notables from a build
- Analyzing build connectivity

Uses data from:
- PSG binary file (authoritative node IDs and connections)
- PoB2 tree.json (names, stats, icons)
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class ResolvedNode:
    """A fully resolved passive tree node."""
    node_id: int
    name: str
    stats: List[str] = field(default_factory=list)
    is_notable: bool = False
    is_keystone: bool = False
    is_jewel_socket: bool = False
    x: float = 0.0
    y: float = 0.0
    connections: List[int] = field(default_factory=list)
    icon: str = ""

    @property
    def node_type(self) -> str:
        """Return the node type as a string."""
        if self.is_keystone:
            return "keystone"
        elif self.is_notable:
            return "notable"
        elif self.is_jewel_socket:
            return "jewel_socket"
        else:
            return "small"


@dataclass
class PathResult:
    """Result of a pathfinding operation."""
    start: int
    end: int
    path: List[int]
    distance: int
    nodes: List[ResolvedNode] = field(default_factory=list)


@dataclass
class BuildAnalysis:
    """Analysis of allocated passive nodes."""
    total_nodes: int
    keystones: List[ResolvedNode]
    notables: List[ResolvedNode]
    small_nodes: List[ResolvedNode]
    jewel_sockets: List[ResolvedNode]
    is_connected: bool
    nearest_notables: List[Tuple[ResolvedNode, int]]  # (node, distance)
    class_start: Optional[str] = None
    unresolved_nodes: List[int] = field(default_factory=list)  # Node IDs not in database (e.g., ascendancy)


class PassiveTreeResolver:
    """
    Resolves poe.ninja passive node IDs to full node data.

    Usage:
        resolver = PassiveTreeResolver()

        # Resolve single node
        node = resolver.resolve(6178)
        print(f"{node.name}: {node.stats}")

        # Resolve character's passives
        analysis = resolver.analyze_build([6178, 41210, ...])
        print(f"Notables: {[n.name for n in analysis.notables]}")

        # Find path to notable
        path = resolver.find_path(50986, 6178)
        print(f"Distance: {path.distance} nodes")
    """

    # Class starting node IDs
    CLASS_STARTS = {
        50459: "RANGER",
        47175: "MARAUDER",
        50986: "DUELIST",
        61525: "TEMPLAR",
        54447: "WITCH",
        44683: "MERCENARY"  # SIX in data
    }

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize the resolver.

        Args:
            data_dir: Path to data directory containing psg_passive_nodes.json
        """
        if data_dir is None:
            # Default to project data directory
            data_dir = Path(__file__).parent.parent.parent / "data"

        self.data_dir = Path(data_dir)
        self._nodes: Dict[int, dict] = {}
        self._adjacency: Dict[int, Set[int]] = {}
        self._loaded = False

    def _ensure_loaded(self):
        """Load node database if not already loaded."""
        if self._loaded:
            return

        db_path = self.data_dir / "psg_passive_nodes.json"
        if not db_path.exists():
            logger.warning(f"PSG database not found at {db_path}")
            self._loaded = True
            return

        try:
            with open(db_path, 'r', encoding='utf-8') as f:
                raw_nodes = json.load(f)

            # Convert string keys to int and build adjacency
            for str_id, node_data in raw_nodes.items():
                node_id = int(str_id)
                self._nodes[node_id] = node_data

                # Build adjacency graph
                connections = node_data.get('connections', [])
                if node_id not in self._adjacency:
                    self._adjacency[node_id] = set()
                for conn in connections:
                    self._adjacency[node_id].add(conn)
                    if conn not in self._adjacency:
                        self._adjacency[conn] = set()
                    self._adjacency[conn].add(node_id)

            logger.info(f"Loaded {len(self._nodes)} passive nodes")
            self._loaded = True

        except Exception as e:
            logger.error(f"Failed to load PSG database: {e}")
            self._loaded = True

    def resolve(self, node_id: int) -> Optional[ResolvedNode]:
        """
        Resolve a single node ID to full data.

        Args:
            node_id: The poe.ninja/PSG numeric node ID

        Returns:
            ResolvedNode with full data, or None if not found
        """
        self._ensure_loaded()

        node_data = self._nodes.get(node_id)
        if not node_data:
            return None

        return ResolvedNode(
            node_id=node_id,
            name=node_data.get('name', f'Unknown-{node_id}'),
            stats=node_data.get('stats', []),
            is_notable=node_data.get('is_notable', False),
            is_keystone=node_data.get('is_keystone', False),
            is_jewel_socket='Jewel Socket' in node_data.get('name', ''),
            x=node_data.get('x', 0.0),
            y=node_data.get('y', 0.0),
            connections=node_data.get('connections', []),
            icon=node_data.get('icon', '')
        )

    def resolve_many(self, node_ids: List[int]) -> List[ResolvedNode]:
        """
        Resolve multiple node IDs.

        Args:
            node_ids: List of node IDs

        Returns:
            List of ResolvedNode objects (only includes found nodes)
        """
        nodes = []
        for nid in node_ids:
            node = self.resolve(nid)
            if node:
                nodes.append(node)
        return nodes

    def find_path(self, start: int, end: int) -> Optional[PathResult]:
        """
        Find shortest path between two nodes using BFS.

        Args:
            start: Starting node ID
            end: Target node ID

        Returns:
            PathResult with path details, or None if no path exists
        """
        self._ensure_loaded()

        if start not in self._adjacency or end not in self._adjacency:
            return None

        if start == end:
            node = self.resolve(start)
            return PathResult(
                start=start,
                end=end,
                path=[start],
                distance=0,
                nodes=[node] if node else []
            )

        visited = {start}
        queue = deque([(start, [start])])

        while queue:
            current, path = queue.popleft()
            for neighbor in self._adjacency.get(current, []):
                if neighbor == end:
                    full_path = path + [neighbor]
                    return PathResult(
                        start=start,
                        end=end,
                        path=full_path,
                        distance=len(full_path) - 1,
                        nodes=self.resolve_many(full_path)
                    )
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None

    def find_nearest_notables(self, from_nodes: List[int], limit: int = 5,
                              exclude: Optional[Set[int]] = None) -> List[Tuple[ResolvedNode, int]]:
        """
        Find nearest notable nodes from a set of nodes.

        Args:
            from_nodes: List of node IDs to search from
            limit: Maximum number of notables to return
            exclude: Set of node IDs to exclude (e.g., already allocated)

        Returns:
            List of (ResolvedNode, distance) tuples sorted by distance
        """
        self._ensure_loaded()

        if exclude is None:
            exclude = set()
        exclude = set(exclude) | set(from_nodes)

        # BFS from all starting nodes simultaneously
        visited = set(from_nodes)
        queue = deque([(nid, 0) for nid in from_nodes if nid in self._adjacency])
        found = []

        while queue and len(found) < limit:
            current, dist = queue.popleft()

            for neighbor in self._adjacency.get(current, []):
                if neighbor in visited:
                    continue
                visited.add(neighbor)

                node = self.resolve(neighbor)
                if node and node.is_notable and neighbor not in exclude:
                    found.append((node, dist + 1))
                    if len(found) >= limit:
                        break

                queue.append((neighbor, dist + 1))

        return sorted(found, key=lambda x: x[1])

    def analyze_build(self, node_ids: List[int], find_recommendations: bool = True) -> BuildAnalysis:
        """
        Analyze a character's allocated passive nodes.

        Args:
            node_ids: List of allocated node IDs from poe.ninja
            find_recommendations: Whether to find nearest unallocated notables

        Returns:
            BuildAnalysis with categorized nodes and recommendations
        """
        self._ensure_loaded()

        keystones = []
        notables = []
        small_nodes = []
        jewel_sockets = []
        unresolved = []

        node_set = set(node_ids)

        for nid in node_ids:
            node = self.resolve(nid)
            if not node:
                unresolved.append(nid)
                continue

            if node.is_keystone:
                keystones.append(node)
            elif node.is_notable:
                notables.append(node)
            elif node.is_jewel_socket:
                jewel_sockets.append(node)
            else:
                small_nodes.append(node)

        # Check connectivity (only among resolved nodes)
        is_connected = self._check_connectivity(node_ids)

        # Find nearest unallocated notables
        nearest_notables = []
        if find_recommendations:
            nearest_notables = self.find_nearest_notables(
                node_ids,
                limit=5,
                exclude=node_set
            )

        # Determine likely class start
        class_start = None
        for class_id, class_name in self.CLASS_STARTS.items():
            path = self.find_path(class_id, node_ids[0] if node_ids else 0)
            if path and all(nid in node_set or nid == class_id for nid in path.path[:3]):
                class_start = class_name
                break

        return BuildAnalysis(
            total_nodes=len(node_ids),
            keystones=keystones,
            notables=notables,
            small_nodes=small_nodes,
            jewel_sockets=jewel_sockets,
            is_connected=is_connected,
            nearest_notables=nearest_notables,
            class_start=class_start,
            unresolved_nodes=unresolved
        )

    def _check_connectivity(self, node_ids: List[int]) -> bool:
        """
        Check if resolved nodes in the list are connected.

        Only checks connectivity among nodes that exist in our database.
        Nodes missing from database (e.g., ascendancy nodes) are ignored.
        """
        if not node_ids:
            return True

        # Filter to only nodes we have in our adjacency graph
        resolved_nodes = [nid for nid in node_ids if nid in self._adjacency]

        if not resolved_nodes:
            # No nodes in our database - can't determine connectivity
            return True

        node_set = set(resolved_nodes)
        start = resolved_nodes[0]

        visited = {start}
        queue = deque([start])

        while queue:
            current = queue.popleft()
            for neighbor in self._adjacency.get(current, []):
                if neighbor in node_set and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        return visited == node_set

    def get_node_count(self) -> int:
        """Return total number of nodes in database."""
        self._ensure_loaded()
        return len(self._nodes)

    def get_all_notables(self) -> List[ResolvedNode]:
        """Return all notable nodes."""
        self._ensure_loaded()
        return [
            self.resolve(nid) for nid in self._nodes
            if self._nodes[nid].get('is_notable', False)
        ]

    def get_all_keystones(self) -> List[ResolvedNode]:
        """Return all keystone nodes."""
        self._ensure_loaded()
        return [
            self.resolve(nid) for nid in self._nodes
            if self._nodes[nid].get('is_keystone', False)
        ]


# Singleton instance for convenience
_resolver: Optional[PassiveTreeResolver] = None

def get_resolver() -> PassiveTreeResolver:
    """Get the singleton PassiveTreeResolver instance."""
    global _resolver
    if _resolver is None:
        _resolver = PassiveTreeResolver()
    return _resolver


if __name__ == '__main__':
    # Demo usage
    resolver = PassiveTreeResolver()

    # Test character nodes
    char_nodes = [2455, 2847, 3717, 6178, 7062, 8092, 13081, 19998, 21755, 28556,
                  30082, 31763, 33415, 41210, 43155, 43578, 44430, 44605, 48588,
                  48635, 49657, 52125, 53683, 54127, 54282, 55802, 59028, 59881,
                  59915, 63526]

    print("=== PASSIVE TREE RESOLVER DEMO ===\n")

    # Resolve single node
    power_shots = resolver.resolve(6178)
    if power_shots:
        print(f"Single node: {power_shots.name}")
        print(f"  Stats: {power_shots.stats}")
        print(f"  Type: {power_shots.node_type}")

    # Analyze full build
    print("\n--- Build Analysis ---")
    analysis = resolver.analyze_build(char_nodes)
    print(f"Total: {analysis.total_nodes} nodes")
    print(f"Keystones: {len(analysis.keystones)}")
    print(f"Notables ({len(analysis.notables)}): {[n.name for n in analysis.notables]}")
    print(f"Connected: {analysis.is_connected}")
    print(f"Class: {analysis.class_start}")

    if analysis.nearest_notables:
        print(f"\nNearest unallocated notables:")
        for node, dist in analysis.nearest_notables:
            print(f"  - {node.name} ({dist} nodes away)")

    # Pathfinding
    print("\n--- Pathfinding ---")
    path = resolver.find_path(50986, 6178)  # DUELIST to Power Shots
    if path:
        print(f"DUELIST -> Power Shots: {path.distance} nodes")
        for i, node in enumerate(path.nodes[:5]):
            print(f"  {i+1}. {node.name} ({node.node_type})")
        if len(path.nodes) > 5:
            print(f"  ... and {len(path.nodes) - 5} more")
