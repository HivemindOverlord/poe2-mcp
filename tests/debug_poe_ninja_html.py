#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug poe.ninja HTML structure
Fetches and analyzes the actual HTML from poe.ninja builds page
"""

import asyncio
import sys
import io
import httpx
from pathlib import Path
from bs4 import BeautifulSoup
import json
import re

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


async def fetch_and_analyze():
    """Fetch poe.ninja builds page and analyze structure"""

    url = "https://poe.ninja/poe2/builds/abyss"

    print(f"Fetching: {url}")
    print("="*80)

    client = httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )

    try:
        response = await client.get(url)

        print(f"Status Code: {response.status_code}")
        print(f"Content Length: {len(response.text):,} bytes")
        print("")

        if response.status_code != 200:
            print("Failed to fetch page!")
            return

        # Save HTML for inspection
        html_file = Path("poe_ninja_builds_debug.html")
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"✓ Saved HTML to: {html_file.absolute()}")

        # Parse with BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        # Look for scripts
        print("\n" + "="*80)
        print("ANALYZING SCRIPTS")
        print("="*80)

        scripts = soup.find_all('script')
        print(f"Found {len(scripts)} script tags")

        for i, script in enumerate(scripts):
            if not script.string:
                print(f"  [{i+1}] Script tag with src: {script.get('src', 'No src')}")
                continue

            script_content = script.string
            script_length = len(script_content)

            # Check for different data structures
            markers = []
            if 'window.__NUXT__' in script_content or '__NUXT__=' in script_content:
                markers.append("__NUXT__")
            if 'window.__data' in script_content:
                markers.append("__data")
            if 'window.__INITIAL_STATE__' in script_content:
                markers.append("__INITIAL_STATE__")
            if '"builds"' in script_content or '"characters"' in script_content:
                markers.append("builds/characters data")

            if markers:
                print(f"  [{i+1}] Script with {', '.join(markers)} ({script_length:,} chars)")

                # Try to extract and analyze
                if '__NUXT__=' in script_content:
                    print(f"       Attempting to parse NUXT data...")

                    try:
                        start_marker = '__NUXT__='
                        json_start = script_content.find(start_marker) + len(start_marker)
                        json_end = script_content.find(';', json_start)
                        if json_end == -1:
                            json_end = len(script_content)

                        json_str = script_content[json_start:json_end].strip()

                        nuxt_data = json.loads(json_str)

                        # Save for inspection
                        nuxt_file = Path("poe_ninja_nuxt_data.json")
                        with open(nuxt_file, 'w', encoding='utf-8') as f:
                            json.dump(nuxt_data, f, indent=2)

                        print(f"       ✓ Parsed NUXT data successfully!")
                        print(f"       ✓ Saved to: {nuxt_file.absolute()}")
                        print(f"       Top-level keys: {list(nuxt_data.keys())}")

                        # Analyze structure
                        analyze_nuxt_structure(nuxt_data)

                    except Exception as e:
                        print(f"       ❌ Failed to parse: {e}")

        # Look for data in HTML
        print("\n" + "="*80)
        print("ANALYZING HTML ELEMENTS")
        print("="*80)

        # Common class patterns
        patterns = [
            'build', 'character', 'player', 'ladder',
            'row', 'item', 'entry', 'card', 'list'
        ]

        for pattern in patterns:
            elements = soup.find_all(class_=re.compile(pattern, re.I))
            if elements:
                print(f"  Elements with class containing '{pattern}': {len(elements)}")

                # Show first element
                if elements:
                    first = elements[0]
                    print(f"    First element: <{first.name} class=\"{first.get('class', [])}\"")

    finally:
        await client.aclose()


def analyze_nuxt_structure(data, prefix="", max_depth=3, current_depth=0):
    """Recursively analyze NUXT data structure"""

    if current_depth >= max_depth:
        return

    if isinstance(data, dict):
        for key, value in data.items():
            value_type = type(value).__name__
            value_desc = ""

            if isinstance(value, list):
                value_desc = f"list[{len(value)}]"
                if len(value) > 0:
                    first_type = type(value[0]).__name__
                    value_desc += f" of {first_type}"

                    # Check if this looks like build data
                    if isinstance(value[0], dict):
                        first_keys = list(value[0].keys())[:5]
                        if any(k in ['character', 'name', 'class', 'level', 'account'] for k in first_keys):
                            value_desc += f" ⭐ POTENTIAL BUILDS (keys: {first_keys})"

            elif isinstance(value, dict):
                value_desc = f"dict with {len(value)} keys: {list(value.keys())[:5]}"
            elif isinstance(value, (str, int, float, bool)):
                if isinstance(value, str) and len(value) > 50:
                    value_desc = f"str[{len(value)}]"
                else:
                    value_desc = f"{value_type}: {repr(value)[:50]}"

            indent = "  " * current_depth
            print(f"{indent}{prefix}{key}: {value_desc}")

            # Recurse
            if isinstance(value, (dict, list)) and current_depth < max_depth - 1:
                analyze_nuxt_structure(value, f"{key}.", max_depth, current_depth + 1)

    elif isinstance(data, list) and len(data) > 0:
        print(f"{'  ' * current_depth}[List with {len(data)} items]")
        if isinstance(data[0], dict):
            print(f"{'  ' * current_depth}  First item keys: {list(data[0].keys())}")


if __name__ == "__main__":
    asyncio.run(fetch_and_analyze())
