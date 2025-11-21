#!/usr/bin/env python3
"""
Test script to verify new MCP tool integration

Tests:
1. find_best_supports - Gem synergy calculator
2. explain_mechanic - Mechanics knowledge base
3. compare_items - Gear comparator
4. analyze_damage_scaling - Damage scaling analyzer
5. check_content_readiness - Content readiness checker
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mcp_server import PoE2BuildOptimizerMCP


async def test_mcp_integration():
    """Test all new MCP tools"""

    print("=" * 80)
    print("Testing MCP Integration for New Enhancement Features")
    print("=" * 80)
    print()

    # Initialize server
    print("Initializing MCP server...")
    server = PoE2BuildOptimizerMCP()
    await server.initialize()
    print("✓ Server initialized\n")

    # Test 1: Find Best Supports
    print("-" * 80)
    print("TEST 1: find_best_supports")
    print("-" * 80)
    try:
        result = await server._handle_find_best_supports({
            "spell_name": "fireball",
            "max_spirit": 100,
            "num_supports": 5,
            "goal": "dps",
            "top_n": 3
        })
        print("✓ find_best_supports works!")
        print(f"Response preview: {result[0].text[:200]}...")
    except Exception as e:
        print(f"✗ find_best_supports failed: {e}")
    print()

    # Test 2: Explain Mechanic
    print("-" * 80)
    print("TEST 2: explain_mechanic")
    print("-" * 80)
    try:
        result = await server._handle_explain_mechanic({
            "mechanic_name": "freeze"
        })
        print("✓ explain_mechanic works!")
        print(f"Response preview: {result[0].text[:200]}...")
    except Exception as e:
        print(f"✗ explain_mechanic failed: {e}")
    print()

    # Test 3: Compare Items
    print("-" * 80)
    print("TEST 3: compare_items")
    print("-" * 80)
    try:
        item_a = {
            "name": "Rare Helmet",
            "life": 80,
            "fire_res": 40,
            "cold_res": 30
        }
        item_b = {
            "name": "Unique Helmet",
            "life": 60,
            "spell_damage": 30,
            "fire_res": 20
        }
        character_data = {
            "fire_res": 65,
            "cold_res": 75,
            "lightning_res": 75,
            "chaos_res": 0
        }
        result = await server._handle_compare_items({
            "item_a": item_a,
            "item_b": item_b,
            "character_data": character_data,
            "build_goal": "balanced"
        })
        print("✓ compare_items works!")
        print(f"Response preview: {result[0].text[:200]}...")
    except Exception as e:
        print(f"✗ compare_items failed: {e}")
    print()

    # Test 4: Analyze Damage Scaling
    print("-" * 80)
    print("TEST 4: analyze_damage_scaling")
    print("-" * 80)
    try:
        character_data = {
            "increased_spell_damage": 250,
            "more_damage_multipliers": 1.6,
            "crit_chance": 20,
            "crit_multiplier": 150,
            "added_flat_damage": 50,
            "cast_speed": 1.5
        }
        result = await server._handle_analyze_damage_scaling({
            "character_data": character_data,
            "skill_type": "spell"
        })
        print("✓ analyze_damage_scaling works!")
        print(f"Response preview: {result[0].text[:200]}...")
    except Exception as e:
        print(f"✗ analyze_damage_scaling failed: {e}")
    print()

    # Test 5: Check Content Readiness
    print("-" * 80)
    print("TEST 5: check_content_readiness")
    print("-" * 80)
    try:
        character_data = {
            "life": 4500,
            "energy_shield": 0,
            "fire_res": 75,
            "cold_res": 75,
            "lightning_res": 68,
            "chaos_res": -20,
            "armor": 5000,
            "evasion": 0,
            "block_chance": 0,
            "dps": 60000
        }
        result = await server._handle_check_content_readiness({
            "character_data": character_data,
            "content": "high_maps"
        })
        print("✓ check_content_readiness works!")
        print(f"Response preview: {result[0].text[:200]}...")
    except Exception as e:
        print(f"✗ check_content_readiness failed: {e}")
    print()

    # Cleanup
    await server.cleanup()

    print("=" * 80)
    print("All Tests Complete!")
    print("=" * 80)


if __name__ == "__main__":
    # Windows console encoding fix
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

    asyncio.run(test_mcp_integration())
