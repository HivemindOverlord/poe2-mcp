#!/usr/bin/env python3
"""
Demo: Undying Hate Timeless Jewel Seed Calculator

This script demonstrates the seed calculator functionality by:
1. Listing all jewel sockets
2. Analyzing a sample seed at a selected socket
3. Showing the complete transformation map
4. Demonstrating seed comparison

Usage:
    python scripts/demo_seed_calculator.py
    python scripts/demo_seed_calculator.py --socket 2491 --seed 12345 --tribute Amanamu
    python scripts/demo_seed_calculator.py --compare 100,500,1000,5000
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from calculator.jewel_radius import (
    JewelRadiusSize,
    get_jewel_sockets,
    load_passive_tree,
)
from calculator.timeless_seed_mapper import (
    ABYSS_LEADERS,
    SeedAnalysis,
    TimelessSeedMapper,
    analyze_undying_hate,
)


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{'='*70}")
    print(f" {text}")
    print(f"{'='*70}")


def print_subheader(text: str) -> None:
    """Print a formatted subheader."""
    print(f"\n--- {text} ---")


def list_sockets() -> None:
    """List all available jewel sockets."""
    print_header("AVAILABLE JEWEL SOCKETS")

    tree_data = load_passive_tree()
    sockets = get_jewel_sockets(tree_data)

    print(f"\nFound {len(sockets)} jewel sockets:\n")
    print(f"{'Socket ID':<12} {'X Position':<12} {'Y Position':<12}")
    print("-" * 36)

    for socket in sockets:
        print(f"{socket.node_id:<12} {socket.x:<12.1f} {socket.y:<12.1f}")


def analyze_single_seed(socket_id: int, seed: int, tribute: str) -> SeedAnalysis:
    """Analyze a single seed and print results."""
    print_header(f"SEED ANALYSIS: {seed} at Socket {socket_id}")

    analysis = analyze_undying_hate(socket_id, seed, tribute)

    print(
        f"\nSocket: {analysis.socket.node_id} at ({analysis.socket.x:.1f}, {analysis.socket.y:.1f})"
    )
    print(f"Seed: {analysis.seed}")
    print(f"Tribute to: {analysis.tribute_name}")
    print(f"Keystone granted: {analysis.keystone}")
    print(f"Radius: {analysis.radius} (Very Large)")

    print_subheader("Summary Statistics")
    print(f"  Total nodes affected: {len(analysis.transformed_nodes)}")
    print(f"  Notables transformed: {analysis.notable_count}")
    print(f"  Small passives: {analysis.small_count}")
    print(f"  Total Tribute value: {analysis.total_tribute}")
    print(f"  Keystone in radius: {'Yes' if analysis.keystone_replaced else 'No'}")

    # Group notables by transformation
    print_subheader("Notable Transformations")
    notable_transforms = [n for n in analysis.transformed_nodes if n.original_type == "notable"]

    # Count each new notable
    notable_counts = {}
    for n in notable_transforms:
        notable_counts[n.new_name] = notable_counts.get(n.new_name, 0) + 1

    print(f"\n{'Original Notable':<30} {'Becomes':<30}")
    print("-" * 60)
    for n in notable_transforms:
        print(f"{n.original_name:<30} {n.new_name:<30}")

    print_subheader("Notable Distribution")
    for name, count in sorted(notable_counts.items(), key=lambda x: -x[1]):
        bar = "#" * count
        print(f"  {name:<25} {count:>2}x {bar}")

    # Show keystone if replaced
    keystone_transforms = [n for n in analysis.transformed_nodes if n.original_type == "keystone"]
    if keystone_transforms:
        print_subheader("Keystone Transformation")
        for n in keystone_transforms:
            print(f"  {n.original_name} -> {n.new_name}")

    return analysis


def compare_seeds(socket_id: int, seeds: list, tribute: str) -> None:
    """Compare multiple seeds at the same socket."""
    print_header(f"SEED COMPARISON at Socket {socket_id}")

    mapper = TimelessSeedMapper()
    analyses = mapper.compare_seeds(socket_id, seeds, tribute)

    print(f"\nComparing {len(seeds)} seeds: {seeds}")
    print(f"Tribute: {tribute} -> Keystone: {ABYSS_LEADERS[tribute]}")

    print_subheader("Comparison Table")
    print(f"\n{'Seed':<10} {'Notables':<10} {'Tribute':<10} {'Top Notable':<25}")
    print("-" * 60)

    for analysis in analyses:
        # Find most common notable
        dist = mapper.get_notable_distribution(socket_id, analysis.seed, tribute)
        top_notable = max(dist.items(), key=lambda x: x[1])[0] if dist else "N/A"
        top_count = dist.get(top_notable, 0)

        print(
            f"{analysis.seed:<10} {analysis.notable_count:<10} {analysis.total_tribute:<10} {top_notable} ({top_count}x)"
        )


def find_notable_seeds(
    socket_id: int, notable: str, node_id: int, tribute: str, max_seeds: int = 10
) -> None:
    """Find seeds that give a specific notable at a specific node."""
    print_header(f"SEARCHING FOR '{notable}' AT NODE {node_id}")

    mapper = TimelessSeedMapper()

    print(f"\nSearching seed range 79-30977...")
    seeds = mapper.find_seeds_with_notable(
        socket_id=socket_id,
        target_notable=notable,
        target_node_id=node_id,
        tribute=tribute,
        max_results=max_seeds,
    )

    if seeds:
        print(f"\nFound {len(seeds)} seeds that give '{notable}' at node {node_id}:")
        for seed in seeds:
            print(f"  Seed: {seed}")
    else:
        print(f"\nNo seeds found that give '{notable}' at node {node_id}")


def demo_mode() -> None:
    """Run interactive demo mode."""
    print_header("UNDYING HATE SEED CALCULATOR - DEMO MODE")

    print(
        """
This calculator determines how an Undying Hate Timeless Jewel transforms
passive nodes based on its seed number and Tribute name.

Available Tribute names (determine keystone):
  - Amanamu  -> Sacrifice of Flesh
  - Ulaman   -> Sacrifice of Loyalty
  - Kurgal   -> Sacrifice of Mind
  - Tacati   -> Sacrifice of Blood
  - Doryani  -> Sacrifice of Sight

Seed range: 79 - 30,977
    """
    )

    # List sockets
    list_sockets()

    # Demo with first socket and sample seeds
    tree_data = load_passive_tree()
    sockets = get_jewel_sockets(tree_data)

    if sockets:
        first_socket = sockets[0]
        print_header("DEMO: Analyzing Sample Seeds")

        # Analyze a few sample seeds
        sample_seeds = [100, 1000, 5000, 15000, 30000]

        for seed in sample_seeds[:2]:  # Just show first 2 in detail
            analyze_single_seed(first_socket.node_id, seed, "Amanamu")

        # Quick comparison of all sample seeds
        print_header("QUICK COMPARISON")
        compare_seeds(first_socket.node_id, sample_seeds, "Amanamu")


def main():
    parser = argparse.ArgumentParser(
        description="Undying Hate Timeless Jewel Seed Calculator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Run demo mode
  %(prog)s --list-sockets                     # List all jewel sockets
  %(prog)s --socket 2491 --seed 12345         # Analyze specific seed
  %(prog)s --socket 2491 --compare 100,500,1000
  %(prog)s --socket 2491 --find "Disciple of Darkness" --at-node 12345
        """,
    )

    parser.add_argument("--list-sockets", action="store_true", help="List all jewel socket IDs")
    parser.add_argument("--socket", type=int, help="Jewel socket node ID")
    parser.add_argument("--seed", type=int, help="Seed to analyze (79-30977)")
    parser.add_argument(
        "--tribute",
        type=str,
        default="Amanamu",
        help="Tribute name (Amanamu, Ulaman, Kurgal, Tacati, Doryani)",
    )
    parser.add_argument("--compare", type=str, help="Comma-separated seeds to compare")
    parser.add_argument("--find", type=str, help="Notable name to search for")
    parser.add_argument(
        "--at-node", type=int, help="Node ID where notable should appear (use with --find)"
    )

    args = parser.parse_args()

    if args.list_sockets:
        list_sockets()
    elif args.socket and args.compare:
        seeds = [int(s.strip()) for s in args.compare.split(",")]
        compare_seeds(args.socket, seeds, args.tribute)
    elif args.socket and args.find and args.at_node:
        find_notable_seeds(args.socket, args.find, args.at_node, args.tribute)
    elif args.socket and args.seed:
        analyze_single_seed(args.socket, args.seed, args.tribute)
    else:
        demo_mode()


if __name__ == "__main__":
    main()
