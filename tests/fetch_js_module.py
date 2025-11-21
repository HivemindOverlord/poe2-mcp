"""Fetch the JavaScript module to find the API endpoint"""

import asyncio
import httpx
import re


async def fetch_js():
    async with httpx.AsyncClient() as client:
        # Fetch the JavaScript module
        url = "https://poe.ninja/chunk.DxzkaMfg.mjs"
        print(f"Fetching: {url}")

        response = await client.get(url)
        js_code = response.text

        print(f"Got {len(js_code)} chars of JavaScript")

        # Look for API endpoints
        api_patterns = [
            r'https?://[^"\']+/api/[^"\']+',
            r'"/api/[^"\']+',
            r'fetch\([^)]+\)',
            r'\.get\([^)]+\)',
        ]

        print("\n=== Found API Patterns ===")
        for pattern in api_patterns:
            matches = re.findall(pattern, js_code)
            if matches:
                print(f"\nPattern: {pattern}")
                for match in matches[:5]:  # First 5 matches
                    print(f"  {match}")

        # Save full JS
        with open("tests/debug_poe_ninja_module.js", "w", encoding="utf-8") as f:
            f.write(js_code)
        print(f"\nSaved full JavaScript to tests/debug_poe_ninja_module.js")


if __name__ == "__main__":
    asyncio.run(fetch_js())
