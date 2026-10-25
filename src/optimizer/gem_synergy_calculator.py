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

import json
import logging
import math
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Import fresh data provider - Single Source of Truth
try:
    from ..data.fresh_data_provider import get_fresh_data_provider
    from ..database.manager import DatabaseManager
    from ..database.models import SupportGem
except ImportError:
    from src.data.fresh_data_provider import get_fresh_data_provider
    from src.database.manager import DatabaseManager
    from src.database.models import SupportGem

from sqlalchemy import select

logger = logging.getLogger(__name__)


# Semantic-conflict detection (damage-type / skill-tag) lives in a lightweight
# sibling module so it can be unit-tested without SQLAlchemy import cost.
try:
    from .support_validation import (
        SUPPORT_DAMAGE_REQUIREMENTS,
        check_semantic_conflicts,
        lookup_spell_tags,
        support_required_tags,
    )
except ImportError:
    from src.optimizer.support_validation import (
        SUPPORT_DAMAGE_REQUIREMENTS,
        check_semantic_conflicts,
        lookup_spell_tags,
        support_required_tags,
    )


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


def _normalize_gem_name(name: str) -> str:
    """
    Canonical form for gem-name comparison: lowercase, underscores as
    spaces, trailing " support" suffix dropped. Makes "Concentrated
    Effect", "Concentrated Effect Support" and "concentrated_effect"
    all compare equal — the 0.5 canonical extraction carries the
    suffix, callers usually don't.
    """
    normalized = name.lower().replace("_", " ").strip()
    if normalized.endswith(" support"):
        normalized = normalized[: -len(" support")].strip()
    return normalized


# HARDCODED_INCOMPATIBILITIES folded to normalized names so conflict checks
# are insensitive to suffix/case/underscore variants of the same gem.
_NORMALIZED_INCOMPATIBILITIES: Dict[str, set] = {}
for _key, _conflicts in HARDCODED_INCOMPATIBILITIES.items():
    _NORMALIZED_INCOMPATIBILITIES.setdefault(_normalize_gem_name(_key), set()).update(
        _normalize_gem_name(_c) for _c in _conflicts
    )


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
    required_tags: List[str] = field(
        default_factory=list
    )  # Support must have matching tags with spell
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

    def __init__(
        self, spell_db_path: Optional[Path] = None, support_db_path: Optional[Path] = None
    ) -> None:
        """
        Initialize calculator with gem databases.

        Now uses FreshDataProvider as Single Source of Truth (SSoT).
        Falls back to JSON files only if FreshDataProvider has no data.

        NEW: Also loads PoB complete skills for constantStats (conversions, built-in mods, etc.)
        """
        self.spell_gems: Dict[str, GemStats] = {}
        self.support_gems: Dict[str, SupportGemEffect] = {}
        # Display-name -> dict-key alias maps. Kept SEPARATE from the gem
        # dicts so iteration (e.g. _get_compatible_supports) never sees the
        # same gem twice under different keys.
        self._spell_aliases: Dict[str, str] = {}
        self._support_aliases: Dict[str, str] = {}
        self._fresh_provider = get_fresh_data_provider()
        self._pob_skills = {}  # Cache for PoB complete skills with constantStats

        # Try to load from FreshDataProvider first (SSoT)
        self._load_from_fresh_provider()

        # Load PoB complete skills for enhanced data (constantStats, damage effectiveness, etc.)
        self._load_pob_complete_skills()

        # Fall back to JSON files if needed
        if not self.spell_gems:
            if spell_db_path is None:
                spell_db_path = (
                    Path(__file__).parent.parent.parent / "data" / "poe2_spell_gems_database.json"
                )
            self._load_spell_database(spell_db_path)

        if not self.support_gems:
            if support_db_path is None:
                support_db_path = (
                    Path(__file__).parent.parent.parent / "data" / "poe2_support_gems_database.json"
                )
            self._load_support_database(support_db_path)

        logger.info(
            f"Loaded {len(self.spell_gems)} spell gems and {len(self.support_gems)} support gems (SSoT: Fresh Game Data + PoB)"
        )

    def _load_from_fresh_provider(self):
        """Load gems from FreshDataProvider (Single Source of Truth)."""
        # Load active skills as spell gems
        active_skills = self._fresh_provider.get_all_active_skills()
        for skill_id, skill_data in active_skills.items():
            # Skip internal/meta skills
            if skill_id.startswith("Art/") or "Meta" in skill_id:
                continue

            key = skill_id.lower()
            display_name = skill_data.get("display_name") or skill_data.get("name") or skill_id
            self.spell_gems[key] = GemStats(
                name=display_name,
                tags=[],  # Tags would need extraction from game files
                base_damage_min=0,  # Damage values need grantedeffectsperlevel extraction
                base_damage_max=0,
                cast_time=1.0,
                crit_chance=0.0,
                damage_effectiveness=100.0,
                mana_cost=0,
                spirit_cost=0,
            )

            # Alias by display name so callers can say "fireball", not
            # "fireballplayer". Player variants win over monster/boss skills
            # that share the same display name (e.g. boss Fireballs).
            name_key = _normalize_gem_name(display_name) if display_name != skill_id else ""
            if name_key and name_key != key:
                is_player_variant = key.endswith("player")
                existing = self._spell_aliases.get(name_key)
                if existing is None or (is_player_variant and not existing.endswith("player")):
                    self._spell_aliases[name_key] = key

        # Load support gems
        support_gems = self._fresh_provider.get_all_support_gems()
        for support_id, support_data in support_gems.items():
            # Skip meta supports for now
            if "Meta" in support_id and "CastOn" not in support_id:
                continue

            name = support_data.get("name", support_id)
            support_key = support_id.lower()
            # Alias by display name (normalized — " Support" suffix dropped)
            # so "Spell Echo" finds the gem stored under its internal id.
            support_name_key = _normalize_gem_name(name)
            if support_name_key and support_name_key != support_key:
                self._support_aliases.setdefault(support_name_key, support_key)
            self.support_gems[support_key] = SupportGemEffect(
                name=name,
                tags=support_data.get("tags", []),
                # Effects would need detailed extraction from grantedeffectsperlevel
                # For now, use defaults (0) and rely on hardcoded values for key supports
                more_damage=support_data.get("effects", {}).get("more_damage", 0.0),
                more_cast_speed=support_data.get("effects", {}).get("more_cast_speed", 0.0),
                more_aoe=support_data.get("effects", {}).get("more_area", 0.0),
                more_crit_chance=support_data.get("effects", {}).get("more_crit_chance", 0.0),
                more_crit_damage=support_data.get("effects", {}).get("more_crit_damage", 0.0),
                less_damage=support_data.get("effects", {}).get("less_damage", 0.0),
                less_cast_speed=support_data.get("effects", {}).get("less_cast_speed", 0.0),
                increased_damage=support_data.get("effects", {}).get("increased_damage", 0.0),
                increased_cast_speed=support_data.get("effects", {}).get(
                    "increased_cast_speed", 0.0
                ),
                increased_crit_chance=support_data.get("effects", {}).get(
                    "increased_crit_chance", 0.0
                ),
                spirit_cost=support_data.get("spirit_cost", 0) or 0,
                mana_cost_multiplier=support_data.get("cost_multiplier", 100.0) or 100.0,
                utility_effects=[],
                required_tags=support_data.get("compatible_with", ["spell", "attack"]),
                incompatible_with=support_data.get("incompatible_with", []),
            )

        logger.info(
            f"FreshDataProvider: {len(self.spell_gems)} active skills, {len(support_gems)} support gems"
        )

    def _get_spell(self, spell_name: str) -> Optional[GemStats]:
        """
        Resolve a spell by dict key, display-name alias, or (last resort)
        a scan over loaded names. The fresh-provider data keys spells by
        internal skill id ("fireballplayer") while callers pass display
        names ("fireball") — the alias map bridges that.
        """
        key = spell_name.lower().strip()
        if key in self.spell_gems:
            return self.spell_gems[key]
        normalized = _normalize_gem_name(spell_name)
        alias = self._spell_aliases.get(normalized)
        if alias and alias in self.spell_gems:
            return self.spell_gems[alias]
        for gem in self.spell_gems.values():
            if _normalize_gem_name(gem.name) == normalized:
                return gem
        return None

    def _get_support(self, support_name: str) -> Optional[Tuple[str, SupportGemEffect]]:
        """
        Resolve a support gem by dict key, display-name alias (suffix
        tolerant: "Spell Echo" matches "Spell Echo Support"), or a scan
        over loaded names. Returns (dict_key, effect) or None.
        """
        key = support_name.lower().strip()
        if key in self.support_gems:
            return key, self.support_gems[key]
        normalized = _normalize_gem_name(support_name)
        alias = self._support_aliases.get(normalized)
        if alias and alias in self.support_gems:
            return alias, self.support_gems[alias]
        for support_id, support in self.support_gems.items():
            if _normalize_gem_name(support.name) == normalized:
                return support_id, support
        return None

    async def load_support_gems_from_database(self, db_manager: DatabaseManager) -> int:
        """
        Load support gems from SQLite database (authoritative source with display names).

        This method replaces support gems loaded from FreshDataProvider with the
        complete data from the SQLite database, which includes proper display names
        and modifier data.

        Args:
            db_manager: Initialized DatabaseManager instance

        Returns:
            Number of support gems loaded
        """
        try:
            async with db_manager.async_session() as session:
                result = await session.execute(select(SupportGem))
                db_gems = result.scalars().all()

                if not db_gems:
                    logger.warning(
                        "No support gems found in database, keeping FreshDataProvider data"
                    )
                    return 0

                # Clear existing support gems and reload from database
                self.support_gems.clear()

                for gem in db_gems:
                    # Parse modifiers to extract relevant stats
                    stats = self._parse_support_gem_modifiers(gem.modifiers or [])

                    # Create lookup keys - both by display name and normalized name
                    display_name = gem.name  # e.g., "Rapid Attacks I"
                    normalized_name = display_name.lower().replace(" ", "_")

                    support_effect = SupportGemEffect(
                        name=display_name,
                        tags=gem.tags or [],
                        more_damage=stats.get("more_damage", 0.0),
                        more_cast_speed=stats.get("more_cast_speed", 0.0),
                        more_aoe=stats.get("more_aoe", 0.0),
                        more_crit_chance=stats.get("more_crit_chance", 0.0),
                        more_crit_damage=stats.get("more_crit_damage", 0.0),
                        less_damage=stats.get("less_damage", 0.0),
                        less_cast_speed=stats.get("less_cast_speed", 0.0),
                        increased_damage=stats.get("increased_damage", 0.0),
                        increased_cast_speed=stats.get("increased_cast_speed", 0.0),
                        increased_crit_chance=stats.get("increased_crit_chance", 0.0),
                        spirit_cost=gem.spirit_cost or 0,
                        mana_cost_multiplier=gem.mana_multiplier or 100.0,
                        utility_effects=stats.get("utility_effects", []),
                        required_tags=gem.compatible_tags or [],
                        incompatible_with=[],
                    )

                    # Store by multiple keys for flexible lookup
                    self.support_gems[normalized_name] = support_effect
                    self.support_gems[display_name.lower()] = support_effect

                    # Also store without tier suffix for generic lookup
                    # e.g., "rapid attacks i" -> also accessible as "rapid attacks"
                    base_name = self._get_base_gem_name(display_name)
                    if base_name.lower() != display_name.lower():
                        # Only add if not already a higher tier
                        if base_name.lower() not in self.support_gems:
                            self.support_gems[base_name.lower()] = support_effect

                logger.info(
                    f"Loaded {len(db_gems)} support gems from SQLite database (replacing FreshDataProvider data)"
                )
                return len(db_gems)

        except Exception as e:
            logger.error(f"Failed to load support gems from database: {e}", exc_info=True)
            return 0

    def _parse_support_gem_modifiers(self, modifiers: List) -> Dict[str, Any]:
        """
        Parse support gem modifiers from database format to SupportGemEffect stats.

        Database format: [['stat_id', value], ['stat_id', value], ...]

        Args:
            modifiers: List of [stat_id, value] pairs from database

        Returns:
            Dict of parsed stats for SupportGemEffect
        """
        stats = {
            "more_damage": 0.0,
            "more_cast_speed": 0.0,
            "more_aoe": 0.0,
            "more_crit_chance": 0.0,
            "more_crit_damage": 0.0,
            "less_damage": 0.0,
            "less_cast_speed": 0.0,
            "increased_damage": 0.0,
            "increased_cast_speed": 0.0,
            "increased_crit_chance": 0.0,
            "utility_effects": [],
        }

        if not modifiers:
            return stats

        # Mapping of stat IDs to our stat fields
        # Format: stat_id -> (field_name, multiplier)
        stat_mapping = {
            # More multipliers (multiplicative)
            "support_gem_damage_+%_final": ("more_damage", 1.0),
            "support_gem_elemental_damage_+%_final": ("more_damage", 1.0),
            "support_attack_skills_elemental_damage_+%_final": ("more_damage", 1.0),
            "support_faster_attacks_damage_+%_final": ("less_damage", -1.0),  # Negative = less
            "support_increased_area_damage_+%_final": ("more_damage", 1.0),
            "support_far_combat_attack_damage_+%_final_from_distance": ("more_damage", 1.0),
            # Cast/Attack speed
            "attack_speed_+%": ("increased_cast_speed", 1.0),
            "cast_speed_+%": ("increased_cast_speed", 1.0),
            "reload_speed_+%": ("increased_cast_speed", 0.5),  # Partial effect on overall speed
            # Area of Effect
            "base_skill_area_of_effect_+%": ("more_aoe", 1.0),
            # Critical
            "critical_strike_chance_+%": ("increased_crit_chance", 1.0),
            "support_inevitable_criticals_critical_strike_chance_+%_per_second": (
                "increased_crit_chance",
                1.0,
            ),
            # Utility effects (flagged, not numeric)
            "support_chain_hit_count_+": ("utility_effects", "chain"),
            "support_fork_forked_projectiles_add": ("utility_effects", "fork"),
            "support_pierce_pierce_chance_%": ("utility_effects", "pierce"),
            "support_conduction_chance_to_shock_+%_final": ("utility_effects", "shock"),
            "support_hypothermia_hit_damage_freeze_multiplier_+%_final": (
                "utility_effects",
                "freeze",
            ),
        }

        for mod in modifiers:
            if not isinstance(mod, (list, tuple)) or len(mod) < 2:
                continue

            stat_id, value = mod[0], mod[1]

            # Check direct mapping
            if stat_id in stat_mapping:
                field, multiplier = stat_mapping[stat_id]
                if field == "utility_effects":
                    stats["utility_effects"].append(multiplier)
                else:
                    stats[field] += float(value) * multiplier

            # Check for generic patterns
            elif "_damage_+%_final" in stat_id:
                if value < 0:
                    stats["less_damage"] += abs(float(value))
                else:
                    stats["more_damage"] += float(value)
            elif "_damage_+%" in stat_id and "_final" not in stat_id:
                stats["increased_damage"] += float(value)
            elif "attack_speed" in stat_id or "cast_speed" in stat_id:
                stats["increased_cast_speed"] += float(value)

        return stats

    def _get_base_gem_name(self, gem_name: str) -> str:
        """
        Get base gem name without tier suffix.

        Args:
            gem_name: Full gem name like "Rapid Attacks III"

        Returns:
            Base name like "Rapid Attacks"
        """
        # Remove Roman numeral suffixes
        import re

        return re.sub(r"\s+[IVX]+$", "", gem_name).strip()

    def _load_pob_complete_skills(self):
        """
        Load PoB complete skills data for enhanced gem information.
        This provides constantStats (conversions, built-in modifiers), damage effectiveness, etc.
        """
        try:
            pob_skills_path = (
                Path(__file__).parent.parent.parent / "data" / "pob_complete_skills.json"
            )
            if not pob_skills_path.exists():
                logger.warning(
                    "pob_complete_skills.json not found, constantStats won't be available"
                )
                return

            with open(pob_skills_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            skills = data.get("skills", {})
            for skill_id, skill_data in skills.items():
                if not isinstance(skill_data, dict):
                    continue

                self._pob_skills[skill_id.lower()] = skill_data
                # Also index by name for easier lookup
                skill_name = skill_data.get("name", "")
                if skill_name:
                    self._pob_skills[skill_name.lower()] = skill_data

            logger.info(
                f"Loaded {len(skills)} skills from PoB complete skills (with constantStats)"
            )

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
        stat_sets = skill_data.get("statSets", [])
        if not stat_sets:
            return []

        primary_stat_set = stat_sets[0] if isinstance(stat_sets, list) else stat_sets
        if not isinstance(primary_stat_set, dict):
            return []

        const_stats = primary_stat_set.get("constantStats", [])
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
            return {"base": 100.0, "incremental": 0.0}

        # Extract from statSets
        stat_sets = skill_data.get("statSets", [])
        if not stat_sets:
            return {"base": 100.0, "incremental": 0.0}

        primary_stat_set = stat_sets[0] if isinstance(stat_sets, list) else stat_sets
        if not isinstance(primary_stat_set, dict):
            return {"base": 100.0, "incremental": 0.0}

        return {
            "base": primary_stat_set.get("baseEffectiveness", 100.0),
            "incremental": primary_stat_set.get("incrementalEffectiveness", 0.0),
        }

    def _load_spell_database(self, path: Path):
        """Load spell gems from JSON database"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Parse spell gems by category
            for category, spells in data.items():
                if category == "metadata":
                    continue

                for spell_id, spell_data in spells.items():
                    # Use level 20 stats if available, otherwise level 1
                    stats = spell_data.get("level_20", spell_data.get("level_1", {}))

                    self.spell_gems[spell_id] = GemStats(
                        name=spell_data.get("name", spell_id),
                        tags=spell_data.get("tags", []),
                        base_damage_min=stats.get("damage_min", 0) or 0,
                        base_damage_max=stats.get("damage_max", 0) or 0,
                        cast_time=stats.get("cast_time", 1.0) or 1.0,
                        crit_chance=stats.get("crit_chance", 0.0) or 0.0,
                        damage_effectiveness=stats.get("damage_effectiveness", 100) or 100,
                        mana_cost=stats.get("mana_cost", 0) or 0,
                    )

            logger.info(f"Loaded {len(self.spell_gems)} spells from {path}")

        except Exception as e:
            logger.error(f"Failed to load spell database from {path}: {e}", exc_info=True)

    def _load_support_database(self, path: Path):
        """Load support gems from JSON database"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Parse support gems from "support_gems" key
            supports = data.get("support_gems", {})

            for support_id, support_data in supports.items():
                # Skip if not a dictionary
                if not isinstance(support_data, dict):
                    continue

                # Parse effects
                effects = support_data.get("effects", {})

                # Determine which tags this support needs (compatible_with)
                compatible_with = support_data.get("compatible_with", [])

                self.support_gems[support_id] = SupportGemEffect(
                    name=support_data.get("name", support_id),
                    tags=support_data.get("tags", []),
                    more_damage=effects.get("more_spell_damage", effects.get("more_damage", 0.0)),
                    more_cast_speed=effects.get("more_cast_speed", 0.0),
                    more_aoe=effects.get("more_area", 0.0),
                    more_crit_chance=effects.get("more_crit_chance", 0.0),
                    more_crit_damage=effects.get("more_crit_damage", 0.0),
                    less_damage=effects.get("less_spell_damage", effects.get("less_damage", 0.0)),
                    less_cast_speed=effects.get("less_cast_speed", 0.0),
                    increased_damage=effects.get(
                        "increased_spell_damage", effects.get("increased_damage", 0.0)
                    ),
                    increased_cast_speed=effects.get("increased_cast_speed", 0.0),
                    increased_crit_chance=effects.get("increased_crit_chance", 0.0),
                    spirit_cost=support_data.get("spirit_cost", 0) or 0,
                    mana_cost_multiplier=support_data.get("cost_multiplier", 100.0) or 100.0,
                    utility_effects=[],  # Would need to parse from effects
                    required_tags=compatible_with,
                    incompatible_with=[],
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
        return_trace: bool = False,
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
            "optimization_goal": optimization_goal,
        }

        # Get spell (key, display-name alias, or name scan)
        spell = self._get_spell(spell_name)
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
            logger.warning(
                f"Only {len(compatible_supports)} compatible supports found (need {num_supports})"
            )
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
                spell, list(support_combo), character_mods, max_spirit
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
                        logger.warning(
                            f"Rejecting {support_id} + {incompatible} (database incompatibility)"
                        )
                        return False

        # Hardcoded incompatibilities — match on normalized id AND display
        # name so internal-id keys ("supportprojectileaccelerationplayer")
        # and display names ("Projectile Acceleration Support") both trip
        # the same rule.
        for i, (id_a, sup_a) in enumerate(support_combo):
            conflict_set = _NORMALIZED_INCOMPATIBILITIES.get(
                _normalize_gem_name(id_a), set()
            ) | _NORMALIZED_INCOMPATIBILITIES.get(_normalize_gem_name(sup_a.name), set())
            if not conflict_set:
                continue
            for id_b, sup_b in support_combo[i + 1 :]:
                if {_normalize_gem_name(id_b), _normalize_gem_name(sup_b.name)} & conflict_set:
                    logger.warning(
                        f"Rejecting {sup_a.name} + {sup_b.name} (hardcoded incompatibility)"
                    )
                    return False

        return True

    def validate_combination(
        self,
        support_names: List[str],
        spell_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Validate if a combination of support gems is valid.

        Hard conflicts (returned as `valid=False`):
            * Two supports that modify the same stat in opposite directions
              (Projectile Acceleration + Deceleration, Concentrated Effect +
              Increased AoE) — see HARDCODED_INCOMPATIBILITIES.

        Soft conflicts (returned as `warnings`, `valid` stays True):
            * Damage-type / skill-tag mismatch detected when `spell_name` is
              supplied. Example: "Added Fire Damage Support" recommended on
              "Ice Nova" (cold spell, no fire/attack tag). Surfaced via
              SUPPORT_DAMAGE_REQUIREMENTS, name-pattern-inferred (the canonical
              support_gems extraction lacks per-gem damage-type metadata —
              see the dict's docstring above).

        Args:
            support_names: List of support gem names (display names).
            spell_name: Optional target spell. When supplied, the spell's tags
                are read from data/game/skill_gems/skill_gems.json and used
                to detect semantic conflicts.

        Returns:
            {
                "valid": bool,         # False only on hard conflicts
                "reason": str,
                "conflicts": List[Tuple[str, str]],
                "warnings": List[Dict[str, Any]],  # one entry per semantic conflict
                "spell_tags": List[str] | None,    # tags resolved from spell_name
            }
        """
        conflicts = []
        warnings: List[Dict[str, Any]] = []
        spell_tags: Optional[List[str]] = None

        # --- Hard conflict check. Names normalized (case, underscores,
        #     " Support" suffix) before matching so callers can pass either
        #     "Concentrated Effect" or "Concentrated Effect Support".
        for i, support_a in enumerate(support_names):
            conflict_set = _NORMALIZED_INCOMPATIBILITIES.get(_normalize_gem_name(support_a), set())
            if not conflict_set:
                continue
            for support_b in support_names[i + 1 :]:
                if _normalize_gem_name(support_b) in conflict_set:
                    conflicts.append((support_a, support_b))

        # --- Semantic-conflict check (new — #117). Delegated to the light
        #     sibling module so unit tests don't drag SQLAlchemy.
        sem = check_semantic_conflicts(support_names, spell_name=spell_name)
        warnings.extend(sem["warnings"])
        spell_tags = sem["spell_tags"]

        if conflicts:
            conflict_pairs = [f"{a} + {b}" for a, b in conflicts]
            return {
                "valid": False,
                "reason": f"Incompatible support combinations detected: {', '.join(conflict_pairs)}",
                "conflicts": conflicts,
                "warnings": warnings,
                "spell_tags": spell_tags,
            }

        if warnings:
            return {
                "valid": True,
                "reason": (
                    f"All supports pass hard compatibility checks. "
                    f"{len(warnings)} semantic warning(s) — see `warnings`."
                ),
                "conflicts": [],
                "warnings": warnings,
                "spell_tags": spell_tags,
            }

        return {
            "valid": True,
            "reason": "All supports are compatible",
            "conflicts": [],
            "warnings": [],
            "spell_tags": spell_tags,
        }

    # Backward-compat thin wrappers — implementation now lives in
    # src/optimizer/support_validation.py so it can be unit-tested without
    # SQLAlchemy import cost.
    def _lookup_spell_tags(self, spell_name: str) -> Optional[List[str]]:
        return lookup_spell_tags(spell_name)

    @staticmethod
    def _support_required_tags(support_name: str) -> List[str]:
        return support_required_tags(support_name)

    def trace_dps_calculation(
        self,
        spell_name: str,
        support_names: List[str],
        character_mods: Optional[Dict[str, float]] = None,
        max_spirit: int = 100,
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
            "errors": [],
        }

        # Get spell (key, display-name alias, or name scan)
        spell = self._get_spell(spell_name)
        if not spell:
            trace["valid"] = False
            trace["errors"].append(f"Spell '{spell_name}' not found")
            return trace

        trace["spell"] = {
            "name": spell.name,
            "base_damage_min": spell.base_damage_min,
            "base_damage_max": spell.base_damage_max,
            "cast_time": spell.cast_time,
        }

        # Get supports (key, display-name alias, or name scan — suffix tolerant)
        support_objs = []
        for sup_name in support_names:
            resolved = self._get_support(sup_name)
            if resolved:
                sup_id, sup_obj = resolved
                support_objs.append((sup_id, sup_obj))
                trace["supports"].append(
                    {
                        "name": sup_obj.name,
                        "more_damage": sup_obj.more_damage,
                        "less_damage": sup_obj.less_damage,
                        "increased_damage": sup_obj.increased_damage,
                        "spirit_cost": sup_obj.spirit_cost,
                    }
                )
            else:
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
            "overflow": max(0, total_spirit - max_spirit),
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
            more_steps.append(
                {"support_name": sup.name, "net_multiplier": net_more, "cumulative": more_total}
            )

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
        max_spirit: int,
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
        total_increased_damage = character_mods.get("increased_damage", 0.0)
        total_more_cast_speed = 1.0
        total_increased_cast_speed = character_mods.get("increased_cast_speed", 0.0)
        total_added_damage = 0.0
        utility_effects = []
        total_mana_cost = spell.mana_cost

        # Apply each support's effects
        for support_id, support in supports:
            # More multipliers (multiplicative)
            if support.more_damage != 0:
                total_more_damage *= 1.0 + support.more_damage / 100.0

            if support.more_cast_speed != 0:
                total_more_cast_speed *= 1.0 + support.more_cast_speed / 100.0

            # Less multipliers (multiplicative penalties)
            if support.less_damage != 0:
                total_more_damage *= 1.0 - support.less_damage / 100.0

            if support.less_cast_speed != 0:
                total_more_cast_speed *= 1.0 - support.less_cast_speed / 100.0

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
            total_mana_cost *= support.mana_cost_multiplier / 100.0

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
                "base_damage": base_damage_avg,
                "added_damage": total_added_damage,
                "after_increased": damage_after_increased,
                "after_more": final_damage,
                "more_multiplier": total_more_damage,
                "increased_total": total_increased_damage,
                "cast_speed_multiplier": total_more_cast_speed,
                "spirit_per_support": [s[1].spirit_cost for s in supports],
            },
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
                result.dps_score * 0.6
                + result.efficiency_score * 10.0  # Scale up efficiency
                + utility_score * 0.1
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
    spell_name: str, max_spirit: int = 100, num_supports: int = 5, goal: str = "dps"
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
        top_n=10,
    )


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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
        spell_name="fireball", max_spirit=100, num_supports=5, goal="dps"
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
