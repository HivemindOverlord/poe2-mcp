"""
Test character fetching from user-provided poe.ninja URLs
Tests both /profile/ and /builds/ URL formats
"""

import asyncio
import sys
import json
import logging
from pathlib import Path
import os

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    # Use UTF-8 encoding for stdout
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from api.character_fetcher import CharacterFetcher
from api.poe_ninja_api import PoeNinjaAPI
from api.rate_limiter import RateLimiter
from api.cache_manager import CacheManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def parse_poe_ninja_url(url: str):
    """
    Parse poe.ninja URL to extract account, character, and league

    URL formats:
    1. /poe2/profile/{account}/character/{character}
    2. /poe2/builds/{league}/character/{account}/{character}
    """
    import urllib.parse

    # Parse URL
    parsed = urllib.parse.urlparse(url)
    path_parts = parsed.path.strip('/').split('/')

    logger.info(f"Parsing URL: {url}")
    logger.info(f"Path parts: {path_parts}")

    if 'profile' in path_parts:
        # Format: /poe2/profile/{account}/character/{character}
        try:
            profile_idx = path_parts.index('profile')
            account = path_parts[profile_idx + 1]
            character_idx = path_parts.index('character')
            character = path_parts[character_idx + 1]
            league = "Abyss"  # Default league

            return {
                'account': account,
                'character': character,
                'league': league,
                'url_type': 'profile'
            }
        except (IndexError, ValueError) as e:
            logger.error(f"Failed to parse profile URL: {e}")
            return None

    elif 'builds' in path_parts:
        # Format: /poe2/builds/{league}/character/{account}/{character}
        try:
            builds_idx = path_parts.index('builds')
            league = path_parts[builds_idx + 1]
            character_idx = path_parts.index('character')
            account = path_parts[character_idx + 1]
            character = path_parts[character_idx + 2]

            # Decode URL-encoded characters (e.g., %EC%97%90...)
            account = urllib.parse.unquote(account)
            character = urllib.parse.unquote(character)

            return {
                'account': account,
                'character': character,
                'league': league,
                'url_type': 'builds'
            }
        except (IndexError, ValueError) as e:
            logger.error(f"Failed to parse builds URL: {e}")
            return None

    else:
        logger.error(f"Unknown URL format: {url}")
        return None


async def test_url(url: str, fetcher: CharacterFetcher):
    """Test fetching a single URL"""
    print("\n" + "="*80)
    print(f"Testing URL: {url}")
    print("="*80)

    # Parse URL
    parsed = parse_poe_ninja_url(url)
    if not parsed:
        print("❌ Failed to parse URL")
        return None

    print(f"Parsed: account={parsed['account']}, character={parsed['character']}, league={parsed['league']}, type={parsed['url_type']}")

    # Try to fetch
    try:
        char_data = await fetcher.get_character(
            account_name=parsed['account'],
            character_name=parsed['character'],
            league=parsed['league']
        )

        if char_data:
            print(f"✅ SUCCESS!")
            print(f"   Name: {char_data.get('name')}")
            print(f"   Class: {char_data.get('class')}")
            print(f"   Level: {char_data.get('level')}")
            print(f"   League: {char_data.get('league')}")
            print(f"   Source: {char_data.get('source')}")

            # Check if we have stats
            stats = char_data.get('stats', {})
            if stats and isinstance(stats, dict):
                print(f"   Life: {stats.get('life', 'N/A')}")
                print(f"   ES: {stats.get('energy_shield', 'N/A')}")
                print(f"   Fire Res: {stats.get('fire_res', 'N/A')}")
            elif isinstance(char_data.get('life'), (int, float)):
                # Stats at top level
                print(f"   Life: {char_data.get('life', 'N/A')}")
                print(f"   ES: {char_data.get('energy_shield', 'N/A')}")
                print(f"   Fire Res: {char_data.get('fire_res', 'N/A')}")

            # Check items
            items = char_data.get('items', [])
            print(f"   Items: {len(items)} equipped")

            # Check skills
            skills = char_data.get('skills', [])
            skill_dps = char_data.get('skill_dps', [])
            print(f"   Skills: {len(skills)} skills")
            print(f"   Skill DPS: {len(skill_dps)} entries")

            return char_data
        else:
            print("❌ FAILED: No data returned")
            return None

    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Main test function"""
    print("="*80)
    print("Character Fetching Test - User-Provided URLs")
    print("="*80)

    # URLs to test
    test_urls = [
        "https://poe.ninja/poe2/profile/Tomawar40-2671/character/DoesFireWorkGoodNow",
        "https://poe.ninja/poe2/builds/abyss/character/%EC%97%90%EC%8A%A4%ED%84%B0%EB%85%B8%EC%9D%B4%EB%93%9C-4045/kabooooman?i=0&search=min-level%3D91%26max-level%3D94",
        "https://poe.ninja/poe2/builds/abyss/character/ITheCon-2183/SkadooshCorruptingArmy",
        "https://poe.ninja/poe2/builds/abyss/character/_Sacrum_-1747/Jebac_Ukraincow?i=3&search=min-level%3D91%26max-level%3D94",
        "https://poe.ninja/poe2/builds/abyss/character/Aranoch-6282/Astrophobic"
    ]

    # Initialize fetcher
    rate_limiter = RateLimiter(rate_limit=5)  # Be gentle with API
    cache_manager = CacheManager()

    fetcher = CharacterFetcher(
        cache_manager=cache_manager,
        rate_limiter=rate_limiter
    )

    # Test each URL
    results = []
    for url in test_urls:
        result = await test_url(url, fetcher)
        results.append({
            'url': url,
            'success': result is not None,
            'data': result
        })

        # Wait between requests to be nice to the API
        await asyncio.sleep(2)

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    success_count = sum(1 for r in results if r['success'])
    print(f"Successful: {success_count}/{len(results)}")

    for i, result in enumerate(results, 1):
        status = "✅" if result['success'] else "❌"
        print(f"{status} URL {i}: {result['url'][:80]}...")

    # Save results to file
    output_file = Path(__file__).parent / "test_results_user_urls.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    print(f"\nFull results saved to: {output_file}")

    # Close resources
    await fetcher.close()

    return results


if __name__ == "__main__":
    asyncio.run(main())
