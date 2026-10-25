"""
Timeless Jewel Seed Mapper for Path of Exile 2

This module connects the TinyMT32 PRNG, jewel radius calculator, and spawn weight data
to determine how a specific Timeless Jewel seed transforms passive nodes within its radius.

For Undying Hate (Abyss faction):
- Keystones in radius -> Replaced by faction keystone (based on Tribute name)
- Notables in radius -> Replaced by one of 29 Abyss notables (seed-determined)
- Small passives in radius -> Replaced by Tribute (+5 Tribute each)

Author: HivemindMinion
Date: 2026-01-16
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .jewel_radius import (
    AffectedNode,
    JewelRadiusSize,
    JewelSocket,
    get_jewel_sockets,
    get_nodes_in_radius,
    load_passive_tree,
)
from .tinymt32 import TinyMT32

logger = logging.getLogger(__name__)


# Abyss faction leader-to-keystone mapping
ABYSS_LEADERS = {
    "Amanamu": "Sacrifice of Flesh",
    "Ulaman": "Sacrifice of Loyalty",
    "Kurgal": "Sacrifice of Mind",
    "Tacati": "Sacrifice of Blood",
    "Doryani": "Sacrifice of Sight",
}

# Alternate spellings/variations
LEADER_ALIASES = {
    "amanamu": "Amanamu",
    "ulaman": "Ulaman",
    "kurgal": "Kurgal",
    "tacati": "Tacati",
    "tecrod": "Tacati",  # Alternate name seen in some sources
    "doryani": "Doryani",
}


@dataclass
class TransformedNode:
    """
    Represents a passive node after Timeless Jewel transformation.

    Attributes:
        original_node_id: The psg_id of the original node
        original_name: Original node name before transformation
        original_type: 'keystone', 'notable', or 'small'
        new_name: Name after transformation
        new_id: Internal ID of the replacement (e.g., 'abyss_notable_5')
        distance: Distance from jewel socket
        x: X coordinate
        y: Y coordinate
        tribute_value: Tribute gained (5 for small, 3 for attribute, 0 for notable/keystone)
    """

    original_node_id: int
    original_name: str
    original_type: str
    new_name: str
    new_id: str
    distance: float
    x: float = 0.0
    y: float = 0.0
    tribute_value: int = 0

    def __repr__(self) -> str:
        return f"TransformedNode({self.original_name} -> {self.new_name})"


@dataclass
class SeedAnalysis:
    """
    Complete analysis of a Timeless Jewel seed at a specific socket.

    Attributes:
        socket: The jewel socket being analyzed
        seed: The jewel seed number (79-30977 for Undying Hate)
        tribute_name: The leader name (determines keystone)
        keystone: The keystone granted by this jewel
        radius: Jewel radius used
        transformed_nodes: List of all transformed nodes
        total_tribute: Sum of all Tribute values
        notable_count: Number of notables transformed
        small_count: Number of small passives transformed
    """

    socket: JewelSocket
    seed: int
    tribute_name: str
    keystone: str
    radius: float
    transformed_nodes: List[TransformedNode]
    total_tribute: int = 0
    notable_count: int = 0
    small_count: int = 0
    keystone_replaced: bool = False

    def __post_init__(self):
        """Calculate summary statistics."""
        self.total_tribute = sum(n.tribute_value for n in self.transformed_nodes)
        self.notable_count = sum(1 for n in self.transformed_nodes if n.original_type == "notable")
        self.small_count = sum(1 for n in self.transformed_nodes if n.original_type == "small")
        self.keystone_replaced = any(n.original_type == "keystone" for n in self.transformed_nodes)


class TimelessSeedMapper:
    """
    Maps Timeless Jewel seeds to passive node transformations.

    This class integrates:
    - TinyMT32 PRNG for deterministic random selection
    - Jewel radius calculator for affected nodes
    - Spawn weight data for weighted notable selection

    Example:
        >>> mapper = TimelessSeedMapper()
        >>> analysis = mapper.analyze_seed(socket_id=2491, seed=12345, tribute="Amanamu")
        >>> for node in analysis.transformed_nodes:
        ...     print(f"{node.original_name} -> {node.new_name}")
    """

    def __init__(self, spawn_weights_path: Optional[Path] = None):
        """
        Initialize the mapper with spawn weight data.

        Args:
            spawn_weights_path: Path to abyss_spawn_weights.json.
                              Defaults to data/abyss_spawn_weights.json
        """
        if spawn_weights_path is None:
            spawn_weights_path = (
                Path(__file__).parent.parent.parent / "data" / "abyss_spawn_weights.json"
            )

        self._load_spawn_weights(spawn_weights_path)
        self._tree_data: Optional[Dict[str, Any]] = None

    def _load_spawn_weights(self, path: Path) -> None:
        """Load spawn weight data from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Build notable pool (only notables with spawn_weight > 0)
        self.notables = [n for n in data.get("notables", []) if n.get("spawn_weight", 0) > 0]

        # Build spawn weight lookup and cumulative weights for weighted selection
        self.notable_weights = {n["id"]: n["spawn_weight"] for n in self.notables}
        self.total_weight = sum(n["spawn_weight"] for n in self.notables)

        # Build cumulative weight array for binary search selection
        cumulative = 0
        self.cumulative_weights = []
        for n in self.notables:
            cumulative += n["spawn_weight"]
            self.cumulative_weights.append((cumulative, n))

        # Load keystones
        self.keystones = {k["leader"]: k for k in data.get("keystones", [])}

        # Small passive data
        self.small_passive = data.get("small_passive", {"name": "Tribute", "spawn_weight": 100})

        logger.info(f"Loaded {len(self.notables)} notables (total weight: {self.total_weight})")

    def _get_tree_data(self) -> Dict[str, Any]:
        """Lazy-load passive tree data."""
        if self._tree_data is None:
            self._tree_data = load_passive_tree()
        return self._tree_data

    def _normalize_tribute_name(self, tribute: str) -> str:
        """Normalize tribute/leader name to canonical form."""
        normalized = LEADER_ALIASES.get(tribute.lower(), tribute)
        if normalized not in ABYSS_LEADERS:
            raise ValueError(
                f"Unknown tribute name: {tribute}. " f"Valid options: {list(ABYSS_LEADERS.keys())}"
            )
        return normalized

    def _select_notable_for_node(self, node_id: int, seed: int) -> Tuple[str, str]:
        """
        Use PRNG to select which notable replaces a node.

        The algorithm:
        1. Initialize TinyMT32 with [node_id, seed]
        2. Generate random value in range [0, total_weight)
        3. Select notable based on cumulative weight threshold

        Args:
            node_id: The passive node's graph ID
            seed: The Timeless Jewel seed

        Returns:
            Tuple of (notable_id, notable_name)
        """
        # Initialize RNG with node-specific seed
        rng = TinyMT32.from_poe_seed(node_id, seed)

        # Roll against total spawn weight
        roll = rng.generate_range(self.total_weight)

        # Find the notable this roll selects (weighted selection)
        for cumulative_weight, notable in self.cumulative_weights:
            if roll < cumulative_weight:
                return (notable["id"], notable["name"])

        # Fallback to last notable (shouldn't happen)
        last = self.notables[-1]
        return (last["id"], last["name"])

    def _classify_node_type(self, node: AffectedNode) -> str:
        """Classify a node as keystone, notable, or small."""
        if node.is_keystone:
            return "keystone"
        elif node.is_notable:
            return "notable"
        else:
            return "small"

    def _calculate_tribute_value(self, node: AffectedNode, original_type: str) -> int:
        """
        Calculate Tribute value for a transformed node.

        - Small passives: +5 Tribute
        - Attribute passives (Str/Dex/Int): +3 Tribute (in addition to original)
        - Notables/Keystones: 0 Tribute (they scale with Tribute instead)
        """
        if original_type == "small":
            # Check if it's an attribute node
            if node.stats:
                for stat in node.stats:
                    stat_lower = stat.lower()
                    if any(
                        attr in stat_lower for attr in ["strength", "dexterity", "intelligence"]
                    ):
                        # Attribute node gets +3 on top of regular +5
                        return 8  # 5 base + 3 attribute bonus
            return 5
        return 0

    def analyze_seed(
        self,
        socket_id: int,
        seed: int,
        tribute: str,
        radius: float = JewelRadiusSize.VERY_LARGE.value,
    ) -> SeedAnalysis:
        """
        Analyze how a specific seed transforms nodes around a jewel socket.

        This is the main entry point for seed analysis. It:
        1. Gets all nodes within the jewel's radius
        2. For each node, determines the transformation based on seed
        3. Returns complete analysis with all transformed nodes

        Args:
            socket_id: The psg_id of the jewel socket
            seed: Timeless Jewel seed (79-30977 for Undying Hate)
            tribute: Leader name (Amanamu, Ulaman, Kurgal, Tacati, Doryani)
            radius: Jewel radius (default: 1500 for Very Large)

        Returns:
            SeedAnalysis with complete transformation data
        """
        # Normalize tribute name
        tribute_name = self._normalize_tribute_name(tribute)
        keystone_name = ABYSS_LEADERS[tribute_name]

        # Get tree data and affected nodes
        tree_data = self._get_tree_data()
        affected_nodes = get_nodes_in_radius(tree_data, socket_id, radius)

        # Get socket info
        socket_key = str(socket_id)
        socket_node = tree_data[socket_key]
        socket = JewelSocket(
            node_id=socket_id,
            x=socket_node.get("x", 0.0),
            y=socket_node.get("y", 0.0),
            name=socket_node.get("name", "Jewel Socket"),
            group_id=socket_node.get("group_id"),
        )

        # Transform each node
        transformed_nodes = []

        for node in affected_nodes:
            original_type = self._classify_node_type(node)

            if original_type == "keystone":
                # Keystones become the faction keystone
                transformed = TransformedNode(
                    original_node_id=node.node_id,
                    original_name=node.name,
                    original_type=original_type,
                    new_name=keystone_name,
                    new_id=f"abyss_keystone_{list(ABYSS_LEADERS.keys()).index(tribute_name) + 1}",
                    distance=node.distance,
                    x=node.x,
                    y=node.y,
                    tribute_value=0,
                )
            elif original_type == "notable":
                # Notables are replaced based on seed
                new_id, new_name = self._select_notable_for_node(node.node_id, seed)
                transformed = TransformedNode(
                    original_node_id=node.node_id,
                    original_name=node.name,
                    original_type=original_type,
                    new_name=new_name,
                    new_id=new_id,
                    distance=node.distance,
                    x=node.x,
                    y=node.y,
                    tribute_value=0,
                )
            else:
                # Small passives become Tribute
                tribute_value = self._calculate_tribute_value(node, original_type)
                transformed = TransformedNode(
                    original_node_id=node.node_id,
                    original_name=node.name,
                    original_type=original_type,
                    new_name=self.small_passive["name"],
                    new_id=self.small_passive.get("id", "abyss_small_tribute"),
                    distance=node.distance,
                    x=node.x,
                    y=node.y,
                    tribute_value=tribute_value,
                )

            transformed_nodes.append(transformed)

        return SeedAnalysis(
            socket=socket,
            seed=seed,
            tribute_name=tribute_name,
            keystone=keystone_name,
            radius=radius,
            transformed_nodes=transformed_nodes,
        )

    def find_seeds_with_notable(
        self,
        socket_id: int,
        target_notable: str,
        target_node_id: int,
        tribute: str = "Amanamu",
        seed_range: Tuple[int, int] = (79, 30977),
        max_results: int = 10,
    ) -> List[int]:
        """
        Find seeds that place a specific notable at a specific node position.

        This brute-forces through the seed range to find matches.

        Args:
            socket_id: The jewel socket ID
            target_notable: Name of the notable to search for
            target_node_id: The node ID where we want the notable
            tribute: Leader name (doesn't affect notable placement)
            seed_range: (min_seed, max_seed) to search
            max_results: Maximum number of seeds to return

        Returns:
            List of seed numbers that place target_notable at target_node_id
        """
        matching_seeds = []
        target_lower = target_notable.lower()

        for seed in range(seed_range[0], seed_range[1] + 1):
            notable_id, notable_name = self._select_notable_for_node(target_node_id, seed)

            if notable_name.lower() == target_lower:
                matching_seeds.append(seed)
                if len(matching_seeds) >= max_results:
                    break

        return matching_seeds

    def compare_seeds(
        self,
        socket_id: int,
        seeds: List[int],
        tribute: str = "Amanamu",
        radius: float = JewelRadiusSize.VERY_LARGE.value,
    ) -> List[SeedAnalysis]:
        """
        Compare multiple seeds at the same socket.

        Useful for evaluating which seed gives the best notable layout.

        Args:
            socket_id: The jewel socket ID
            seeds: List of seeds to compare
            tribute: Leader name
            radius: Jewel radius

        Returns:
            List of SeedAnalysis for each seed
        """
        return [self.analyze_seed(socket_id, seed, tribute, radius) for seed in seeds]

    def get_notable_distribution(
        self,
        socket_id: int,
        seed: int,
        tribute: str = "Amanamu",
        radius: float = JewelRadiusSize.VERY_LARGE.value,
    ) -> Dict[str, int]:
        """
        Get a count of each notable that appears for a given seed.

        Args:
            socket_id: The jewel socket ID
            seed: The seed to analyze
            tribute: Leader name
            radius: Jewel radius

        Returns:
            Dictionary of notable_name -> count
        """
        analysis = self.analyze_seed(socket_id, seed, tribute, radius)

        distribution = {}
        for node in analysis.transformed_nodes:
            if node.original_type == "notable":
                distribution[node.new_name] = distribution.get(node.new_name, 0) + 1

        return distribution


def analyze_undying_hate(
    socket_id: int, seed: int, tribute: str, radius: float = 1500.0
) -> SeedAnalysis:
    """
    Convenience function to analyze an Undying Hate jewel.

    Args:
        socket_id: Jewel socket node ID
        seed: Seed number (79-30977)
        tribute: Leader name (Amanamu, Ulaman, Kurgal, Tacati, Doryani)
        radius: Jewel radius (default 1500 for Very Large)

    Returns:
        Complete SeedAnalysis
    """
    mapper = TimelessSeedMapper()
    return mapper.analyze_seed(socket_id, seed, tribute, radius)


# CLI entry point
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze Undying Hate Timeless Jewel seed")
    parser.add_argument("--socket", type=int, required=True, help="Jewel socket node ID")
    parser.add_argument("--seed", type=int, required=True, help="Jewel seed (79-30977)")
    parser.add_argument("--tribute", type=str, default="Amanamu", help="Tribute/leader name")
    parser.add_argument("--radius", type=float, default=1500.0, help="Jewel radius")

    args = parser.parse_args()

    analysis = analyze_undying_hate(args.socket, args.seed, args.tribute, args.radius)

    print(f"\n{'='*60}")
    print(f"UNDYING HATE SEED ANALYSIS")
    print(f"{'='*60}")
    print(
        f"Socket: {analysis.socket.node_id} at ({analysis.socket.x:.1f}, {analysis.socket.y:.1f})"
    )
    print(f"Seed: {analysis.seed}")
    print(f"Tribute to: {analysis.tribute_name}")
    print(f"Keystone: {analysis.keystone}")
    print(f"Radius: {analysis.radius}")
    print(f"\n--- Statistics ---")
    print(f"Total Tribute: {analysis.total_tribute}")
    print(f"Notables transformed: {analysis.notable_count}")
    print(f"Small passives transformed: {analysis.small_count}")
    print(f"Keystone replaced: {'Yes' if analysis.keystone_replaced else 'No'}")

    print(f"\n--- Transformed Notables ---")
    for node in analysis.transformed_nodes:
        if node.original_type == "notable":
            print(f"  {node.original_name} -> {node.new_name}")

    print(f"\n--- Transformed Keystones ---")
    for node in analysis.transformed_nodes:
        if node.original_type == "keystone":
            print(f"  {node.original_name} -> {node.new_name}")
