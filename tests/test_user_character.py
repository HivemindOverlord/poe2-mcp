#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Fetching User's Actual Character
Account: Tomawar40-2671
Character: DoesFireWorkGoodNow
"""

import asyncio
import sys
import io
import json
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.character_fetcher import CharacterFetcher
from src.api.poe_ninja_api import PoeNinjaAPI
from src.api.cache_manager import CacheManager
from src.api.rate_limiter import RateLimiter


async def test_fetch_character():
    """Test fetching the user's character"""

    print("="*60)
    print("Fetching Character: DoesFireWorkGoodNow")
    print("Account: Tomawar40-2671")
    print("="*60)

    # Initialize components
    cache_manager = CacheManager()
    await cache_manager.initialize()

    rate_limiter = RateLimiter(rate_limit=5)

    # Try poe.ninja API client first
    print("\n[1/4] Trying poe.ninja API client...")
    ninja_api = PoeNinjaAPI(rate_limiter=rate_limiter, cache_manager=cache_manager)

    try:
        char_data = await ninja_api.get_character("Tomawar40-2671", "DoesFireWorkGoodNow")
        if char_data:
            print("✓ SUCCESS via poe.ninja API!")
            await print_character_data(char_data)
            await ninja_api.close()
            await cache_manager.close()
            return char_data
        else:
            print("✗ Failed via poe.ninja API")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Try character fetcher with all fallbacks
    print("\n[2/4] Trying CharacterFetcher (all fallback methods)...")
    fetcher = CharacterFetcher(cache_manager=cache_manager, rate_limiter=rate_limiter)

    try:
        char_data = await fetcher.get_character(
            "Tomawar40-2671",
            "DoesFireWorkGoodNow",
            "Standard"
        )

        if char_data:
            print("✓ SUCCESS via CharacterFetcher!")
            await print_character_data(char_data)
            await fetcher.close()
            await ninja_api.close()
            await cache_manager.close()
            return char_data
        else:
            print("✗ All fetcher methods failed")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

    # Try direct SSE API approach
    print("\n[3/4] Trying direct SSE/Model API...")
    try:
        char_data = await fetcher._fetch_from_poe_ninja_api("Tomawar40-2671", "DoesFireWorkGoodNow")
        if char_data:
            print("✓ SUCCESS via SSE API!")
            await print_character_data(char_data)
            await fetcher.close()
            await ninja_api.close()
            await cache_manager.close()
            return char_data
        else:
            print("✗ SSE API failed")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Try direct scraping
    print("\n[4/4] Trying direct HTML scraping...")
    try:
        char_data = await fetcher._scrape_character_direct("Tomawar40-2671", "DoesFireWorkGoodNow")
        if char_data:
            print("✓ SUCCESS via direct scraping!")
            await print_character_data(char_data)
            await fetcher.close()
            await ninja_api.close()
            await cache_manager.close()
            return char_data
        else:
            print("✗ Direct scraping failed")
    except Exception as e:
        print(f"✗ Error: {e}")

    await fetcher.close()
    await ninja_api.close()
    await cache_manager.close()

    print("\n" + "="*60)
    print("❌ ALL METHODS FAILED")
    print("="*60)
    return None


async def print_character_data(char_data: dict):
    """Pretty print character data"""
    print("\n" + "-"*60)
    print("CHARACTER DATA:")
    print("-"*60)

    print(f"\nBasic Info:")
    print(f"  Name: {char_data.get('name', 'Unknown')}")
    print(f"  Account: {char_data.get('account', 'Unknown')}")
    print(f"  Class: {char_data.get('class', 'Unknown')}")
    print(f"  Level: {char_data.get('level', 0)}")
    print(f"  League: {char_data.get('league', 'Unknown')}")
    print(f"  Source: {char_data.get('source', 'Unknown')}")

    # Items
    items = char_data.get('items', [])
    print(f"\nEquipped Items: {len(items)}")
    if items:
        for item in items[:5]:  # Show first 5
            item_name = item.get('name', item.get('typeLine', 'Unknown'))
            print(f"  - {item_name}")
        if len(items) > 5:
            print(f"  ... and {len(items) - 5} more")

    # Skills
    skills = char_data.get('skills', [])
    print(f"\nSkills: {len(skills)}")
    if skills:
        for skill in skills[:3]:  # Show first 3
            skill_name = skill.get('name', skill.get('id', 'Unknown'))
            print(f"  - {skill_name}")
        if len(skills) > 3:
            print(f"  ... and {len(skills) - 3} more")

    # Passives
    passives = char_data.get('passives', char_data.get('passive_tree', {}))
    if isinstance(passives, list):
        print(f"\nPassive Points: {len(passives)}")
    elif isinstance(passives, dict):
        print(f"\nPassive Tree: {len(passives)} entries")

    # Stats
    stats = char_data.get('stats', {})
    if stats:
        print(f"\nStats:")
        for key, value in list(stats.items())[:5]:
            print(f"  {key}: {value}")

    print("\n" + "-"*60)
    print("Full JSON data:")
    print("-"*60)
    print(json.dumps(char_data, indent=2)[:2000] + "\n... (truncated)")
    print("-"*60)


async def main():
    """Main entry point"""
    char_data = await test_fetch_character()

    if char_data:
        print("\n" + "="*60)
        print("✓✓✓ SUCCESS! ✓✓✓")
        print("="*60)
        print(f"\nCharacter data successfully fetched!")
        print(f"Total keys in data: {len(char_data)}")
        return 0
    else:
        print("\n" + "="*60)
        print("❌ FAILED TO FETCH CHARACTER")
        print("="*60)
        print("\nPossible reasons:")
        print("1. Profile is not public")
        print("2. Character name or account name incorrect")
        print("3. poe.ninja hasn't indexed this character yet")
        print("4. Network issues or rate limiting")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
