"""Test the discovered poe.ninja API endpoint"""

import asyncio
import httpx
import json


async def test_api():
    # Try different version values
    versions = ["1", "latest", "v1", ""]

    account = "Tomawar40-2671"
    name = "DoesFireWorkGoodNow"
    overview = "abyss"

    async with httpx.AsyncClient() as client:
        for version in versions:
            if version:
                url = f"https://poe.ninja/poe2/api/builds/{version}/character"
            else:
                url = "https://poe.ninja/poe2/api/builds/character"

            params = {
                "account": account,
                "name": name,
                "overview": overview
            }

            print(f"\nTrying: {url}")
            print(f"Params: {params}")

            try:
                response = await client.get(url, params=params)
                print(f"Status: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    print(f"SUCCESS! Got JSON response")
                    print(f"Keys: {list(data.keys())[:10]}")

                    # Save response
                    with open(f"tests/api_response_version_{version or 'none'}.json", "w") as f:
                        json.dump(data, f, indent=2)
                    print(f"Saved to: tests/api_response_version_{version or 'none'}.json")

                    # Show character info
                    if "name" in data:
                        print(f"\nCharacter Name: {data.get('name')}")
                        print(f"Level: {data.get('level')}")
                        print(f"Class: {data.get('class')}")
                    break
                else:
                    print(f"Failed: {response.status_code}")
                    print(f"Response: {response.text[:200]}")

            except Exception as e:
                print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_api())
