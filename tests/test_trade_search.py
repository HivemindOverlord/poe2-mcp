#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Trade Search Integration
Tests the new trade search functionality for character upgrades
"""

import asyncio
import sys
import io
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.trade_api import TradeAPI


async def test_trade_search_for_character():
    """Test trade search with DoesFireWorkGoodNow's upgrade needs"""

    print("="*80)
    print("TRADE SEARCH TEST - CHARACTER UPGRADE NEEDS")
    print("="*80)
    print()
    print("Character: DoesFireWorkGoodNow (Level 91 Stormweaver)")
    print("League: Rise of the Abyssal (Abyss)")
    print()
    print("Critical Issues:")
    print("  - Fire Resistance: -2% (need +2% minimum)")
    print("  - Cold Resistance: -8% (need +8% minimum)")
    print("  - Low Life: 1,413 (need more)")
    print()
    print("-"*80)
    print()

    trade_api = TradeAPI()

    try:
        # Test 1: Search for resistance charms
        print("[Test 1] Searching for Resistance Charms...")
        print("Criteria: Fire and Cold resistances, max 20 chaos each")
        print()

        character_needs = {
            "missing_resistances": {
                "fire": 2,
                "cold": 8
            },
            "needs_life": False,
            "needs_es": False,
            "item_slots": ["charm"]
        }

        results = await trade_api.search_for_upgrades(
            league="Abyss",
            character_needs=character_needs,
            max_price_chaos=20
        )

        if results.get("charms"):
            print(f"✓ Found {len(results['charms'])} charms!")
            print()
            for i, item in enumerate(results["charms"][:5], 1):
                print_item(i, item)
        else:
            print("⚠️  No charms found")
            print()

        # Test 2: Search for amulets with resistances and spell levels
        print("-"*80)
        print()
        print("[Test 2] Searching for Amulets...")
        print("Criteria: +2 Spell Levels, resistances, max 100 chaos")
        print()

        character_needs = {
            "missing_resistances": {
                "fire": 2,
                "cold": 8
            },
            "needs_life": True,
            "needs_es": False,
            "item_slots": ["amulet"]
        }

        results = await trade_api.search_for_upgrades(
            league="Abyss",
            character_needs=character_needs,
            max_price_chaos=100
        )

        if results.get("amulets"):
            print(f"✓ Found {len(results['amulets'])} amulets!")
            print()
            for i, item in enumerate(results["amulets"][:3], 1):
                print_item(i, item)
        else:
            print("⚠️  No amulets found")
            print()

        # Test 3: Search for helmets with life/ES and resistances
        print("-"*80)
        print()
        print("[Test 3] Searching for Helmets...")
        print("Criteria: Life + ES + resistances, max 100 chaos")
        print()

        character_needs = {
            "missing_resistances": {
                "fire": 2,
                "cold": 8
            },
            "needs_life": True,
            "needs_es": True,
            "item_slots": ["helmet"]
        }

        results = await trade_api.search_for_upgrades(
            league="Abyss",
            character_needs=character_needs,
            max_price_chaos=100
        )

        if results.get("helmets"):
            print(f"✓ Found {len(results['helmets'])} helmets!")
            print()
            for i, item in enumerate(results["helmets"][:3], 1):
                print_item(i, item)
        else:
            print("⚠️  No helmets found")
            print()

        print("="*80)
        print("TEST COMPLETE")
        print("="*80)
        print()
        print("Notes:")
        print("- If no results found, ensure POESESSID cookie is configured")
        print("- Results depend on current trade market availability")
        print("- Prices and availability change frequently")
        print()

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await trade_api.close()


def print_item(index: int, item: dict):
    """Print item details"""
    name = item.get("name") or item.get("type", "Unknown")
    price = item.get("price", {})
    price_str = f"{price.get('amount', '?')} {price.get('currency', 'chaos')}"

    seller = item.get("seller", {})
    seller_name = seller.get("account", "Unknown")
    online = "🟢 ONLINE" if seller.get("online") else "🔴 Offline"

    print(f"[{index}] {name}")
    print(f"    Price: {price_str}")
    print(f"    Seller: {seller_name} {online}")

    # Show mods
    explicit_mods = item.get("explicit_mods", [])
    implicit_mods = item.get("implicit_mods", [])

    if implicit_mods:
        print("    Implicit:")
        for mod in implicit_mods[:2]:
            print(f"      - {mod}")

    if explicit_mods:
        print("    Explicit:")
        for mod in explicit_mods[:4]:
            print(f"      - {mod}")
        if len(explicit_mods) > 4:
            print(f"      ... and {len(explicit_mods) - 4} more")

    print()


if __name__ == "__main__":
    try:
        asyncio.run(test_trade_search_for_character())
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
