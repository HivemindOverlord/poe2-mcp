"""
Analyze Astrophobic character to demonstrate weakness detection
"""

import asyncio
import sys
import json
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.api.character_fetcher import CharacterFetcher
from src.api.rate_limiter import RateLimiter
from src.api.cache_manager import CacheManager
from src.analyzer.weakness_detector import WeaknessDetector, CharacterData


async def main():
    """Analyze Astrophobic character"""
    print("="*80)
    print("Character Weakness Analysis - Astrophobic")
    print("="*80)
    print()

    # Initialize fetcher
    rate_limiter = RateLimiter(rate_limit=5)
    cache_manager = CacheManager()
    fetcher = CharacterFetcher(cache_manager=cache_manager, rate_limiter=rate_limiter)

    # Fetch character
    print("Fetching character data...")
    char_data = await fetcher.get_character(
        account_name="Aranoch-6282",
        character_name="Astrophobic",
        league="abyss"
    )

    if not char_data:
        print("❌ Failed to fetch character")
        return

    print(f"✅ Fetched: {char_data['name']} - Level {char_data['level']} {char_data['class']}")
    print()

    # Extract stats for weakness detection
    stats = char_data.get('stats', {})

    # Handle stats being at top level or nested
    def get_stat(key, default=0):
        if stats:
            return stats.get(key, char_data.get(key, default))
        return char_data.get(key, default)

    char_for_analysis = CharacterData(
        level=char_data.get('level', 0),
        character_class=char_data.get('class', 'Unknown'),
        life=get_stat('life', 0),
        energy_shield=get_stat('energy_shield', 0),
        mana=get_stat('mana', 0),
        spirit_max=get_stat('spirit', 0),
        spirit_reserved=0,  # Would need to calculate from skills
        strength=get_stat('strength', 0),
        dexterity=get_stat('dexterity', 0),
        intelligence=get_stat('intelligence', 0),
        armor=get_stat('armor', 0),
        evasion=get_stat('evasion', 0),
        block_chance=get_stat('block_chance', 0),
        fire_res=get_stat('fire_res', 0),
        cold_res=get_stat('cold_res', 0),
        lightning_res=get_stat('lightning_res', 0),
        chaos_res=get_stat('chaos_res', 0)
    )

    print("Character Stats:")
    print(f"  Life: {char_for_analysis.life}")
    print(f"  Energy Shield: {char_for_analysis.energy_shield}")
    print(f"  Mana: {char_for_analysis.mana}")
    print(f"  Fire Res: {char_for_analysis.fire_res}%")
    print(f"  Cold Res: {char_for_analysis.cold_res}%")
    print(f"  Lightning Res: {char_for_analysis.lightning_res}%")
    print(f"  Chaos Res: {char_for_analysis.chaos_res}%")
    print(f"  Armor: {char_for_analysis.armor}")
    print(f"  Evasion: {char_for_analysis.evasion}")
    print()

    # Run weakness detection
    print("Running weakness detection...")
    detector = WeaknessDetector()
    weaknesses = detector.detect_all_weaknesses(char_for_analysis)

    # Print full report
    report = detector.format_weakness_report(weaknesses, include_low_severity=False)
    print(report)

    # Get summary
    summary = detector.get_weakness_summary(char_for_analysis)
    print()
    print("="*80)
    print("ACTIONABLE INSIGHTS")
    print("="*80)
    print(f"Total Issues Found: {summary['total_weaknesses']}")
    print(f"Critical Issues: {summary['by_severity']['critical']}")
    print(f"High Priority: {summary['by_severity']['high']}")
    print(f"Medium Priority: {summary['by_severity']['medium']}")
    print()

    if summary['needs_immediate_attention']:
        print("⚠️ THIS BUILD NEEDS IMMEDIATE ATTENTION!")
        print("   Fix critical issues before continuing to map.")
        print()

    # Show top 3 priorities
    print("TOP 3 PRIORITIES:")
    for i, priority in enumerate(summary['top_priorities'][:3], 1):
        print(f"{i}. [{priority['severity'].upper()}] {priority['title']}")
    print()

    # Save detailed analysis
    output = {
        'character': {
            'name': char_data['name'],
            'class': char_data['class'],
            'level': char_data['level']
        },
        'weaknesses': [
            {
                'category': w.category.value,
                'severity': w.severity.value,
                'title': w.title,
                'description': w.description,
                'current_value': w.current_value,
                'recommended_value': w.recommended_value,
                'priority': w.priority,
                'recommendations': w.recommendations
            }
            for w in weaknesses
        ],
        'summary': summary
    }

    output_file = Path(__file__).parent / "astrophobic_analysis.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Full analysis saved to: {output_file}")

    await fetcher.close()


if __name__ == "__main__":
    asyncio.run(main())
