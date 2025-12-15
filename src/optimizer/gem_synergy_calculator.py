"""
Gem Synergy Calculator for Path of Exile 2

Calculates optimal spell gem + support gem combinations considering:
- DPS output
- Spirit cost efficiency
- Utility effects (freeze, shock, cull, etc.)
- Quality of life (AoE, cast speed, etc.)

Author: Claude
Date: 2025-10-24
"""

import logging
import json
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from pathlib import Path
from itertools import combinations
import math

# Import fresh data provider - Single Source of Truth
try:
    from ..data.fresh_data_provider import get_fresh_data_provider
except ImportError:
    from src.data.fresh_data_provider import get_fresh_data_provider

logger = logging.getLogger(__name__)


# Hardcoded support gem incompatibilities (until database is complete)
# Based on PoE2 game mechanics - supports that modify the same stat in opposite directions
# or have mutually exclusive effects cannot be used together
HARDCODED_INCOMPATIBILITIES = {
    # PoE2 uses Projectile Acceleration/Deceleration instead of Faster/Slower
    "Projectile Acceleration Support": ["Projectile Deceleration Support"],
    "Projectile Deceleration Support": ["Projectile Acceleration Support"],
    "SupportProjectileAccelerationPlayer": ["SupportProjectileDecelerationPlayer"],
    "SupportProjectileDecelerationPlayer": ["SupportProjectileAccelerationPlayer"],
    # AoE incompatibilities
    "Concentrated Effect Support": ["Increased Area of Effect Support"],
    "Increased Area of Effect Support": ["Concentrated Effect Support"],
    # Legacy PoE1 names (for backward compatibility)
    "Faster Projectiles": ["Slower Projectiles"],
    "Slower Projectiles": ["Faster Projectiles"],
    "Faster Projectiles Support": ["Slower Projectiles Support"],
    "Slower Projectiles Support": ["Faster Projectiles Support"],
    # Lowercase variations
    "faster_projectiles": ["slower_projectiles"],
    "slower_projectiles": ["faster_projectiles"],
    "projectile_acceleration": ["projectile_deceleration"],
    "projectile_deceleration": ["projectile_acceleration"],
}


@dataclass
class GemStats:
    """Base gem statistics"""
    name: str
    tags: List[str] = field(default_factory=list)
    base_damage_min: float = 0.0
    base_damage_max: float = 0.0
    cast_time: float = 1.0
    crit_chance: float = 0.0
    damage_effectiveness: float = 100.0
    mana_cost: float = 0.0
    spirit_cost: int = 0


@dataclass
class SupportGemEffect:
    """Support gem effects and costs"""
    name: str
    tags: List[str] = field(default_factory=list)

    # Multipliers (More)
    more_damage: float = 0.0  # % more damage
    more_cast_speed: float = 0.0
    more_aoe: float = 0.0
    more_crit_chance: float = 0.0
    more_crit_damage: float = 0.0

    # Multipliers (Less)
    less_damage: float = 0.0  # % less damage
    less_cast_speed: float = 0.0

    # Increased (additive)
    increased_damage: float = 0.0
    increased_cast_speed: float = 0.0
    increased_aoe: float = 0.0
    increased_crit_chance: float = 0.0

    # Added flat damage
    added_damage_min: float = 0.0
    added_damage_max: float = 0.0
    damage_type: str = ""  # fire, cold, lightning, chaos, physical

    # Costs
    spirit_cost: int = 0
    mana_cost_multiplier: float = 100.0  # % of base mana

    # Utility effects
    utility_effects: List[str] = field(default_factory=list)  # ["chain", "fork", "pierce", etc.]

    # Requirements/restrictions
    required_tags: List[str] = field(default_factory=list)  # Support must have matching tags with spell
    incompatible_with: List[str] = field(default_factory=list)  # Cannot be used with these supports


@dataclass
class SynergyResult:
    """Result of a gem combination analysis"""
    spell_name: str
    support_gems: List[str]

    # DPS metrics
    total_dps: float
    average_hit: float
    casts_per_second: float

    # Costs
    total_spirit_cost: int
    total_mana_cost: float

    # Multipliers applied
    total_more_multiplier: float
    total_increased_damage: float

    # Utility
    utility_effects: List[str] = field(default_factory=list)

    # Scoring
    dps_score: float = 0.0
    efficiency_score: float = 0.0  # DPS per spirit
    overall_score: float = 0.0

    # Breakdown
    calculation_breakdown: Dict[str, Any] = field(default_factory=dict)

    # Convenience properties for access
    @property
    def support_names(self) -> List[str]:
        """Alias for support_gems for compatibility"""
        return self.support_gems

    @property
    def total_spirit(self) -> int:
        """Alias for total_spirit_cost for compatibility"""
        return self.total_spirit_cost


class GemSynergyCalculator:
    """
    Calculate optimal spell + support gem combinations

    Usage:
        >>> calc = GemSynergyCalculator()
        >>> results = calc.find_best_combinations(
        ...     spell_name="fireball",
        ...     character_mods={},
        ...     max_spirit=100,
        ...     optimization_goal="dps"
        ... )
        >>> for result in results[:5]:
        ...     print(f"{result.spell_name}: {result.total_dps:.1f} DPS")
    """

    def __init__(self, spell_db_path: Optional[Path] = None, support_db_path: Optional[Path] = None) -> None:
        """
        Initialize calculator with gem databases.

        Now uses FreshDataProvider as Single Source of Truth (SSoT).
        Falls back to JSON files only if FreshDataProvider has no data.

        NEW: Also loads PoB complete skills for constantStats (conversions, built-in mods, etc.)
        """
        self.spell_gems: Dict[str, GemStats] = {}
        self.support_gems: Dict[str, SupportGemEffect] = {}
        self._fresh_provider = get_fresh_data_provider()
        self._pob_skills = {}  # Cache for PoB complete skills with constantStats

        # Try to load from FreshDataProvider first (SSoT)
        self._load_from_fresh_provider()

        # Load PoB complete skills for enhanced data (constantStats, damage effectiveness, etc.)
        self._load_pob_complete_skills()

        # Fall back to JSON files if needed
        if not self.spell_gems:
            if spell_db_path is None:
                spell_db_path = Path(__file__).parent.parent.parent / "data" / "poe2_spell_gems_database.json"
            self._load_spell_database(spell_db_path)

        if not self.support_gems:
            if support_db_path is None:
                support_db_path = Path(__file__).parent.parent.parent / "data" / "poe2_support_gems_database.json"
            self._load_support_database(support_db_path)

        logger.info(f"Loaded {len(self.spell_gems)} spell gems and {len(self.support_gems)} support gems (SSoT: Fresh Game Data + PoB)")

    def _load_from_fresh_provider(self):
        """Load gems from FreshDataProvider (Single Source of Truth)."""
        # Load active skills as spell gems
        active_skills = self._fresh_provider.get_all_active_skills()
        for skill_id, skill_data in active_skills.items():
            # Skip internal/meta skills
            if skill_id.startswith('Art/') or 'Meta' in skill_id:
                continue

            self.spell_gems[skill_id.lower()] = GemStats(
                name=skill_data.get('name', skill_id),
                tags=[],  # Tags would need extraction from game files
                base_damage_min=0,  # Damage values need grantedeffectsperlevel extraction
                base_damage_max=0,
                cast_time=1.0,
                crit_chance=0.0,
                damage_effectiveness=100.0,
                mana_cost=0,
                spirit_cost=0
            )

        # Load support gems
        support_gems = self._fresh_provider.get_all_support_gems()
        for support_id, support_data in support_gems.items():
            # Skip meta supports for now
            if 'Meta' in support_id and 'CastOn' not in support_id:
                continue

            name = support_data.get('name', support_id)
            self.support_gems[support_id.lower()] = SupportGemEffect(
                name=name,
                tags=support_data.get('tags', []),
                # Effects would need detailed extraction from grantedeffectsperlevel
                # For now, use defaults (0) and rely on hardcoded values for key supports
                more_damage=support_data.get('effects', {}).get('more_damage', 0.0),
                more_cast_speed=support_data.get('effects', {}).get('more_cast_speed', 0.0),
                more_aoe=support_data.get('effects', {}).get('more_area', 0.0),
                more_crit_chance=support_data.get('effects', {}).get('more_crit_chance', 0.0),
                more_crit_damage=support_data.get('effects', {}).get('more_crit_damage', 0.0),
                less_damage=support_data.get('effects', {}).get('less_damage', 0.0),
                less_cast_speed=support_data.get('effects', {}).get('less_cast_speed', 0.0),
                increased_damage=support_data.get('effects', {}).get('increased_damage', 0.0),
                increased_cast_speed=support_data.get('effects', {}).get('increased_cast_speed', 0.0),
                increased_crit_chance=support_data.get('effects', {}).get('increased_crit_chance', 0.0),
                spirit_cost=support_data.get('spirit_cost', 0) or 0,
                mana_cost_multiplier=support_data.get('cost_multiplier', 100.0) or 100.0,
                utility_effects=[],
                required_tags=support_data.get('compatible_with', ['spell', 'attack']),
                incompatible_with=support_data.get('incompatible_with', [])
            )

        logger.info(f"FreshDataProvider: {len(self.spell_gems)} active skills, {len(support_gems)} support gems")

    def _load_pob_complete_skills(self):
        """
        Load PoB complete skills data for enhanced gem information.
        This provides constantStats (conversions, built-in modifiers), damage effectiveness, etc.
        """
        try:
            pob_skills_path = Path(__file__).parent.parent.parent / "data" / "pob_complete_skills.json"
            if not pob_skills_path.exists():
                logger.warning("pob_complete_skills.json not found, constantStats won't be available")
                return

            with open(pob_skills_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            skills = data.get('skills', {})
            for skill_id, skill_data in skills.items():
                if not isinstance(skill_data, dict):
                    continue

                self._pob_skills[skill_id.lower()] = skill_data
                # Also index by name for easier lookup
                skill_name = skill_data.get('name', '')
                if skill_name:
                    self._pob_skills[skill_name.lower()] = skill_data

            logger.info(f"Loaded {len(skills)} skills from PoB complete skills (with constantStats)")

        except Exception as e:
            logger.error(f"Failed to load PoB complete skills: {e}")

    def get_skill_constant_stats(self, skill_name: str) -> List[Tuple[str, Any]]:
        """
        Get constantStats for a skill from PoB data.
        These include conversions (e.g., 80% phys -> lightning), built-in modifiers, etc.

        Returns:
            List of (stat_id, value) tuples
        """
        skill_name_lower = skill_name.lower()
        skill_data = self._pob_skills.get(skill_name_lower)

        if not skill_data:
            return []

        # Extract constantStats from statSets (usually the first statSet)
        stat_sets = skill_data.get('statSets', [])
        if not stat_sets:
            return []

        primary_stat_set = stat_sets[0] if isinstance(stat_sets, list) else stat_sets
        if not isinstance(primary_stat_set, dict):
            return []

        const_stats = primary_stat_set.get('constantStats', [])
        return const_stats

    def get_skill_damage_effectiveness(self, skill_name: str) -> Dict[str, float]:
        """
        Get damage effectiveness for a skill from PoB data.

        Returns:
            Dict with 'base' and 'incremental' effectiveness values
        """
        skill_name_lower = skill_name.lower()
        skill_data = self._pob_skills.get(skill_name_lower)

        if not skill_data:
            return {'base': 100.0, 'incremental': 0.0}

        # Extract from statSets
        stat_sets = skill_data.get('statSets', [])
        if not stat_sets:
            return {'base': 100.0, 'incremental': 0.0}

        primary_stat_set = stat_sets[0] if isinstance(stat_sets, list) else stat_sets
        if not isinstance(primary_stat_set, dict):
            return {'base': 100.0, 'incremental': 0.0}

        return {
            'base': primary_stat_set.get('baseEffectiveness', 100.0),
            'incremental': primary_stat_set.get('incrementalEffectiveness', 0.0)
        }

    def _load_spell_database(self, path: Path):
        """Load spell gems from JSON database"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Parse spell gems by category
            for category, spells in data.items():
                if category == "metadata":
                    continue

                for spell_id, spell_data in spells.items():
                    # Use level 20 stats if available, otherwise level 1
                    stats = spell_data.get('level_20', spell_data.get('level_1', {}))

                    self.spell_gems[spell_id] = GemStats(
                        name=spell_data.get('name', spell_id),
                        tags=spell_data.get('tags', []),
                        base_damage_min=stats.get('damage_min', 0) or 0,
                        base_damage_max=stats.get('damage_max', 0) or 0,
                        cast_time=stats.get('cast_time', 1.0) or 1.0,
                        crit_chance=stats.get('crit_chance', 0.0) or 0.0,
                        damage_effectiveness=stats.get('damage_effectiveness', 100) or 100,
                        mana_cost=stats.get('mana_cost', 0) or 0
                    )

            logger.info(f"Loaded {len(self.spell_gems)} spells from {path}")

        except Exception as e:
            logger.error(f"Failed to load spell database from {path}: {e}", exc_info=True)

    def _load_support_database(self, path: Path):
        """Load support gems from JSON database"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Parse support gems from "support_gems" key
            supports = data.get('support_gems', {})

            for support_id, support_data in supports.items():
                # Skip if not a dictionary
                if not isinstance(support_data, dict):
                    continue

                # Parse effects
                effects = support_data.get('effects', {})

                # Determine which tags this support needs (compatible_with)
                compatible_with = support_data.get('compatible_with', [])

                self.support_gems[support_id] = SupportGemEffect(
                    name=support_data.get('name', support_id),
                    tags=support_data.get('tags', []),
                    more_damage=effects.get('more_spell_damage', effects.get('more_damage', 0.0)),
                    more_cast_speed=effects.get('more_cast_speed', 0.0),
                    more_aoe=effects.get('more_area', 0.0),
                    more_crit_chance=effects.get('more_crit_chance', 0.0),
                    more_crit_damage=effects.get('more_crit_damage', 0.0),
                    less_damage=effects.get('less_spell_damage', effects.get('less_damage', 0.0)),
                    less_cast_speed=effects.get('less_cast_speed', 0.0),
                    increased_damage=effects.get('increased_spell_damage', effects.get('increased_damage', 0.0)),
                    increased_cast_speed=effects.get('increased_cast_speed', 0.0),
                    increased_crit_chance=effects.get('increased_crit_chance', 0.0),
                    spirit_cost=support_data.get('spirit_cost', 0) or 0,
                    mana_cost_multiplier=support_data.get('cost_multiplier', 100.0) or 100.0,
                    utility_effects=[],  # Would need to parse from effects
                    required_tags=compatible_with,
                    incompatible_with=[]
                )

            logger.info(f"Loaded {len(self.support_gems)} supports from {path}")

        except Exception as e:
            logger.error(f"Failed to load support database from {path}: {e}", exc_info=True)

    def find_best_combinations(
        self,
        spell_name: str,
        character_mods: Optional[Dict[str, float]] = None,
        max_spirit: int = 100,
        num_supports: int = 5,
        optimization_goal: str = "dps",
        top_n: int = 10,
        return_trace: bool = False
    ) -> Union[List[SynergyResult], Dict[str, Any]]:
        """
        Find the best support gem combinations for a spell

        Args:
            spell_name: Name or ID of the spell gem
            character_mods: Character modifiers (increased damage, cast speed, etc.)
            max_spirit: Maximum spirit available
            num_supports: Number of support gems to use (1-5)
            optimization_goal: "dps", "efficiency", "balanced", "utility"
            top_n: Number of top combinations to return
            return_trace: If True, return trace data showing selection process

        Returns:
            If return_trace=False: List of top N synergy results, sorted by score
            If return_trace=True: Dict with "results" and "trace" keys
        """
        if character_mods is None:
            character_mods = {}

        trace_data = {
            "spell_found": False,
            "compatible_supports_count": 0,
            "compatible_supports": [],
            "total_combinations": 0,
            "valid_combinations": 0,
            "invalid_combinations": 0,
            "spirit_filtered": 0,
            "optimization_goal": optimization_goal
        }

        # Get spell
        spell = self.spell_gems.get(spell_name.lower())
        if not spell:
            logger.error(f"Spell '{spell_name}' not found in database")
            if return_trace:
                return {"results": [], "trace": trace_data}
            return []

        trace_data["spell_found"] = True

        logger.info(f"Finding best {num_supports}-support combinations for {spell.name}")
        logger.info(f"Optimization goal: {optimization_goal}, Max spirit: {max_spirit}")

        # Get compatible supports
        compatible_supports = self._get_compatible_supports(spell)
        trace_data["compatible_supports_count"] = len(compatible_supports)
        trace_data["compatible_supports"] = [s[0] for s in compatible_supports[:20]]  # First 20

        if len(compatible_supports) < num_supports:
            logger.warning(f"Only {len(compatible_supports)} compatible supports found (need {num_supports})")
            num_supports = len(compatible_supports)

        logger.info(f"Found {len(compatible_supports)} compatible support gems")

        # Generate all combinations
        all_results = []
        total_combinations = math.comb(len(compatible_supports), num_supports)
        trace_data["total_combinations"] = total_combinations
        logger.info(f"Testing {total_combinations} combinations...")

        for i, support_combo in enumerate(combinations(compatible_supports, num_supports)):
            # Check if combination is valid (no conflicts)
            if not self._is_valid_combination(support_combo):
                trace_data["invalid_combinations"] += 1
                continue

            trace_data["valid_combinations"] += 1

            # Calculate DPS and metrics
            result = self._calculate_combination_dps(
                spell,
                list(support_combo),
                character_mods,
                max_spirit
            )

            if result is None:
                trace_data["spirit_filtered"] += 1
                continue

            # Calculate scores based on optimization goal
            result = self._score_result(result, optimization_goal)
            all_results.append(result)

            # Log progress every 1000 combinations
            if (i + 1) % 1000 == 0:
                logger.debug(f"Tested {i+1}/{total_combinations} combinations...")

        logger.info(f"Calculated {len(all_results)} valid combinations")

        # Sort by overall score
        all_results.sort(key=lambda r: r.overall_score, reverse=True)

        sorted_results = all_results[:top_n]
        if sorted_results:
            trace_data["top_result_dps"] = sorted_results[0].total_dps

        if return_trace:
            return {"results": sorted_results, "trace": trace_data}
        return sorted_results

    def _get_compatible_supports(self, spell: GemStats) -> List[Tuple[str, SupportGemEffect]]:
        """Get all support gems compatible with this spell"""
        compatible = []

        for support_id, support in self.support_gems.items():
            # Check if support requires specific tags
            if support.required_tags:
                # Spell must have at least one matching tag
                # Check both exact matches and if "spell" tag matches
                matches = False
                for required_tag in support.required_tags:
                    # Exact match
                    if required_tag in spell.tags:
                        matches = True
                        break
                    # Case-insensitive match
                    if required_tag.lower() in [t.lower() for t in spell.tags]:
                        matches = True
                        break

                if not matches:
                    continue

            compatible.append((support_id, support))

        return compatible

    def _is_valid_combination(self, support_combo: List[Tuple[str, SupportGemEffect]]) -> bool:
        """Check if a combination of supports is valid (no conflicts)"""
        support_names = [s[0] for s in support_combo]

        for support_id, support in support_combo:
            # Check database incompatibilities (currently empty but checked for future)
            if support.incompatible_with:
                for incompatible in support.incompatible_with:
                    if incompatible in support_names:
                        logger.warning(f"Rejecting {support_id} + {incompatible} (database incompatibility)")
                        return False

            # Check hardcoded incompatibilities
            if support_id in HARDCODED_INCOMPATIBILITIES:
                for incompatible in HARDCODED_INCOMPATIBILITIES[support_id]:
                    if incompatible in support_names:
                        logger.warning(f"Rejecting {support_id} + {incompatible} (hardcoded incompatibility)")
                        return False

            # Also check normalized names (without "Support" suffix)
            support_base_name = support_id.replace(" Support", "")
            if support_base_name in HARDCODED_INCOMPATIBILITIES:
                for incompatible in HARDCODED_INCOMPATIBILITIES[support_base_name]:
                    incomp_variations = [incompatible, incompatible + " Support"]
                    for variation in incomp_variations:
                        if variation in support_names:
                            logger.warning(f"Rejecting {support_id} + {incompatible} (hardcoded incompatibility - normalized)")
                            return False

        return True

    def validate_combination(self, support_names: List[str]) -> Dict[str, Any]:
        """
        Validate if a combination of support gems is valid

        Args:
            support_names: List of support gem names

        Returns:
            {
                "valid": bool,
                "reason": str (if invalid),
                "conflicts": List[Tuple[str, str]] (pairs of incompatible gems)
            }
        """
        conflicts = []

        for i, support_a in enumerate(support_names):
            # Check hardcoded incompatibilities
            if support_a in HARDCODED_INCOMPATIBILITIES:
                for incompatible in HARDCODED_INCOMPATIBILITIES[support_a]:
                    if incompatible in support_names:
                        conflicts.append((support_a, incompatible))

            # Also check normalized names
            support_base = support_a.replace(" Support", "")
            if support_base in HARDCODED_INCOMPATIBILITIES:
                for incompatible in HARDCODED_INCOMPATIBILITIES[support_base]:
                    incomp_variations = [incompatible, incompatible + " Support"]
                    for variation in incomp_variations:
                        if variation in support_names:
                            conflicts.append((support_a, variation))

        if conflicts:
            conflict_pairs = [f"{a} + {b}" for a, b in conflicts]
            return {
                "valid": False,
                "reason": f"Incompatible support combinations detected: {', '.join(conflict_pairs)}",
                "conflicts": conflicts
            }

        return {
            "valid": True,
            "reason": "All supports are compatible",
            "conflicts": []
        }

    def trace_dps_calculation(
        self,
        spell_name: str,
        support_names: List[str],
        character_mods: Optional[Dict[str, float]] = None,
        max_spirit: int = 100
    ) -> Dict[str, Any]:
        """
        Trace DPS calculation step-by-step for debugging and explanation

        Args:
            spell_name: Name of the spell gem
            support_names: List of support gem names
            character_mods: Character modifiers (increased_damage, etc.)
            max_spirit: Maximum spirit available

        Returns:
            {
                "spell": {name, base_damage_min, base_damage_max, cast_time},
                "supports": [{name, more_damage, increased_damage, ...}],
                "calculations": {
                    "base_damage_avg": float,
                    "more_multipliers": [{support_name, value, cumulative}],
                    "more_total": float,
                    "increased_char": float,
                    "increased_supports": float,
                    "increased_total": float,
                    "final_damage_per_cast": float,
                    "cast_time": float,
                    "final_dps": float
                },
                "spirit": {total, available, overflow},
                "valid": bool,
                "errors": List[str]
            }
        """
        if character_mods is None:
            character_mods = {}

        trace = {
            "spell": {},
            "supports": [],
            "calculations": {},
            "spirit": {},
            "valid": True,
            "errors": []
        }

        # Get spell
        spell = self.spell_gems.get(spell_name.lower())
        if not spell:
            trace["valid"] = False
            trace["errors"].append(f"Spell '{spell_name}' not found")
            return trace

        trace["spell"] = {
            "name": spell.name,
            "base_damage_min": spell.base_damage_min,
            "base_damage_max": spell.base_damage_max,
            "cast_time": spell.cast_time
        }

        # Get supports
        support_objs = []
        for sup_name in support_names:
            found = False
            for sup_id, sup_obj in self.support_gems.items():
                if sup_obj.name.lower() == sup_name.lower() or sup_id.lower() == sup_name.lower():
                    support_objs.append((sup_id, sup_obj))
                    trace["supports"].append({
                        "name": sup_obj.name,
                        "more_damage": sup_obj.more_damage,
                        "less_damage": sup_obj.less_damage,
                        "increased_damage": sup_obj.increased_damage,
                        "spirit_cost": sup_obj.spirit_cost
                    })
                    found = True
                    break
            if not found:
                trace["errors"].append(f"Support '{sup_name}' not found")

        if trace["errors"]:
            trace["valid"] = False
            return trace

        # Validate combination
        validation = self.validate_combination(support_names)
        if not validation["valid"]:
            trace["valid"] = False
            trace["errors"].append(validation["reason"])
            return trace

        # Calculate spirit
        total_spirit = spell.spirit_cost + sum(s[1].spirit_cost for s in support_objs)
        trace["spirit"] = {
            "total": total_spirit,
            "available": max_spirit,
            "overflow": max(0, total_spirit - max_spirit)
        }

        if total_spirit > max_spirit:
            trace["valid"] = False
            trace["errors"].append(f"Spirit overflow: {total_spirit} > {max_spirit}")

        # Step 1: Base damage
        base_damage_avg = (spell.base_damage_min + spell.base_damage_max) / 2
        trace["calculations"]["base_damage_avg"] = base_damage_avg

        # Step 2: More multipliers (multiplicative)
        more_total = 1.0
        more_steps = []
        for sup_id, sup in support_objs:
            # Net more multiplier (more_damage - less_damage)
            net_more = (1.0 + sup.more_damage / 100.0) * (1.0 - sup.less_damage / 100.0)
            more_total *= net_more
            more_steps.append({
                "support_name": sup.name,
                "net_multiplier": net_more,
                "cumulative": more_total
            })

        trace["calculations"]["more_multipliers"] = more_steps
        trace["calculations"]["more_total"] = more_total

        # Step 3: Increased modifiers (additive)
        increased_char = character_mods.get("increased_damage", 0.0)
        increased_supports = sum(s[1].increased_damage for s in support_objs)
        increased_total = 1.0 + (increased_char + increased_supports) / 100.0

        trace["calculations"]["increased_char"] = increased_char
        trace["calculations"]["increased_supports"] = increased_supports
        trace["calculations"]["increased_total"] = increased_total

        # Step 4: Final damage per cast
        final_damage = base_damage_avg * more_total * increased_total
        trace["calculations"]["final_damage_per_cast"] = final_damage

        # Step 5: DPS
        cast_time = spell.cast_time
        if cast_time > 0:
            final_dps = final_damage / cast_time
        else:
            final_dps = 0
            trace["errors"].append("Cast time is 0, cannot calculate DPS")

        trace["calculations"]["cast_time"] = cast_time
        trace["calculations"]["final_dps"] = final_dps

        return trace

    def _calculate_combination_dps(
        self,
        spell: GemStats,
        supports: List[Tuple[str, SupportGemEffect]],
        character_mods: Dict[str, float],
        max_spirit: int
    ) -> Optional[SynergyResult]:
        """Calculate DPS for a specific spell + support combination"""

        # Calculate total spirit cost
        total_spirit = spell.spirit_cost + sum(s[1].spirit_cost for s in supports)

        # Skip if over spirit budget
        if total_spirit > max_spirit:
            return None

        # Start with base damage
        base_damage_avg = (spell.base_damage_min + spell.base_damage_max) / 2

        if base_damage_avg == 0:
            logger.debug(f"Skipping {spell.name} - no base damage data")
            return None

        # Accumulate modifiers
        total_more_damage = 1.0
        total_increased_damage = character_mods.get('increased_damage', 0.0)
        total_more_cast_speed = 1.0
        total_increased_cast_speed = character_mods.get('increased_cast_speed', 0.0)
        total_added_damage = 0.0
        utility_effects = []
        total_mana_cost = spell.mana_cost

        # Apply each support's effects
        for support_id, support in supports:
            # More multipliers (multiplicative)
            if support.more_damage != 0:
                total_more_damage *= (1.0 + support.more_damage / 100.0)

            if support.more_cast_speed != 0:
                total_more_cast_speed *= (1.0 + support.more_cast_speed / 100.0)

            # Less multipliers (multiplicative penalties)
            if support.less_damage != 0:
                total_more_damage *= (1.0 - support.less_damage / 100.0)

            if support.less_cast_speed != 0:
                total_more_cast_speed *= (1.0 - support.less_cast_speed / 100.0)

            # Increased (additive)
            total_increased_damage += support.increased_damage
            total_increased_cast_speed += support.increased_cast_speed

            # Added damage
            if support.added_damage_min > 0 or support.added_damage_max > 0:
                added_avg = (support.added_damage_min + support.added_damage_max) / 2
                # Apply damage effectiveness
                total_added_damage += added_avg * (spell.damage_effectiveness / 100.0)

            # Utility
            utility_effects.extend(support.utility_effects)

            # Mana cost
            total_mana_cost *= (support.mana_cost_multiplier / 100.0)

        # Calculate final damage
        damage_after_added = base_damage_avg + total_added_damage
        damage_after_increased = damage_after_added * (1.0 + total_increased_damage / 100.0)
        final_damage = damage_after_increased * total_more_damage

        # Calculate cast speed
        base_casts_per_sec = 1.0 / spell.cast_time
        casts_after_increased = base_casts_per_sec * (1.0 + total_increased_cast_speed / 100.0)
        final_casts_per_sec = casts_after_increased * total_more_cast_speed

        # Calculate DPS
        total_dps = final_damage * final_casts_per_sec

        # Create result
        result = SynergyResult(
            spell_name=spell.name,
            support_gems=[s[1].name for s in supports],
            total_dps=total_dps,
            average_hit=final_damage,
            casts_per_second=final_casts_per_sec,
            total_spirit_cost=total_spirit,
            total_mana_cost=total_mana_cost,
            total_more_multiplier=total_more_damage,
            total_increased_damage=total_increased_damage,
            utility_effects=utility_effects,
            calculation_breakdown={
                'base_damage': base_damage_avg,
                'added_damage': total_added_damage,
                'after_increased': damage_after_increased,
                'after_more': final_damage,
                'more_multiplier': total_more_damage,
                'increased_total': total_increased_damage,
                'cast_speed_multiplier': total_more_cast_speed,
                'spirit_per_support': [s[1].spirit_cost for s in supports]
            }
        )

        return result

    def _score_result(self, result: SynergyResult, optimization_goal: str) -> SynergyResult:
        """Calculate scores for a result based on optimization goal"""

        # DPS score (normalized)
        result.dps_score = result.total_dps

        # Efficiency score (DPS per spirit)
        if result.total_spirit_cost > 0:
            result.efficiency_score = result.total_dps / result.total_spirit_cost
        else:
            result.efficiency_score = result.total_dps

        # Utility score (bonus for utility effects)
        utility_score = len(result.utility_effects) * 1000  # Arbitrary bonus

        # Calculate overall score based on goal
        if optimization_goal == "dps":
            result.overall_score = result.dps_score
        elif optimization_goal == "efficiency":
            result.overall_score = result.efficiency_score
        elif optimization_goal == "utility":
            result.overall_score = result.dps_score * 0.7 + utility_score
        else:  # balanced
            result.overall_score = (
                result.dps_score * 0.6 +
                result.efficiency_score * 10.0 +  # Scale up efficiency
                utility_score * 0.1
            )

        return result

    def format_result(self, result: SynergyResult, detailed: bool = False) -> str:
        """Format a synergy result as human-readable text"""
        lines = []
        lines.append("=" * 80)
        lines.append(f"Spell: {result.spell_name}")
        lines.append(f"Support Gems: {', '.join(result.support_gems)}")
        lines.append("-" * 80)
        lines.append(f"Total DPS: {result.total_dps:,.1f}")
        lines.append(f"Average Hit: {result.average_hit:,.1f}")
        lines.append(f"Casts per Second: {result.casts_per_second:.2f}")
        lines.append(f"Spirit Cost: {result.total_spirit_cost}")
        lines.append(f"Mana Cost: {result.total_mana_cost:.1f}")
        lines.append(f"More Multiplier: {result.total_more_multiplier:.2f}x")
        lines.append(f"Increased Damage: {result.total_increased_damage:+.0f}%")

        if result.utility_effects:
            lines.append(f"Utility: {', '.join(result.utility_effects)}")

        lines.append("-" * 80)
        lines.append(f"DPS Score: {result.dps_score:,.1f}")
        lines.append(f"Efficiency (DPS/Spirit): {result.efficiency_score:,.1f}")
        lines.append(f"Overall Score: {result.overall_score:,.1f}")

        if detailed and result.calculation_breakdown:
            lines.append("-" * 80)
            lines.append("Calculation Breakdown:")
            for key, value in result.calculation_breakdown.items():
                lines.append(f"  {key}: {value}")

        lines.append("=" * 80)

        return "\n".join(lines)


# Convenience function
def find_best_supports_for_spell(
    spell_name: str,
    max_spirit: int = 100,
    num_supports: int = 5,
    goal: str = "dps"
) -> List[SynergyResult]:
    """
    Quick function to find best support combinations

    Args:
        spell_name: Name of the spell
        max_spirit: Maximum spirit available
        num_supports: Number of supports to use
        goal: "dps", "efficiency", "balanced", or "utility"

    Returns:
        List of top 10 combinations
    """
    calc = GemSynergyCalculator()
    return calc.find_best_combinations(
        spell_name=spell_name,
        max_spirit=max_spirit,
        num_supports=num_supports,
        optimization_goal=goal,
        top_n=10
    )


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 80)
    print("Path of Exile 2 Gem Synergy Calculator")
    print("=" * 80)
    print()

    # Example: Find best supports for Fireball
    print("Finding best 5-support combinations for Fireball...")
    print("Optimization goal: DPS")
    print("Max spirit: 100")
    print()

    results = find_best_supports_for_spell(
        spell_name="fireball",
        max_spirit=100,
        num_supports=5,
        goal="dps"
    )

    if results:
        print(f"Top {len(results)} combinations:")
        print()

        calc = GemSynergyCalculator()
        for i, result in enumerate(results, 1):
            print(f"#{i}")
            print(calc.format_result(result, detailed=False))
            print()
    else:
        print("No valid combinations found.")
