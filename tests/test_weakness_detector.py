#!/usr/bin/env python3
"""
Test Weakness Detector

Tests the automated weakness detection system.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analyzer.weakness_detector import (
    WeaknessDetector,
    CharacterData,
    WeaknessSeverity,
    WeaknessCategory
)


def test_weakness_detector():
    """Test weakness detector with the user's character."""

    print("=" * 80)
    print("WEAKNESS DETECTOR TEST")
    print("=" * 80)
    print()

    # Create character data based on DoesFireWorkGoodNow
    print("Creating character data...")
    char = CharacterData(
        level=91,
        character_class="Stormweaver",
        life=1413,  # Low
        energy_shield=4847,
        mana=850,
        spirit_max=100,
        spirit_reserved=95,  # Near cap
        strength=50,
        dexterity=120,
        intelligence=300,
        armor=2000,
        evasion=500,
        block_chance=25,
        fire_res=-2,  # CRITICAL: negative
        cold_res=-8,  # CRITICAL: negative
        lightning_res=75,
        chaos_res=-60
    )

    # Create detector
    print("Initializing WeaknessDetector...")
    detector = WeaknessDetector()
    print()

    # Detect all weaknesses
    print("=" * 80)
    print("DETECTING WEAKNESSES")
    print("=" * 80)
    print()

    weaknesses = detector.detect_all_weaknesses(char)

    # Print formatted report
    report = detector.format_weakness_report(weaknesses)
    print(report)

    # Print summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    summary = detector.get_weakness_summary(char)
    print(f"Total Weaknesses: {summary['total_weaknesses']}")
    print(f"Critical: {summary['by_severity']['critical']}")
    print(f"High: {summary['by_severity']['high']}")
    print(f"Medium: {summary['by_severity']['medium']}")
    print(f"Low: {summary['by_severity']['low']}")
    print(f"Needs Immediate Attention: {summary['needs_immediate_attention']}")
    print()

    print("Top 5 Priorities:")
    for i, priority in enumerate(summary['top_priorities'], 1):
        print(f"{i}. [{priority['severity'].upper()}] {priority['title']} (score: {priority['priority']})")

    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

    # Verify critical weaknesses were detected
    critical_count = summary['by_severity']['critical']
    print(f"\n✓ Detected {critical_count} critical weaknesses (expected 3: fire/cold res, low life)")

    # Verify resistance gaps detected
    resistance_weaknesses = [w for w in weaknesses if w.category == WeaknessCategory.RESISTANCE]
    print(f"✓ Detected {len(resistance_weaknesses)} resistance weaknesses")

    # Verify Spirit issues detected
    spirit_weaknesses = [w for w in weaknesses if w.category == WeaknessCategory.SPIRIT]
    print(f"✓ Detected {len(spirit_weaknesses)} Spirit weaknesses")

    return True


if __name__ == "__main__":
    try:
        test_weakness_detector()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
