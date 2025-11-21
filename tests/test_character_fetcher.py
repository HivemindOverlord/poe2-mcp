"""
Test script for character fetcher
Tests fetching character data from poe.ninja without OAuth2
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.character_fetcher import CharacterFetcher
from src.api.cache_manager import CacheManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_poe_ninja_fetch():
    """Test fetching character from poe.ninja"""
    print("\n" + "="*60)
    print("Testing Character Fetcher - poe.ninja")
    print("="*60 + "\n")

    # Test with the example character from user's HAR file
    account_name = "Tomawar40-2671"
    character_name = "DoesFireWorkGoodNow"

    async with CharacterFetcher() as fetcher:
        print(f"Fetching character: {account_name}/{character_name}")
        print("-" * 60)

        character_data = await fetcher.get_character_from_poe_ninja(
            account_name=account_name,
            character_name=character_name
        )

        if character_data:
            print("\n[SUCCESS] Character data retrieved:")
            print("-" * 60)
            print(f"Name: {character_data.get('name')}")
            print(f"Account: {character_data.get('account')}")
            print(f"Level: {character_data.get('level')}")
            print(f"Class: {character_data.get('class')}")
            print(f"League: {character_data.get('league')}")
            print(f"Experience: {character_data.get('experience')}")
            print(f"\nItems found: {len(character_data.get('items', []))}")
            print(f"Skills found: {len(character_data.get('skills', []))}")
            print("-" * 60)

            # Print raw data for debugging
            if character_data.get('raw_data'):
                print("\nRaw data keys:", list(character_data['raw_data'].keys()))
                import json
                print("\nFull character data:")
                print(json.dumps(character_data, indent=2, default=str)[:2000])

            return True
        else:
            print("\n[FAILED] Could not retrieve character data")
            print("This might be because:")
            print("  1. poe.ninja uses heavy client-side rendering")
            print("  2. The character profile is private")
            print("  3. We need to reverse engineer their API")
            return False

async def test_ladder_fetch():
    """Test fetching from public ladder API"""
    print("\n" + "="*60)
    print("Testing Character Fetcher - Ladder API")
    print("="*60 + "\n")

    # This will only work for characters in top of ladder
    character_name = "DoesFireWorkGoodNow"  # May not be in top 1000

    async with CharacterFetcher() as fetcher:
        print(f"Searching ladder for: {character_name}")
        print("-" * 60)

        character_data = await fetcher.get_character_from_ladder(
            character_name=character_name,
            league="Standard"  # Try Standard league
        )

        if character_data:
            print("\n[SUCCESS] Found character in ladder:")
            print("-" * 60)
            print(f"Name: {character_data.get('name')}")
            print(f"Account: {character_data.get('account')}")
            print(f"Level: {character_data.get('level')}")
            print(f"Class: {character_data.get('class')}")
            print(f"Rank: {character_data.get('rank')}")
            print("-" * 60)
            return True
        else:
            print("\n[FAILED] Character not found in top 1000 of ladder")
            print("Note: Ladder API only works for highly ranked characters")
            return False

async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("CHARACTER FETCHER TEST SUITE")
    print("="*60)

    # Test 1: poe.ninja
    poe_ninja_success = await test_poe_ninja_fetch()

    # Small delay between tests
    await asyncio.sleep(2)

    # Test 2: Ladder API
    ladder_success = await test_ladder_fetch()

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"poe.ninja fetch: {'[PASSED]' if poe_ninja_success else '[FAILED]'}")
    print(f"Ladder API fetch: {'[PASSED]' if ladder_success else '[FAILED]'}")
    print("="*60 + "\n")

    if not poe_ninja_success and not ladder_success:
        print("WARNING - NEXT STEPS:")
        print("  Since both methods failed, we need to:")
        print("  1. Inspect the actual poe.ninja page to find their API")
        print("  2. Or implement a proper headless browser scraper")
        print("  3. Or use a different data source")

if __name__ == "__main__":
    asyncio.run(main())
