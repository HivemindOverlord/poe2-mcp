#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test poe.ninja league availability
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

from src.api.poe_ninja_api import PoeNinjaAPI
from src.api.cache_manager import CacheManager
from src.api.rate_limiter import RateLimiter


async def test_leagues():
    """Test what leagues are available on poe.ninja"""

    print("="*80)
    print("POE.NINJA LEAGUE AVAILABILITY TEST")
    print("="*80)

    cache_manager = CacheManager()
    await cache_manager.initialize()

    rate_limiter = RateLimiter(rate_limit=5)
    ninja_api = PoeNinjaAPI(
        rate_limiter=rate_limiter,
        cache_manager=cache_manager
    )

    try:
        # Test different league names
        leagues_to_test = [
            "Rise of the Abyssal",
            "Standard",
            "Hardcore",
            "SSF Standard",
            "SSF Hardcore",
            "Settlers of Kalguur",  # Last PoE1 league
        ]

        print("\nTesting league availability:\n")

        for league in leagues_to_test:
            print(f"Testing '{league}'...")
            try:
                # Try to get top builds for this league
                builds = await ninja_api.get_top_builds(
                    league=league,
                    class_name=None,
                    limit=5
                )

                if builds:
                    print(f"  ✓ Found {len(builds)} builds in '{league}'")
                    if builds:
                        first_build = builds[0]
                        print(f"    Example: {first_build.get('character', 'Unknown')} - Level {first_build.get('level', '?')}")
                else:
                    print(f"  ⚠️  No builds found in '{league}' (may not be tracked)")

            except Exception as e:
                print(f"  ❌ Error: {e}")

            # Rate limit
            await asyncio.sleep(1)

        # Also try to get item prices to confirm API is working
        print("\n" + "-"*80)
        print("Testing item price API (to confirm poe.ninja access):\n")

        prices = await ninja_api.get_item_prices(
            league="Standard",
            item_type="UniqueWeapon"
        )

        if prices:
            print(f"✓ Successfully fetched {len(prices)} item prices from Standard")
            print(f"  Example: {prices[0].get('name', 'Unknown')} - {prices[0].get('chaosValue', 0)} chaos")
        else:
            print("⚠️  No item prices found")

    finally:
        await ninja_api.close()
        await cache_manager.close()

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_leagues())
