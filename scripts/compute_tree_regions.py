#!/usr/bin/env python3
"""
Compute authoritative tree regions from passive node coordinates.

Uses Voronoi-style distance-based clustering to assign each node to its
nearest class starting position.

Class starting positions form a hexagon (PoE2 classes):
- WARRIOR: (-1271, 733) - bottom-left (Pure STR)
- RANGER: (1275, 736) - bottom-right (Pure DEX, shared with HUNTRESS)
- SORCERESS: (0, -1491) - top-center (Pure INT, shared with WITCH)
- MERCENARY: (2, 1470) - bottom-center (STR/DEX hybrid)
- DRUID: (-1245, -729) - top-left (STR/INT hybrid)
- MONK: (1270, -729) - top-right (DEX/INT hybrid)

Output:
- data/passive_tree_regions.json: Complete region mapping
"""

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

# Class starting positions (authoritative coordinates from psg_passive_nodes.json)
# FIXED: Correct node-to-class mappings for PoE2
# Note: HUNTRESS shares RANGER position, WITCH shares SORCERESS position
CLASS_STARTS = {
    "WARRIOR": {"node_id": 47175, "x": -1271.185, "y": 733.095},  # Pure STR (bottom-left)
    "RANGER": {"node_id": 50459, "x": 1274.675, "y": 735.845},  # Pure DEX (bottom-right)
    "SORCERESS": {"node_id": 54447, "x": 0.005, "y": -1490.585},  # Pure INT (top-center)
    "MERCENARY": {"node_id": 50986, "x": 1.945, "y": 1469.815},  # STR/DEX hybrid (bottom-center)
    "DRUID": {"node_id": 61525, "x": -1245.175, "y": -728.895},  # STR/INT hybrid (top-left)
    "MONK": {"node_id": 44683, "x": 1270.425, "y": -728.835},  # DEX/INT hybrid (top-right)
}


def euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Calculate Euclidean distance between two points."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def assign_node_to_region(x: float, y: float) -> Tuple[str, float]:
    """
    Assign a node to the nearest class region using Voronoi-style assignment.

    Returns:
        Tuple of (region_name, distance_to_region_start)
    """
    best_region = None
    best_distance = float("inf")

    for region_name, start_pos in CLASS_STARTS.items():
        distance = euclidean_distance(x, y, start_pos["x"], start_pos["y"])
        if distance < best_distance:
            best_distance = distance
            best_region = region_name

    return best_region, best_distance


def compute_region_boundaries(node_regions: Dict[int, dict]) -> Dict[str, dict]:
    """
    Compute the bounding box for each region based on assigned nodes.

    Returns:
        Dict mapping region name to boundary info
    """
    region_coords = defaultdict(lambda: {"xs": [], "ys": []})

    for node_id, data in node_regions.items():
        region = data["region"]
        region_coords[region]["xs"].append(data["x"])
        region_coords[region]["ys"].append(data["y"])

    boundaries = {}
    for region_name, coords in region_coords.items():
        if coords["xs"] and coords["ys"]:
            boundaries[region_name] = {
                "x_range": (min(coords["xs"]), max(coords["xs"])),
                "y_range": (min(coords["ys"]), max(coords["ys"])),
                "centroid": (
                    sum(coords["xs"]) / len(coords["xs"]),
                    sum(coords["ys"]) / len(coords["ys"]),
                ),
                "node_count": len(coords["xs"]),
            }

    return boundaries


def main():
    """Compute regions and save to JSON."""
    # Paths
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / "data"
    input_file = data_dir / "psg_passive_nodes.json"
    output_file = data_dir / "passive_tree_regions.json"

    print(f"Loading nodes from {input_file}...")

    with open(input_file, "r", encoding="utf-8") as f:
        nodes = json.load(f)

    print(f"Processing {len(nodes)} nodes...")

    # Assign each node to a region
    node_regions = {}
    region_stats = defaultdict(lambda: {"count": 0, "notables": 0, "keystones": 0})
    ascendancy_nodes = []

    for str_id, node_data in nodes.items():
        node_id = int(str_id)
        x = node_data.get("x", 0.0)
        y = node_data.get("y", 0.0)
        is_ascendancy = node_data.get("is_ascendancy", False)

        # Skip ascendancy nodes - they exist in separate sub-trees
        if is_ascendancy:
            ascendancy_nodes.append(node_id)
            continue

        region, distance = assign_node_to_region(x, y)

        node_regions[node_id] = {
            "region": region,
            "distance_to_start": round(distance, 2),
            "x": x,
            "y": y,
        }

        # Track stats
        region_stats[region]["count"] += 1
        if node_data.get("is_notable", False):
            region_stats[region]["notables"] += 1
        if node_data.get("is_keystone", False):
            region_stats[region]["keystones"] += 1

    # Compute boundaries
    boundaries = compute_region_boundaries(node_regions)

    # Prepare output
    output = {
        "metadata": {
            "total_nodes": len(nodes),
            "assigned_nodes": len(node_regions),
            "ascendancy_nodes_excluded": len(ascendancy_nodes),
            "class_starts": CLASS_STARTS,
            "method": "voronoi_nearest_neighbor",
        },
        "boundaries": boundaries,
        "region_stats": dict(region_stats),
        "node_regions": {str(k): v["region"] for k, v in node_regions.items()},
        "node_details": {str(k): v for k, v in node_regions.items()},
    }

    # Save to file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to {output_file}")
    print("\n=== REGION STATISTICS ===")
    print(f"Total nodes: {len(nodes)}")
    print(f"Assigned to regions: {len(node_regions)}")
    print(f"Ascendancy nodes excluded: {len(ascendancy_nodes)}")

    print("\n=== NODES PER REGION ===")
    for region in sorted(CLASS_STARTS.keys()):
        stats = region_stats[region]
        bounds = boundaries.get(region, {})
        print(f"\n{region}:")
        print(f"  Nodes: {stats['count']}")
        print(f"  Notables: {stats['notables']}")
        print(f"  Keystones: {stats['keystones']}")
        if bounds:
            x_range = bounds["x_range"]
            y_range = bounds["y_range"]
            print(f"  X Range: ({x_range[0]:.1f}, {x_range[1]:.1f})")
            print(f"  Y Range: ({y_range[0]:.1f}, {y_range[1]:.1f})")

    # Generate code snippet for TREE_REGIONS
    print("\n=== CODE FOR TREE_REGIONS ===")
    print("TREE_REGIONS = {")
    for region in sorted(CLASS_STARTS.keys()):
        bounds = boundaries.get(region, {})
        if bounds:
            x_range = bounds["x_range"]
            y_range = bounds["y_range"]
            centroid = bounds["centroid"]
            print(f'    "{region}": {{')
            print(f'        "x_range": ({x_range[0]:.1f}, {x_range[1]:.1f}),')
            print(f'        "y_range": ({y_range[0]:.1f}, {y_range[1]:.1f}),')
            print(f'        "centroid": ({centroid[0]:.1f}, {centroid[1]:.1f}),')
            print(f'        "node_count": {bounds["node_count"]}')
            print(f"    }},")
    print("}")

    return output


if __name__ == "__main__":
    main()
