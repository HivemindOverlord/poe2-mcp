"""
Test PoB Import Functionality
Tests the poe.ninja PoB import API endpoint
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.poe_ninja_api import PoeNinjaAPI


async def test_pob_import():
    """Test fetching PoB codes from poe.ninja"""

    print("=" * 80)
    print("POB IMPORT API TEST")
    print("=" * 80)
    print()

    # Test characters
    test_characters = [
        {
            "account": "Tomawar40-2671",
            "character": "DoesFireWorkGoodNow",
            "description": "Primary test character (Stormweaver)"
        },
        {
            "account": "ITheCon-2183",
            "character": "SkadooshCorruptingArmy",
            "description": "Secondary test character (Warbringer)"
        },
    ]

    api = PoeNinjaAPI()

    for i, char_info in enumerate(test_characters, 1):
        print(f"[{i}/{len(test_characters)}] Testing: {char_info['character']}")
        print(f"   Description: {char_info['description']}")
        print()

        try:
            # Fetch PoB code
            pob_code = await api.get_pob_import(
                account=char_info["account"],
                character=char_info["character"]
            )

            if pob_code:
                print(f"   SUCCESS!")

                # Check if it's a dict or string
                if isinstance(pob_code, dict):
                    print(f"   Response type: dict (API response)")
                    print(f"   Response keys: {list(pob_code.keys())}")

                    # Try to find the actual code
                    actual_code = pob_code.get("pob") or pob_code.get("code") or pob_code.get("build")
                    if actual_code:
                        print(f"   PoB code found: {actual_code[:50]}..." if len(actual_code) > 50 else f"   PoB code: {actual_code}")
                    else:
                        print(f"   WARNING: Could not find PoB code in response")
                        print(f"   Full response: {pob_code}")

                elif isinstance(pob_code, str):
                    print(f"   Response type: string (PoB code)")
                    print(f"   Code length: {len(pob_code)} characters")
                    print(f"   Code preview: {pob_code[:100]}...")

                    # Basic validation - PoB codes are base64
                    if pob_code.isalnum() or '+' in pob_code or '/' in pob_code or '=' in pob_code:
                        print(f"   FORMAT: Looks like valid base64 encoding")
                    else:
                        print(f"   WARNING: Doesn't look like base64")
                else:
                    print(f"   WARNING: Unexpected response type: {type(pob_code)}")

            else:
                print(f"   FAILED: No PoB code returned (character may not be on poe.ninja)")

        except Exception as e:
            print(f"   EXCEPTION: {e}")
            import traceback
            traceback.print_exc()

        print()

    await api.close()

    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_pob_import())
