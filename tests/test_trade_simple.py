#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Trade API Test
Tests basic item search functionality
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


async def test_simple_search():
    """Test simple item search"""

    print("="*80)
    print("SIMPLE TRADE API TEST")
    print("="*80)

    trade_api = TradeAPI()

    try:
        # Test 1: Search for charms (simplest search)
        print("\n[Test 1] Searching for Charms...")
        print("-"*80)

        filters = {
            "term": "charm resistance"  # Simple text search
        }

        results = await trade_api.search_items(
            league="Rise of the Abyssal",
            filters=filters,
            limit=5
        )

        if results:
            print(f"✓ Found {len(results)} charms!")
            for i, item in enumerate(results, 1):
                name = item.get("name") or item.get("type")
                price = item.get("price", {})
                print(f"  [{i}] {name}")
                print(f"      Price: {price.get('amount')} {price.get('currency')}")
                print(f"      Seller: {item.get('seller', {}).get('account')}")
        else:
            print("⚠️  No charms found (this could mean API needs session cookie)")

        # Test 2: Search for amulets
        print("\n[Test 2] Searching for Amulets...")
        print("-"*80)

        filters = {
            "type": "Amulet",
            "term": "spell"
        }

        results = await trade_api.search_items(
            league="Rise of the Abyssal",
            filters=filters,
            limit=5
        )

        if results:
            print(f"✓ Found {len(results)} amulets!")
            for i, item in enumerate(results, 1):
                name = item.get("name") or item.get("type")
                price = item.get("price", {})
                print(f"  [{i}] {name}")
                print(f"      Price: {price.get('amount')} {price.get('currency')}")
        else:
            print("⚠️  No amulets found")

        print("\n" + "="*80)
        print("TEST COMPLETE")
        print("="*80)

        if not any([results]):  # If no results from any test
            print("\n⚠️  NOTE: If no results were found, you may need to:")
            print("   1. Provide a POESESSID cookie for authentication")
            print("   2. Check if the league name is correct")
            print("   3. The trade API might require browser-based access")

    finally:
        await trade_api.close()


if __name__ == "__main__":
    asyncio.run(test_simple_search())
