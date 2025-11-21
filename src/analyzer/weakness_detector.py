"""
Weakness Detector for Path of Exile 2 Builds

This module automatically identifies character weaknesses and provides
actionable recommendations for improvement.

Integrates with all calculator modules to provide comprehensive analysis:
- Resistance gaps (using defense_calculator)
- Life/ES pool deficiencies (using resource_calculator)
- Spirit overflow issues (using spirit_calculator)
- Overcapped stats (wasted investment)
- Missing defensive layers (using ehp_calculator)
- Stun vulnerability (using stun_calculator)

Author: Claude
Date: 2025-10-22
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

# Import all our calculator modules
from ..calculator.defense_calculator import DefenseCalculator, DefenseConstants
from ..calculator.resource_calculator import ResourceCalculator, AttributeStats
from ..calculator.ehp_calculator import EHPCalculator, DefensiveStats, ThreatProfile, DamageType
from ..calculator.spirit_calculator import SpiritCalculator
from ..calculator.damage_calculator import DamageCalculator

logger = logging.getLogger(__name__)


class WeaknessSeverity(Enum):
    """Severity levels for weaknesses."""
    CRITICAL = "critical"  # Immediate danger (negative res, no life)
    HIGH = "high"  # Serious problem (very low EHP, overcapped)
    MEDIUM = "medium"  # Room for improvement
    LOW = "low"  # Minor optimization
    INFO = "info"  # Informational only


class WeaknessCategory(Enum):
    """Categories of weaknesses."""
    RESISTANCE = "resistance"
    LIFE_POOL = "life_pool"
    ENERGY_SHIELD = "energy_shield"
    DEFENSE_LAYERS = "defense_layers"
    SPIRIT = "spirit"
    OVERCAPPED_STAT = "overcapped_stat"
    DAMAGE = "damage"
    RESOURCE_MANAGEMENT = "resource_management"
    STUN_VULNERABILITY = "stun_vulnerability"


@dataclass
class Weakness:
    """
    Represents a detected character weakness.

    Attributes:
        category: Category of weakness
        severity: Severity level
        title: Short title
        description: Detailed description
        current_value: Current value of the stat
        recommended_value: Recommended target value
        impact: Impact description
        recommendations: List of specific recommendations to fix
        priority: Priority score (0-100, higher = more urgent)
    """
    category: WeaknessCategory
    severity: WeaknessSeverity
    title: str
    description: str
    current_value: Any
    recommended_value: Any
    impact: str
    recommendations: List[str] = field(default_factory=list)
    priority: int = 50


@dataclass
class CharacterData:
    """
    Simplified character data for weakness detection.

    This is a convenience wrapper that extracts the necessary data
    from the full character JSON.
    """
    level: int
    character_class: str

    # Core stats
    life: float
    energy_shield: float
    mana: float
    spirit_max: int = 0
    spirit_reserved: int = 0

    # Attributes
    strength: int = 0
    dexterity: int = 0
    intelligence: int = 0

    # Defenses
    armor: float = 0.0
    evasion: float = 0.0
    block_chance: float = 0.0

    # Resistances
    fire_res: float = 0.0
    cold_res: float = 0.0
    lightning_res: float = 0.0
    chaos_res: float = 0.0

    # Damage (if available)
    total_dps: Optional[float] = None

    # Gear slots (for detecting missing items)
    equipped_items: Dict[str, bool] = field(default_factory=dict)


class WeaknessDetector:
    """
    Main weakness detection engine.

    Uses all available calculator modules to provide comprehensive
    character analysis and improvement recommendations.

    Example:
        >>> detector = WeaknessDetector()
        >>> char_data = CharacterData(level=91, character_class="Stormweaver", ...)
        >>> weaknesses = detector.detect_all_weaknesses(char_data)
        >>> for weakness in weaknesses:
        ...     print(f"[{weakness.severity.value.upper()}] {weakness.title}")
    """

    def __init__(self):
        """Initialize weakness detector with calculator modules."""
        self.defense_calc = DefenseCalculator()
        self.ehp_calc = EHPCalculator()
        # Note: ResourceCalculator and DamageCalculator require parameters,
        # so they're created on-demand when needed

        logger.info("WeaknessDetector initialized")

    # ============================================================================
    # MAIN DETECTION METHODS
    # ============================================================================

    def detect_all_weaknesses(
        self,
        char_data: CharacterData,
        threat_profile: Optional[ThreatProfile] = None
    ) -> List[Weakness]:
        """
        Detect all weaknesses in a character build.

        Args:
            char_data: Character data to analyze
            threat_profile: Optional threat profile for EHP calculations

        Returns:
            List of detected weaknesses, sorted by priority (highest first)
        """
        logger.info(f"Detecting weaknesses for level {char_data.level} {char_data.character_class}")

        threat_profile = threat_profile or ThreatProfile()
        weaknesses = []

        # Run all detection methods
        weaknesses.extend(self._detect_resistance_gaps(char_data))
        weaknesses.extend(self._detect_life_pool_issues(char_data))
        weaknesses.extend(self._detect_es_issues(char_data))
        weaknesses.extend(self._detect_spirit_issues(char_data))
        weaknesses.extend(self._detect_overcapped_stats(char_data))
        weaknesses.extend(self._detect_defense_layer_issues(char_data, threat_profile))
        weaknesses.extend(self._detect_stun_vulnerability(char_data))
        weaknesses.extend(self._detect_resource_issues(char_data))

        # Sort by priority (highest first)
        weaknesses.sort(key=lambda w: w.priority, reverse=True)

        logger.info(f"Detected {len(weaknesses)} weaknesses")
        return weaknesses

    def get_critical_weaknesses(
        self,
        char_data: CharacterData
    ) -> List[Weakness]:
        """
        Get only CRITICAL severity weaknesses.

        These are issues that need immediate attention.
        """
        all_weaknesses = self.detect_all_weaknesses(char_data)
        critical = [w for w in all_weaknesses if w.severity == WeaknessSeverity.CRITICAL]
        logger.info(f"Found {len(critical)} critical weaknesses")
        return critical

    def get_weakness_summary(
        self,
        char_data: CharacterData
    ) -> Dict[str, Any]:
        """
        Get a summary of all weaknesses by category and severity.

        Returns:
            Dictionary with summary statistics
        """
        weaknesses = self.detect_all_weaknesses(char_data)

        # Count by severity
        by_severity = {
            severity: len([w for w in weaknesses if w.severity == severity])
            for severity in WeaknessSeverity
        }

        # Count by category
        by_category = {
            category: len([w for w in weaknesses if w.category == category])
            for category in WeaknessCategory
        }

        # Get top priorities
        top_5 = weaknesses[:5]

        summary = {
            'total_weaknesses': len(weaknesses),
            'by_severity': {k.value: v for k, v in by_severity.items()},
            'by_category': {k.value: v for k, v in by_category.items()},
            'top_priorities': [
                {
                    'title': w.title,
                    'severity': w.severity.value,
                    'category': w.category.value,
                    'priority': w.priority
                }
                for w in top_5
            ],
            'needs_immediate_attention': by_severity[WeaknessSeverity.CRITICAL] > 0
        }

        return summary

    # ============================================================================
    # RESISTANCE DETECTION
    # ============================================================================

    def _detect_resistance_gaps(self, char_data: CharacterData) -> List[Weakness]:
        """Detect resistance weaknesses."""
        weaknesses = []
        cap = DefenseConstants.RESISTANCE_DEFAULT_CAP

        resistances = {
            'Fire': char_data.fire_res,
            'Cold': char_data.cold_res,
            'Lightning': char_data.lightning_res,
            'Chaos': char_data.chaos_res
        }

        for res_name, res_value in resistances.items():
            # Negative resistances (CRITICAL)
            if res_value < 0:
                deficit = abs(res_value)
                weaknesses.append(Weakness(
                    category=WeaknessCategory.RESISTANCE,
                    severity=WeaknessSeverity.CRITICAL,
                    title=f"Negative {res_name} Resistance",
                    description=f"{res_name} resistance is {res_value:.0f}%, amplifying damage taken",
                    current_value=res_value,
                    recommended_value=cap,
                    impact=f"Taking {deficit:.0f}% MORE {res_name.lower()} damage",
                    recommendations=[
                        f"Add +{deficit:.0f}% {res_name} resistance to reach 0%",
                        f"Ideally reach {cap}% cap for maximum mitigation",
                        "Check gear, passive tree, and charms for resistance mods"
                    ],
                    priority=95 + int(deficit / 10)  # More negative = higher priority
                ))

            # Below cap (HIGH/MEDIUM)
            elif res_value < cap:
                deficit = cap - res_value

                # Chaos res is less critical
                if res_name == 'Chaos':
                    severity = WeaknessSeverity.MEDIUM if res_value < cap * 0.5 else WeaknessSeverity.LOW
                    priority = 40 + int(deficit / 5)
                else:
                    severity = WeaknessSeverity.HIGH if deficit > 20 else WeaknessSeverity.MEDIUM
                    priority = 70 + int(deficit / 5)

                weaknesses.append(Weakness(
                    category=WeaknessCategory.RESISTANCE,
                    severity=severity,
                    title=f"Uncapped {res_name} Resistance",
                    description=f"{res_name} resistance is {res_value:.0f}%, {deficit:.0f}% below cap",
                    current_value=res_value,
                    recommended_value=cap,
                    impact=f"Taking extra {res_name.lower()} damage",
                    recommendations=[
                        f"Add +{deficit:.0f}% {res_name} resistance to reach {cap}% cap",
                        "Prioritize this before increasing damage"
                    ],
                    priority=priority
                ))

        return weaknesses

    # ============================================================================
    # LIFE POOL DETECTION
    # ============================================================================

    def _detect_life_pool_issues(self, char_data: CharacterData) -> List[Weakness]:
        """Detect life pool weaknesses."""
        weaknesses = []

        # Expected life: rough benchmark is 100 life per level
        expected_life = char_data.level * 100

        # Very low life (CRITICAL)
        if char_data.life < expected_life * 0.5:
            deficit = expected_life - char_data.life
            weaknesses.append(Weakness(
                category=WeaknessCategory.LIFE_POOL,
                severity=WeaknessSeverity.CRITICAL,
                title="Critically Low Life Pool",
                description=f"Life pool ({char_data.life:.0f}) is dangerously low for level {char_data.level}",
                current_value=char_data.life,
                recommended_value=expected_life,
                impact="Extremely vulnerable to one-shots",
                recommendations=[
                    f"Increase life by {deficit:.0f} (current: {char_data.life:.0f}, recommended: {expected_life:.0f})",
                    "Focus on % increased maximum life from tree",
                    "Look for flat +life on all gear pieces",
                    "Consider using life flasks more actively"
                ],
                priority=90
            ))

        # Low life (HIGH/MEDIUM)
        elif char_data.life < expected_life * 0.75:
            deficit = expected_life - char_data.life
            severity = WeaknessSeverity.HIGH if char_data.life < expected_life * 0.6 else WeaknessSeverity.MEDIUM

            weaknesses.append(Weakness(
                category=WeaknessCategory.LIFE_POOL,
                severity=severity,
                title="Low Life Pool",
                description=f"Life pool ({char_data.life:.0f}) is below recommended for level {char_data.level}",
                current_value=char_data.life,
                recommended_value=expected_life,
                impact="Vulnerable to burst damage",
                recommendations=[
                    f"Increase life by {deficit:.0f}",
                    "Allocate life nodes on passive tree",
                    "Upgrade gear with higher life rolls"
                ],
                priority=65
            ))

        return weaknesses

    # ============================================================================
    # ENERGY SHIELD DETECTION
    # ============================================================================

    def _detect_es_issues(self, char_data: CharacterData) -> List[Weakness]:
        """Detect energy shield weaknesses."""
        weaknesses = []

        # Check if ES-focused build (ES > Life)
        if char_data.energy_shield > char_data.life:
            # ES build with low ES
            expected_es = char_data.level * 150  # ES builds need more

            if char_data.energy_shield < expected_es * 0.6:
                weaknesses.append(Weakness(
                    category=WeaknessCategory.ENERGY_SHIELD,
                    severity=WeaknessSeverity.HIGH,
                    title="Low Energy Shield for ES Build",
                    description=f"ES ({char_data.energy_shield:.0f}) is low for an ES-focused build at level {char_data.level}",
                    current_value=char_data.energy_shield,
                    recommended_value=expected_es,
                    impact="Insufficient effective HP pool",
                    recommendations=[
                        f"Increase ES by {expected_es - char_data.energy_shield:.0f}",
                        "Focus on % increased ES and flat +ES on gear",
                        "Consider ES recharge rate improvements"
                    ],
                    priority=70
                ))

        return weaknesses

    # ============================================================================
    # SPIRIT DETECTION
    # ============================================================================

    def _detect_spirit_issues(self, char_data: CharacterData) -> List[Weakness]:
        """Detect Spirit system weaknesses."""
        weaknesses = []

        # Only check if character uses Spirit
        if char_data.spirit_max == 0:
            return weaknesses

        # Spirit overflow (CRITICAL)
        if char_data.spirit_reserved > char_data.spirit_max:
            overflow = char_data.spirit_reserved - char_data.spirit_max
            weaknesses.append(Weakness(
                category=WeaknessCategory.SPIRIT,
                severity=WeaknessSeverity.CRITICAL,
                title="Spirit Overflow",
                description=f"Spirit reserved ({char_data.spirit_reserved}) exceeds maximum ({char_data.spirit_max})",
                current_value=char_data.spirit_reserved,
                recommended_value=char_data.spirit_max,
                impact="Cannot activate all Spirit gems",
                recommendations=[
                    f"Reduce Spirit reservation by {overflow}",
                    "Disable lowest priority Spirit gems",
                    "Remove support gems with high multipliers",
                    "Get more maximum Spirit from gear or passives"
                ],
                priority=95
            ))

        # Very high Spirit usage (MEDIUM)
        elif char_data.spirit_reserved > char_data.spirit_max * 0.95:
            available = char_data.spirit_max - char_data.spirit_reserved
            weaknesses.append(Weakness(
                category=WeaknessCategory.SPIRIT,
                severity=WeaknessSeverity.MEDIUM,
                title="Near Spirit Cap",
                description=f"Using {char_data.spirit_reserved}/{char_data.spirit_max} Spirit ({available} available)",
                current_value=char_data.spirit_reserved,
                recommended_value=char_data.spirit_max * 0.85,
                impact="No room for additional Spirit gems",
                recommendations=[
                    "Consider getting more maximum Spirit",
                    "Optimize support gems to reduce costs",
                    "Leave some Spirit headroom for flexibility"
                ],
                priority=45
            ))

        return weaknesses

    # ============================================================================
    # OVERCAPPED STATS DETECTION
    # ============================================================================

    def _detect_overcapped_stats(self, char_data: CharacterData) -> List[Weakness]:
        """Detect overcapped stats (wasted investment)."""
        weaknesses = []

        # Block overcap (PoE2: 50% max)
        if char_data.block_chance > DefenseConstants.BLOCK_MAX_CHANCE:
            waste = char_data.block_chance - DefenseConstants.BLOCK_MAX_CHANCE
            weaknesses.append(Weakness(
                category=WeaknessCategory.OVERCAPPED_STAT,
                severity=WeaknessSeverity.MEDIUM if waste > 10 else WeaknessSeverity.LOW,
                title="Overcapped Block Chance",
                description=f"Block chance ({char_data.block_chance:.0f}%) exceeds cap ({DefenseConstants.BLOCK_MAX_CHANCE}%)",
                current_value=char_data.block_chance,
                recommended_value=DefenseConstants.BLOCK_MAX_CHANCE,
                impact=f"Wasting {waste:.0f}% block chance investment",
                recommendations=[
                    f"Remove {waste:.0f}% block chance from tree/gear",
                    "Reallocate to other defenses (armor, evasion, ES)",
                    "Block cap in PoE2 is 50%, not 75% like PoE1"
                ],
                priority=50 if waste > 10 else 35
            ))

        # Resistance overcap (90% hard cap in PoE2)
        for res_name in ['Fire', 'Cold', 'Lightning', 'Chaos']:
            res_value = getattr(char_data, f"{res_name.lower()}_res")

            if res_value > DefenseConstants.RESISTANCE_HARD_CAP:
                waste = res_value - DefenseConstants.RESISTANCE_HARD_CAP
                weaknesses.append(Weakness(
                    category=WeaknessCategory.OVERCAPPED_STAT,
                    severity=WeaknessSeverity.LOW,
                    title=f"Overcapped {res_name} Resistance",
                    description=f"{res_name} resistance ({res_value:.0f}%) exceeds hard cap ({DefenseConstants.RESISTANCE_HARD_CAP}%)",
                    current_value=res_value,
                    recommended_value=DefenseConstants.RESISTANCE_HARD_CAP,
                    impact=f"Wasting {waste:.0f}% resistance",
                    recommendations=[
                        f"Remove {waste:.0f}% {res_name} resistance",
                        "Reallocate to other uncapped resistances or stats",
                        "Note: PoE2 has 90% hard cap, cannot be exceeded"
                    ],
                    priority=30
                ))

        return weaknesses

    # ============================================================================
    # DEFENSE LAYERS DETECTION
    # ============================================================================

    def _detect_defense_layer_issues(
        self,
        char_data: CharacterData,
        threat_profile: ThreatProfile
    ) -> List[Weakness]:
        """Detect defense layer weaknesses using EHP calculator."""
        weaknesses = []

        # Build DefensiveStats from CharacterData
        defensive_stats = DefensiveStats(
            life=char_data.life,
            energy_shield=char_data.energy_shield,
            armor=char_data.armor,
            evasion=char_data.evasion,
            block_chance=char_data.block_chance,
            fire_res=char_data.fire_res,
            cold_res=char_data.cold_res,
            lightning_res=char_data.lightning_res,
            chaos_res=char_data.chaos_res
        )

        # Use EHP calculator's built-in gap detection
        ehp_gaps = self.ehp_calc.identify_defense_gaps(defensive_stats, threat_profile)

        # Convert EHP gaps to our Weakness format
        for gap in ehp_gaps:
            # Map EHP severity (0-10) to our severity enum
            if gap.severity >= 8:
                severity = WeaknessSeverity.CRITICAL
            elif gap.severity >= 6:
                severity = WeaknessSeverity.HIGH
            elif gap.severity >= 4:
                severity = WeaknessSeverity.MEDIUM
            else:
                severity = WeaknessSeverity.LOW

            weaknesses.append(Weakness(
                category=WeaknessCategory.DEFENSE_LAYERS,
                severity=severity,
                title=gap.gap_type.replace('_', ' ').title(),
                description=gap.description,
                current_value=gap.current_value,
                recommended_value=gap.recommended_value,
                impact="Reduced survivability",
                recommendations=[gap.recommendation],
                priority=int(gap.severity * 10)
            ))

        return weaknesses

    # ============================================================================
    # STUN VULNERABILITY DETECTION
    # ============================================================================

    def _detect_stun_vulnerability(self, char_data: CharacterData) -> List[Weakness]:
        """Detect stun vulnerability issues."""
        weaknesses = []

        # Low life makes you more vulnerable to stuns
        # In PoE2, stun chance = (damage / max_life) × 100
        # If life is very low, even small hits can stun

        if char_data.life < 2000:
            weaknesses.append(Weakness(
                category=WeaknessCategory.STUN_VULNERABILITY,
                severity=WeaknessSeverity.HIGH,
                title="High Stun Vulnerability",
                description=f"Very low life ({char_data.life:.0f}) makes you vulnerable to stuns",
                current_value=char_data.life,
                recommended_value=3000,
                impact="Frequently interrupted by Light Stuns, rapid Heavy Stun buildup",
                recommendations=[
                    "Increase life pool to reduce stun chance",
                    "Consider stun avoidance/threshold modifiers",
                    "Look for 'reduced stun threshold' on gear"
                ],
                priority=60
            ))

        return weaknesses

    # ============================================================================
    # RESOURCE MANAGEMENT DETECTION
    # ============================================================================

    def _detect_resource_issues(self, char_data: CharacterData) -> List[Weakness]:
        """Detect resource management weaknesses."""
        weaknesses = []

        # Low mana pool for mana-based build
        if char_data.mana > 0:
            expected_mana = char_data.level * 50

            if char_data.mana < expected_mana * 0.5:
                weaknesses.append(Weakness(
                    category=WeaknessCategory.RESOURCE_MANAGEMENT,
                    severity=WeaknessSeverity.MEDIUM,
                    title="Low Mana Pool",
                    description=f"Mana pool ({char_data.mana:.0f}) is low for level {char_data.level}",
                    current_value=char_data.mana,
                    recommended_value=expected_mana,
                    impact="May run out of mana during combat",
                    recommendations=[
                        f"Increase mana by {expected_mana - char_data.mana:.0f}",
                        "Add mana nodes from passive tree",
                        "Consider mana regeneration improvements"
                    ],
                    priority=45
                ))

        return weaknesses

    # ============================================================================
    # FORMATTING AND DISPLAY
    # ============================================================================

    def format_weakness_report(
        self,
        weaknesses: List[Weakness],
        include_low_severity: bool = True
    ) -> str:
        """
        Format weaknesses into a human-readable report.

        Args:
            weaknesses: List of weaknesses to format
            include_low_severity: Include LOW and INFO severity issues

        Returns:
            Formatted string report
        """
        if not weaknesses:
            return "✓ No significant weaknesses detected! Build looks solid."

        # Filter by severity if requested
        if not include_low_severity:
            weaknesses = [
                w for w in weaknesses
                if w.severity not in [WeaknessSeverity.LOW, WeaknessSeverity.INFO]
            ]

        # Group by severity
        by_severity = {}
        for weakness in weaknesses:
            if weakness.severity not in by_severity:
                by_severity[weakness.severity] = []
            by_severity[weakness.severity].append(weakness)

        # Build report
        lines = []
        lines.append("=" * 80)
        lines.append("CHARACTER WEAKNESS REPORT")
        lines.append("=" * 80)
        lines.append("")

        severity_order = [
            WeaknessSeverity.CRITICAL,
            WeaknessSeverity.HIGH,
            WeaknessSeverity.MEDIUM,
            WeaknessSeverity.LOW,
            WeaknessSeverity.INFO
        ]

        for severity in severity_order:
            if severity not in by_severity:
                continue

            severity_weaknesses = by_severity[severity]

            # Severity header
            severity_emoji = {
                WeaknessSeverity.CRITICAL: "🚨",
                WeaknessSeverity.HIGH: "⚠️",
                WeaknessSeverity.MEDIUM: "⚡",
                WeaknessSeverity.LOW: "ℹ️",
                WeaknessSeverity.INFO: "💡"
            }

            lines.append(f"{severity_emoji[severity]} {severity.value.upper()} PRIORITY ({len(severity_weaknesses)})")
            lines.append("-" * 80)
            lines.append("")

            for weakness in severity_weaknesses:
                lines.append(f"[{weakness.category.value.upper()}] {weakness.title}")
                lines.append(f"  {weakness.description}")
                lines.append(f"  Impact: {weakness.impact}")
                lines.append(f"  Current: {weakness.current_value} → Recommended: {weakness.recommended_value}")

                if weakness.recommendations:
                    lines.append("  Recommendations:")
                    for rec in weakness.recommendations:
                        lines.append(f"    • {rec}")

                lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def quick_weakness_check(char_data: CharacterData) -> List[str]:
    """
    Quick weakness check returning just the titles.

    Args:
        char_data: Character data to analyze

    Returns:
        List of weakness titles
    """
    detector = WeaknessDetector()
    weaknesses = detector.detect_all_weaknesses(char_data)
    return [f"[{w.severity.value.upper()}] {w.title}" for w in weaknesses]


def get_critical_issues(char_data: CharacterData) -> List[str]:
    """
    Get critical issues only.

    Args:
        char_data: Character data to analyze

    Returns:
        List of critical issue descriptions
    """
    detector = WeaknessDetector()
    critical = detector.get_critical_weaknesses(char_data)
    return [w.description for w in critical]


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 80)
    print("Path of Exile 2 Weakness Detector - Test")
    print("=" * 80)
    print()

    # Example: Character with several issues
    char = CharacterData(
        level=91,
        character_class="Stormweaver",
        life=1413,  # Very low
        energy_shield=4847,
        mana=850,
        spirit_max=100,
        spirit_reserved=95,
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

    # Run detection
    detector = WeaknessDetector()
    weaknesses = detector.detect_all_weaknesses(char)

    # Print report
    report = detector.format_weakness_report(weaknesses)
    print(report)

    # Print summary
    print()
    summary = detector.get_weakness_summary(char)
    print("SUMMARY:")
    print(f"  Total Weaknesses: {summary['total_weaknesses']}")
    print(f"  Critical: {summary['by_severity']['critical']}")
    print(f"  High: {summary['by_severity']['high']}")
    print(f"  Medium: {summary['by_severity']['medium']}")
    print(f"  Needs Immediate Attention: {summary['needs_immediate_attention']}")
    print()

    print("=" * 80)
    print("Test Complete!")
    print("=" * 80)
