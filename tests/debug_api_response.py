"""
Debug API Response Format
Shows exactly what poe.ninja API returns
"""

import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.poe_ninja_api import PoeNinjaAPI


async def debug_api_response():
    """Debug the actual API response"""

    print("=" * 80)
    print("DEBUG: POE.NINJA API RESPONSE FORMAT")
    print("=" * 80)
    print()

    api = PoeNinjaAPI()

    # Test character
    account = "Tomawar40-2671"
    character = "DoesFireWorkGoodNow"
    league = "Abyss"

    print(f"Fetching: {character} (Account: {account}, League: {league})")
    print()

    try:
        # Get index state first
        index_state = await api._get_index_state()

        if index_state:
            print("INDEX STATE RECEIVED:")
            print(f"  Snapshot versions available: {len(index_state.get('snapshotVersions', []))}")

            # Find our league
            league_slug = api._get_league_slug(league)
            snapshot = None
            for snap in index_state.get("snapshotVersions", []):
                if snap.get("url") == league_slug:
                    snapshot = snap
                    break

            if snapshot:
                print(f"  Found snapshot for '{league}' (slug: '{league_slug}')")
                print(f"  Version: {snapshot.get('version')}")
                print(f"  Snapshot name: {snapshot.get('snapshotName')}")
                print()

                # Now fetch character
                version = snapshot.get("version")
                overview = snapshot.get("snapshotName")

                url = f"{api.base_url}/poe2/api/builds/{version}/character"
                params = {
                    "account": account,
                    "name": character,
                    "overview": overview
                }

                print(f"CALLING API:")
                print(f"  URL: {url}")
                print(f"  Params: {params}")
                print()

                response = await api.client.get(url, params=params)

                print(f"RESPONSE STATUS: {response.status_code}")
                print()

                if response.status_code == 200:
                    data = response.json()

                    print("RESPONSE STRUCTURE:")
                    print(f"  Top-level keys: {list(data.keys())}")
                    print()

                    # Show each top-level field
                    for key in data.keys():
                        value = data[key]
                        if isinstance(value, dict):
                            print(f"  {key}: {{...}} (dict with {len(value)} keys)")
                            print(f"    Keys: {list(value.keys())[:10]}")
                        elif isinstance(value, list):
                            print(f"  {key}: [...] (list with {len(value)} items)")
                        else:
                            print(f"  {key}: {value}")

                    print()
                    print("=" * 80)
                    print("DEFENSIVE STATS:")
                    print("=" * 80)

                    defensive_stats = data.get("defensiveStats", {})
                    if defensive_stats:
                        print(json.dumps(defensive_stats, indent=2))
                    else:
                        print("  No defensiveStats field found!")

                    print()
                    print("=" * 80)
                    print("FULL RAW RESPONSE:")
                    print("=" * 80)
                    print(json.dumps(data, indent=2))

                else:
                    print(f"ERROR: Status {response.status_code}")
                    print(f"Response: {response.text}")
            else:
                print(f"ERROR: No snapshot found for league '{league}'")
        else:
            print("ERROR: Could not fetch index state")

    except Exception as e:
        print(f"EXCEPTION: {e}")
        import traceback
        traceback.print_exc()

    await api.close()


if __name__ == "__main__":
    asyncio.run(debug_api_response())
