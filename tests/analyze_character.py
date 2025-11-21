#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Detailed Character Analysis
Extracts and displays all character information in structured format
"""

import asyncio
import sys
import io
import json
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.character_fetcher import CharacterFetcher
from src.api.cache_manager import CacheManager
from src.api.rate_limiter import RateLimiter


async def fetch_and_analyze():
    """Fetch and analyze character"""

    print("="*80)
    print("POE2 CHARACTER ANALYZER")
    print("="*80)

    # Initialize
    cache_manager = CacheManager()
    await cache_manager.initialize()
    fetcher = CharacterFetcher(cache_manager=cache_manager, rate_limiter=RateLimiter(rate_limit=5))

    try:
        # Fetch character
        print("\nFetching character data...")
        char_data = await fetcher.get_character(
            "Tomawar40-2671",
            "DoesFireWorkGoodNow",
            "Standard"
        )

        if not char_data:
            print("❌ Failed to fetch character")
            return

        print("✓ Character data fetched successfully\n")

        # Analyze
        await analyze_character(char_data)

    finally:
        await fetcher.close()
        await cache_manager.close()


async def analyze_character(char_data: dict):
    """Comprehensive character analysis"""

    # ===== BASIC INFO =====
    print("\n" + "="*80)
    print("BASIC INFORMATION")
    print("="*80)
    print(f"Character Name:  {char_data.get('name', 'Unknown')}")
    print(f"Account:         {char_data.get('account', 'Unknown')}")
    print(f"Class:           {char_data.get('class', 'Unknown')}")
    print(f"Level:           {char_data.get('level', 0)}")
    print(f"League:          {char_data.get('league', 'Unknown')}")
    print(f"Experience:      {char_data.get('experience', 0):,}")

    # ===== STATS =====
    stats = char_data.get('stats', {})
    if stats:
        print("\n" + "="*80)
        print("CHARACTER STATS")
        print("="*80)

        # Defensive stats
        print("\nDefensive:")
        print(f"  Life:              {stats.get('life', 0):,}")
        print(f"  Energy Shield:     {stats.get('energyShield', 0):,}")
        print(f"  Mana:              {stats.get('mana', 0):,}")
        print(f"  Spirit:            {stats.get('spirit', 0)}")

        # Movement
        print(f"\nMovement:")
        print(f"  Speed:             {stats.get('movementSpeed', 0)}%")

        # Other stats
        other_stats = {k: v for k, v in stats.items()
                      if k not in ['life', 'energyShield', 'mana', 'spirit', 'movementSpeed']}
        if other_stats:
            print(f"\nOther Stats:")
            for key, value in other_stats.items():
                print(f"  {key}: {value}")

    # ===== EQUIPMENT =====
    items = char_data.get('items', [])
    print("\n" + "="*80)
    print(f"EQUIPMENT ({len(items)} items)")
    print("="*80)

    # Group items by slot
    slots = {}
    for item in items:
        item_data = item.get('itemData', item)
        slot = item_data.get('inventoryId', 'Unknown')
        if slot not in slots:
            slots[slot] = []
        slots[slot].append(item_data)

    # Display by slot
    slot_order = ['Helm', 'Amulet', 'BodyArmour', 'Ring', 'Ring2', 'Belt', 'Gloves', 'Boots',
                  'Weapon', 'Offhand', 'Weapon2', 'Offhand2', 'Flask', 'Flask2', 'Flask3',
                  'Flask4', 'Flask5', 'Trinket']

    for slot in slot_order:
        if slot in slots:
            for item_data in slots[slot]:
                print_item(item_data, slot)

    # Print remaining items not in standard slots
    for slot, slot_items in slots.items():
        if slot not in slot_order:
            for item_data in slot_items:
                print_item(item_data, slot)

    # ===== SKILLS =====
    skills = char_data.get('skills', [])
    print("\n" + "="*80)
    print(f"SKILLS ({len(skills)} skill groups)")
    print("="*80)

    for i, skill_group in enumerate(skills, 1):
        skill_data = skill_group.get('skillData', skill_group)

        # Main skill
        main_skill = skill_data.get('name', skill_data.get('id', 'Unknown'))
        print(f"\n[{i}] {main_skill}")

        # Slot info
        if 'slot' in skill_data:
            print(f"    Slot: {skill_data['slot']}")

        # Support gems
        supports = skill_data.get('supports', skill_data.get('supportGems', []))
        if supports:
            print(f"    Supports ({len(supports)}):")
            for support in supports:
                support_name = support.get('name', support.get('id', 'Unknown'))
                support_level = support.get('level', '?')
                print(f"      - {support_name} (Level {support_level})")

        # Socket info
        if 'sockets' in skill_data:
            print(f"    Sockets: {skill_data['sockets']}")

    # ===== PASSIVES =====
    passive_tree = char_data.get('passive_tree', char_data.get('passives', {}))
    print("\n" + "="*80)
    print("PASSIVE TREE")
    print("="*80)

    if isinstance(passive_tree, dict):
        hashes = passive_tree.get('hashes', passive_tree.get('nodes', []))
        if hashes:
            print(f"Allocated Nodes: {len(hashes)}")
            print(f"First 10 node IDs: {hashes[:10]}")
        else:
            print("No passive node data available")
    elif isinstance(passive_tree, list):
        print(f"Allocated Nodes: {len(passive_tree)}")
        if passive_tree:
            print(f"First 10 node IDs: {passive_tree[:10]}")
    else:
        print("Passive tree data structure unknown")

    # ===== RAW DATA SUMMARY =====
    print("\n" + "="*80)
    print("RAW DATA STRUCTURE")
    print("="*80)
    print(f"Top-level keys: {list(char_data.keys())}")
    print(f"\nTotal data size: ~{len(json.dumps(char_data))} characters")

    # Save to file
    output_file = Path("character_data_full.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(char_data, f, indent=2)
    print(f"\nFull data saved to: {output_file.absolute()}")


def print_item(item_data: dict, slot: str):
    """Print item details"""
    name = item_data.get('name', '').strip()
    type_line = item_data.get('typeLine', '').strip()
    display_name = name if name else type_line

    ilvl = item_data.get('ilvl', '?')
    corrupted = " [CORRUPTED]" if item_data.get('corrupted') else ""

    print(f"\n{slot}:")
    print(f"  {display_name} (iLvl {ilvl}){corrupted}")

    # Implicit mods
    implicit_mods = item_data.get('implicitMods', [])
    if implicit_mods:
        print(f"  Implicit:")
        for mod in implicit_mods:
            print(f"    - {mod}")

    # Explicit mods
    explicit_mods = item_data.get('explicitMods', [])
    if explicit_mods:
        print(f"  Explicit:")
        for mod in explicit_mods[:5]:  # Limit to 5 mods
            print(f"    - {mod}")
        if len(explicit_mods) > 5:
            print(f"    ... and {len(explicit_mods) - 5} more mods")

    # Enchant
    enchant_mods = item_data.get('enchantMods', [])
    if enchant_mods:
        print(f"  Enchant:")
        for mod in enchant_mods:
            print(f"    - {mod}")

    # Sockets
    sockets = item_data.get('sockets', item_data.get('socketCount', 0))
    if sockets:
        if isinstance(sockets, int):
            print(f"  Sockets: {sockets}")
        else:
            print(f"  Sockets: {len(sockets)}")


if __name__ == "__main__":
    asyncio.run(fetch_and_analyze())
