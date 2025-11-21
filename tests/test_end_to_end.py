"""
End-to-End Test
Tests the complete workflow: fetch character -> analyze -> generate report
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.character_fetcher import CharacterFetcher
from src.analyzer.character_analyzer import CharacterAnalyzer, GearRecommender
from src.analyzer.report_generator import ReportGenerator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_full_workflow():
    """Test complete workflow from fetch to report generation"""
    print("\n" + "="*70)
    print("END-TO-END TEST: Character Analysis Workflow")
    print("="*70 + "\n")

    # Step 1: Fetch character data
    print("[STEP 1] Fetching character data from poe.ninja...")
    print("-" * 70)

    account_name = "Tomawar40-2671"
    character_name = "DoesFireWorkGoodNow"

    async with CharacterFetcher() as fetcher:
        character_data = await fetcher.get_character_from_poe_ninja(
            account_name=account_name,
            character_name=character_name
        )

    if not character_data:
        print("[FAILED] Could not fetch character data")
        return False

    print(f"[SUCCESS] Fetched character: {character_data.get('name')}")
    print(f"          League: {character_data.get('league')}")
    print(f"          Stats available: {len(character_data.get('stats', {})) > 0}")
    print()

    # Step 2: Analyze character
    print("[STEP 2] Analyzing character...")
    print("-" * 70)

    analyzer = CharacterAnalyzer()
    analysis = analyzer.analyze_character(character_data)

    if 'error' in analysis:
        print(f"[FAILED] Analysis error: {analysis['error']}")
        return False

    print(f"[SUCCESS] Analysis complete")
    print(f"          Defense Quality: {analysis['defensive_analysis']['quality']}")
    print(f"          Issues Found: {len(analysis['defensive_analysis']['issues'])}")
    print(f"          Recommendations: {len(analysis['recommendations'])}")
    print()

    # Step 3: Generate gear recommendations
    print("[STEP 3] Generating gear recommendations...")
    print("-" * 70)

    gear_recommender = GearRecommender()
    gear_recs = gear_recommender.recommend_upgrades(character_data, analysis)

    print(f"[SUCCESS] Generated {len(gear_recs)} gear recommendations")
    print()

    # Step 4: Generate comprehensive report
    print("[STEP 4] Generating comprehensive report...")
    print("-" * 70)

    report_generator = ReportGenerator()
    report = report_generator.generate_report(
        character_data=character_data,
        analysis=analysis,
        gear_recommendations=gear_recs
    )

    print("[SUCCESS] Report generated")
    print()

    # Display the report
    print("="*70)
    print("COMPREHENSIVE CHARACTER ANALYSIS REPORT")
    print("="*70)
    print()
    print(report)
    print()

    # Save report to file
    report_file = Path(__file__).parent.parent / "data" / f"{character_name}_analysis.md"
    report_file.parent.mkdir(exist_ok=True, parents=True)

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print("="*70)
    print(f"[SUCCESS] Report saved to: {report_file}")
    print("="*70)
    print()

    return True

async def main():
    """Run the end-to-end test"""
    success = await test_full_workflow()

    print("\n" + "="*70)
    if success:
        print("[TEST PASSED] End-to-end workflow completed successfully!")
    else:
        print("[TEST FAILED] Workflow encountered errors")
    print("="*70 + "\n")

    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
