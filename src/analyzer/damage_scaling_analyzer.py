"""
Damage Scaling Analyzer

Identifies the best ways to increase your DPS based on current stats.
Answers "What should I focus on to increase my damage?"

Author: Claude
Date: 2025-10-24
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import math

logger = logging.getLogger(__name__)


@dataclass
class ScalingRecommendation:
    """Recommendation for scaling damage"""
    stat_name: str
    current_value: float
    impact_rating: float  # 0-100, how much this stat affects DPS
    priority: str  # "critical", "high", "medium", "low"
    explanation: str
    example_improvement: str  # e.g., "+50% increased damage = +15% DPS"
    bottleneck: bool = False  # Is this stat bottlenecking your damage?


@dataclass
class DPSBreakdown:
    """Breakdown of DPS calculation"""
    base_damage: float
    after_added: float
    after_increased: float
    after_more: float
    after_crit: float
    final_dps: float

    # Multipliers
    added_flat_multiplier: float
    increased_multiplier: float
    more_multiplier: float
    crit_multiplier: float

    # Breakdown by component
    breakdown: Dict[str, float] = field(default_factory=dict)


class DamageScalingAnalyzer:
    """
    Analyze character's damage scaling and provide recommendations

    Usage:
        >>> analyzer = DamageScalingAnalyzer()
        >>> recommendations = analyzer.analyze_scaling(
        ...     character_data={"spell_damage": 250, "crit_chance": 30, ...},
        ...     skill_type="spell"
        ... )
        >>> for rec in recommendations:
        ...     print(f"{rec.priority.upper()}: {rec.stat_name} - {rec.explanation}")
    """

    def analyze_scaling(
        self,
        character_data: Dict[str, Any],
        skill_type: str = "spell",
        current_dps: Optional[float] = None
    ) -> List[ScalingRecommendation]:
        """
        Analyze damage scaling and provide recommendations

        Args:
            character_data: Character stats and modifiers
            skill_type: "spell", "attack", or "dot"
            current_dps: Current DPS (if known)

        Returns:
            List of scaling recommendations, sorted by priority
        """
        logger.info(f"Analyzing damage scaling for {skill_type} build")

        recommendations = []

        # Extract current stats
        stats = self._extract_stats(character_data, skill_type)

        # Calculate current DPS breakdown
        dps_breakdown = self._calculate_dps_breakdown(stats, skill_type)

        # Analyze each scaling vector
        recommendations.extend(self._analyze_increased_damage(stats, dps_breakdown, skill_type))
        recommendations.extend(self._analyze_more_multipliers(stats, dps_breakdown, skill_type))
        recommendations.extend(self._analyze_crit_scaling(stats, dps_breakdown, skill_type))
        recommendations.extend(self._analyze_added_damage(stats, dps_breakdown, skill_type))
        recommendations.extend(self._analyze_cast_attack_speed(stats, dps_breakdown, skill_type))

        # Sort by priority and impact
        priority_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        recommendations.sort(
            key=lambda r: (priority_order.get(r.priority, 0), r.impact_rating),
            reverse=True
        )

        return recommendations

    def _extract_stats(self, character_data: Dict[str, Any], skill_type: str) -> Dict[str, float]:
        """Extract relevant stats from character data"""
        stats = {
            # Base damage
            'base_damage': character_data.get('base_damage', 100.0),

            # Increased modifiers
            'increased_damage': character_data.get('increased_spell_damage', 0.0) if skill_type == 'spell' else character_data.get('increased_attack_damage', 0.0),

            # More multipliers (from supports)
            'more_multipliers': character_data.get('more_multipliers', []),

            # Added damage
            'added_flat_damage': character_data.get('added_flat_damage', 0.0),

            # Crit
            'base_crit_chance': character_data.get('base_crit_chance', 5.0),
            'increased_crit_chance': character_data.get('increased_crit_chance', 0.0),
            'crit_multiplier': character_data.get('crit_multiplier', 150.0),  # Base +100%, often have +50%
            'increased_crit_multi': character_data.get('increased_crit_multi', 0.0),

            # Speed
            'base_cast_time': character_data.get('base_cast_time', 1.0) if skill_type == 'spell' else character_data.get('base_attack_time', 1.0),
            'increased_cast_speed': character_data.get('increased_cast_speed', 0.0) if skill_type == 'spell' else character_data.get('increased_attack_speed', 0.0),

            # Damage effectiveness
            'damage_effectiveness': character_data.get('damage_effectiveness', 100.0),
        }

        return stats

    def _calculate_dps_breakdown(self, stats: Dict[str, float], skill_type: str) -> DPSBreakdown:
        """Calculate DPS with full breakdown"""
        # Step 1: Base damage
        base = stats['base_damage']

        # Step 2: Add flat damage
        added_flat = stats['added_flat_damage'] * (stats['damage_effectiveness'] / 100.0)
        after_added = base + added_flat
        added_multiplier = after_added / base if base > 0 else 1.0

        # Step 3: Apply increased
        increased_total = stats['increased_damage']
        increased_multi = 1.0 + (increased_total / 100.0)
        after_increased = after_added * increased_multi

        # Step 4: Apply more multipliers
        more_multi = 1.0
        for more_percent in stats['more_multipliers']:
            more_multi *= (1.0 + more_percent / 100.0)
        after_more = after_increased * more_multi

        # Step 5: Apply crit
        final_crit_chance = min(100.0, stats['base_crit_chance'] + stats['increased_crit_chance']) / 100.0
        crit_multi_total = 1.0 + (stats['crit_multiplier'] / 100.0) * (1.0 + stats['increased_crit_multi'] / 100.0)

        # Expected damage with crits
        expected_hit = after_more * (1 - final_crit_chance) + after_more * crit_multi_total * final_crit_chance
        effective_crit_multi = expected_hit / after_more if after_more > 0 else 1.0

        # Step 6: Cast/attack speed
        speed_multi = 1.0 + (stats['increased_cast_speed'] / 100.0)
        casts_per_second = 1.0 / (stats['base_cast_time'] / speed_multi)

        final_dps = expected_hit * casts_per_second

        return DPSBreakdown(
            base_damage=base,
            after_added=after_added,
            after_increased=after_increased,
            after_more=after_more,
            after_crit=expected_hit,
            final_dps=final_dps,
            added_flat_multiplier=added_multiplier,
            increased_multiplier=increased_multi,
            more_multiplier=more_multi,
            crit_multiplier=effective_crit_multi,
            breakdown={
                'base': base,
                'added_flat': added_flat,
                'increased_total': increased_total,
                'more_total': more_multi,
                'crit_impact': effective_crit_multi,
                'speed_multi': speed_multi
            }
        )

    def _analyze_increased_damage(
        self,
        stats: Dict[str, float],
        dps_breakdown: DPSBreakdown,
        skill_type: str
    ) -> List[ScalingRecommendation]:
        """Analyze increased damage scaling"""
        recommendations = []

        current_increased = stats['increased_damage']

        # Calculate impact of adding more increased damage
        # Law of diminishing returns
        impact = self._calculate_impact_of_increased(current_increased, 100.0)  # Adding 100% increased

        # Determine priority based on current amount
        if current_increased < 200:
            priority = "high"
            bottleneck = True
            explanation = f"You only have {current_increased:.0f}% increased damage. This is a good scaling vector."
        elif current_increased < 400:
            priority = "medium"
            bottleneck = False
            explanation = f"You have {current_increased:.0f}% increased damage. Diminishing returns are starting."
        else:
            priority = "low"
            bottleneck = False
            explanation = f"You have {current_increased:.0f}% increased damage. Heavy diminishing returns - focus on 'more' multipliers instead."

        # Calculate example improvement
        new_multi = 1.0 + ((current_increased + 100) / 100.0)
        old_multi = 1.0 + (current_increased / 100.0)
        percent_gain = ((new_multi / old_multi) - 1.0) * 100.0

        example = f"+100% increased damage = +{percent_gain:.1f}% DPS"

        recommendations.append(ScalingRecommendation(
            stat_name="Increased Damage",
            current_value=current_increased,
            impact_rating=impact,
            priority=priority,
            explanation=explanation,
            example_improvement=example,
            bottleneck=bottleneck
        ))

        return recommendations

    def _analyze_more_multipliers(
        self,
        stats: Dict[str, float],
        dps_breakdown: DPSBreakdown,
        skill_type: str
    ) -> List[ScalingRecommendation]:
        """Analyze more multipliers"""
        recommendations = []

        current_more = dps_breakdown.more_multiplier
        num_supports = len(stats['more_multipliers'])

        # More multipliers are almost always high value
        impact = 85.0  # Very high impact

        if num_supports < 5:
            priority = "critical"
            bottleneck = True
            explanation = f"You have {num_supports} support gems. Adding high-quality supports with 'more' multipliers is your best DPS increase."
        elif current_more < 2.0:
            priority = "high"
            bottleneck = True
            explanation = f"Your total 'more' multiplier is {current_more:.2f}x. Upgrade supports to ones with higher 'more' values."
        else:
            priority = "medium"
            bottleneck = False
            explanation = f"Your 'more' multipliers are good ({current_more:.2f}x). Focus on other scaling vectors."

        # Example: Adding 30% more support
        new_more = current_more * 1.3
        percent_gain = ((new_more / current_more) - 1.0) * 100.0

        example = f"+30% more damage support = +{percent_gain:.1f}% DPS"

        recommendations.append(ScalingRecommendation(
            stat_name="More Multipliers (Support Gems)",
            current_value=current_more,
            impact_rating=impact,
            priority=priority,
            explanation=explanation,
            example_improvement=example,
            bottleneck=bottleneck
        ))

        return recommendations

    def _analyze_crit_scaling(
        self,
        stats: Dict[str, float],
        dps_breakdown: DPSBreakdown,
        skill_type: str
    ) -> List[ScalingRecommendation]:
        """Analyze critical strike scaling"""
        recommendations = []

        crit_chance = min(100.0, stats['base_crit_chance'] + stats['increased_crit_chance'])
        crit_multi = stats['crit_multiplier']

        # Calculate crit impact
        current_crit_multi = dps_breakdown.crit_multiplier

        # If not investing in crit at all
        if crit_chance < 20:
            impact = 40.0
            priority = "low"
            explanation = f"You have {crit_chance:.1f}% crit chance. Not worth investing in crit without more chance."
            example = "Skip crit scaling for now"
        # If investing in crit but not optimized
        elif crit_chance < 50:
            impact = 70.0
            priority = "medium"
            explanation = f"You have {crit_chance:.1f}% crit chance. Increasing crit chance to 60%+ would help."
            new_impact = self._calculate_crit_impact(crit_chance + 20, crit_multi)
            old_impact = self._calculate_crit_impact(crit_chance, crit_multi)
            percent_gain = ((new_impact / old_impact) - 1.0) * 100.0
            example = f"+20% crit chance = +{percent_gain:.1f}% DPS"
        # High crit chance, check multiplier
        elif crit_multi < 250:
            impact = 75.0
            priority = "high"
            explanation = f"You have {crit_chance:.1f}% crit but only {crit_multi:.0f}% multiplier. Increase crit multi!"
            new_impact = self._calculate_crit_impact(crit_chance, crit_multi + 50)
            old_impact = self._calculate_crit_impact(crit_chance, crit_multi)
            percent_gain = ((new_impact / old_impact) - 1.0) * 100.0
            example = f"+50% crit multi = +{percent_gain:.1f}% DPS"
        # Well optimized crit
        else:
            impact = 50.0
            priority = "medium"
            explanation = f"Your crit is well optimized ({crit_chance:.1f}% chance, {crit_multi:.0f}% multi). Diminishing returns now."
            example = "Focus on other scaling vectors"

        recommendations.append(ScalingRecommendation(
            stat_name="Critical Strike",
            current_value=crit_chance,
            impact_rating=impact,
            priority=priority,
            explanation=explanation,
            example_improvement=example,
            bottleneck=False
        ))

        return recommendations

    def _analyze_added_damage(
        self,
        stats: Dict[str, float],
        dps_breakdown: DPSBreakdown,
        skill_type: str
    ) -> List[ScalingRecommendation]:
        """Analyze added flat damage"""
        recommendations = []

        added_flat = stats['added_flat_damage']
        base_damage = stats['base_damage']

        # Calculate how much added flat contributes
        contribution_percent = (added_flat / base_damage) * 100.0 if base_damage > 0 else 0

        if contribution_percent < 20:
            impact = 60.0
            priority = "medium"
            explanation = f"Added flat damage is {contribution_percent:.1f}% of your base. Adding more flat damage is effective."
            example = f"+50 flat damage = ~{(50/base_damage)*100:.1f}% more damage (before multipliers)"
        else:
            impact = 40.0
            priority = "low"
            explanation = f"Added flat damage is {contribution_percent:.1f}% of your base. Scaling through multipliers is better."
            example = "Focus on increased/more multipliers instead"

        recommendations.append(ScalingRecommendation(
            stat_name="Added Flat Damage",
            current_value=added_flat,
            impact_rating=impact,
            priority=priority,
            explanation=explanation,
            example_improvement=example,
            bottleneck=False
        ))

        return recommendations

    def _analyze_cast_attack_speed(
        self,
        stats: Dict[str, float],
        dps_breakdown: DPSBreakdown,
        skill_type: str
    ) -> List[ScalingRecommendation]:
        """Analyze cast/attack speed"""
        recommendations = []

        increased_speed = stats['increased_cast_speed']
        speed_name = "Cast Speed" if skill_type == "spell" else "Attack Speed"

        # Speed is linear scaling (doesn't have diminishing returns like increased damage)
        impact = 70.0

        if increased_speed < 50:
            priority = "high"
            explanation = f"You only have {increased_speed:.0f}% increased {speed_name.lower()}. This is excellent linear scaling."
            new_multi = 1.0 + ((increased_speed + 50) / 100.0)
            old_multi = 1.0 + (increased_speed / 100.0)
            percent_gain = ((new_multi / old_multi) - 1.0) * 100.0
            example = f"+50% {speed_name.lower()} = +{percent_gain:.1f}% DPS"
        elif increased_speed < 100:
            priority = "medium"
            explanation = f"You have {increased_speed:.0f}% increased {speed_name.lower()}. Still decent scaling."
            new_multi = 1.0 + ((increased_speed + 30) / 100.0)
            old_multi = 1.0 + (increased_speed / 100.0)
            percent_gain = ((new_multi / old_multi) - 1.0) * 100.0
            example = f"+30% {speed_name.lower()} = +{percent_gain:.1f}% DPS"
        else:
            priority = "low"
            explanation = f"You have {increased_speed:.0f}% increased {speed_name.lower()}. Heavily invested already."
            example = "Focus on other scaling vectors"

        recommendations.append(ScalingRecommendation(
            stat_name=speed_name,
            current_value=increased_speed,
            impact_rating=impact,
            priority=priority,
            explanation=explanation,
            example_improvement=example,
            bottleneck=False
        ))

        return recommendations

    def _calculate_impact_of_increased(self, current: float, additional: float) -> float:
        """Calculate impact rating of adding more increased damage"""
        # Diminishing returns formula
        new_multi = 1.0 + ((current + additional) / 100.0)
        old_multi = 1.0 + (current / 100.0)
        percent_gain = ((new_multi / old_multi) - 1.0) * 100.0

        # Convert to impact rating (0-100)
        # 50% gain = 100 impact, 10% gain = 20 impact
        impact = min(100.0, percent_gain * 2.0)

        return impact

    def _calculate_crit_impact(self, crit_chance: float, crit_multi: float) -> float:
        """Calculate DPS multiplier from crit"""
        chance_decimal = crit_chance / 100.0
        multi_decimal = 1.0 + (crit_multi / 100.0)

        # Expected damage multiplier
        expected = (1.0 - chance_decimal) + (chance_decimal * multi_decimal)

        return expected

    def format_recommendations(self, recommendations: List[ScalingRecommendation]) -> str:
        """Format recommendations as readable text"""
        lines = []
        lines.append("=" * 80)
        lines.append("DAMAGE SCALING ANALYSIS")
        lines.append("=" * 80)
        lines.append("")

        # Group by priority
        by_priority = {
            'critical': [],
            'high': [],
            'medium': [],
            'low': []
        }

        for rec in recommendations:
            by_priority[rec.priority].append(rec)

        for priority in ['critical', 'high', 'medium', 'low']:
            recs = by_priority[priority]
            if not recs:
                continue

            lines.append(f"{priority.upper()} PRIORITY:")
            lines.append("-" * 80)

            for rec in recs:
                lines.append(f"\n{rec.stat_name}:")
                lines.append(f"  Current: {rec.current_value:.1f}")
                lines.append(f"  Impact: {rec.impact_rating:.1f}/100")
                lines.append(f"  {rec.explanation}")
                lines.append(f"  Example: {rec.example_improvement}")
                if rec.bottleneck:
                    lines.append(f"  ⚠️ BOTTLENECK: This stat is limiting your damage!")
                lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)


if __name__ == "__main__":
    # Demo
    analyzer = DamageScalingAnalyzer()

    # Example character with moderate investment
    character = {
        'base_damage': 100,
        'increased_spell_damage': 250,
        'more_multipliers': [30, 25],  # Two supports
        'added_flat_damage': 50,
        'base_crit_chance': 7,
        'increased_crit_chance': 40,
        'crit_multiplier': 180,
        'base_cast_time': 0.8,
        'increased_cast_speed': 30,
        'damage_effectiveness': 100
    }

    recommendations = analyzer.analyze_scaling(character, skill_type="spell")
    print(analyzer.format_recommendations(recommendations))
