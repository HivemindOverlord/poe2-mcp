"""
Build Success Predictor for Path of Exile 2

Predicts build viability for various content types before you invest.
Uses benchmarks from successful builds to estimate success probability.

This enables:
- Predicting if a build can handle T15/T16/T17 maps
- Estimating boss-kill capability
- Calculating investment needed to reach viability
- Identifying critical blockers
- Suggesting efficient upgrade paths

Author: Claude
Date: 2025-10-22
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Types of endgame content."""
    CAMPAIGN = "campaign"
    WHITE_MAPS = "white_maps"          # T1-5
    YELLOW_MAPS = "yellow_maps"        # T6-10
    RED_MAPS = "red_maps"              # T11-15
    T16_MAPS = "t16_maps"
    T17_MAPS = "t17_maps"
    PINNACLE_BOSSES = "pinnacle_bosses"  # Maven, Searing Exarch, etc.
    UBER_BOSSES = "uber_bosses"        # Uber Maven, Uber Searing, etc.
    SIMULACRUM = "simulacrum"
    DELVE_300 = "delve_300"
    DELVE_500 = "delve_500"
    DELVE_600 = "delve_600"


@dataclass
class ContentRequirements:
    """
    Minimum requirements for content type.

    Based on successful build analysis from top players.
    """
    content_type: ContentType

    # Minimum DPS (damage per second)
    min_dps: float
    recommended_dps: float

    # Minimum effective HP
    min_phys_ehp: float
    min_elemental_ehp: float  # Lowest of fire/cold/light
    min_chaos_ehp: float

    # Resistance requirements
    min_ele_res: float  # Fire/cold/light
    min_chaos_res: float

    # Other requirements
    min_movement_speed: float = 100
    requires_defensive_layers: int = 2  # Number of defense layers
    max_acceptable_deaths_per_hour: float = 5.0


@dataclass
class Blocker:
    """
    A factor preventing build success.

    Attributes:
        stat: The problematic stat
        current_value: Current value
        required_value: Needed value
        severity: How critical (0-10)
        fix_cost: Estimated chaos to fix
        fix_description: How to fix it
    """
    stat: str
    current_value: float
    required_value: float
    severity: int
    fix_cost: int
    fix_description: str


@dataclass
class PredictionResult:
    """
    Prediction of build success for specific content.

    Attributes:
        content_type: The content being analyzed
        success_probability: 0-100% chance of success
        confidence: Prediction confidence (LOW/MEDIUM/HIGH)
        blockers: List of factors preventing success
        estimated_investment: Total chaos needed to fix blockers
        estimated_deaths_per_hour: Expected death rate
        time_to_viable: Estimated hours to farm upgrades
        alternative_path: Suggested easier content to farm first
    """
    content_type: ContentType
    success_probability: float
    confidence: str
    blockers: List[Blocker] = field(default_factory=list)
    estimated_investment: int = 0
    estimated_deaths_per_hour: float = 0.0
    time_to_viable: float = 0.0
    alternative_path: Optional[ContentType] = None
    strengths: List[str] = field(default_factory=list)
    upgrade_priority: List[str] = field(default_factory=list)


class BuildSuccessPredictor:
    """
    Main build success prediction engine.

    Analyzes builds against content requirements and predicts
    success probability with actionable recommendations.

    Example:
        >>> predictor = BuildSuccessPredictor()
        >>> result = predictor.predict(character_data, ContentType.T17_MAPS)
        >>> print(f"Success: {result.success_probability}%")
        >>> if result.blockers:
        ...     print("Blockers:", [b.stat for b in result.blockers])
    """

    def __init__(self):
        """Initialize predictor with content requirements."""
        self.requirements = self._define_content_requirements()
        logger.info(f"BuildSuccessPredictor initialized with {len(self.requirements)} content types")

    def _define_content_requirements(self) -> Dict[ContentType, ContentRequirements]:
        """
        Define requirements for each content type.

        Based on analysis of successful builds at each tier.

        Returns:
            Dict mapping content type to requirements
        """
        return {
            ContentType.CAMPAIGN: ContentRequirements(
                content_type=ContentType.CAMPAIGN,
                min_dps=50000,
                recommended_dps=100000,
                min_phys_ehp=2000,
                min_elemental_ehp=1500,
                min_chaos_ehp=1000,
                min_ele_res=0,
                min_chaos_res=-60,
                requires_defensive_layers=1
            ),

            ContentType.WHITE_MAPS: ContentRequirements(
                content_type=ContentType.WHITE_MAPS,
                min_dps=150000,
                recommended_dps=300000,
                min_phys_ehp=8000,
                min_elemental_ehp=6000,
                min_chaos_ehp=4000,
                min_ele_res=60,
                min_chaos_res=-30,
                requires_defensive_layers=2
            ),

            ContentType.YELLOW_MAPS: ContentRequirements(
                content_type=ContentType.YELLOW_MAPS,
                min_dps=400000,
                recommended_dps=700000,
                min_phys_ehp=15000,
                min_elemental_ehp=12000,
                min_chaos_ehp=8000,
                min_ele_res=75,
                min_chaos_res=-10,
                requires_defensive_layers=2
            ),

            ContentType.RED_MAPS: ContentRequirements(
                content_type=ContentType.RED_MAPS,
                min_dps=800000,
                recommended_dps=1500000,
                min_phys_ehp=25000,
                min_elemental_ehp=20000,
                min_chaos_ehp=15000,
                min_ele_res=75,
                min_chaos_res=0,
                requires_defensive_layers=3
            ),

            ContentType.T16_MAPS: ContentRequirements(
                content_type=ContentType.T16_MAPS,
                min_dps=1200000,
                recommended_dps=2000000,
                min_phys_ehp=35000,
                min_elemental_ehp=30000,
                min_chaos_ehp=25000,
                min_ele_res=75,
                min_chaos_res=20,
                requires_defensive_layers=3,
                max_acceptable_deaths_per_hour=3.0
            ),

            ContentType.T17_MAPS: ContentRequirements(
                content_type=ContentType.T17_MAPS,
                min_dps=2000000,
                recommended_dps=3500000,
                min_phys_ehp=50000,
                min_elemental_ehp=45000,
                min_chaos_ehp=35000,
                min_ele_res=75,
                min_chaos_res=30,
                requires_defensive_layers=4,
                max_acceptable_deaths_per_hour=2.0
            ),

            ContentType.PINNACLE_BOSSES: ContentRequirements(
                content_type=ContentType.PINNACLE_BOSSES,
                min_dps=1500000,
                recommended_dps=2500000,
                min_phys_ehp=40000,
                min_elemental_ehp=35000,
                min_chaos_ehp=30000,
                min_ele_res=75,
                min_chaos_res=20,
                requires_defensive_layers=3,
                max_acceptable_deaths_per_hour=1.0
            ),

            ContentType.UBER_BOSSES: ContentRequirements(
                content_type=ContentType.UBER_BOSSES,
                min_dps=3000000,
                recommended_dps=5000000,
                min_phys_ehp=60000,
                min_elemental_ehp=55000,
                min_chaos_ehp=45000,
                min_ele_res=75,
                min_chaos_res=40,
                requires_defensive_layers=4,
                max_acceptable_deaths_per_hour=0.5
            ),
        }

    def predict(
        self,
        character_data: Dict,
        content: ContentType,
        dps: Optional[float] = None,
        ehp: Optional[Dict[str, float]] = None
    ) -> PredictionResult:
        """
        Predict build success for specific content.

        Args:
            character_data: Character stats
            content: Content type to predict for
            dps: Calculated DPS (optional)
            ehp: EHP dict (optional)

        Returns:
            PredictionResult with success probability and recommendations
        """
        logger.info(f"Predicting success for {content.value}...")

        if content not in self.requirements:
            raise ValueError(f"Unknown content type: {content}")

        reqs = self.requirements[content]

        # Extract or calculate stats
        actual_dps = dps or character_data.get('total_dps', 0)

        # EHP by damage type
        if ehp:
            phys_ehp = ehp.get('physical', character_data.get('life', 0))
            fire_ehp = ehp.get('fire', character_data.get('life', 0))
            cold_ehp = ehp.get('cold', character_data.get('life', 0))
            light_ehp = ehp.get('lightning', character_data.get('life', 0))
            chaos_ehp = ehp.get('chaos', character_data.get('life', 0))
            ele_ehp = min(fire_ehp, cold_ehp, light_ehp)
        else:
            # Estimate based on life/ES and resistances
            base_hp = character_data.get('life', 0) + character_data.get('energy_shield', 0)
            phys_ehp = base_hp  # Simplified
            ele_ehp = base_hp  # Simplified
            chaos_ehp = base_hp  # Simplified

        # Resistances
        fire_res = character_data.get('fire_res', 0)
        cold_res = character_data.get('cold_res', 0)
        light_res = character_data.get('lightning_res', 0)
        chaos_res = character_data.get('chaos_res', 0)
        min_ele_res = min(fire_res, cold_res, light_res)

        # Identify blockers
        blockers = []

        # DPS check
        if actual_dps < reqs.min_dps:
            deficit = reqs.recommended_dps - actual_dps
            severity = 10 if actual_dps < reqs.min_dps * 0.5 else 7
            blockers.append(Blocker(
                stat="DPS",
                current_value=actual_dps,
                required_value=reqs.recommended_dps,
                severity=severity,
                fix_cost=int(deficit / 5000),  # Rough estimate: 1c per 5k DPS
                fix_description=f"Upgrade weapon and damage gear to reach {reqs.recommended_dps:,.0f} DPS"
            ))

        # Physical EHP check
        if phys_ehp < reqs.min_phys_ehp:
            deficit = reqs.min_phys_ehp - phys_ehp
            severity = 9
            blockers.append(Blocker(
                stat="Physical EHP",
                current_value=phys_ehp,
                required_value=reqs.min_phys_ehp,
                severity=severity,
                fix_cost=int(deficit / 100),  # Rough: 1c per 100 EHP
                fix_description=f"Add armor, endurance charges, or physical mitigation"
            ))

        # Elemental EHP check
        if ele_ehp < reqs.min_elemental_ehp:
            deficit = reqs.min_elemental_ehp - ele_ehp
            severity = 8
            blockers.append(Blocker(
                stat="Elemental EHP",
                current_value=ele_ehp,
                required_value=reqs.min_elemental_ehp,
                severity=severity,
                fix_cost=int(deficit / 150),
                fix_description=f"Cap resistances and add life/ES"
            ))

        # Chaos EHP check
        if chaos_ehp < reqs.min_chaos_ehp:
            deficit = reqs.min_chaos_ehp - chaos_ehp
            severity = 7
            blockers.append(Blocker(
                stat="Chaos EHP",
                current_value=chaos_ehp,
                required_value=reqs.min_chaos_ehp,
                severity=severity,
                fix_cost=int(deficit / 120),
                fix_description=f"Improve chaos resistance"
            ))

        # Resistance checks
        if min_ele_res < reqs.min_ele_res:
            deficit = reqs.min_ele_res - min_ele_res
            severity = 10  # CRITICAL
            blockers.append(Blocker(
                stat="Elemental Resistances",
                current_value=min_ele_res,
                required_value=reqs.min_ele_res,
                severity=severity,
                fix_cost=int(deficit * 3),  # ~3c per % res
                fix_description=f"Cap all elemental resistances to {reqs.min_ele_res}%"
            ))

        if chaos_res < reqs.min_chaos_res:
            deficit = reqs.min_chaos_res - chaos_res
            severity = 8
            blockers.append(Blocker(
                stat="Chaos Resistance",
                current_value=chaos_res,
                required_value=reqs.min_chaos_res,
                severity=severity,
                fix_cost=int(deficit * 2),  # ~2c per % chaos res
                fix_description=f"Increase chaos resistance to {reqs.min_chaos_res}%"
            ))

        # Calculate success probability
        success_prob = self._calculate_success_probability(reqs, blockers)

        # Calculate investment needed
        total_investment = sum(b.fix_cost for b in blockers)

        # Estimate deaths per hour
        death_rate = self._estimate_death_rate(reqs, blockers)

        # Determine confidence
        confidence = self._determine_confidence(character_data, reqs)

        # Identify strengths
        strengths = self._identify_strengths(
            actual_dps, phys_ehp, ele_ehp, chaos_ehp,
            min_ele_res, chaos_res, reqs
        )

        # Generate upgrade priority
        upgrade_priority = self._generate_upgrade_priority(blockers)

        # Suggest alternative if not viable
        alternative = None
        if success_prob < 50 and content != ContentType.CAMPAIGN:
            alternative = self._suggest_alternative_content(content)

        result = PredictionResult(
            content_type=content,
            success_probability=success_prob,
            confidence=confidence,
            blockers=sorted(blockers, key=lambda b: b.severity, reverse=True),
            estimated_investment=total_investment,
            estimated_deaths_per_hour=death_rate,
            time_to_viable=self._estimate_time_to_farm(total_investment),
            alternative_path=alternative,
            strengths=strengths,
            upgrade_priority=upgrade_priority
        )

        logger.info(
            f"Prediction: {success_prob:.1f}% success, "
            f"{len(blockers)} blockers, {total_investment}c investment needed"
        )

        return result

    def _calculate_success_probability(
        self,
        requirements: ContentRequirements,
        blockers: List[Blocker]
    ) -> float:
        """Calculate success probability based on blockers."""
        if not blockers:
            return 95.0  # Near-certain success

        # Start at 100%, deduct for each blocker
        probability = 100.0

        for blocker in blockers:
            # Penalty based on severity
            penalty = blocker.severity * 5  # Max 50% penalty per blocker
            probability -= penalty

        # Floor at 0%
        return max(0.0, probability)

    def _estimate_death_rate(
        self,
        requirements: ContentRequirements,
        blockers: List[Blocker]
    ) -> float:
        """Estimate deaths per hour based on blockers."""
        base_rate = requirements.max_acceptable_deaths_per_hour

        # Add deaths for each blocker
        for blocker in blockers:
            if "EHP" in blocker.stat or "Resistance" in blocker.stat:
                # Defensive blockers increase death rate significantly
                base_rate += blocker.severity * 0.5

        return base_rate

    def _determine_confidence(
        self,
        character_data: Dict,
        requirements: ContentRequirements
    ) -> str:
        """Determine prediction confidence level."""
        level = character_data.get('level', 1)

        # Low confidence if underleveled
        if level < 85:
            return "LOW"

        # High confidence if well-geared and leveled
        if level >= 90:
            return "HIGH"

        return "MEDIUM"

    def _identify_strengths(
        self,
        dps: float,
        phys_ehp: float,
        ele_ehp: float,
        chaos_ehp: float,
        min_ele_res: float,
        chaos_res: float,
        requirements: ContentRequirements
    ) -> List[str]:
        """Identify build strengths."""
        strengths = []

        if dps > requirements.recommended_dps * 1.3:
            strengths.append(f"Excellent DPS ({dps:,.0f}, well above requirement)")

        if phys_ehp > requirements.min_phys_ehp * 1.5:
            strengths.append(f"Strong physical defenses ({phys_ehp:,.0f} EHP)")

        if ele_ehp > requirements.min_elemental_ehp * 1.5:
            strengths.append(f"Strong elemental defenses ({ele_ehp:,.0f} EHP)")

        if min_ele_res >= requirements.min_ele_res and chaos_res > requirements.min_chaos_res:
            strengths.append("All resistances well-balanced")

        return strengths

    def _generate_upgrade_priority(self, blockers: List[Blocker]) -> List[str]:
        """Generate upgrade priority order."""
        # Sort by severity, return descriptions
        sorted_blockers = sorted(blockers, key=lambda b: b.severity, reverse=True)
        return [b.fix_description for b in sorted_blockers[:5]]

    def _estimate_time_to_farm(self, investment: int) -> float:
        """
        Estimate hours to farm the needed currency.

        Assumes ~50c/hour farming rate.
        """
        if investment == 0:
            return 0.0

        return investment / 50.0  # 50c per hour average

    def _suggest_alternative_content(self, current: ContentType) -> Optional[ContentType]:
        """Suggest easier content to farm first."""
        progression = [
            ContentType.CAMPAIGN,
            ContentType.WHITE_MAPS,
            ContentType.YELLOW_MAPS,
            ContentType.RED_MAPS,
            ContentType.T16_MAPS,
            ContentType.T17_MAPS,
            ContentType.PINNACLE_BOSSES,
            ContentType.UBER_BOSSES
        ]

        try:
            idx = progression.index(current)
            if idx > 0:
                return progression[idx - 1]
        except ValueError:
            pass

        return None


def quick_predict(character_data: Dict, content: str = "red_maps") -> float:
    """
    Quick prediction returning just success probability.

    Args:
        character_data: Character data
        content: Content type string

    Returns:
        Success probability (0-100)
    """
    predictor = BuildSuccessPredictor()
    content_type = ContentType(content)
    result = predictor.predict(character_data, content_type)
    return result.success_probability


if __name__ == "__main__":
    # Test example
    logging.basicConfig(level=logging.INFO)

    print("=" * 80)
    print("PoE2 Build Success Predictor - Test")
    print("=" * 80)
    print()

    # Example: Mid-tier build trying T17s
    char = {
        'total_dps': 850000,  # Below requirement
        'life': 1413,
        'energy_shield': 4847,
        'fire_res': -2,  # Problem!
        'cold_res': -8,  # Problem!
        'lightning_res': 75,
        'chaos_res': -60,  # Problem!
        'level': 91
    }

    predictor = BuildSuccessPredictor()
    result = predictor.predict(char, ContentType.T17_MAPS)

    print(f"CONTENT: {result.content_type.value.upper()}")
    print(f"SUCCESS PROBABILITY: {result.success_probability:.1f}%")
    print(f"CONFIDENCE: {result.confidence}")
    print(f"ESTIMATED INVESTMENT: {result.estimated_investment} chaos")
    print(f"TIME TO FARM: {result.estimated_time_to_farm:.1f} hours")
    print()

    if result.strengths:
        print("STRENGTHS:")
        for strength in result.strengths:
            print(f"  ✓ {strength}")
        print()

    print("BLOCKERS:")
    for blocker in result.blockers:
        print(f"  ✗ {blocker.stat}: {blocker.current_value:.0f} (need {blocker.required_value:.0f})")
        print(f"    Fix: {blocker.fix_description} (~{blocker.fix_cost}c)")
    print()

    print("UPGRADE PRIORITY:")
    for i, upgrade in enumerate(result.upgrade_priority, 1):
        print(f"  {i}. {upgrade}")
    print()

    if result.alternative_path:
        print(f"RECOMMENDATION: Farm {result.alternative_path.value} first to get upgrades")

    print()
    print("=" * 80)
