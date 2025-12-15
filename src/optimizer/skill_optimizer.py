"""Skill setup optimization with fresh game data integration"""

import logging
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from sqlalchemy import text

try:
    from ..config import DATA_DIR
    from ..data.fresh_data_provider import get_fresh_data_provider
except ImportError:
    from src.config import DATA_DIR
    from src.data.fresh_data_provider import get_fresh_data_provider

logger = logging.getLogger(__name__)


class SkillOptimizer:
    """Optimizes skill gem setups using fresh game data and PoB complete skill data"""

    def __init__(self, db_manager) -> None:
        self.db_manager = db_manager
        self._support_gems_cache = None
        self._spell_gems_cache = None
        self._pob_skills_cache = None
        self._fresh_provider = get_fresh_data_provider()

    async def _load_support_gems(self) -> Dict[str, Any]:
        """Load support gems from JSON database (scraped data)"""
        if self._support_gems_cache is not None:
            return self._support_gems_cache

        try:
            support_gems_path = DATA_DIR / "poe2_support_gems_database.json"
            with open(support_gems_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._support_gems_cache = data.get("support_gems", {})
                return self._support_gems_cache
        except Exception as e:
            logger.error(f"Failed to load support gems database: {e}")
            return {}

    def _load_pob_skills(self) -> Dict[str, Any]:
        """Load skill data from pob_complete_skills.json"""
        if self._pob_skills_cache is not None:
            return self._pob_skills_cache

        try:
            pob_skills_path = DATA_DIR / "pob_complete_skills.json"
            with open(pob_skills_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._pob_skills_cache = data.get("skills", {})
                return self._pob_skills_cache
        except Exception as e:
            logger.error(f"Failed to load PoB skills database: {e}")
            return {}

    def _get_skill_from_fresh_data(self, skill_name: str) -> Dict[str, Any]:
        """Get skill data from FreshDataProvider (no database query needed)."""
        # Try exact match first
        skill = self._fresh_provider.get_active_skill(skill_name)
        if skill:
            return skill

        # Normalize search term: convert CamelCase to snake_case and lowercase
        import re
        normalized = re.sub(r'([A-Z])', r'_\1', skill_name).lower().strip('_')
        normalized_no_underscore = skill_name.lower().replace('_', '').replace(' ', '')

        # Try case-insensitive search
        all_skills = self._fresh_provider.get_all_active_skills()
        for skill_id, skill_data in all_skills.items():
            skill_id_normalized = skill_id.lower().replace('_', '')
            skill_name_normalized = skill_data.get('name', '').lower().replace(' ', '')

            # Match by normalized ID or name
            if (normalized_no_underscore in skill_id_normalized or
                normalized_no_underscore in skill_name_normalized or
                skill_name.lower() in skill_data.get('name', '').lower()):
                return skill_data

        return {}

    def _get_skill_from_pob(self, skill_name: str, gem_level: int = 20) -> Dict[str, Any]:
        """
        Get skill data from pob_complete_skills.json with per-level stats.

        Returns enriched skill data including:
        - Per-level stats (mana cost, base multiplier, crit chance, etc.)
        - StatSets with damage effectiveness and constantStats
        - Quality stats
        """
        pob_skills = self._load_pob_skills()

        # First pass: try exact matches
        for skill_id, skill_data in pob_skills.items():
            if not isinstance(skill_data, dict):
                continue

            skill_data_name = skill_data.get('name', '')
            if skill_data_name.lower() == skill_name.lower() or skill_id.lower() == skill_name.lower():
                # Exact match found
                levels = skill_data.get('levels', {})
                level_key = str(gem_level)
                level_data = levels.get(level_key, levels.get('1', {}))

                return {
                    'id': skill_id,
                    'name': skill_data.get('name', skill_name),
                    'description': skill_data.get('description', ''),
                    'skill_types': skill_data.get('skillTypes', []),
                    'weapon_types': skill_data.get('weaponTypes', []),
                    'cast_time': skill_data.get('castTime', 1.0),
                    'level_data': level_data,
                    'stat_sets': skill_data.get('statSets', []),
                    'quality_stats': skill_data.get('qualityStats', []),
                    'full_skill_data': skill_data  # Include full data for advanced processing
                }

        # Second pass: partial matches (only if no exact match found)
        for skill_id, skill_data in pob_skills.items():
            if not isinstance(skill_data, dict):
                continue

            skill_data_name = skill_data.get('name', '')
            if skill_name.lower() in skill_data_name.lower():
                # Partial match found
                levels = skill_data.get('levels', {})
                level_key = str(gem_level)
                level_data = levels.get(level_key, levels.get('1', {}))

                return {
                    'id': skill_id,
                    'name': skill_data.get('name', skill_name),
                    'description': skill_data.get('description', ''),
                    'skill_types': skill_data.get('skillTypes', []),
                    'weapon_types': skill_data.get('weaponTypes', []),
                    'cast_time': skill_data.get('castTime', 1.0),
                    'level_data': level_data,
                    'stat_sets': skill_data.get('statSets', []),
                    'quality_stats': skill_data.get('qualityStats', []),
                    'full_skill_data': skill_data  # Include full data for advanced processing
                }

        return {}

    async def _get_skill_from_datc64(self, skill_name: str) -> Dict[str, Any]:
        """
        Query activeskills - now uses PoB complete skills first, then FreshDataProvider.
        Returns enriched skill data with per-level stats when available.
        """
        # Priority 1: Try PoB complete skills (has full per-level data)
        pob_skill = self._get_skill_from_pob(skill_name)
        if pob_skill:
            logger.info(f"Found skill '{skill_name}' in PoB complete skills database")
            return pob_skill

        # Priority 2: Try fresh data provider (datc64 extraction)
        result = self._get_skill_from_fresh_data(skill_name)
        if result:
            logger.info(f"Found skill '{skill_name}' in FreshDataProvider")
            return result

        # Fallback to database query
        logger.info(f"Falling back to database query for skill '{skill_name}'")
        async with self.db_manager.async_session() as session:
            datc64_db_path = DATA_DIR / "poe2_datc64.db"
            await session.execute(text(f"ATTACH DATABASE '{datc64_db_path}' AS datc64"))

            try:
                # Search activeskills for the skill
                query = text("""
                    SELECT data FROM datc64.activeskills
                    WHERE json_extract(data, '$.DisplayedName') LIKE :name
                       OR json_extract(data, '$.Id') LIKE :name
                    LIMIT 1
                """)
                result = await session.execute(query, {"name": f"%{skill_name}%"})
                row = result.fetchone()

                if row:
                    return json.loads(row[0])
                return {}

            finally:
                await session.execute(text("DETACH DATABASE datc64"))

    async def optimize(
        self,
        character_data: Dict[str, Any],
        goal: str = "balanced"
    ) -> Dict[str, Any]:
        """
        Generate skill setup recommendations using PoB complete skills data with per-level stats.

        Args:
            character_data: Character data including active skills and gem level
            goal: Optimization goal (balanced, dps, defense)

        Returns:
            Skill setup recommendations with compatible support gems and per-level stats
        """
        try:
            # Extract main skill from character data
            main_skill = character_data.get("main_skill", "")
            gem_level = character_data.get("gem_level", 20)  # Default to level 20
            if not main_skill:
                # Try to infer from skills list
                skills = character_data.get("skills", [])
                if skills:
                    main_skill = skills[0] if isinstance(skills, list) else str(skills)

            # Load support gems database
            support_gems = await self._load_support_gems()

            # Get skill metadata (now with per-level stats from PoB)
            skill_data = await self._get_skill_from_datc64(main_skill) if main_skill else {}

            # Determine skill type - handle both old and new data formats
            skill_type = self._classify_skill(skill_data, main_skill)

            # Find compatible supports based on skill type and goal
            recommended_supports = self._find_compatible_supports(
                skill_type, support_gems, goal
            )

            # Extract per-level data if available (from PoB)
            level_data = skill_data.get('level_data', {})
            stat_sets = skill_data.get('stat_sets', [])

            # Build response
            response = {
                "skill_analyzed": skill_data.get("name", skill_data.get("DisplayedName", main_skill)),
                "skill_id": skill_data.get("id", skill_data.get("Id", "")),
                "skill_description": skill_data.get("description", skill_data.get("Description", "")),
                "skill_type": skill_type,
                "suggested_setups": [{
                    "skill_name": skill_data.get("name", skill_data.get("DisplayedName", main_skill)),
                    "supports": recommended_supports[:5],  # PoE2 max 5 support gems per skill
                    "priority": "high",
                    "reasoning": f"Optimized for {goal} with {skill_type} skill"
                }],
                "data_source": "PoB Complete Skills (with per-level stats) + Fresh game data extraction"
            }

            # Add per-level stats if available
            if level_data:
                response["level_stats"] = {
                    "gem_level": gem_level,
                    "mana_cost": level_data.get('cost', {}).get('Mana', 0),
                    "base_multiplier": level_data.get('baseMultiplier', 0),
                    "crit_chance": level_data.get('critChance'),
                    "cooldown": level_data.get('cooldown'),
                    "cast_time": skill_data.get('cast_time', 1.0)
                }

            # Add damage effectiveness from statSets if available
            if stat_sets:
                primary_stat_set = stat_sets[0] if isinstance(stat_sets, list) else stat_sets
                if isinstance(primary_stat_set, dict):
                    response["damage_effectiveness"] = {
                        "base": primary_stat_set.get('baseEffectiveness', 0),
                        "incremental": primary_stat_set.get('incrementalEffectiveness', 0)
                    }

            return response

        except Exception as e:
            logger.error(f"Skill optimization failed: {e}")
            return {
                "error": str(e),
                "suggested_setups": []
            }

    def _classify_skill(self, skill_data: Dict[str, Any], skill_name: str) -> str:
        """
        Classify skill as attack, spell, etc. from both PoB and datc64 data formats.
        Handles both old format (DisplayedName, Description) and new format (name, skill_types).
        """
        if not skill_data:
            # Fallback heuristics
            if any(word in skill_name.lower() for word in ["strike", "slam", "shot", "arrow"]):
                return "attack"
            return "spell"

        # New format (PoB) - use skill_types directly
        skill_types = skill_data.get("skill_types", [])
        if skill_types:
            skill_types_lower = [st.lower() for st in skill_types]

            # Check for attack types
            if any(t in skill_types_lower for t in ["attack", "melee", "rangedattack", "bow", "crossbow"]):
                return "attack"
            # Check for spell types
            elif any(t in skill_types_lower for t in ["spell", "cast", "totem"]):
                return "spell"
            # Check for minion types
            elif any(t in skill_types_lower for t in ["minion", "summon", "createsminion"]):
                return "minion"
            # Check for aura/buff types
            elif any(t in skill_types_lower for t in ["aura", "buff", "herald"]):
                return "aura"
            # Check for warcry
            elif "warcry" in skill_types_lower:
                return "warcry"

        # Old format (datc64) - use description analysis
        description = skill_data.get("description", skill_data.get("Description", "")).lower()
        displayed_name = skill_data.get("name", skill_data.get("DisplayedName", "")).lower()

        # Check description for attack keywords first (more specific)
        if any(word in description for word in ["attack", "strike", "slam", "swing", "weapon", "mace", "sword", "bow", "arrow"]):
            return "attack"
        # Then check for spell keywords
        elif any(word in description for word in ["spell", "cast", "conjure", "channel", "projectile"]):
            # But exclude attack projectiles
            if any(word in description for word in ["bow", "arrow", "shot"]):
                return "attack"
            return "spell"
        # Minion skills
        elif any(word in description for word in ["minion", "summon", "raise", "animate"]):
            return "minion"
        # Aura/buff skills
        elif any(word in description for word in ["aura", "buff", "reserve"]):
            return "aura"
        else:
            # Default based on name
            if any(word in displayed_name for word in ["slam", "strike", "swing", "smash"]):
                return "attack"
            return "spell"

    def _find_compatible_supports(
        self,
        skill_type: str,
        support_gems: Dict[str, Any],
        goal: str
    ) -> List[str]:
        """Find compatible support gems based on skill type and goal"""
        compatible = []

        for gem_id, gem_data in support_gems.items():
            compatible_with = gem_data.get("compatible_with", [])

            # Check if support is compatible with skill type
            if skill_type in compatible_with or "all" in compatible_with:
                gem_name = gem_data.get("name", gem_id)

                # Prioritize based on goal
                if goal == "dps":
                    # Prefer damage multipliers
                    if any(key in gem_data.get("effects", {}) for key in [
                        "more_spell_damage", "more_attack_damage", "more_damage"
                    ]):
                        compatible.insert(0, gem_name)
                    else:
                        compatible.append(gem_name)
                else:
                    compatible.append(gem_name)

        # Return top recommendations
        return compatible[:10]
