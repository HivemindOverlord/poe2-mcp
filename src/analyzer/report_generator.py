"""
Report Generator
Creates comprehensive analysis reports for Path of Exile 2 characters
"""

import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate comprehensive character analysis reports"""

    def generate_report(
        self,
        character_data: Dict[str, Any],
        analysis: Dict[str, Any],
        gear_recommendations: list = None
    ) -> str:
        """
        Generate a comprehensive markdown report

        Args:
            character_data: Raw character data
            analysis: Character analysis results
            gear_recommendations: Gear upgrade recommendations

        Returns:
            Markdown-formatted report
        """
        report_lines = []

        # Header
        report_lines.append("# Path of Exile 2 Character Analysis Report")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")

        # Character Overview
        report_lines.append("## Character Overview")
        report_lines.append("")
        report_lines.append(f"**Name:** {character_data.get('name', 'Unknown')}")
        report_lines.append(f"**Account:** {character_data.get('account', 'Unknown')}")
        report_lines.append(f"**League:** {character_data.get('league', 'Unknown')}")
        report_lines.append(f"**Class:** {character_data.get('class', 'Unknown')}")
        report_lines.append("")

        # Defensive Stats
        defense = analysis.get('defensive_analysis', {})
        report_lines.append("## Defensive Stats")
        report_lines.append("")
        report_lines.append(f"**Overall Quality:** {defense.get('quality', 'Unknown')}")
        report_lines.append("")
        report_lines.append(f"- **Life:** {defense.get('life', 0):,}")
        report_lines.append(f"- **Energy Shield:** {defense.get('energy_shield', 0):,}")
        report_lines.append(f"- **Effective HP:** {defense.get('effective_hp', 0):,}")
        report_lines.append("")

        # Resistances
        res = defense.get('resistances', {})
        report_lines.append("### Resistances")
        report_lines.append("")
        report_lines.append(f"- **Fire:** {res.get('fire', 0)}% {self._get_resistance_status(res.get('fire', 0))}")
        report_lines.append(f"- **Cold:** {res.get('cold', 0)}% {self._get_resistance_status(res.get('cold', 0))}")
        report_lines.append(f"- **Lightning:** {res.get('lightning', 0)}% {self._get_resistance_status(res.get('lightning', 0))}")
        report_lines.append(f"- **Chaos:** {res.get('chaos', 0)}%")
        report_lines.append("")

        # Issues
        if defense.get('issues'):
            report_lines.append("### Defense Issues")
            report_lines.append("")
            for issue in defense['issues']:
                report_lines.append(f"- [!] {issue}")
            report_lines.append("")

        # Skills
        skill_analysis = analysis.get('skill_analysis', {})
        report_lines.append("## Skills")
        report_lines.append("")
        report_lines.append(f"**Total Skill Groups:** {skill_analysis.get('total_skills', 0)}")
        report_lines.append("")

        # Display skills if available
        skills = character_data.get('skills', [])
        if skills:
            for i, skill_group in enumerate(skills[:5], 1):  # Limit to first 5
                gems = skill_group.get('allGems', skill_group.get('gems', []))
                if gems:
                    main_gem = gems[0]
                    gem_name = main_gem.get('name', main_gem.get('itemData', {}).get('typeLine', 'Unknown'))
                    report_lines.append(f"{i}. **{gem_name}**")
                    if len(gems) > 1:
                        supports = [g.get('name', 'Unknown') for g in gems[1:]]
                        report_lines.append(f"   - Supports: {', '.join(supports[:3])}")
            report_lines.append("")

        # Recommendations
        recommendations = analysis.get('recommendations', [])
        if recommendations:
            report_lines.append("## Recommendations")
            report_lines.append("")

            # Group by priority
            high_priority = [r for r in recommendations if r.get('priority') == 'HIGH']
            medium_priority = [r for r in recommendations if r.get('priority') == 'MEDIUM']

            if high_priority:
                report_lines.append("### High Priority")
                report_lines.append("")
                for rec in high_priority:
                    report_lines.append(f"#### {rec.get('title', 'Recommendation')}")
                    report_lines.append(f"{rec.get('description', '')}")
                    report_lines.append("")

            if medium_priority:
                report_lines.append("### Medium Priority")
                report_lines.append("")
                for rec in medium_priority:
                    report_lines.append(f"#### {rec.get('title', 'Recommendation')}")
                    report_lines.append(f"{rec.get('description', '')}")
                    report_lines.append("")

        # Gear Recommendations
        if gear_recommendations:
            report_lines.append("## Gear Upgrade Suggestions")
            report_lines.append("")
            for gear_rec in gear_recommendations:
                report_lines.append(f"### {gear_rec.get('stat', 'Unknown Stat')}")
                report_lines.append(f"**Priority:** {gear_rec.get('priority', 'MEDIUM')}")
                report_lines.append(f"**Reason:** {gear_rec.get('reason', '')}")
                report_lines.append(f"**Suggested Slots:** {', '.join(gear_rec.get('suggested_slots', []))}")
                report_lines.append("")

        # Summary
        report_lines.append("---")
        report_lines.append("")
        report_lines.append("## Summary")
        report_lines.append("")

        overall_status = self._get_overall_status(defense, recommendations)
        report_lines.append(f"**Overall Build Status:** {overall_status}")
        report_lines.append("")

        if defense.get('quality') in ['Critical', 'Weak']:
            report_lines.append("[!] **Action Required:** Your character has critical defensive weaknesses that should be addressed immediately.")
        elif recommendations:
            report_lines.append("[OK] **Moderate Issues:** Your character is functional but has room for improvement.")
        else:
            report_lines.append("[OK] **Build Looks Good:** No critical issues detected!")

        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")
        report_lines.append("*Report generated by Path of Exile 2 Enhancement Service*")

        return '\n'.join(report_lines)

    def _get_resistance_status(self, value: int) -> str:
        """Get resistance status indicator"""
        if value >= 75:
            return "(Capped [OK])"
        elif value >= 60:
            return "(OK)"
        elif value >= 40:
            return "(Low [WARNING])"
        else:
            return "(CRITICAL [!])"

    def _get_overall_status(
        self,
        defense: Dict[str, Any],
        recommendations: list
    ) -> str:
        """Determine overall build status"""
        if defense.get('quality') == 'Critical':
            return "[!] Critical - Immediate Action Required"
        elif defense.get('quality') == 'Weak':
            return "[!] Weak - Needs Improvement"
        elif len(recommendations) > 3:
            return "[!] Moderate - Multiple Issues"
        elif len(recommendations) > 0:
            return "[OK] Good - Minor Issues"
        else:
            return "[OK] Excellent - Well Optimized"
