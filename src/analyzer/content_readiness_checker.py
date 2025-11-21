"""
Content Readiness Checker

Determines if a character has sufficient defenses for specific endgame content.
Answers "Can I do this boss/map tier safely?"

Author: Claude
Date: 2025-10-24
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ContentDifficulty(Enum):
    """Difficulty tiers for content"""
    CAMPAIGN = "campaign"
    EARLY_MAPS = "early_maps"  # T1-T5
    MID_MAPS = "mid_maps"  # T6-T10
    HIGH_MAPS = "high_maps"  # T11-T15
    PINNACLE_MAPS = "pinnacle_maps"  # T16
    BOSS_NORMAL = "boss_normal"
    BOSS_PINNACLE = "boss_pinnacle"


class ReadinessLevel(Enum):
    """Readiness assessment"""
    READY = "ready"
    MOSTLY_READY = "mostly_ready"
    RISKY = "risky"
    NOT_READY = "not_ready"


@dataclass
class DefenseRequirement:
    """Defense requirements for specific content"""
    content_name: str
    difficulty: ContentDifficulty

    # Minimum requirements
    min_life: int
    min_ehp: int
    min_fire_res: int
    min_cold_res: int
    min_lightning_res: int
    min_chaos_res: int

    # Recommended
    rec_life: int
    rec_ehp: int
    rec_fire_res: int
    rec_cold_res: int
    rec_lightning_res: int
    rec_chaos_res: int

    # Additional requirements
    requires_stun_immunity: bool = False
    requires_freeze_immunity: bool = False
    requires_curse_immunity: bool = False
    min_phys_mitigation: float = 0.0
    min_ele_mitigation: float = 0.0

    # Damage requirements
    rec_dps: int = 0
    min_dps: int = 0

    # Notes
    dangerous_mechanics: List[str] = field(default_factory=list)
    tips: List[str] = field(default_factory=list)


@dataclass
class ReadinessReport:
    """Report on whether character is ready for content"""
    content_name: str
    readiness: ReadinessLevel
    confidence: float  # 0-100

    # Assessment breakdown
    life_check: str  # "pass", "warning", "fail"
    ehp_check: str
    resistance_check: str
    damage_check: str
    immunity_check: str

    # Detailed gaps
    gaps: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    passes: List[str] = field(default_factory=list)

    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    priority_upgrades: List[str] = field(default_factory=list)


class ContentReadinessChecker:
    """
    Check if character is ready for specific content

    Usage:
        >>> checker = ContentReadinessChecker()
        >>> report = checker.check_readiness(
        ...     character_data={"life": 3000, "fire_res": 75, ...},
        ...     content="Tier 15 Maps"
        ... )
        >>> print(f"Ready: {report.readiness.value}")
        >>> for gap in report.gaps:
        ...     print(f"Gap: {gap}")
    """

    def __init__(self):
        self.content_requirements = self._initialize_requirements()

    def _initialize_requirements(self) -> Dict[str, DefenseRequirement]:
        """Initialize defense requirements for various content"""
        reqs = {}

        # Campaign
        reqs['campaign'] = DefenseRequirement(
            content_name="Campaign",
            difficulty=ContentDifficulty.CAMPAIGN,
            min_life=800,
            min_ehp=800,
            min_fire_res=0,
            min_cold_res=0,
            min_lightning_res=0,
            min_chaos_res=-60,
            rec_life=1500,
            rec_ehp=1500,
            rec_fire_res=50,
            rec_cold_res=50,
            rec_lightning_res=50,
            rec_chaos_res=-30,
            rec_dps=5000,
            min_dps=2000,
            tips=[
                "Focus on life and resistances",
                "Damage isn't critical yet",
                "Learn boss mechanics"
            ]
        )

        # Early Maps (T1-T5)
        reqs['early_maps'] = DefenseRequirement(
            content_name="Early Maps (T1-T5)",
            difficulty=ContentDifficulty.EARLY_MAPS,
            min_life=2000,
            min_ehp=3000,
            min_fire_res=60,
            min_cold_res=60,
            min_lightning_res=60,
            min_chaos_res=-50,
            rec_life=3000,
            rec_ehp=5000,
            rec_fire_res=75,
            rec_cold_res=75,
            rec_lightning_res=75,
            rec_chaos_res=-20,
            rec_dps=20000,
            min_dps=10000,
            dangerous_mechanics=["Rare monster mods", "Maven invitations"],
            tips=[
                "Cap elemental resistances (75%)",
                "3000+ life is comfortable",
                "Focus on clearing speed"
            ]
        )

        # Mid Maps (T6-T10)
        reqs['mid_maps'] = DefenseRequirement(
            content_name="Mid Maps (T6-T10)",
            difficulty=ContentDifficulty.MID_MAPS,
            min_life=3000,
            min_ehp=5000,
            min_fire_res=75,
            min_cold_res=75,
            min_lightning_res=75,
            min_chaos_res=-30,
            rec_life=4000,
            rec_ehp=7000,
            rec_fire_res=75,
            rec_cold_res=75,
            rec_lightning_res=75,
            rec_chaos_res=0,
            rec_dps=50000,
            min_dps=25000,
            min_phys_mitigation=20.0,
            dangerous_mechanics=["Essence mobs", "Expedition", "Breach"],
            tips=[
                "Elemental resistances MUST be capped",
                "Start investing in chaos res",
                "Add defensive layers (armor, evasion, block)"
            ]
        )

        # High Maps (T11-T15)
        reqs['high_maps'] = DefenseRequirement(
            content_name="High Maps (T11-T15)",
            difficulty=ContentDifficulty.HIGH_MAPS,
            min_life=4000,
            min_ehp=8000,
            min_fire_res=75,
            min_cold_res=75,
            min_lightning_res=75,
            min_chaos_res=-10,
            rec_life=5000,
            rec_ehp=12000,
            rec_fire_res=85,  # Overcap recommended
            rec_cold_res=85,
            rec_lightning_res=85,
            rec_chaos_res=20,
            rec_dps=100000,
            min_dps=50000,
            min_phys_mitigation=30.0,
            min_ele_mitigation=10.0,
            dangerous_mechanics=["Delirium", "Simulacrum", "Uber Expedition"],
            tips=[
                "5000+ life strongly recommended",
                "Overcap resistances for map mods",
                "Multiple defense layers required",
                "DPS becomes important for safety"
            ]
        )

        # Pinnacle Maps (T16)
        reqs['pinnacle_maps'] = DefenseRequirement(
            content_name="Pinnacle Maps (T16+)",
            difficulty=ContentDifficulty.PINNACLE_MAPS,
            min_life=5000,
            min_ehp=12000,
            min_fire_res=75,
            min_cold_res=75,
            min_lightning_res=75,
            min_chaos_res=0,
            rec_life=6500,
            rec_ehp=15000,
            rec_fire_res=90,
            rec_cold_res=90,
            rec_lightning_res=90,
            rec_chaos_res=40,
            rec_dps=200000,
            min_dps=100000,
            min_phys_mitigation=40.0,
            min_ele_mitigation=20.0,
            requires_stun_immunity=False,
            dangerous_mechanics=["All map mods", "Multiple damage types", "High DPS checks"],
            tips=[
                "6000+ life is baseline",
                "Heavily overcap resistances",
                "Need 3+ defensive layers",
                "High DPS = better defense (kill before they kill you)",
                "Consider corrupted blood immunity"
            ]
        )

        # Normal Bosses
        reqs['boss_normal'] = DefenseRequirement(
            content_name="Normal Endgame Bosses",
            difficulty=ContentDifficulty.BOSS_NORMAL,
            min_life=4000,
            min_ehp=8000,
            min_fire_res=75,
            min_cold_res=75,
            min_lightning_res=75,
            min_chaos_res=-10,
            rec_life=5500,
            rec_ehp=10000,
            rec_fire_res=75,
            rec_cold_res=75,
            rec_lightning_res=75,
            rec_chaos_res=20,
            rec_dps=75000,
            min_dps=40000,
            dangerous_mechanics=["Boss-specific attacks", "Telegraphed abilities"],
            tips=[
                "Learn mechanics > raw tankiness",
                "5000+ life recommended",
                "Capped resistances mandatory",
                "Practice dodge timing"
            ]
        )

        # Pinnacle Bosses
        reqs['boss_pinnacle'] = DefenseRequirement(
            content_name="Pinnacle Bosses",
            difficulty=ContentDifficulty.BOSS_PINNACLE,
            min_life=5500,
            min_ehp=12000,
            min_fire_res=75,
            min_cold_res=75,
            min_lightning_res=75,
            min_chaos_res=20,
            rec_life=7000,
            rec_ehp=18000,
            rec_fire_res=75,
            rec_cold_res=75,
            rec_lightning_res=75,
            rec_chaos_res=50,
            rec_dps=300000,
            min_dps=150000,
            min_phys_mitigation=50.0,
            requires_stun_immunity=True,
            dangerous_mechanics=["One-shot mechanics", "Phase transitions", "Multiple damage types"],
            tips=[
                "7000+ life for safety",
                "Know mechanics perfectly",
                "High DPS shortens dangerous phases",
                "Stun immunity highly recommended",
                "Practice is essential"
            ]
        )

        return reqs

    def check_readiness(
        self,
        character_data: Dict[str, Any],
        content: str
    ) -> ReadinessReport:
        """
        Check if character is ready for specific content

        Args:
            character_data: Character stats
            content: Content name (e.g., "high_maps", "boss_pinnacle")

        Returns:
            Detailed readiness report
        """
        logger.info(f"Checking readiness for: {content}")

        # Normalize content name
        content_key = content.lower().replace(" ", "_").replace("-", "_")

        # Get requirements
        if content_key not in self.content_requirements:
            # Try to fuzzy match
            for key in self.content_requirements.keys():
                if key in content_key or content_key in key:
                    content_key = key
                    break
            else:
                logger.error(f"Unknown content: {content}")
                return self._create_unknown_content_report(content)

        requirements = self.content_requirements[content_key]

        # Extract character stats
        stats = self._extract_character_stats(character_data)

        # Initialize report
        report = ReadinessReport(
            content_name=requirements.content_name,
            readiness=ReadinessLevel.READY,
            confidence=100.0,
            life_check="pass",
            ehp_check="pass",
            resistance_check="pass",
            damage_check="pass",
            immunity_check="pass"
        )

        # Check each requirement
        report = self._check_life(stats, requirements, report)
        report = self._check_ehp(stats, requirements, report)
        report = self._check_resistances(stats, requirements, report)
        report = self._check_damage(stats, requirements, report)
        report = self._check_immunities(stats, requirements, report)

        # Determine overall readiness
        report = self._determine_readiness(report, requirements)

        # Generate recommendations
        report = self._generate_recommendations(report, requirements, stats)

        return report

    def _extract_character_stats(self, character_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract relevant stats"""
        stats_nested = character_data.get('stats', {})

        return {
            'life': stats_nested.get('life', character_data.get('life', 0)),
            'ehp': stats_nested.get('effective_health_pool', character_data.get('effective_health_pool', stats_nested.get('life', character_data.get('life', 0)))),
            'fire_res': stats_nested.get('fire_res', character_data.get('fire_res', 0)),
            'cold_res': stats_nested.get('cold_res', character_data.get('cold_res', 0)),
            'lightning_res': stats_nested.get('lightning_res', character_data.get('lightning_res', 0)),
            'chaos_res': stats_nested.get('chaos_res', character_data.get('chaos_res', 0)),
            'armor': stats_nested.get('armor', character_data.get('armor', 0)),
            'evasion': stats_nested.get('evasion', character_data.get('evasion', 0)),
            'block': stats_nested.get('block_chance', character_data.get('block_chance', 0)),
            'dps': character_data.get('total_dps', 0),
        }

    def _check_life(
        self,
        stats: Dict[str, float],
        reqs: DefenseRequirement,
        report: ReadinessReport
    ) -> ReadinessReport:
        """Check life pool"""
        life = stats['life']

        if life < reqs.min_life:
            report.life_check = "fail"
            report.gaps.append(f"Life too low: {life:.0f} (need {reqs.min_life})")
            report.priority_upgrades.append(f"Increase life to at least {reqs.min_life}")
        elif life < reqs.rec_life:
            report.life_check = "warning"
            report.warnings.append(f"Life below recommended: {life:.0f} (recommended {reqs.rec_life})")
            report.recommendations.append(f"Consider increasing life to {reqs.rec_life}+ for safety")
        else:
            report.passes.append(f"Life: {life:.0f} ✅")

        return report

    def _check_ehp(
        self,
        stats: Dict[str, float],
        reqs: DefenseRequirement,
        report: ReadinessReport
    ) -> ReadinessReport:
        """Check effective HP"""
        ehp = stats['ehp']

        if ehp < reqs.min_ehp:
            report.ehp_check = "fail"
            report.gaps.append(f"EHP too low: {ehp:.0f} (need {reqs.min_ehp})")
            report.priority_upgrades.append(f"Increase EHP to at least {reqs.min_ehp}")
        elif ehp < reqs.rec_ehp:
            report.ehp_check = "warning"
            report.warnings.append(f"EHP below recommended: {ehp:.0f} (recommended {reqs.rec_ehp})")
            report.recommendations.append(f"Add defensive layers to reach {reqs.rec_ehp}+ EHP")
        else:
            report.passes.append(f"EHP: {ehp:.0f} ✅")

        return report

    def _check_resistances(
        self,
        stats: Dict[str, float],
        reqs: DefenseRequirement,
        report: ReadinessReport
    ) -> ReadinessReport:
        """Check resistances"""
        resistances = {
            'Fire': (stats['fire_res'], reqs.min_fire_res, reqs.rec_fire_res),
            'Cold': (stats['cold_res'], reqs.min_cold_res, reqs.rec_cold_res),
            'Lightning': (stats['lightning_res'], reqs.min_lightning_res, reqs.rec_lightning_res),
            'Chaos': (stats['chaos_res'], reqs.min_chaos_res, reqs.rec_chaos_res),
        }

        res_fail = False
        res_warning = False

        for res_name, (current, min_val, rec_val) in resistances.items():
            if current < min_val:
                res_fail = True
                report.gaps.append(f"{res_name} res too low: {current:.0f}% (need {min_val}%)")
                report.priority_upgrades.append(f"Increase {res_name} resistance to {min_val}%")
            elif current < rec_val:
                res_warning = True
                report.warnings.append(f"{res_name} res below recommended: {current:.0f}% (recommended {rec_val}%)")
            else:
                report.passes.append(f"{res_name} Resistance: {current:.0f}% ✅")

        if res_fail:
            report.resistance_check = "fail"
        elif res_warning:
            report.resistance_check = "warning"
        else:
            report.resistance_check = "pass"

        return report

    def _check_damage(
        self,
        stats: Dict[str, float],
        reqs: DefenseRequirement,
        report: ReadinessReport
    ) -> ReadinessReport:
        """Check DPS"""
        dps = stats['dps']

        if dps == 0:
            report.damage_check = "unknown"
            report.warnings.append("DPS unknown - cannot assess")
            return report

        if dps < reqs.min_dps:
            report.damage_check = "fail"
            report.gaps.append(f"DPS too low: {dps:.0f} (need {reqs.min_dps})")
            report.recommendations.append(f"Increase DPS to at least {reqs.min_dps}")
        elif dps < reqs.rec_dps:
            report.damage_check = "warning"
            report.warnings.append(f"DPS below recommended: {dps:.0f} (recommended {reqs.rec_dps})")
        else:
            report.passes.append(f"DPS: {dps:.0f} ✅")

        return report

    def _check_immunities(
        self,
        stats: Dict[str, float],
        reqs: DefenseRequirement,
        report: ReadinessReport
    ) -> ReadinessReport:
        """Check for required immunities"""
        # This would need actual immunity data from character
        # For now, just note if immunities are required

        if reqs.requires_stun_immunity:
            report.recommendations.append("Stun immunity recommended for this content")

        if reqs.requires_freeze_immunity:
            report.recommendations.append("Freeze immunity recommended for this content")

        if reqs.requires_curse_immunity:
            report.recommendations.append("Curse immunity recommended for this content")

        report.immunity_check = "pass"  # Default to pass for now

        return report

    def _determine_readiness(
        self,
        report: ReadinessReport,
        reqs: DefenseRequirement
    ) -> ReadinessReport:
        """Determine overall readiness level"""
        checks = [
            report.life_check,
            report.ehp_check,
            report.resistance_check,
            report.damage_check
        ]

        fail_count = checks.count("fail")
        warning_count = checks.count("warning")

        if fail_count > 0:
            report.readiness = ReadinessLevel.NOT_READY
            report.confidence = max(0, 100 - (fail_count * 30) - (warning_count * 10))
        elif warning_count > 2:
            report.readiness = ReadinessLevel.RISKY
            report.confidence = 100 - (warning_count * 15)
        elif warning_count > 0:
            report.readiness = ReadinessLevel.MOSTLY_READY
            report.confidence = 100 - (warning_count * 10)
        else:
            report.readiness = ReadinessLevel.READY
            report.confidence = 100.0

        return report

    def _generate_recommendations(
        self,
        report: ReadinessReport,
        reqs: DefenseRequirement,
        stats: Dict[str, float]
    ) -> ReadinessReport:
        """Generate final recommendations"""
        # Add dangerous mechanics warning
        if reqs.dangerous_mechanics:
            report.recommendations.append("\nDangerous Mechanics:")
            for mechanic in reqs.dangerous_mechanics:
                report.recommendations.append(f"  • {mechanic}")

        # Add tips
        if reqs.tips:
            report.recommendations.append("\nTips:")
            for tip in reqs.tips:
                report.recommendations.append(f"  • {tip}")

        return report

    def _create_unknown_content_report(self, content: str) -> ReadinessReport:
        """Create report for unknown content"""
        return ReadinessReport(
            content_name=content,
            readiness=ReadinessLevel.NOT_READY,
            confidence=0.0,
            life_check="unknown",
            ehp_check="unknown",
            resistance_check="unknown",
            damage_check="unknown",
            immunity_check="unknown",
            gaps=[f"Unknown content: {content}"],
            recommendations=["Please specify valid content (e.g., 'high_maps', 'boss_pinnacle')"]
        )

    def format_report(self, report: ReadinessReport) -> str:
        """Format report as readable text"""
        lines = []
        lines.append("=" * 80)
        lines.append("CONTENT READINESS REPORT")
        lines.append("=" * 80)
        lines.append(f"Content: {report.content_name}")
        lines.append(f"Readiness: {report.readiness.value.upper()}")
        lines.append(f"Confidence: {report.confidence:.0f}%")
        lines.append("")

        # Status checks
        lines.append("Status Checks:")
        lines.append(f"  Life: {report.life_check.upper()}")
        lines.append(f"  EHP: {report.ehp_check.upper()}")
        lines.append(f"  Resistances: {report.resistance_check.upper()}")
        lines.append(f"  Damage: {report.damage_check.upper()}")
        lines.append("")

        # Gaps
        if report.gaps:
            lines.append("❌ CRITICAL GAPS:")
            for gap in report.gaps:
                lines.append(f"  • {gap}")
            lines.append("")

        # Warnings
        if report.warnings:
            lines.append("⚠️ WARNINGS:")
            for warning in report.warnings:
                lines.append(f"  • {warning}")
            lines.append("")

        # Passes
        if report.passes:
            lines.append("✅ PASSED:")
            for pass_item in report.passes:
                lines.append(f"  • {pass_item}")
            lines.append("")

        # Priority upgrades
        if report.priority_upgrades:
            lines.append("🔥 PRIORITY UPGRADES:")
            for upgrade in report.priority_upgrades:
                lines.append(f"  • {upgrade}")
            lines.append("")

        # Recommendations
        if report.recommendations:
            lines.append("📋 RECOMMENDATIONS:")
            for rec in report.recommendations:
                lines.append(f"{rec}")
            lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)


if __name__ == "__main__":
    # Demo
    checker = ContentReadinessChecker()

    # Example character
    character = {
        'stats': {
            'life': 4500,
            'effective_health_pool': 8000,
            'fire_res': 75,
            'cold_res': 75,
            'lightning_res': 68,
            'chaos_res': -20,
            'armor': 5000,
        },
        'total_dps': 60000
    }

    # Check readiness for high maps
    report = checker.check_readiness(character, "high_maps")
    print(checker.format_report(report))
