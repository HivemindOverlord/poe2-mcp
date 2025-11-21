"""Fetch the API client module to find the endpoint"""

import asyncio
import httpx
import re


async def fetch_api_client():
    async with httpx.AsyncClient() as client:
        # Fetch the API client module
        url = "https://poe.ninja/chunk.BmqzvNR7.mjs"
        print(f"Fetching: {url}")

        response = await client.get(url)
        js_code = response.text

        print(f"Got {len(js_code)} chars of JavaScript\n")

        # Look for API endpoints - more specific patterns
        patterns = [
            r'https?://[^"\']+',
            r'/api/[^"\']+',
            r'"/poe2?/[^"\']+',
            r'`[^`]*\/api[^`]*`',
            r'fetch\([^)]+\)',
        ]

        print("=== Searching for API endpoints ===\n")
        for pattern in patterns:
            matches = re.findall(pattern, js_code)
            if matches:
                print(f"Pattern: {pattern}")
                for match in set(matches[:10]):  # Unique, first 10
                    print(f"  {match}")
                print()

        # Save full JS
        with open("tests/debug_api_client.js", "w", encoding="utf-8") as f:
            f.write(js_code)
        print(f"Saved full JavaScript to tests/debug_api_client.js")

        # Look for getCharacter function specifically
        if "getCharacter" in js_code:
            print("\n=== Found getCharacter function ===")
            start = js_code.find("getCharacter")
            snippet = js_code[max(0, start-200):start+500]
            print(snippet)


if __name__ == "__main__":
    asyncio.run(fetch_api_client())
