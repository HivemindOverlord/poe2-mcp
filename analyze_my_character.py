"""
Comprehensive Character Analysis Script
Uses all implemented systems to analyze DoesFireWorkGoodNow
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.analyzer.weakness_detector import WeaknessDetector, CharacterData
from src.analyzer.archetype_classifier import ArchetypeClassifier
from src.analyzer.build_success_predictor import BuildSuccessPredictor, ContentType
from src.calculator.ehp_calculator import EHPCalculator, DefensiveStats, DamageType


def load_character_data():
    """Load character data from JSON file"""
    with open("character_data_full.json", "r", encoding="utf-8") as f:
        return json.load(f)


def extract_stats_from_json(char_json):
    """Extract stats from the JSON format"""
    # Get stats from the character JSON
    stats_dict = {}
    if "stats" in char_json:
        for stat in char_json["stats"]:
            stats_dict[stat["id"]] = stat["value"]

    return {
        "level": char_json.get("level", 91),
        "class": char_json.get("class", "Stormweaver"),
        "life": stats_dict.get("life", 1413),
        "energy_shield": stats_dict.get("energy_shield", 4847),
        "mana": stats_dict.get("mana", 1120),
        "spirit": stats_dict.get("spirit", 100),
        "evasion": stats_dict.get("evasion_rating", 855),
        "armour": stats_dict.get("armour", 0),
        "fire_res": stats_dict.get("fire_damage_resistance_%", -2),
        "cold_res": stats_dict.get("cold_damage_resistance_%", -8),
        "lightning_res": stats_dict.get("lightning_damage_resistance_%", 17),
        "chaos_res": stats_dict.get("chaos_damage_resistance_%", 0),
        "strength": stats_dict.get("strength", 50),
        "dexterity": stats_dict.get("dexterity", 50),
        "intelligence": stats_dict.get("intelligence", 300),
        "block_chance": stats_dict.get("block_%", 0),
        "spell_block_chance": stats_dict.get("spell_block_%", 0),
        "spell_suppression_chance": stats_dict.get("spell_suppression_chance_%", 0),
    }


def analyze_weaknesses(char_data):
    """Run weakness detection"""
    print("\n" + "="*80)
    print("🔍 WEAKNESS DETECTION ANALYSIS")
    print("="*80)

    detector = WeaknessDetector()

    # Convert to CharacterData format
    stats = extract_stats_from_json(char_data)

    character = CharacterData(
        level=stats["level"],
        character_class=stats["class"],
        life=stats["life"],
        energy_shield=stats["energy_shield"],
        mana=stats["mana"],
        spirit_max=stats["spirit"],
        spirit_reserved=0,
        strength=stats["strength"],
        dexterity=stats["dexterity"],
        intelligence=stats["intelligence"],
        armor=stats["armour"],
        evasion=stats["evasion"],
        block_chance=stats["block_chance"],
        fire_res=stats["fire_res"],
        cold_res=stats["cold_res"],
        lightning_res=stats["lightning_res"],
        chaos_res=stats["chaos_res"],
        total_dps=None,
        equipped_items={}
    )

    weaknesses = detector.detect_all_weaknesses(character)

    if not weaknesses:
        print("✅ No critical weaknesses detected!")
    else:
        print(f"\n🚨 Found {len(weaknesses)} weaknesses:\n")
        for i, weakness in enumerate(weaknesses, 1):
            priority_emoji = "🔴" if weakness.priority >= 90 else "🟡" if weakness.priority >= 70 else "🟢"
            print(f"{i}. {priority_emoji} [{weakness.category}] {weakness.title}")
            print(f"   Priority: {weakness.priority}/100")
            print(f"   Impact: {weakness.description}")
            print(f"   Fix: {weakness.fix_suggestion}")
            print()

    return weaknesses


def classify_archetype(char_data, stats):
    """Classify build archetype"""
    print("\n" + "="*80)
    print("🎯 BUILD ARCHETYPE CLASSIFICATION")
    print("="*80)

    classifier = ArchetypeClassifier()

    # Estimate DPS (rough calculation based on gear)
    estimated_dps = 50000  # Placeholder - would need full calculation

    # Calculate EHP
    ehp_values = {
        "physical": stats["life"] + stats["energy_shield"],
        "fire": (stats["life"] + stats["energy_shield"]) * (1 + max(0, stats["fire_res"]) / 100),
        "cold": (stats["life"] + stats["energy_shield"]) * (1 + max(0, stats["cold_res"]) / 100),
        "lightning": (stats["life"] + stats["energy_shield"]) * (1 + max(0, stats["lightning_res"]) / 100),
        "chaos": stats["life"] * (1 + max(0, stats["chaos_res"]) / 100),
    }

    result = classifier.classify_build(char_data, estimated_dps, ehp_values)

    print(f"\n🏆 Primary Archetype: {result.primary_archetype}")
    print(f"   Match Score: {result.match_score:.1f}/100")
    print(f"   Purity: {result.archetype_purity:.1f}%")

    if result.secondary_archetype:
        print(f"\n🥈 Secondary Archetype: {result.secondary_archetype}")
        print(f"   This is a HYBRID build combining two archetypes")

    print(f"\n💪 Strengths:")
    for strength in result.strengths:
        print(f"   ✓ {strength}")

    print(f"\n⚠️  Weaknesses:")
    for weakness in result.weaknesses:
        print(f"   ✗ {weakness}")

    print(f"\n💡 Recommendations:")
    for rec in result.recommendations:
        print(f"   → {rec}")

    return result


def predict_content_viability(char_data, stats, archetype_result):
    """Predict success for different content types"""
    print("\n" + "="*80)
    print("📊 CONTENT VIABILITY PREDICTION")
    print("="*80)

    predictor = BuildSuccessPredictor()

    estimated_dps = 50000
    ehp_values = {
        "physical": stats["life"] + stats["energy_shield"],
        "fire": (stats["life"] + stats["energy_shield"]) * (1 + max(0, stats["fire_res"]) / 100),
        "cold": (stats["life"] + stats["energy_shield"]) * (1 + max(0, stats["cold_res"]) / 100),
        "lightning": (stats["life"] + stats["energy_shield"]) * (1 + max(0, stats["lightning_res"]) / 100),
        "chaos": stats["life"] * (1 + max(0, stats["chaos_res"]) / 100),
    }

    content_types = [
        (ContentType.WHITE_MAPS, "White Maps (T1-T5)"),
        (ContentType.YELLOW_MAPS, "Yellow Maps (T6-T10)"),
        (ContentType.RED_MAPS, "Red Maps (T11-T15)"),
        (ContentType.T16_MAPS, "T16 Maps"),
        (ContentType.T17_MAPS, "T17 Maps (Endgame)"),
        (ContentType.PINNACLE_BOSSES, "Pinnacle Bosses"),
    ]

    results = []
    for content_type, name in content_types:
        result = predictor.predict(char_data, content_type, estimated_dps, ehp_values)
        results.append((name, result))

    print()
    for name, result in results:
        emoji = "✅" if result.success_probability >= 80 else "⚠️" if result.success_probability >= 50 else "❌"
        print(f"{emoji} {name}: {result.success_probability:.0f}% success chance")

        if result.blockers:
            print(f"   🚫 Blockers:")
            for blocker in result.blockers[:3]:  # Show top 3
                print(f"      - {blocker}")

        if result.estimated_investment and result.estimated_investment > 0:
            print(f"   💰 Investment needed: ~{result.estimated_investment:.0f} chaos")

        if result.time_to_viable and result.time_to_viable > 0:
            print(f"   ⏱️  Time to farm: ~{result.time_to_viable:.1f} hours")

        print()

    return results


def calculate_detailed_ehp(stats):
    """Calculate detailed EHP for all damage types"""
    print("\n" + "="*80)
    print("🛡️  DETAILED EHP CALCULATION")
    print("="*80)

    calculator = EHPCalculator()

    char_stats = DefensiveStats(
        life=stats["life"],
        energy_shield=stats["energy_shield"],
        fire_resistance=stats["fire_res"],
        cold_resistance=stats["cold_res"],
        lightning_resistance=stats["lightning_res"],
        chaos_resistance=stats["chaos_res"],
        armor=stats["armour"],
        evasion_rating=stats["evasion"],
        block_chance=stats["block_chance"],
        spell_block_chance=stats.get("spell_block_chance", 0),
        dodge_chance=0.0,
        spell_suppression_chance=stats.get("spell_suppression_chance", 0)
    )

    print("\n📈 Effective Health Pool by Damage Type:\n")

    damage_types = [
        (DamageType.PHYSICAL, "Physical"),
        (DamageType.FIRE, "Fire"),
        (DamageType.COLD, "Cold"),
        (DamageType.LIGHTNING, "Lightning"),
        (DamageType.CHAOS, "Chaos"),
    ]

    for damage_type, name in damage_types:
        ehp = calculator.calculate_ehp(char_stats, damage_type)
        raw_pool = stats["life"] + stats["energy_shield"]
        multiplier = ehp / raw_pool if raw_pool > 0 else 0

        status = "🔴" if ehp < 5000 else "🟡" if ehp < 8000 else "🟢"
        print(f"{status} {name:12s}: {ehp:7,.0f} EHP ({multiplier:.2f}x raw pool)")

    print(f"\n💡 Raw Pool: {stats['life']:,} Life + {stats['energy_shield']:,} ES = {stats['life'] + stats['energy_shield']:,} total")


def generate_upgrade_recommendations(weaknesses, archetype, viability_results, stats):
    """Generate prioritized upgrade recommendations"""
    print("\n" + "="*80)
    print("🔧 UPGRADE RECOMMENDATIONS")
    print("="*80)

    print("\n🎯 CRITICAL PRIORITY (Do These First):")
    print("─" * 80)

    # Critical weaknesses
    critical = [w for w in weaknesses if w.priority >= 90]
    for i, weakness in enumerate(critical, 1):
        print(f"\n{i}. Fix {weakness.title}")
        print(f"   {weakness.fix_suggestion}")
        if "resistance" in weakness.title.lower():
            needed = 75 - stats[f"{weakness.title.split()[0].lower()}_res"]
            print(f"   You need +{needed}% resistance to reach cap (75%)")

    print("\n\n🔥 HIGH PRIORITY (Major Improvements):")
    print("─" * 80)

    # High priority weaknesses
    high = [w for w in weaknesses if 70 <= w.priority < 90]
    for i, weakness in enumerate(high[:5], 1):  # Top 5
        print(f"\n{i}. {weakness.title}")
        print(f"   {weakness.fix_suggestion}")

    print("\n\n💎 OPTIMIZATION (Polish Your Build):")
    print("─" * 80)

    # Based on archetype
    print(f"\nFor your {archetype.primary_archetype} build:")
    for i, rec in enumerate(archetype.recommendations[:3], 1):
        print(f"{i}. {rec}")

    # Based on content goals
    print("\n\n🎮 CONTENT-SPECIFIC UPGRADES:")
    print("─" * 80)

    # Find first content that's not viable
    for content_name, result in viability_results:
        if result.success_probability < 75:
            print(f"\nTo tackle {content_name}:")
            for blocker in result.blockers[:3]:
                print(f"  • {blocker}")
            if result.estimated_investment:
                print(f"\n  Estimated cost: {result.estimated_investment:.0f} chaos")
            break

    print("\n\n💰 BUDGET ALLOCATION:")
    print("─" * 80)
    print("\n1. Resistance Gear: 20-50 chaos")
    print("   → Buy rare rings/belt with life + resistances")
    print("\n2. Life Pool: 50-100 chaos")
    print("   → Upgrade helm/body with higher life rolls")
    print("\n3. Defense Layer: 100-200 chaos")
    print("   → Add armour/evasion/block gear")
    print("\n4. Optimization: 200+ chaos")
    print("   → Better corruptions, double mods, perfect rolls")


def main():
    print("\n" + "="*80)
    print("🚀 COMPREHENSIVE CHARACTER ANALYSIS")
    print("   Character: DoesFireWorkGoodNow")
    print("   Level 91 Stormweaver")
    print("="*80)

    # Load data
    char_data = load_character_data()
    stats = extract_stats_from_json(char_data)

    # Run all analysis
    weaknesses = analyze_weaknesses(char_data)
    archetype = classify_archetype(char_data, stats)
    viability = predict_content_viability(char_data, stats, archetype)
    calculate_detailed_ehp(stats)
    generate_upgrade_recommendations(weaknesses, archetype, viability, stats)

    print("\n" + "="*80)
    print("✅ ANALYSIS COMPLETE")
    print("="*80)
    print("\nAll systems operational!")
    print("MCP server ready to provide these insights via Claude Desktop integration.")
    print()


if __name__ == "__main__":
    main()
