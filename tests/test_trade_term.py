#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Trade API with Term Search Only
Matches the PowerShell example format exactly
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


async def test_term_searches():
    """Test searches using only term filter (like the PowerShell example)"""

    print("="*80)
    print("TRADE API - TERM SEARCH TEST")
    print("="*80)

    trade_api = TradeAPI()

    searches = [
        ("Resistance Charms", "charm resistance"),
        ("Amulets with Spell", "amulet spell"),
        ("Life Helmets", "helmet life"),
        ("Any Flask", "flask"),
    ]

    try:
        for search_name, search_term in searches:
            print(f"\n[Search] {search_name}")
            print(f"Term: '{search_term}'")
            print("-"*80)

            filters = {
                "term": search_term
            }

            results = await trade_api.search_items(
                league="Rise of the Abyssal",
                filters=filters,
                limit=3
            )

            if results:
                print(f"✓ Found {len(results)} items!")
                for i, item in enumerate(results, 1):
                    name = item.get("name") or item.get("type", "Unknown")
                    price = item.get("price", {})
                    amount = price.get("amount", "?")
                    currency = price.get("currency", "?")
                    seller = item.get("seller", {}).get("account", "Unknown")
                    online = "🟢" if item.get("seller", {}).get("online") else "🔴"

                    print(f"  [{i}] {name}")
                    print(f"      Price: {amount} {currency}")
                    print(f"      Seller: {seller} {online}")

                    # Show some mods if available
                    mods = item.get("explicit_mods", [])
                    if mods:
                        print(f"      Mods: {', '.join(mods[:2])}")
            else:
                print("  ⚠️  No items found")

            # Wait between searches
            await asyncio.sleep(1)

        print("\n" + "="*80)
        print("SEARCH COMPLETE")
        print("="*80)

    finally:
        await trade_api.close()


if __name__ == "__main__":
    asyncio.run(test_term_searches())
