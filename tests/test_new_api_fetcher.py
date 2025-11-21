"""
Test the new API-based character fetcher
Tests with all 5 real characters from the test suite
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.poe_ninja_api import PoeNinjaAPI

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_new_api():
    """Test the new API-based character fetcher with real characters"""

    print("\n" + "="*80)
    print("NEW API CHARACTER FETCHER TEST")
    print("="*80)

    # Test characters from the real character test suite
    test_characters = [
        {
            "account": "Tomawar40-2671",
            "character": "DoesFireWorkGoodNow",
            "league": "Abyss"
        },
        {
            "account": "ITheCon-2183",
            "character": "SkadooshCorruptingArmy",
            "league": "Abyss"
        },
        {
            "account": "Aranoch-6282",
            "character": "Astrophobic",
            "league": "Abyss"
        }
    ]

    api = PoeNinjaAPI()

    results = {
        "success": 0,
        "failed": 0,
        "total": len(test_characters)
    }

    for i, char_info in enumerate(test_characters, 1):
        print(f"\n{'-'*80}")
        print(f"Test {i}/{len(test_characters)}: {char_info['character']}")
        print(f"{'-'*80}")

        try:
            char_data = await api.get_character(
                account=char_info["account"],
                character=char_info["character"],
                league=char_info["league"]
            )

            if char_data:
                print(f"\nSUCCESS!")
                print(f"   Name: {char_data.get('name', 'Unknown')}")
                print(f"   Class: {char_data.get('class', 'Unknown')}")
                print(f"   Level: {char_data.get('level', '?')}")
                print(f"   League: {char_data.get('league', 'Unknown')}")
                print(f"   Source: {char_data.get('source', 'unknown')}")

                # Show stats
                stats = char_data.get('stats', {})
                print(f"\n   Stats:")
                print(f"      Life: {stats.get('life', 0)}")
                print(f"      Energy Shield: {stats.get('energy_shield', 0)}")
                print(f"      Fire Res: {stats.get('fire_res', 0)}")
                print(f"      Cold Res: {stats.get('cold_res', 0)}")
                print(f"      Lightning Res: {stats.get('lightning_res', 0)}")

                results["success"] += 1
            else:
                print(f"\nFAILED: No data returned")
                results["failed"] += 1

        except Exception as e:
            print(f"\nEXCEPTION: {e}")
            logger.error(f"Exception details:", exc_info=True)
            results["failed"] += 1

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total Tests:  {results['total']}")
    print(f"Passed:       {results['success']}")
    print(f"Failed:       {results['failed']}")
    print(f"Success Rate: {(results['success']/results['total']*100):.1f}%")
    print("="*80)

    await api.close()

    return results["success"] == results["total"]


if __name__ == "__main__":
    success = asyncio.run(test_new_api())
    sys.exit(0 if success else 1)
