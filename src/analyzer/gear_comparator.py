"""
Gear Comparison Tool

Compares two items and provides detailed analysis of which is better for your build.
Considers offense, defense, resistances, and special properties.

Author: Claude
Date: 2025-10-24
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ComparisonResult(Enum):
    """Result of comparing two items"""
    ITEM_A_BETTER = "item_a_better"
    ITEM_B_BETTER = "item_b_better"
    SITUATIONAL = "situational"
    EQUAL = "equal"


@dataclass
class StatComparison:
    """Comparison of a specific stat between two items"""
    stat_name: str
    item_a_value: Any
    item_b_value: Any
    difference: Any
    winner: str  # "item_a", "item_b", or "tie"
    importance: str  # "critical", "high", "medium", "low"
    explanation: str


@dataclass
class ItemComparisonReport:
    """Full comparison report between two items"""
    item_a_name: str
    item_b_name: str
    overall_result: ComparisonResult
    overall_winner: str  # "item_a", "item_b", "situational", "equal"
    confidence: float  # 0-100, how confident we are in the recommendation

    # Stat-by-stat breakdown
    offense_comparison: List[StatComparison] = field(default_factory=list)
    defense_comparison: List[StatComparison] = field(default_factory=list)
    resistance_comparison: List[StatComparison] = field(default_factory=list)
    utility_comparison: List[StatComparison] = field(default_factory=list)
    special_properties: Dict[str, Any] = field(default_factory=dict)

    # Scoring
    item_a_score: float = 0.0
    item_b_score: float = 0.0

    # Summary
    summary: str = ""
    recommendation: str = ""
    situational_notes: List[str] = field(default_factory=list)


class GearComparator:
    """
    Compare two items and determine which is better for a character

    Usage:
        >>> comparator = GearComparator()
        >>> report = comparator.compare_items(
        ...     item_a={"name": "Rare Helmet", "life": 80, "fire_res": 40},
        ...     item_b={"name": "Unique Helmet", "life": 60, "fire_res": 0, "special": "20% more spell damage"},
        ...     character_data={"class": "Stormweaver", "focus": "damage"},
        ...     build_goal="dps"
        ... )
        >>> print(report.recommendation)
    """

    # Stat importance weights
    STAT_WEIGHTS = {
        # Offense
        "damage": {"dps": 10.0, "defense": 3.0, "balanced": 7.0},
        "crit_chance": {"dps": 8.0, "defense": 2.0, "balanced": 5.0},
        "attack_speed": {"dps": 7.0, "defense": 2.0, "balanced": 4.5},
        "cast_speed": {"dps": 7.0, "defense": 2.0, "balanced": 4.5},

        # Defense
        "life": {"dps": 5.0, "defense": 10.0, "balanced": 8.0},
        "energy_shield": {"dps": 4.0, "defense": 9.0, "balanced": 7.0},
        "armor": {"dps": 3.0, "defense": 8.0, "balanced": 6.0},
        "evasion": {"dps": 3.0, "defense": 8.0, "balanced": 6.0},

        # Resistances (critical for survivability)
        "fire_res": {"dps": 7.0, "defense": 9.0, "balanced": 8.5},
        "cold_res": {"dps": 7.0, "defense": 9.0, "balanced": 8.5},
        "lightning_res": {"dps": 7.0, "defense": 9.0, "balanced": 8.5},
        "chaos_res": {"dps": 5.0, "defense": 7.0, "balanced": 6.5},

        # Utility
        "movement_speed": {"dps": 4.0, "defense": 5.0, "balanced": 5.0},
        "attributes": {"dps": 6.0, "defense": 6.0, "balanced": 6.0},
    }

    def compare_items(
        self,
        item_a: Dict[str, Any],
        item_b: Dict[str, Any],
        character_data: Optional[Dict[str, Any]] = None,
        build_goal: str = "balanced"
    ) -> ItemComparisonReport:
        """
        Compare two items and generate detailed report

        Args:
            item_a: First item data
            item_b: Second item data
            character_data: Character data for context (optional)
            build_goal: "dps", "defense", or "balanced"

        Returns:
            Detailed comparison report
        """
        logger.info(f"Comparing items: {item_a.get('name')} vs {item_b.get('name')}")

        report = ItemComparisonReport(
            item_a_name=item_a.get('name', 'Item A'),
            item_b_name=item_b.get('name', 'Item B'),
            overall_result=ComparisonResult.EQUAL,
            overall_winner="equal",
            confidence=50.0  # Start with neutral confidence
        )

        # Compare offense
        report.offense_comparison = self._compare_offensive_stats(item_a, item_b, build_goal)

        # Compare defense
        report.defense_comparison = self._compare_defensive_stats(item_a, item_b, build_goal)

        # Compare resistances
        report.resistance_comparison = self._compare_resistances(item_a, item_b, character_data)

        # Compare utility
        report.utility_comparison = self._compare_utility(item_a, item_b, build_goal)

        # Identify special properties
        report.special_properties = self._identify_special_properties(item_a, item_b)

        # Calculate scores
        report.item_a_score, report.item_b_score = self._calculate_scores(report, build_goal)

        # Determine winner
        report = self._determine_winner(report)

        # Generate summary and recommendation
        report.summary = self._generate_summary(report)
        report.recommendation = self._generate_recommendation(report, character_data)

        return report

    def _compare_offensive_stats(
        self,
        item_a: Dict[str, Any],
        item_b: Dict[str, Any],
        build_goal: str
    ) -> List[StatComparison]:
        """Compare offensive stats"""
        comparisons = []

        offensive_stats = [
            ('damage', 'Increased Damage'),
            ('spell_damage', 'Spell Damage'),
            ('attack_damage', 'Attack Damage'),
            ('crit_chance', 'Critical Strike Chance'),
            ('crit_multi', 'Critical Strike Multiplier'),
            ('attack_speed', 'Attack Speed'),
            ('cast_speed', 'Cast Speed'),
        ]

        for stat_key, stat_name in offensive_stats:
            val_a = item_a.get(stat_key, 0)
            val_b = item_b.get(stat_key, 0)

            if val_a != 0 or val_b != 0:
                diff = val_b - val_a
                winner = "item_b" if diff > 0 else ("item_a" if diff < 0 else "tie")

                importance = "high" if abs(diff) > 20 else ("medium" if abs(diff) > 10 else "low")

                explanation = f"{stat_name}: {abs(diff):.1f}% " + ("higher" if diff > 0 else ("lower" if diff < 0 else "equal"))

                comparisons.append(StatComparison(
                    stat_name=stat_name,
                    item_a_value=val_a,
                    item_b_value=val_b,
                    difference=diff,
                    winner=winner,
                    importance=importance,
                    explanation=explanation
                ))

        return comparisons

    def _compare_defensive_stats(
        self,
        item_a: Dict[str, Any],
        item_b: Dict[str, Any],
        build_goal: str
    ) -> List[StatComparison]:
        """Compare defensive stats"""
        comparisons = []

        defensive_stats = [
            ('life', 'Maximum Life'),
            ('energy_shield', 'Energy Shield'),
            ('armor', 'Armor'),
            ('evasion', 'Evasion'),
            ('block_chance', 'Block Chance'),
        ]

        for stat_key, stat_name in defensive_stats:
            val_a = item_a.get(stat_key, 0)
            val_b = item_b.get(stat_key, 0)

            if val_a != 0 or val_b != 0:
                diff = val_b - val_a
                winner = "item_b" if diff > 0 else ("item_a" if diff < 0 else "tie")

                # Life is always important
                if stat_key == 'life':
                    importance = "critical" if abs(diff) > 50 else ("high" if abs(diff) > 30 else "medium")
                else:
                    importance = "high" if abs(diff) > 100 else ("medium" if abs(diff) > 50 else "low")

                explanation = f"{stat_name}: {abs(diff):.0f} " + ("higher" if diff > 0 else ("lower" if diff < 0 else "equal"))

                comparisons.append(StatComparison(
                    stat_name=stat_name,
                    item_a_value=val_a,
                    item_b_value=val_b,
                    difference=diff,
                    winner=winner,
                    importance=importance,
                    explanation=explanation
                ))

        return comparisons

    def _compare_resistances(
        self,
        item_a: Dict[str, Any],
        item_b: Dict[str, Any],
        character_data: Optional[Dict[str, Any]]
    ) -> List[StatComparison]:
        """Compare resistances (very important!)"""
        comparisons = []

        resistances = [
            ('fire_res', 'Fire Resistance'),
            ('cold_res', 'Cold Resistance'),
            ('lightning_res', 'Lightning Resistance'),
            ('chaos_res', 'Chaos Resistance'),
        ]

        # Get current character resistances if available
        current_res = {}
        if character_data and 'stats' in character_data:
            stats = character_data['stats']
            current_res = {
                'fire_res': stats.get('fire_res', 0),
                'cold_res': stats.get('cold_res', 0),
                'lightning_res': stats.get('lightning_res', 0),
                'chaos_res': stats.get('chaos_res', 0),
            }

        for stat_key, stat_name in resistances:
            val_a = item_a.get(stat_key, 0)
            val_b = item_b.get(stat_key, 0)

            if val_a != 0 or val_b != 0:
                diff = val_b - val_a
                winner = "item_b" if diff > 0 else ("item_a" if diff < 0 else "tie")

                # Determine importance based on whether character is capped
                current = current_res.get(stat_key, 0)
                if current < 75:  # Not capped
                    importance = "critical" if abs(diff) > 20 else "high"
                else:
                    importance = "medium" if abs(diff) > 20 else "low"

                explanation = f"{stat_name}: {abs(diff):.0f}% " + ("higher" if diff > 0 else ("lower" if diff < 0 else "equal"))

                if current_res:
                    new_total_a = current + val_a - item_a.get(stat_key, 0)  # Remove old item
                    new_total_b = current + val_b - item_a.get(stat_key, 0)

                    if new_total_a < 75 and new_total_b >= 75:
                        explanation += f" (CAPS {stat_name}!)"
                        importance = "critical"
                    elif new_total_b < 75 and new_total_a >= 75:
                        explanation += f" (UNCAPS {stat_name}!)"
                        importance = "critical"

                comparisons.append(StatComparison(
                    stat_name=stat_name,
                    item_a_value=val_a,
                    item_b_value=val_b,
                    difference=diff,
                    winner=winner,
                    importance=importance,
                    explanation=explanation
                ))

        return comparisons

    def _compare_utility(
        self,
        item_a: Dict[str, Any],
        item_b: Dict[str, Any],
        build_goal: str
    ) -> List[StatComparison]:
        """Compare utility stats"""
        comparisons = []

        utility_stats = [
            ('movement_speed', 'Movement Speed', '%'),
            ('strength', 'Strength', ''),
            ('dexterity', 'Dexterity', ''),
            ('intelligence', 'Intelligence', ''),
        ]

        for stat_key, stat_name, suffix in utility_stats:
            val_a = item_a.get(stat_key, 0)
            val_b = item_b.get(stat_key, 0)

            if val_a != 0 or val_b != 0:
                diff = val_b - val_a
                winner = "item_b" if diff > 0 else ("item_a" if diff < 0 else "tie")

                importance = "medium" if abs(diff) > 30 else "low"

                explanation = f"{stat_name}: {abs(diff):.0f}{suffix} " + ("higher" if diff > 0 else ("lower" if diff < 0 else "equal"))

                comparisons.append(StatComparison(
                    stat_name=stat_name,
                    item_a_value=val_a,
                    item_b_value=val_b,
                    difference=diff,
                    winner=winner,
                    importance=importance,
                    explanation=explanation
                ))

        return comparisons

    def _identify_special_properties(
        self,
        item_a: Dict[str, Any],
        item_b: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Identify special properties that can't be directly compared"""
        special = {
            'item_a_uniques': [],
            'item_b_uniques': [],
            'item_a_has_sockets': item_a.get('sockets', 0) > 0,
            'item_b_has_sockets': item_b.get('sockets', 0) > 0,
        }

        # Check for unique modifiers
        if 'special_mods' in item_a:
            special['item_a_uniques'] = item_a['special_mods']

        if 'special_mods' in item_b:
            special['item_b_uniques'] = item_b['special_mods']

        return special

    def _calculate_scores(
        self,
        report: ItemComparisonReport,
        build_goal: str
    ) -> Tuple[float, float]:
        """Calculate overall scores for both items"""
        score_a = 0.0
        score_b = 0.0

        # Score all comparisons
        all_comparisons = (
            report.offense_comparison +
            report.defense_comparison +
            report.resistance_comparison +
            report.utility_comparison
        )

        importance_weights = {
            'critical': 10.0,
            'high': 5.0,
            'medium': 2.0,
            'low': 1.0
        }

        for comp in all_comparisons:
            weight = importance_weights.get(comp.importance, 1.0)

            if comp.winner == 'item_a':
                score_a += weight * abs(comp.difference)
            elif comp.winner == 'item_b':
                score_b += weight * abs(comp.difference)

        return score_a, score_b

    def _determine_winner(self, report: ItemComparisonReport) -> ItemComparisonReport:
        """Determine overall winner"""
        score_diff = abs(report.item_a_score - report.item_b_score)
        total_score = report.item_a_score + report.item_b_score

        # Calculate confidence (0-100)
        if total_score > 0:
            report.confidence = min(100, (score_diff / total_score) * 100)
        else:
            report.confidence = 0

        # Determine result
        threshold = 10.0  # Minimum score difference to declare a winner

        if score_diff < threshold:
            report.overall_result = ComparisonResult.EQUAL
            report.overall_winner = "equal"
        elif report.item_a_score > report.item_b_score:
            report.overall_result = ComparisonResult.ITEM_A_BETTER
            report.overall_winner = "item_a"
        else:
            report.overall_result = ComparisonResult.ITEM_B_BETTER
            report.overall_winner = "item_b"

        # Check for situational cases
        has_critical_tradeoffs = any(
            comp.importance == 'critical'
            for comp in (report.offense_comparison + report.defense_comparison + report.resistance_comparison)
            if comp.winner != 'tie'
        )

        if has_critical_tradeoffs and report.confidence < 70:
            report.overall_result = ComparisonResult.SITUATIONAL
            report.overall_winner = "situational"

        return report

    def _generate_summary(self, report: ItemComparisonReport) -> str:
        """Generate summary text"""
        if report.overall_winner == "item_a":
            return f"{report.item_a_name} is better overall (Score: {report.item_a_score:.1f} vs {report.item_b_score:.1f})"
        elif report.overall_winner == "item_b":
            return f"{report.item_b_name} is better overall (Score: {report.item_b_score:.1f} vs {report.item_a_score:.1f})"
        elif report.overall_winner == "situational":
            return f"Choice depends on your specific needs (Scores: {report.item_a_score:.1f} vs {report.item_b_score:.1f})"
        else:
            return f"Items are roughly equal (Scores: {report.item_a_score:.1f} vs {report.item_b_score:.1f})"

    def _generate_recommendation(
        self,
        report: ItemComparisonReport,
        character_data: Optional[Dict[str, Any]]
    ) -> str:
        """Generate detailed recommendation"""
        lines = []

        if report.overall_winner == "item_a":
            lines.append(f"✅ RECOMMENDATION: Use {report.item_a_name}")
            lines.append(f"   Confidence: {report.confidence:.0f}%")
        elif report.overall_winner == "item_b":
            lines.append(f"✅ RECOMMENDATION: Use {report.item_b_name}")
            lines.append(f"   Confidence: {report.confidence:.0f}%")
        elif report.overall_winner == "situational":
            lines.append(f"⚠️ SITUATIONAL: Choose based on your priorities")
        else:
            lines.append(f"↔️ EQUAL: Either item works, choose based on preference")

        # Add key differences
        lines.append("\nKey Differences:")

        # Find most important differences
        all_comps = (
            report.offense_comparison +
            report.defense_comparison +
            report.resistance_comparison +
            report.utility_comparison
        )

        critical_diffs = [c for c in all_comps if c.importance == 'critical' and c.winner != 'tie']
        high_diffs = [c for c in all_comps if c.importance == 'high' and c.winner != 'tie']

        for comp in critical_diffs[:3]:
            winner_name = report.item_a_name if comp.winner == 'item_a' else report.item_b_name
            lines.append(f"  • [CRITICAL] {winner_name}: {comp.explanation}")

        for comp in high_diffs[:3]:
            winner_name = report.item_a_name if comp.winner == 'item_a' else report.item_b_name
            lines.append(f"  • {winner_name}: {comp.explanation}")

        return "\n".join(lines)

    def format_full_report(self, report: ItemComparisonReport) -> str:
        """Format complete comparison report"""
        lines = []
        lines.append("=" * 80)
        lines.append("GEAR COMPARISON REPORT")
        lines.append("=" * 80)
        lines.append(f"{report.item_a_name} vs {report.item_b_name}")
        lines.append("")
        lines.append(report.summary)
        lines.append("")
        lines.append("-" * 80)
        lines.append("DETAILED COMPARISON")
        lines.append("-" * 80)

        # Offense
        if report.offense_comparison:
            lines.append("\nOffensive Stats:")
            for comp in report.offense_comparison:
                symbol = ">" if comp.winner == "item_a" else ("<" if comp.winner == "item_b" else "=")
                lines.append(f"  {comp.stat_name}: {comp.item_a_value} {symbol} {comp.item_b_value}")

        # Defense
        if report.defense_comparison:
            lines.append("\nDefensive Stats:")
            for comp in report.defense_comparison:
                symbol = ">" if comp.winner == "item_a" else ("<" if comp.winner == "item_b" else "=")
                lines.append(f"  {comp.stat_name}: {comp.item_a_value} {symbol} {comp.item_b_value}")

        # Resistances
        if report.resistance_comparison:
            lines.append("\nResistances:")
            for comp in report.resistance_comparison:
                symbol = ">" if comp.winner == "item_a" else ("<" if comp.winner == "item_b" else "=")
                lines.append(f"  {comp.stat_name}: {comp.item_a_value}% {symbol} {comp.item_b_value}%")

        lines.append("")
        lines.append("-" * 80)
        lines.append("RECOMMENDATION")
        lines.append("-" * 80)
        lines.append(report.recommendation)
        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)


if __name__ == "__main__":
    # Demo
    comparator = GearComparator()

    item_a = {
        'name': 'Rare Helmet',
        'life': 80,
        'fire_res': 40,
        'cold_res': 35,
        'lightning_res': 30,
        'armor': 200
    }

    item_b = {
        'name': 'Unique Helmet',
        'life': 60,
        'fire_res': 0,
        'cold_res': 0,
        'lightning_res': 0,
        'spell_damage': 30,
        'crit_chance': 15,
        'armor': 100
    }

    character = {
        'stats': {
            'fire_res': 50,
            'cold_res': 60,
            'lightning_res': 70
        }
    }

    report = comparator.compare_items(item_a, item_b, character, build_goal="dps")
    print(comparator.format_full_report(report))
