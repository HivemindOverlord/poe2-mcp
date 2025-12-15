"""
Character Analyzer
Analyzes character stats, skills, and gear to provide recommendations
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class CharacterAnalyzer:
    """Analyze character builds and provide recommendations"""

    def analyze_character(self, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive character analysis

        Args:
            character_data: Character data from poe.ninja or other source

        Returns:
            Analysis results with recommendations
        """
        try:
            analysis = {
                'character_name': character_data.get('name', 'Unknown'),
                'league': character_data.get('league', 'Unknown'),
                'defensive_analysis': self._analyze_defenses(character_data),
                'skill_analysis': self._analyze_skills(character_data),
                'gear_analysis': self._analyze_gear(character_data),
                'recommendations': []
            }

            # Generate recommendations based on analysis
            analysis['recommendations'] = self._generate_recommendations(analysis, character_data)

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing character: {e}", exc_info=True)
            return {'error': str(e)}

    def _analyze_defenses(self, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze defensive stats - handles both normalized and poe.ninja raw formats"""
        # Try multiple stat sources for compatibility
        stats = character_data.get('stats', {})
        raw_data = character_data.get('raw_data', {})
        char_model = raw_data.get('charModel', {}) if raw_data else {}
        defense_stats = char_model.get('defensiveStats', stats)

        # Extract values with fallbacks for different field names
        life = (
            defense_stats.get('life') or
            stats.get('life') or
            0
        )
        es = (
            defense_stats.get('energyShield') or
            stats.get('energyShield') or
            stats.get('energy_shield') or
            0
        )

        # Raw HP pool (life + ES)
        raw_hp = life + es

        # Effective HP considers resistances - use poe.ninja's calculation if available
        # This represents worst-case damage survivability
        ehp = (
            defense_stats.get('effectiveHealthPool') or
            stats.get('effectiveHealthPool') or
            raw_hp  # Fallback to raw HP if not calculated
        )

        # Resistances - handle multiple possible field names
        fire_res = (
            defense_stats.get('fireRes') or
            defense_stats.get('fireResistance') or
            stats.get('fireResistance') or
            0
        )
        cold_res = (
            defense_stats.get('coldRes') or
            defense_stats.get('coldResistance') or
            stats.get('coldResistance') or
            0
        )
        lightning_res = (
            defense_stats.get('lightningRes') or
            defense_stats.get('lightningResistance') or
            stats.get('lightningResistance') or
            0
        )
        chaos_res = (
            defense_stats.get('chaosRes') or
            defense_stats.get('chaosResistance') or
            stats.get('chaosResistance') or
            0
        )

        # Evaluate defense quality based on level-appropriate thresholds
        level = character_data.get('level', 1)
        if raw_data:
            level = char_model.get('level', level)

        defense_quality = 'Good'
        issues = []

        # Scale EHP expectations by level
        min_ehp = max(500, level * 50)  # ~50 EHP per level minimum
        target_ehp = level * 100  # ~100 EHP per level target

        if ehp < min_ehp:
            defense_quality = 'Critical'
            issues.append(f'EHP critically low ({ehp} < {min_ehp} for level {level})')
        elif ehp < target_ehp:
            defense_quality = 'Weak'
            issues.append(f'EHP below target ({ehp} < {target_ehp} for level {level})')

        # Check resistances (75% is cap for elemental in PoE2)
        res_target = min(75, level)  # Scale target by level
        if fire_res < res_target:
            issues.append(f'Fire resistance low ({fire_res}%)')
        if cold_res < res_target:
            issues.append(f'Cold resistance low ({cold_res}%)')
        if lightning_res < res_target:
            issues.append(f'Lightning resistance low ({lightning_res}%)')

        return {
            'life': life,
            'energy_shield': es,
            'raw_hp': raw_hp,
            'effective_hp': ehp,
            'resistances': {
                'fire': fire_res,
                'cold': cold_res,
                'lightning': lightning_res,
                'chaos': chaos_res
            },
            'quality': defense_quality,
            'issues': issues
        }

    def _analyze_skills(self, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze skill setup"""
        skills = character_data.get('skills', [])

        return {
            'total_skills': len(skills),
            'skill_groups': skills,
            'issues': []
        }

    def _analyze_gear(self, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze equipped gear"""
        items = character_data.get('items', [])

        return {
            'total_items': len(items),
            'items': items,
            'issues': []
        }

    def _generate_recommendations(
        self,
        analysis: Dict[str, Any],
        character_data: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Generate improvement recommendations"""
        recommendations = []

        # Defense recommendations
        defense = analysis['defensive_analysis']
        if defense['quality'] in ['Critical', 'Weak']:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Defense',
                'title': 'Increase Effective HP',
                'description': f"Your EHP ({defense['effective_hp']}) is below recommended. Consider upgrading armor pieces with higher life/ES rolls."
            })

        for issue in defense['issues']:
            if 'resistance' in issue.lower():
                recommendations.append({
                    'priority': 'HIGH',
                    'category': 'Defense',
                    'title': 'Fix Resistances',
                    'description': issue + '. Prioritize gear with resistance mods.'
                })

        return recommendations


class GearRecommender:
    """Recommend gear upgrades based on character needs"""

    def recommend_upgrades(
        self,
        character_data: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Recommend specific gear upgrades

        Args:
            character_data: Character data
            analysis: Character analysis from CharacterAnalyzer

        Returns:
            List of recommended upgrades
        """
        recommendations = []

        # Analyze what stats the character needs
        needed_stats = self._determine_needed_stats(analysis)

        # For each gear slot, recommend improvements
        for stat in needed_stats:
            recommendations.append({
                'stat': stat['name'],
                'priority': stat['priority'],
                'suggested_slots': stat['slots'],
                'reason': stat['reason']
            })

        return recommendations

    def _determine_needed_stats(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Determine what stats the character needs most"""
        needed = []

        defense = analysis['defensive_analysis']

        # Check resistances
        res = defense['resistances']
        for res_type, value in res.items():
            if value < 75 and res_type != 'chaos':  # Elemental res cap is 75
                needed.append({
                    'name': f'{res_type.capitalize()} Resistance',
                    'priority': 'HIGH',
                    'slots': ['Ring', 'Amulet', 'Boots', 'Gloves', 'Belt'],
                    'reason': f'Currently at {value}%, need 75%'
                })

        # Check HP/ES
        if defense['effective_hp'] < 5000:
            needed.append({
                'name': 'Life/Energy Shield',
                'priority': 'HIGH',
                'slots': ['Body Armour', 'Helmet', 'Gloves', 'Boots'],
                'reason': f'EHP too low ({defense["effective_hp"]})'
            })

        return needed
