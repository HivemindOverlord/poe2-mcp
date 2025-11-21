#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Character Comparison System
Tests the full workflow of comparing user's character against top players
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

from src.api.cache_manager import CacheManager
from src.api.rate_limiter import RateLimiter
from src.analyzer.top_player_fetcher import TopPlayerFetcher
from src.analyzer.character_comparator import CharacterComparator


async def test_comparison_system():
    """Test the full comparison workflow"""

    print("="*80)
    print("CHARACTER COMPARISON SYSTEM TEST")
    print("="*80)

    # Initialize
    print("\n[1/5] Initializing components...")
    cache_manager = CacheManager()
    await cache_manager.initialize()

    rate_limiter = RateLimiter(rate_limit=5)
    top_player_fetcher = TopPlayerFetcher(
        cache_manager=cache_manager,
        rate_limiter=rate_limiter
    )
    comparator = CharacterComparator()

    print("✓ Components initialized")

    try:
        # Load user's character data
        print("\n[2/5] Loading user's character data...")
        character_file = Path("character_data_full.json")

        if not character_file.exists():
            print("❌ character_data_full.json not found!")
            print("   Run tests/analyze_character.py first to fetch character data")
            return

        with open(character_file, 'r', encoding='utf-8') as f:
            user_character = json.load(f)

        print(f"✓ Loaded character: {user_character.get('name', 'Unknown')}")
        print(f"  Level: {user_character.get('level', 0)}")
        print(f"  Class: {user_character.get('class', 'Unknown')}")
        print(f"  League: {user_character.get('league', 'Unknown')}")

        # Extract skills
        print("\n[3/5] Extracting main skills...")
        user_skills = comparator.extract_main_skills(user_character)
        print(f"✓ Detected skills: {user_skills if user_skills else 'None detected'}")

        # Find similar top players
        print("\n[4/5] Finding similar top players...")
        print("  (This may take a few minutes due to rate limiting...)")

        league = user_character.get('league', 'Standard')
        top_players = await top_player_fetcher.find_similar_top_players(
            user_character,
            league=league,
            min_level=user_character.get('level', 90) - 5,  # Allow 5 levels below
            limit=10
        )

        if not top_players:
            print("⚠️  No similar top players found")
            print("   This could be because:")
            print("   - The league is not active on poe.ninja")
            print("   - No players with similar skills found")
            print("   - API rate limiting or connectivity issues")

            # Try with relaxed criteria (remove class filter)
            print("\n   Trying with relaxed criteria (any class, lower level)...")

            # Create a copy without class filter
            relaxed_char = user_character.copy()
            relaxed_char['class'] = ""  # Remove class filter

            top_players = await top_player_fetcher.find_similar_top_players(
                relaxed_char,
                league=league,
                min_level=85,  # Lower minimum level
                limit=10
            )

        if top_players:
            print(f"✓ Found {len(top_players)} similar top players")
            for i, player in enumerate(top_players[:3], 1):
                print(f"  {i}. {player.get('name', 'Unknown')} - Level {player.get('level', '?')}")
        else:
            print("❌ Could not find any top players to compare against")
            print("   Skipping comparison test")
            return

        # Perform comparison
        print("\n[5/5] Performing detailed comparison...")
        comparison = comparator.compare_to_top_players(
            user_character,
            top_players,
            comparison_focus="balanced"
        )

        print("✓ Comparison completed")

        # Display results
        print("\n" + "="*80)
        print("COMPARISON RESULTS")
        print("="*80)

        # Summary
        pool = comparison.get('comparison_pool', {})
        print(f"\n📊 Comparison Pool:")
        print(f"  Players analyzed: {pool.get('count', 0)}")
        print(f"  Average level: {pool.get('avg_level', 0):.1f}")
        print(f"  Level range: {pool.get('min_level', 0)} - {pool.get('max_level', 0)}")

        # Key differences
        differences = comparison.get('key_differences', [])
        if differences:
            print(f"\n🔍 Key Differences Found:")
            for i, diff in enumerate(differences[:5], 1):
                print(f"  {i}. {diff}")

        # Recommendations
        recommendations = comparison.get('recommendations', [])
        if recommendations:
            print(f"\n💡 Top Recommendations:")
            for i, rec in enumerate(recommendations[:5], 1):
                print(f"  {i}. {rec}")

        # Gear comparison
        gear_comp = comparison.get('gear_comparison', {})
        if gear_comp:
            popular_uniques = gear_comp.get('popular_uniques', {})
            if popular_uniques:
                print(f"\n🛡️  Popular Unique Items (Top 5):")
                for item, count in list(popular_uniques.items())[:5]:
                    percentage = (count / pool.get('count', 1)) * 100
                    print(f"  - {item}: {percentage:.0f}% of players")

        # Skill comparison
        skill_comp = comparison.get('skill_comparison', {})
        if skill_comp:
            common_supports = skill_comp.get('common_supports_in_top_players', {})
            if common_supports:
                print(f"\n💎 Popular Support Gems (Top 5):")
                for support, count in list(common_supports.items())[:5]:
                    percentage = (count / pool.get('count', 1)) * 100
                    print(f"  - {support}: {percentage:.0f}% of players")

        # Stat highlights
        stat_comp = comparison.get('stat_comparison', {})
        if stat_comp:
            print(f"\n📈 Your Stat Percentiles (Key Stats):")
            key_stats = ['life', 'energyShield', 'fireResistance', 'coldResistance', 'lightningResistance']
            for stat in key_stats:
                if stat in stat_comp:
                    data = stat_comp[stat]
                    percentile = data.get('percentile', 0)
                    status = "⬆️ " if percentile > 75 else "⬇️ " if percentile < 25 else "➡️ "
                    print(f"  {status}{stat}: {percentile:.0f}th percentile ({data.get('user', 0)} vs avg {data.get('average', 0):.0f})")

        # Save detailed report
        print("\n" + "="*80)
        output_file = Path("comparison_report.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(comparison, f, indent=2)
        print(f"✓ Detailed report saved to: {output_file.absolute()}")

        print("\n" + "="*80)
        print("✅ TEST COMPLETED SUCCESSFULLY")
        print("="*80)

    except Exception as e:
        print(f"\n❌ Test failed with error:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await top_player_fetcher.close()
        await cache_manager.close()


if __name__ == "__main__":
    asyncio.run(test_comparison_system())
