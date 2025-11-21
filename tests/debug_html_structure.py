"""
Debug script to examine the HTML structure from poe.ninja
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.poe_ninja_api import PoeNinjaAPI


async def debug_html():
    """Fetch and save HTML to examine structure"""

    api = PoeNinjaAPI()

    # Build the URL manually
    account = "Tomawar40-2671"
    character = "DoesFireWorkGoodNow"
    league = "abyss"

    url = f"https://poe.ninja/poe2/builds/{league}/character/{account}/{character}"

    print(f"Fetching: {url}")

    response = await api.client.get(url)

    if response.status_code == 200:
        html = response.text
        print(f"Got HTML: {len(html)} chars")

        # Save to file
        output_file = Path(__file__).parent / "debug_poe_ninja_response.html"
        output_file.write_text(html, encoding='utf-8')
        print(f"Saved to: {output_file}")

        # Look for script tags
        if 'window.__NUXT__' in html:
            print("Found: window.__NUXT__")
            start_idx = html.find('window.__NUXT__')
            snippet = html[start_idx:start_idx+200]
            print(f"Snippet: {snippet}")

        if 'window.__data' in html:
            print("Found: window.__data")
            start_idx = html.find('window.__data')
            snippet = html[start_idx:start_idx+200]
            print(f"Snippet: {snippet}")

        if '__NUXT__' in html:
            print("Found: __NUXT__ (without window.)")
            start_idx = html.find('__NUXT__')
            snippet = html[start_idx:start_idx+200]
            print(f"Snippet: {snippet}")

        # Check for any JSON-like structures
        if '"character":' in html or '"name":"DoesFireWorkGoodNow"' in html:
            print("Found character data in HTML!")

        # Count script tags
        import re
        scripts = re.findall(r'<script[^>]*>', html)
        print(f"Found {len(scripts)} script tags")

    else:
        print(f"Failed: {response.status_code}")

    await api.close()


if __name__ == "__main__":
    asyncio.run(debug_html())
