"""
Build Archetype Classifier for Path of Exile 2

Automatically classifies builds into standard archetypes and compares
performance within each archetype category.

This enables:
- Understanding build strengths/weaknesses relative to archetype
- Benchmarking against similar builds
- Identifying hybrid archetypes
- Recommending archetype-specific optimizations

Author: Claude
Date: 2025-10-22
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class BuildArchetype(Enum):
    """Standard PoE2 build archetypes."""
    GLASS_CANNON = "glass_cannon"              # High DPS, low defenses
    IMMORTAL_TANK = "immortal_tank"            # High EHP, low DPS
    HIT_AND_RUN = "hit_and_run"                # Mobility-based
    AILMENT_PROLIFERATOR = "ailment_proliferator"  # Ignite/freeze spreader
    MINION_ARMY = "minion_army"                # Summoner
    AURA_STACKER = "aura_stacker"              # Herald/aura scaling
    TOTEM_PLACER = "totem_placer"              # Totem build
    TRIGGER_BOMBER = "trigger_bomber"          # CWDT/CoC
    DOT_APPLICATOR = "dot_applicator"          # DoT damage
    CRIT_ASSASSIN = "crit_assassin"            # Crit-based one-shots
    BALANCED_ALLROUNDER = "balanced_allrounder"  # Jack of all trades
    ES_RECHARGE_TANK = "es_recharge_tank"      # ES recharge focused
    BLOCK_TANK = "block_tank"                  # Block-based defense
    EVASION = "evasion"                        # Evasion-based defense
    LIFE_REGEN = "life_regen"                  # Life regeneration tank


@dataclass
class ArchetypeSignature:
    """
    Signature characteristics that define an archetype.

    Each archetype has typical stat ranges and characteristics.
    """
    name: BuildArchetype

    # Stat ranges (min, max, ideal)
    dps_range: Tuple[float, float, float] = (0, 999999, 500000)
    ehp_range: Tuple[float, float, float] = (0, 999999, 20000)

    # Boolean characteristics
    requires_high_crit: bool = False
    requires_minions: bool = False
    requires_totems: bool = False
    requires_block: bool = False
    requires_evasion: bool = False
    requires_es_recharge: bool = False
    requires_life_regen: bool = False
    requires_movement_speed: bool = False
    requires_ailment_focus: bool = False
    requires_dot_focus: bool = False
    requires_auras: bool = False

    # Stat priorities (what matters most)
    priority_stats: List[str] = field(default_factory=list)

    # Typical weaknesses
    common_weaknesses: List[str] = field(default_factory=list)


@dataclass
class ArchetypeMatch:
    """
    Result of archetype classification.

    Attributes:
        primary_archetype: Best matching archetype
        match_score: How well build matches archetype (0-100)
        secondary_archetype: Second-best match (for hybrids)
        secondary_score: Score for secondary archetype
        archetype_purity: How "pure" the build is (0-100)
        strengths: What this build does well for its archetype
        weaknesses: What this build lacks for its archetype
        recommendations: Archetype-specific improvements
    """
    primary_archetype: BuildArchetype
    match_score: float
    secondary_archetype: Optional[BuildArchetype] = None
    secondary_score: float = 0.0
    archetype_purity: float = 100.0
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    vs_archetype_stats: Dict[str, float] = field(default_factory=dict)


class ArchetypeClassifier:
    """
    Main archetype classification engine.

    Analyzes builds and classifies them into standard archetypes,
    then provides archetype-specific optimization recommendations.

    Example:
        >>> classifier = ArchetypeClassifier()
        >>> match = classifier.classify_build(character_data)
        >>> print(f"You are a {match.primary_archetype.value}")
        >>> print(f"Match score: {match.match_score}/100")
    """

    def __init__(self) -> None:
        """Initialize classifier with archetype signatures."""
        self.archetypes = self._define_archetypes()
        logger.info(f"ArchetypeClassifier initialized with {len(self.archetypes)} archetypes")

    def _define_archetypes(self) -> Dict[BuildArchetype, ArchetypeSignature]:
        """
        Define signature characteristics for each archetype.

        Returns:
            Dictionary mapping archetype to its signature
        """
        return {
            BuildArchetype.GLASS_CANNON: ArchetypeSignature(
                name=BuildArchetype.GLASS_CANNON,
                dps_range=(1000000, 9999999, 3000000),  # Very high DPS
                ehp_range=(5000, 15000, 10000),          # Low EHP
                requires_high_crit=True,
                priority_stats=["dps", "crit_chance", "crit_multi"],
                common_weaknesses=["physical_ehp", "chaos_res", "stun_vulnerability"]
            ),

            BuildArchetype.IMMORTAL_TANK: ArchetypeSignature(
                name=BuildArchetype.IMMORTAL_TANK,
                dps_range=(100000, 800000, 400000),      # Low-medium DPS
                ehp_range=(40000, 200000, 80000),        # Very high EHP
                requires_block=True,
                priority_stats=["ehp", "resistances", "armor", "block"],
                common_weaknesses=["dps", "clear_speed", "boss_damage"]
            ),

            BuildArchetype.CRIT_ASSASSIN: ArchetypeSignature(
                name=BuildArchetype.CRIT_ASSASSIN,
                dps_range=(1500000, 9999999, 4000000),   # Very high burst
                ehp_range=(8000, 20000, 12000),          # Low-medium EHP
                requires_high_crit=True,
                priority_stats=["crit_chance", "crit_multi", "power_charges"],
                common_weaknesses=["sustained_damage", "physical_mitigation"]
            ),

            BuildArchetype.DOT_APPLICATOR: ArchetypeSignature(
                name=BuildArchetype.DOT_APPLICATOR,
                dps_range=(500000, 3000000, 1500000),    # Medium-high DoT
                ehp_range=(15000, 40000, 25000),         # Medium EHP
                requires_dot_focus=True,
                priority_stats=["dot_multi", "ailment_effect", "duration"],
                common_weaknesses=["single_target_burst", "physical_bosses"]
            ),

            BuildArchetype.MINION_ARMY: ArchetypeSignature(
                name=BuildArchetype.MINION_ARMY,
                dps_range=(800000, 4000000, 2000000),    # Minion DPS
                ehp_range=(20000, 60000, 35000),         # Medium-high EHP
                requires_minions=True,
                priority_stats=["minion_damage", "minion_life", "spirit"],
                common_weaknesses=["personal_damage", "minion_survivability"]
            ),

            BuildArchetype.AURA_STACKER: ArchetypeSignature(
                name=BuildArchetype.AURA_STACKER,
                dps_range=(1200000, 6000000, 2500000),
                ehp_range=(25000, 80000, 45000),
                requires_auras=True,
                priority_stats=["aura_effect", "spirit", "increased_effect"],
                common_weaknesses=["early_game_power", "gear_dependency"]
            ),

            BuildArchetype.ES_RECHARGE_TANK: ArchetypeSignature(
                name=BuildArchetype.ES_RECHARGE_TANK,
                dps_range=(400000, 1500000, 800000),
                ehp_range=(30000, 100000, 55000),
                requires_es_recharge=True,
                priority_stats=["es", "es_recharge_rate", "chaos_res"],
                common_weaknesses=["chaos_damage", "continuous_damage"]
            ),

            BuildArchetype.BLOCK_TANK: ArchetypeSignature(
                name=BuildArchetype.BLOCK_TANK,
                dps_range=(500000, 2000000, 1000000),
                ehp_range=(30000, 90000, 50000),
                requires_block=True,
                priority_stats=["block_chance", "life", "armor"],
                common_weaknesses=["spell_damage", "dot_damage"]
            ),

            BuildArchetype.EVASION: ArchetypeSignature(
                name=BuildArchetype.EVASION,
                dps_range=(600000, 2500000, 1200000),
                ehp_range=(12000, 30000, 18000),
                requires_evasion=True,
                requires_movement_speed=True,
                priority_stats=["evasion", "movement_speed", "spell_suppression"],
                common_weaknesses=["spell_hits", "unavoidable_damage", "stun"]
            ),

            BuildArchetype.BALANCED_ALLROUNDER: ArchetypeSignature(
                name=BuildArchetype.BALANCED_ALLROUNDER,
                dps_range=(800000, 2500000, 1500000),
                ehp_range=(20000, 45000, 30000),
                priority_stats=["dps", "ehp", "resistances", "movement"],
                common_weaknesses=["specialization", "min_maxing"]
            ),
        }

    def classify_build(
        self,
        character_data: Dict,
        dps: Optional[float] = None,
        ehp: Optional[Dict[str, float]] = None
    ) -> ArchetypeMatch:
        """
        Classify a build into an archetype.

        Args:
            character_data: Character stat data
            dps: Total DPS (calculated or provided)
            ehp: EHP for all damage types (calculated or provided)

        Returns:
            ArchetypeMatch with classification results
        """
        logger.info("Classifying build archetype...")

        # Extract key characteristics
        characteristics = self._extract_characteristics(character_data, dps, ehp)

        # Score against each archetype
        scores = {}
        for archetype, signature in self.archetypes.items():
            score = self._calculate_archetype_score(characteristics, signature)
            scores[archetype] = score

        # Find best matches
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary_archetype, primary_score = sorted_scores[0]
        secondary_archetype, secondary_score = sorted_scores[1] if len(sorted_scores) > 1 else (None, 0)

        # Calculate purity (how "pure" vs hybrid)
        archetype_purity = self._calculate_purity(primary_score, secondary_score)

        # Identify strengths and weaknesses
        strengths, weaknesses = self._analyze_archetype_fit(
            characteristics,
            self.archetypes[primary_archetype]
        )

        # Generate recommendations
        recommendations = self._generate_archetype_recommendations(
            characteristics,
            self.archetypes[primary_archetype],
            weaknesses
        )

        result = ArchetypeMatch(
            primary_archetype=primary_archetype,
            match_score=primary_score,
            secondary_archetype=secondary_archetype,
            secondary_score=secondary_score,
            archetype_purity=archetype_purity,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations
        )

        logger.info(
            f"Build classified as {primary_archetype.value} "
            f"(score: {primary_score:.1f}, purity: {archetype_purity:.1f}%)"
        )

        return result

    def _extract_characteristics(
        self,
        character_data: Dict,
        dps: Optional[float],
        ehp: Optional[Dict[str, float]]
    ) -> Dict:
        """Extract key characteristics from character data."""
        char = character_data

        # Calculate average EHP if provided
        avg_ehp = 0
        if ehp:
            ehp_values = [v for k, v in ehp.items() if k != 'summary']
            avg_ehp = sum(ehp_values) / len(ehp_values) if ehp_values else 0

        return {
            'dps': dps or char.get('total_dps', 0),
            'ehp': avg_ehp or char.get('life', 0) + char.get('energy_shield', 0),
            'life': char.get('life', 0),
            'es': char.get('energy_shield', 0),
            'armor': char.get('armor', 0),
            'evasion': char.get('evasion', 0),
            'block': char.get('block_chance', 0),
            'crit_chance': char.get('crit_chance', 0),
            'movement_speed': char.get('movement_speed', 100),
            'spirit_reserved': char.get('spirit_reserved', 0),
            'spirit_max': char.get('spirit_max', 0),

            # Derived characteristics
            'is_crit_build': char.get('crit_chance', 0) > 50,
            'is_es_build': char.get('energy_shield', 0) > char.get('life', 0),
            'is_life_build': char.get('life', 0) > char.get('energy_shield', 0),
            'has_high_block': char.get('block_chance', 0) > 40,
            'has_high_evasion': char.get('evasion', 0) > 10000,
            'uses_spirit': char.get('spirit_reserved', 0) > 0,
        }

    def _calculate_archetype_score(
        self,
        characteristics: Dict,
        signature: ArchetypeSignature
    ) -> float:
        """
        Calculate how well characteristics match an archetype signature.

        Returns score 0-100.
        """
        score = 50.0  # Start at neutral

        # DPS fit
        dps = characteristics['dps']
        dps_min, dps_max, dps_ideal = signature.dps_range
        if dps_min <= dps <= dps_max:
            # Within range
            dps_score = 100 - abs(dps - dps_ideal) / dps_ideal * 50
            score += dps_score * 0.3  # 30% weight
        else:
            # Out of range - penalty
            score -= 20

        # EHP fit
        ehp = characteristics['ehp']
        ehp_min, ehp_max, ehp_ideal = signature.ehp_range
        if ehp_min <= ehp <= ehp_max:
            ehp_score = 100 - abs(ehp - ehp_ideal) / ehp_ideal * 50
            score += ehp_score * 0.3  # 30% weight
        else:
            score -= 20

        # Boolean requirements
        requirements_met = 0
        requirements_total = 0

        if signature.requires_high_crit:
            requirements_total += 1
            if characteristics['is_crit_build']:
                requirements_met += 1

        if signature.requires_block:
            requirements_total += 1
            if characteristics['has_high_block']:
                requirements_met += 1

        if signature.requires_evasion:
            requirements_total += 1
            if characteristics['has_high_evasion']:
                requirements_met += 1

        if signature.requires_es_recharge:
            requirements_total += 1
            if characteristics['is_es_build']:
                requirements_met += 1

        if signature.requires_auras:
            requirements_total += 1
            if characteristics['uses_spirit']:
                requirements_met += 1

        # Requirement score
        if requirements_total > 0:
            req_score = (requirements_met / requirements_total) * 100
            score += req_score * 0.4  # 40% weight

        # Clamp to 0-100
        return max(0, min(100, score))

    def _calculate_purity(self, primary_score: float, secondary_score: float) -> float:
        """
        Calculate archetype purity.

        High purity = strong primary, weak secondary
        Low purity = hybrid build with similar scores
        """
        if secondary_score == 0:
            return 100.0

        # Purity is inversely related to how close secondary is to primary
        gap = primary_score - secondary_score
        purity = min(100, max(0, gap * 2))

        return purity

    def _analyze_archetype_fit(
        self,
        characteristics: Dict,
        signature: ArchetypeSignature
    ) -> Tuple[List[str], List[str]]:
        """
        Analyze strengths and weaknesses relative to archetype.

        Returns:
            (strengths, weaknesses)
        """
        strengths = []
        weaknesses = []

        # Check DPS
        dps = characteristics['dps']
        _, _, dps_ideal = signature.dps_range
        if dps > dps_ideal * 1.2:
            strengths.append(f"Exceptional DPS ({dps:,.0f}, {((dps/dps_ideal - 1) * 100):.1f}% above archetype average)")
        elif dps < dps_ideal * 0.7:
            weaknesses.append(f"Below-average DPS ({dps:,.0f}, need {dps_ideal:,.0f})")

        # Check EHP
        ehp = characteristics['ehp']
        _, _, ehp_ideal = signature.ehp_range
        if ehp > ehp_ideal * 1.3:
            strengths.append(f"Excellent survivability ({ehp:,.0f} EHP, {((ehp/ehp_ideal - 1) * 100):.1f}% above average)")
        elif ehp < ehp_ideal * 0.7:
            weaknesses.append(f"Low survivability ({ehp:,.0f} EHP, need {ehp_ideal:,.0f})")

        # Check specific requirements
        if signature.requires_high_crit and not characteristics['is_crit_build']:
            weaknesses.append(f"Low crit chance ({characteristics['crit_chance']:.1f}%, need 50%+)")

        if signature.requires_block and not characteristics['has_high_block']:
            weaknesses.append(f"Low block chance ({characteristics['block']:.1f}%, need 40%+)")

        return strengths, weaknesses

    def _generate_archetype_recommendations(
        self,
        characteristics: Dict,
        signature: ArchetypeSignature,
        weaknesses: List[str]
    ) -> List[str]:
        """Generate archetype-specific recommendations."""
        recommendations = []

        # Add priority stat recommendations
        for priority_stat in signature.priority_stats[:3]:  # Top 3 priorities
            if priority_stat == "dps" and characteristics['dps'] < signature.dps_range[2]:
                recommendations.append(f"Increase DPS to reach {signature.dps_range[2]:,.0f} (archetype ideal)")

            elif priority_stat == "ehp" and characteristics['ehp'] < signature.ehp_range[2]:
                recommendations.append(f"Increase EHP to reach {signature.ehp_range[2]:,.0f} (archetype ideal)")

            elif priority_stat == "crit_chance" and characteristics['crit_chance'] < 60:
                recommendations.append("Increase crit chance to 60%+ for reliable crits")

            elif priority_stat == "block_chance" and characteristics['block'] < 45:
                recommendations.append("Increase block chance to 45%+ (near PoE2 cap of 50%)")

        # Add common weakness warnings
        for weakness in signature.common_weaknesses:
            recommendations.append(f"Watch out for {weakness.replace('_', ' ')} (common archetype weakness)")

        return recommendations[:5]  # Top 5 recommendations


def quick_classify(character_data: Dict) -> str:
    """
    Quick classification returning just the archetype name.

    Args:
        character_data: Character data

    Returns:
        Archetype name string
    """
    classifier = ArchetypeClassifier()
    match = classifier.classify_build(character_data)
    return match.primary_archetype.value


if __name__ == "__main__":
    # Test example
    logging.basicConfig(level=logging.INFO)

    print("=" * 80)
    print("PoE2 Build Archetype Classifier - Test")
    print("=" * 80)
    print()

    # Example: Glass cannon build
    glass_cannon = {
        'total_dps': 3500000,
        'life': 1200,
        'energy_shield': 4800,
        'armor': 2000,
        'evasion': 500,
        'block_chance': 15,
        'crit_chance': 75,
        'movement_speed': 120,
        'spirit_reserved': 0,
        'spirit_max': 0
    }

    classifier = ArchetypeClassifier()
    result = classifier.classify_build(glass_cannon)

    print(f"PRIMARY ARCHETYPE: {result.primary_archetype.value}")
    print(f"Match Score: {result.match_score:.1f}/100")
    print(f"Purity: {result.archetype_purity:.1f}%")
    print()

    if result.secondary_archetype:
        print(f"SECONDARY: {result.secondary_archetype.value} ({result.secondary_score:.1f}/100)")
        print()

    print("STRENGTHS:")
    for strength in result.strengths:
        print(f"  ✓ {strength}")
    print()

    print("WEAKNESSES:")
    for weakness in result.weaknesses:
        print(f"  ✗ {weakness}")
    print()

    print("RECOMMENDATIONS:")
    for i, rec in enumerate(result.recommendations, 1):
        print(f"  {i}. {rec}")

    print()
    print("=" * 80)
