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
        """Analyze defensive stats"""
        stats = character_data.get('stats', {})

        life = stats.get('life', 0)
        es = stats.get('energyShield', 0)
        ehp = stats.get('effectiveHealthPool', 0)

        # Resistances
        fire_res = stats.get('fireResistance', 0)
        cold_res = stats.get('coldResistance', 0)
        lightning_res = stats.get('lightningResistance', 0)
        chaos_res = stats.get('chaosResistance', 0)

        # Evaluate defense quality
        defense_quality = 'Good'
        issues = []

        if ehp < 3000:
            defense_quality = 'Critical'
            issues.append('EHP critically low')
        elif ehp < 5000:
            defense_quality = 'Weak'
            issues.append('EHP below recommended threshold')

        # Check resistances (75% is cap for elemental, 0% for chaos in PoE2)
        if fire_res < 60:
            issues.append(f'Fire resistance low ({fire_res}%)')
        if cold_res < 60:
            issues.append(f'Cold resistance low ({cold_res}%)')
        if lightning_res < 60:
            issues.append(f'Lightning resistance low ({lightning_res}%)')

        return {
            'life': life,
            'energy_shield': es,
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
