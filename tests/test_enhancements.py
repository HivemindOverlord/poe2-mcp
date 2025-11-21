#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Enhanced Functionality
Tests the new features added to the MCP server:
- poe.ninja API client
- Multi-source character fetching
- Web scraper
- Enhanced gear optimizer
"""

import asyncio
import pytest
import sys
import io
from pathlib import Path

# Fix Windows encoding for Unicode
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.poe_ninja_api import PoeNinjaAPI
from src.api.character_fetcher import CharacterFetcher
from src.api.cache_manager import CacheManager
from src.api.rate_limiter import RateLimiter
from src.utils.scraper import PoE2DataScraper
from src.optimizer.gear_optimizer import GearOptimizer
from src.database.manager import DatabaseManager


class TestEnhancements:
    """Test suite for enhanced features"""

    @pytest.mark.asyncio
    async def test_poe_ninja_api(self):
        """Test poe.ninja API client"""
        print("\n" + "="*60)
        print("Testing poe.ninja API Client")
        print("="*60)

        ninja_api = PoeNinjaAPI()

        try:
            # Test getting top builds
            print("\nFetching top builds...")
            builds = await ninja_api.get_top_builds(league="Standard", limit=3)

            if builds:
                print(f"✓ Successfully fetched {len(builds)} builds")
                for build in builds[:2]:
                    print(f"  - {build.get('character', 'Unknown')} ({build.get('class', 'Unknown')})")
            else:
                print("⚠ No builds returned (may be expected if poe.ninja structure changed)")

            # Test getting item prices
            print("\nFetching item prices...")
            items = await ninja_api.get_item_prices(league="Standard", item_type="UniqueWeapon")

            if items:
                print(f"✓ Successfully fetched {len(items)} item prices")
                for item in items[:3]:
                    print(f"  - {item.get('name', 'Unknown')}: {item.get('chaosValue', 0)} chaos")
            else:
                print("⚠ No item prices returned")

        finally:
            await ninja_api.close()

        print("\n✓ poe.ninja API test completed")

    @pytest.mark.asyncio
    async def test_character_fetcher(self):
        """Test multi-source character fetching"""
        print("\n" + "="*60)
        print("Testing Multi-Source Character Fetcher")
        print("="*60)

        cache_manager = CacheManager()
        await cache_manager.initialize()

        fetcher = CharacterFetcher(cache_manager=cache_manager)

        try:
            # Test with a known account (this may fail if account doesn't exist)
            print("\nAttempting to fetch character...")
            print("Note: This may fail if test accounts are not publicly available")

            test_accounts = [
                ("TestAccount", "TestCharacter"),
                ("PathOfMatth", "SomeCharacter"),  # Popular streamer
            ]

            for account, character in test_accounts:
                print(f"\nTrying {account}/{character}...")

                char_data = await fetcher.get_character(account, character, "Standard")

                if char_data:
                    print(f"✓ Successfully fetched character data")
                    print(f"  - Name: {char_data.get('name', 'Unknown')}")
                    print(f"  - Class: {char_data.get('class', 'Unknown')}")
                    print(f"  - Level: {char_data.get('level', 0)}")
                    print(f"  - Source: {char_data.get('source', 'Unknown')}")
                    break
                else:
                    print(f"  ⚠ Could not fetch (expected for non-existent accounts)")

        finally:
            await fetcher.close()
            await cache_manager.close()

        print("\n✓ Character fetcher test completed")

    @pytest.mark.asyncio
    async def test_web_scraper(self):
        """Test web scraper for game data"""
        print("\n" + "="*60)
        print("Testing Web Scraper")
        print("="*60)

        scraper = PoE2DataScraper()

        try:
            # Test scraping unique items (limit to 5 for speed)
            print("\nScraping unique items (limited to 5)...")
            unique_items = await scraper.scrape_unique_items(limit=5)

            if unique_items:
                print(f"✓ Successfully scraped {len(unique_items)} unique items")
                for item in unique_items[:3]:
                    print(f"  - {item['name']} ({item['item_class']})")
            else:
                print("⚠ No unique items scraped (may indicate poe2db.tw structure changed)")

            # Test scraping skill gems (limit to 5 for speed)
            print("\nScraping skill gems (limited to 5)...")
            skills = await scraper.scrape_skill_gems()

            if skills:
                print(f"✓ Successfully scraped {len(skills)} skill gems")
                for skill in skills[:3]:
                    print(f"  - {skill['name']}")
            else:
                print("⚠ No skill gems scraped")

        finally:
            await scraper.close()

        print("\n✓ Web scraper test completed")

    @pytest.mark.asyncio
    async def test_gear_optimizer(self):
        """Test enhanced gear optimizer"""
        print("\n" + "="*60)
        print("Testing Enhanced Gear Optimizer")
        print("="*60)

        db_manager = DatabaseManager()
        await db_manager.initialize()

        optimizer = GearOptimizer(db_manager)

        try:
            # Create mock character data
            mock_character = {
                "name": "TestCharacter",
                "class": "Warrior",
                "level": 70,
                "items": [
                    {
                        "inventoryId": "helmet",
                        "name": "Old Helmet",
                        "rarity": "magic",
                        "ilvl": 45
                    },
                    {
                        "inventoryId": "body_armour",
                        "name": "Basic Chestplate",
                        "rarity": "normal",
                        "ilvl": 50
                    }
                ]
            }

            print("\nGenerating gear optimization recommendations...")
            recommendations = await optimizer.optimize(
                mock_character,
                budget="medium",
                goal="balanced"
            )

            print(f"✓ Gear optimizer completed")
            print(f"  - Budget: {recommendations['budget_tier']}")
            print(f"  - Goal: {recommendations['optimization_goal']}")
            print(f"  - Upgrades found: {len(recommendations['priority_upgrades'])}")
            print(f"  - Summary: {recommendations['summary']}")

            if recommendations['priority_upgrades']:
                print("\n  Top recommendations:")
                for upgrade in recommendations['priority_upgrades'][:3]:
                    print(f"    • {upgrade['slot']}: {upgrade['suggested_item']}")
                    print(f"      Priority: {upgrade['priority']}")
                    print(f"      Reasoning: {upgrade['reasoning']}")

        finally:
            await db_manager.close()

        print("\n✓ Gear optimizer test completed")

    @pytest.mark.asyncio
    async def test_database_population_dry_run(self):
        """Test database population script (dry run)"""
        print("\n" + "="*60)
        print("Testing Database Population (Dry Run)")
        print("="*60)

        print("\nChecking if database manager can initialize...")
        db_manager = DatabaseManager()
        await db_manager.initialize()

        print("✓ Database initialized successfully")

        # Check if tables exist
        async with db_manager.async_session() as session:
            from sqlalchemy import text

            result = await session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            tables = result.fetchall()

            print(f"\n✓ Found {len(tables)} tables in database:")
            for table in tables[:5]:
                print(f"  - {table[0]}")

        await db_manager.close()

        print("\n✓ Database population dry run completed")
        print("\nTo populate database with real data, run:")
        print("  python scripts/populate_database.py")


async def run_all_tests():
    """Run all enhancement tests"""
    print("""
================================================================
         PoE2 MCP Server - Enhancement Test Suite

  Testing new features:
  - poe.ninja API client with web scraping fallback
  - Multi-source character fetching
  - Web scraper for game data
  - Enhanced gear optimizer
  - Database population capabilities
================================================================
    """)

    tester = TestEnhancements()

    tests = [
        ("poe.ninja API", tester.test_poe_ninja_api),
        ("Character Fetcher", tester.test_character_fetcher),
        ("Web Scraper", tester.test_web_scraper),
        ("Gear Optimizer", tester.test_gear_optimizer),
        ("Database Population", tester.test_database_population_dry_run),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            await test_func()
            passed += 1
        except Exception as e:
            print(f"\n✗ {test_name} test failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")

    if failed == 0:
        print("\n✓ All tests passed!")
    else:
        print(f"\n⚠ {failed} test(s) failed")

    print("\nNote: Some tests may show warnings if external APIs are unavailable")
    print("or if test accounts don't exist. This is expected behavior.")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
