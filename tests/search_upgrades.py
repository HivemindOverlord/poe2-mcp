#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Search Trade Market for Character Upgrades
Finds specific items for DoesFireWorkGoodNow
"""

import asyncio
import sys
import io
from pathlib import Path
from typing import Dict

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.trade_api import (
    TradeAPI,
    search_amulet_with_spell_levels_and_resistances,
    search_helmet_with_life_es_resistances,
    search_resistance_charms
)


async def search_all_upgrades():
    """Search for all recommended upgrades"""

    print("="*80)
    print("TRADE MARKET SEARCH - CHARACTER UPGRADES")
    print("="*80)
    print("\nSearching for upgrades for: DoesFireWorkGoodNow (Level 91 Stormweaver)")
    print("League: Abyss")
    print("\n")

    league = "Abyss"

    # Search 1: Amulets
    print("="*80)
    print("[1/3] SEARCHING FOR AMULETS")
    print("="*80)
    print("Requirements:")
    print("  - +2 to Level of all Spell Skills")
    print("  - 80+ Total Elemental Resistances")
    print("  - Life or Energy Shield")
    print("  - Max Price: 100 chaos")
    print("\nSearching...")

    try:
        amulets = await search_amulet_with_spell_levels_and_resistances(
            league=league,
            min_spell_levels=2,
            min_life=0,  # Accept any with life or ES
            min_total_res=80,
            max_price_chaos=100
        )

        if amulets:
            print(f"\n✓ Found {len(amulets)} amulets!\n")
            for i, item in enumerate(amulets[:5], 1):
                print_item_summary(i, item)
        else:
            print("\n⚠️  No amulets found matching criteria")
            print("   Try: Lower resistance requirement or increase budget")

    except Exception as e:
        print(f"\n❌ Error searching amulets: {e}")

    # Wait between searches (rate limiting)
    await asyncio.sleep(2)

    # Search 2: Helmets
    print("\n" + "="*80)
    print("[2/3] SEARCHING FOR HELMETS")
    print("="*80)
    print("Requirements:")
    print("  - 100+ Maximum Life")
    print("  - 100+ Energy Shield")
    print("  - 60+ Total Resistances")
    print("  - Max Price: 100 chaos")
    print("\nSearching...")

    try:
        helmets = await search_helmet_with_life_es_resistances(
            league=league,
            min_life=100,
            min_es=100,
            min_total_res=60,
            max_price_chaos=100
        )

        if helmets:
            print(f"\n✓ Found {len(helmets)} helmets!\n")
            for i, item in enumerate(helmets[:5], 1):
                print_item_summary(i, item)
        else:
            print("\n⚠️  No helmets found matching criteria")
            print("   Try: Lower life/ES requirement or increase budget")

    except Exception as e:
        print(f"\n❌ Error searching helmets: {e}")

    # Wait between searches
    await asyncio.sleep(2)

    # Search 3: Resistance Charms
    print("\n" + "="*80)
    print("[3/3] SEARCHING FOR RESISTANCE CHARMS")
    print("="*80)
    print("Requirements:")
    print("  - 30+ Total Resistances")
    print("  - Max Price: 20 chaos each")
    print("\nSearching...")

    try:
        charms = await search_resistance_charms(
            league=league,
            min_total_res=30,
            max_price_chaos=20
        )

        if charms:
            print(f"\n✓ Found {len(charms)} charms!\n")
            for i, item in enumerate(charms[:8], 1):
                print_item_summary(i, item)
        else:
            print("\n⚠️  No charms found matching criteria")
            print("   Try: Lower resistance requirement")

    except Exception as e:
        print(f"\n❌ Error searching charms: {e}")

    print("\n" + "="*80)
    print("SEARCH COMPLETE")
    print("="*80)
    print("\nNext Steps:")
    print("1. Review the items above")
    print("2. Whisper sellers in-game to purchase")
    print("3. Equip items and verify resistances are capped")
    print("\n")


def print_item_summary(index: int, item: Dict):
    """Print a clean summary of an item"""
    name = item.get("name") or item.get("type")
    item_type = item.get("type", "Unknown")
    ilvl = item.get("item_level", 0)
    corrupted = " [CORRUPTED]" if item.get("corrupted") else ""

    # Price
    price_info = item.get("price", {})
    price_amount = price_info.get("amount", "?")
    price_currency = price_info.get("currency", "chaos")
    price_str = f"{price_amount} {price_currency}"

    # Seller
    seller = item.get("seller", {})
    seller_name = seller.get("account", "Unknown")
    online_status = "🟢 ONLINE" if seller.get("online") else "🔴 Offline"

    print(f"[{index}] {name}{corrupted}")
    print(f"    Type: {item_type} (iLvl {ilvl})")
    print(f"    Price: {price_str}")
    print(f"    Seller: {seller_name} - {online_status}")

    # Show key mods
    explicit_mods = item.get("explicit_mods", [])
    implicit_mods = item.get("implicit_mods", [])

    if implicit_mods:
        print(f"    Implicit:")
        for mod in implicit_mods[:2]:
            print(f"      - {mod}")

    if explicit_mods:
        print(f"    Explicit Mods ({len(explicit_mods)} total):")
        for mod in explicit_mods[:4]:
            print(f"      - {mod}")
        if len(explicit_mods) > 4:
            print(f"      ... and {len(explicit_mods) - 4} more")

    print()


if __name__ == "__main__":
    try:
        asyncio.run(search_all_upgrades())
    except KeyboardInterrupt:
        print("\n\nSearch cancelled by user")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
