#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test official PoE ladder API
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

from src.api.character_fetcher import CharacterFetcher
from src.api.cache_manager import CacheManager
from src.api.rate_limiter import RateLimiter


async def test_ladder():
    """Test ladder API with different league names"""

    cache_manager = CacheManager()
    await cache_manager.initialize()

    fetcher = CharacterFetcher(
        cache_manager=cache_manager,
        rate_limiter=RateLimiter(rate_limit=5)
    )

    # Test different league names
    leagues_to_test = [
        "Standard",
        "Hardcore",
        "Abyss",  # Short name
        "Rise of the Abyssal",  # Full name
    ]

    print("Testing official PoE ladder API:")
    print("="*80)

    for league in leagues_to_test:
        print(f"\nTesting league: '{league}'")
        try:
            characters = await fetcher.get_top_ladder_characters(
                league=league,
                limit=5
            )

            if characters:
                print(f"  ✓ Found {len(characters)} characters")
                for char in characters[:3]:
                    print(f"    {char['rank']}. {char['character']} (Level {char['level']}) - {char['class']}")
            else:
                print(f"  ⚠️  No characters found (league may not exist or be empty)")

        except Exception as e:
            print(f"  ❌ Error: {e}")

    await fetcher.close()
    await cache_manager.close()


if __name__ == "__main__":
    asyncio.run(test_ladder())
