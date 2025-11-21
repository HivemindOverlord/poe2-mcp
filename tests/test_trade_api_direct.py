#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Direct test of PoE trade API to understand structure
"""

import asyncio
import httpx
import json


async def test_trade_endpoints():
    """Test different possible trade API endpoints"""

    print("Testing PoE2 Trade API Endpoints")
    print("="*80)

    client = httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }
    )

    # Test different possible endpoints
    endpoints = [
        ("PoE2 Trade Search", "https://www.pathofexile.com/trade2/search/poe2/Abyss"),
        ("PoE2 Trade Data", "https://www.pathofexile.com/api/trade2/data/leagues"),
        ("PoE1 Trade (for comparison)", "https://www.pathofexile.com/api/trade/data/leagues"),
    ]

    for name, url in endpoints:
        print(f"\nTesting: {name}")
        print(f"URL: {url}")
        print("-"*80)

        try:
            response = await client.get(url)
            print(f"Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type')}")
            print(f"Response length: {len(response.text)} bytes")

            if response.status_code == 200:
                # Try to parse as JSON
                try:
                    data = response.json()
                    print(f"✓ Valid JSON response")
                    print(f"Keys: {list(data.keys())}")
                    print(f"Sample: {json.dumps(data, indent=2)[:500]}")
                except:
                    print(f"✗ Not JSON, HTML response")
                    print(f"Preview: {response.text[:200]}")
            else:
                print(f"Error response: {response.text[:200]}")

        except Exception as e:
            print(f"❌ Error: {e}")

    # Test if we can access the trade site at all
    print("\n" + "="*80)
    print("Testing main trade page access:")
    print("="*80)

    try:
        response = await client.get("https://www.pathofexile.com/trade2/search/poe2/Abyss")
        print(f"Status: {response.status_code}")
        print(f"Can access trade site: {'✓ Yes' if response.status_code == 200 else '✗ No'}")

        if "poe2" in response.text.lower():
            print("✓ Page contains 'poe2' references")

        # Check for any JSON data in the page
        if "__NEXT_DATA__" in response.text or "window.__" in response.text:
            print("✓ Page contains embedded data (client-side rendered)")
            print("   Note: This means we need to parse HTML or find the API the page uses")

    except Exception as e:
        print(f"❌ Error: {e}")

    await client.aclose()


if __name__ == "__main__":
    asyncio.run(test_trade_endpoints())
