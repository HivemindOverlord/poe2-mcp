"""
Tests for CharacterAnalyzer - particularly the poe.ninja format compatibility fixes
"""

import pytest
from src.analyzer.character_analyzer import CharacterAnalyzer, GearRecommender


class TestCharacterAnalyzerDefenses:
    """Test defense analysis with various data formats"""

    def setup_method(self):
        self.analyzer = CharacterAnalyzer()

    def test_analyze_defenses_with_stats_format(self):
        """Test with normalized stats format (life, energyShield keys)"""
        char_data = {
            'name': 'TestChar',
            'level': 50,
            'stats': {
                'life': 2000,
                'energyShield': 500,
                'fireResistance': 75,
                'coldResistance': 60,
                'lightningResistance': 45,
                'chaosResistance': 0
            }
        }

        result = self.analyzer._analyze_defenses(char_data)

        assert result['life'] == 2000
        assert result['energy_shield'] == 500
        assert result['raw_hp'] == 2500
        assert result['resistances']['fire'] == 75
        assert result['resistances']['cold'] == 60
        assert result['resistances']['lightning'] == 45

    def test_analyze_defenses_with_poe_ninja_raw_format(self):
        """Test with poe.ninja raw_data.charModel.defensiveStats format"""
        char_data = {
            'name': 'TestChar',
            'level': 30,
            'raw_data': {
                'charModel': {
                    'level': 30,
                    'defensiveStats': {
                        'life': 487,
                        'energyShield': 116,
                        'effectiveHealthPool': 394,
                        'fireRes': -40,
                        'coldRes': -66,
                        'lightningRes': -54,
                        'chaosRes': 0
                    }
                }
            }
        }

        result = self.analyzer._analyze_defenses(char_data)

        assert result['life'] == 487
        assert result['energy_shield'] == 116
        assert result['raw_hp'] == 603
        assert result['effective_hp'] == 394  # Uses poe.ninja's calculated EHP
        assert result['resistances']['fire'] == -40
        assert result['resistances']['cold'] == -66
        assert result['resistances']['lightning'] == -54

    def test_analyze_defenses_field_name_fallbacks(self):
        """Test that both fireRes and fireResistance formats work"""
        # Test with fireRes format
        char_data_res = {
            'level': 50,
            'raw_data': {
                'charModel': {
                    'defensiveStats': {
                        'life': 1000,
                        'fireRes': 50
                    }
                }
            }
        }
        result = self.analyzer._analyze_defenses(char_data_res)
        assert result['resistances']['fire'] == 50

        # Test with fireResistance format
        char_data_resistance = {
            'level': 50,
            'stats': {
                'life': 1000,
                'fireResistance': 60
            }
        }
        result = self.analyzer._analyze_defenses(char_data_resistance)
        assert result['resistances']['fire'] == 60

    def test_level_scaled_ehp_thresholds(self):
        """Test that EHP quality thresholds scale with character level"""
        # min_ehp = max(500, level * 50)
        # target_ehp = level * 100
        # Critical if ehp < min_ehp, Weak if ehp < target_ehp, else Good

        # Level 10: min=500, target=1000
        # 500 EHP is == min but < target, so Weak
        char_level_10_weak = {
            'level': 10,
            'stats': {'life': 400, 'energyShield': 100}
        }
        result = self.analyzer._analyze_defenses(char_level_10_weak)
        assert result['quality'] == 'Weak'  # 500 == 500 (min) but < 1000 (target)

        # Level 10: 1100 EHP is >= target (1000), so Good
        char_level_10_good = {
            'level': 10,
            'stats': {'life': 1000, 'energyShield': 100}
        }
        result = self.analyzer._analyze_defenses(char_level_10_good)
        assert result['quality'] == 'Good'  # 1100 >= 1000 (target)

        # Level 50: min=2500, target=5000
        # 1500 EHP is < min (2500), so Critical
        char_level_50 = {
            'level': 50,
            'stats': {'life': 1500, 'energyShield': 0}
        }
        result = self.analyzer._analyze_defenses(char_level_50)
        assert result['quality'] == 'Critical'  # 1500 < 2500 (min)

        # Level 50: 3000 EHP is >= min but < target, so Weak
        char_level_50_weak = {
            'level': 50,
            'stats': {'life': 3000, 'energyShield': 0}
        }
        result = self.analyzer._analyze_defenses(char_level_50_weak)
        assert result['quality'] == 'Weak'  # 3000 >= 2500 but < 5000

        # Level 50: 5500 EHP is >= target, so Good
        char_level_50_good = {
            'level': 50,
            'stats': {'life': 5000, 'energyShield': 500}
        }
        result = self.analyzer._analyze_defenses(char_level_50_good)
        assert result['quality'] == 'Good'

    def test_level_scaled_resistance_thresholds(self):
        """Test that resistance warnings scale with character level"""
        # Level 30 character with 25% fire res should get warning (target=30)
        char_data = {
            'level': 30,
            'stats': {'life': 2000, 'fireResistance': 25}
        }
        result = self.analyzer._analyze_defenses(char_data)
        issues = [i for i in result['issues'] if 'Fire resistance' in i]
        assert len(issues) == 1

        # Level 30 character with 35% fire res should be OK (35 >= 30)
        char_data_ok = {
            'level': 30,
            'stats': {'life': 2000, 'fireResistance': 35}
        }
        result = self.analyzer._analyze_defenses(char_data_ok)
        issues = [i for i in result['issues'] if 'Fire resistance' in i]
        assert len(issues) == 0

    def test_ehp_fallback_to_raw_hp(self):
        """Test that EHP falls back to life+ES when effectiveHealthPool not provided"""
        char_data = {
            'level': 50,
            'stats': {
                'life': 3000,
                'energyShield': 1000
                # No effectiveHealthPool
            }
        }
        result = self.analyzer._analyze_defenses(char_data)
        assert result['effective_hp'] == 4000  # Falls back to life + ES


class TestCharacterAnalyzerIntegration:
    """Integration tests for full character analysis"""

    def setup_method(self):
        self.analyzer = CharacterAnalyzer()

    def test_analyze_character_basic(self):
        """Test full character analysis flow"""
        char_data = {
            'name': 'TestCharacter',
            'league': 'Standard',
            'level': 70,
            'stats': {
                'life': 4000,
                'energyShield': 500,
                'fireResistance': 75,
                'coldResistance': 75,
                'lightningResistance': 75,
                'chaosResistance': 0
            },
            'skills': [{'name': 'Fireball'}, {'name': 'Herald of Ash'}],
            'items': [{'name': 'Some Helmet'}, {'name': 'Some Boots'}]
        }

        result = self.analyzer.analyze_character(char_data)

        assert result['character_name'] == 'TestCharacter'
        assert result['league'] == 'Standard'
        assert 'defensive_analysis' in result
        assert 'skill_analysis' in result
        assert 'gear_analysis' in result
        assert result['skill_analysis']['total_skills'] == 2
        assert result['gear_analysis']['total_items'] == 2

    def test_analyze_character_poe_ninja_format(self):
        """Test analysis with poe.ninja style data"""
        char_data = {
            'name': 'TomawarTheFourth',
            'level': 29,
            'raw_data': {
                'charModel': {
                    'name': 'TomawarTheFourth',
                    'level': 29,
                    'class': 'Witchhunter',
                    'defensiveStats': {
                        'life': 487,
                        'energyShield': 116,
                        'effectiveHealthPool': 394,
                        'fireRes': -40,
                        'coldRes': -66,
                        'lightningRes': -54,
                        'chaosRes': 0
                    }
                }
            }
        }

        result = self.analyzer.analyze_character(char_data)

        assert result['character_name'] == 'TomawarTheFourth'
        defense = result['defensive_analysis']
        assert defense['life'] == 487
        assert defense['energy_shield'] == 116
        assert defense['effective_hp'] == 394
        assert defense['quality'] == 'Critical'  # Low EHP for level 29
        # Should have multiple issues for negative resistances
        assert len(defense['issues']) > 0

    def test_recommendations_generated_for_low_defenses(self):
        """Test that recommendations are generated for weak defenses"""
        char_data = {
            'name': 'WeakChar',
            'level': 50,
            'stats': {
                'life': 1000,  # Very low for level 50
                'fireResistance': 20,  # Below target
                'coldResistance': 75,
                'lightningResistance': 75
            }
        }

        result = self.analyzer.analyze_character(char_data)

        # Should have EHP recommendation (title is "Increase Effective HP")
        ehp_recs = [r for r in result['recommendations'] if 'Effective HP' in r['title']]
        assert len(ehp_recs) >= 1

        # Should have resistance recommendation
        res_recs = [r for r in result['recommendations'] if 'Resistance' in r['title']]
        assert len(res_recs) >= 1


class TestGearRecommender:
    """Test GearRecommender functionality"""

    def setup_method(self):
        self.recommender = GearRecommender()

    def test_recommend_resistance_upgrades(self):
        """Test that resistance upgrades are recommended when needed"""
        analysis = {
            'defensive_analysis': {
                'effective_hp': 6000,
                'resistances': {
                    'fire': 40,  # Below 75
                    'cold': 75,
                    'lightning': 75,
                    'chaos': 0
                }
            }
        }

        recommendations = self.recommender._determine_needed_stats(analysis)

        fire_rec = [r for r in recommendations if 'Fire' in r['name']]
        assert len(fire_rec) == 1
        assert fire_rec[0]['priority'] == 'HIGH'

    def test_recommend_hp_upgrades(self):
        """Test that HP upgrades are recommended when EHP is low"""
        analysis = {
            'defensive_analysis': {
                'effective_hp': 3000,  # Below 5000 threshold
                'resistances': {
                    'fire': 75,
                    'cold': 75,
                    'lightning': 75,
                    'chaos': 0
                }
            }
        }

        recommendations = self.recommender._determine_needed_stats(analysis)

        hp_rec = [r for r in recommendations if 'Life' in r['name'] or 'Energy Shield' in r['name']]
        assert len(hp_rec) == 1
