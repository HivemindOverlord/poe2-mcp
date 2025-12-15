"""
FRESH DATA PROVIDER - Single Source of Truth
Provides game data directly from .datc64 files - NO PoB dependency.
December 12, 2025 - Full independence implementation.
"""

import struct
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

# Data paths
BASE_DIR = Path(__file__).parent.parent.parent
EXTRACTED_DATA_PATH = BASE_DIR / 'data' / 'extracted' / 'data'
CACHE_PATH = BASE_DIR / 'data' / 'fresh_gamedata'
COMPLETE_MODELS_PATH = BASE_DIR / 'data' / 'complete_models'


class Datc64Parser:
    """Parser for .datc64 binary files with corrected pointer handling."""

    POINTER_CORRECTION = 8  # All string pointers need -8 adjustment

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.content = filepath.read_bytes()
        self.row_count = struct.unpack('<I', self.content[:4])[0]

        bbbb = self.content.find(b'\xbb\xbb\xbb\xbb\xbb\xbb\xbb\xbb')
        self.bbbb_pos = bbbb
        self.row_size = (bbbb - 4) // self.row_count if self.row_count > 0 else 0
        self.data_section = self.content[bbbb + 8:] if bbbb > 0 else b''

    def read_string(self, raw_ptr: int) -> str:
        """Read UTF-16LE string from data section with pointer correction."""
        corrected = raw_ptr - self.POINTER_CORRECTION
        if corrected < 0 or corrected >= len(self.data_section):
            return ''

        end = corrected
        while end < len(self.data_section) - 1:
            if self.data_section[end] == 0 and self.data_section[end+1] == 0:
                break
            end += 2

        if end > corrected:
            try:
                return self.data_section[corrected:end].decode('utf-16-le', errors='ignore')
            except:
                pass
        return ''

    def read_row(self, row_idx: int) -> bytes:
        """Get raw bytes for a row."""
        if row_idx >= self.row_count:
            return b''
        offset = 4 + (row_idx * self.row_size)
        return self.content[offset:offset + self.row_size]

    def read_int32(self, row: bytes, offset: int) -> int:
        if offset + 4 > len(row):
            return 0
        return struct.unpack('<i', row[offset:offset+4])[0]

    def read_int64(self, row: bytes, offset: int) -> int:
        if offset + 8 > len(row):
            return 0
        return struct.unpack('<Q', row[offset:offset+8])[0]

    def read_float(self, row: bytes, offset: int) -> float:
        if offset + 4 > len(row):
            return 0.0
        return struct.unpack('<f', row[offset:offset+4])[0]


class FreshDataProvider:
    """
    Provides game data from fresh .datc64 extractions.
    Single Source of Truth - replaces all PoB JSON dependencies.
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._passive_skills: Dict[int, Dict] = {}
        self._passive_by_id: Dict[str, Dict] = {}
        self._passive_by_name: Dict[str, Dict] = {}
        self._support_gems: Dict[str, Dict] = {}
        self._active_skills: Dict[str, Dict] = {}
        self._granted_effects: Dict[str, Dict] = {}
        self._stats: Dict[int, str] = {}
        self._base_items: Dict[str, Dict] = {}

        self._load_all_data()

    def _load_all_data(self):
        """Load all game data from fresh extractions."""
        logger.info("Loading fresh game data...")

        # Priority 1: Try to load from complete models (most detailed)
        if self._load_from_complete_models():
            logger.info("Loaded from complete_models successfully")
            return

        # Priority 2: Try to load from fresh_gamedata cache
        if self._load_from_cache():
            logger.info("Loaded from cache successfully")
            return

        # Priority 3: Extract from raw files
        self._extract_passive_skills()
        self._extract_support_gems()
        self._extract_active_skills()
        self._extract_granted_effects()
        self._extract_stats()
        self._extract_base_items()

        # Save to cache
        self._save_to_cache()
        logger.info("Fresh data extraction complete")

    def _load_from_complete_models(self) -> bool:
        """Load from complete_models directory (best quality data)."""
        try:
            model_files = [
                COMPLETE_MODELS_PATH / 'active_skills.json',
                COMPLETE_MODELS_PATH / 'support_gems.json',
                COMPLETE_MODELS_PATH / 'passive_tree.json',
                COMPLETE_MODELS_PATH / 'stats.json',
            ]

            # Check all required files exist
            for mf in model_files:
                if not mf.exists():
                    logger.debug(f"Complete model file not found: {mf}")
                    return False

            # Load active skills
            with open(COMPLETE_MODELS_PATH / 'active_skills.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                for skill_id, skill_data in data.get('active_skills', {}).items():
                    self._active_skills[skill_id] = skill_data
                    # Also add to granted_effects for compatibility
                    self._granted_effects[skill_id] = skill_data

            # Load support gems (with inferred effects)
            with open(COMPLETE_MODELS_PATH / 'support_gems.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                for gem_id, gem_data in data.get('support_gems', {}).items():
                    self._support_gems[gem_id] = gem_data

            # Load passive tree
            with open(COMPLETE_MODELS_PATH / 'passive_tree.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                for node_id, node_data in data.get('nodes', {}).items():
                    row_idx = node_data.get('row_index', 0)
                    self._passive_skills[row_idx] = node_data
                    self._passive_by_id[node_id] = node_data
                    name = node_data.get('display_name', '')
                    if name:
                        self._passive_by_name[name] = node_data

            # Load stats
            with open(COMPLETE_MODELS_PATH / 'stats.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                stats_data = data.get('stats', data)  # Handle both formats
                for stat_id, stat_name in stats_data.items():
                    try:
                        self._stats[int(stat_id)] = stat_name
                    except ValueError:
                        pass

            logger.info(f"Loaded complete models: {len(self._active_skills)} active skills, "
                       f"{len(self._support_gems)} support gems, {len(self._passive_skills)} passives")
            return True

        except Exception as e:
            logger.warning(f"Failed to load from complete_models: {e}")
            return False

    def _load_from_cache(self) -> bool:
        """Try to load from JSON cache."""
        try:
            cache_files = [
                (CACHE_PATH / 'passive_skills.json', '_passive_skills'),
                (CACHE_PATH / 'support_gems_fresh.json', '_support_gems'),  # Fresh extraction
                (CACHE_PATH / 'active_skills.json', '_active_skills'),
                (CACHE_PATH / 'granted_effects.json', '_granted_effects'),
                (CACHE_PATH / 'stats.json', '_stats'),
                (CACHE_PATH / 'base_items.json', '_base_items'),
            ]

            for cache_file, attr in cache_files:
                if not cache_file.exists():
                    return False

            # Load passive skills
            with open(CACHE_PATH / 'passive_skills.json', 'r', encoding='utf-8') as f:
                passives = json.load(f)
                for p in passives:
                    self._passive_skills[p['row_index']] = p
                    self._passive_by_id[p['id']] = p
                    if p.get('name'):
                        self._passive_by_name[p['name']] = p

            # Load support gems (fresh extraction format)
            with open(CACHE_PATH / 'support_gems_fresh.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Handle both old list format and new dict format
                if isinstance(data, dict) and 'support_gems' in data:
                    # New format: {metadata: {...}, support_gems: {id: {...}}}
                    for gem_id, gem_data in data['support_gems'].items():
                        self._support_gems[gem_id] = gem_data
                elif isinstance(data, list):
                    # Old format: [{...}, {...}]
                    for s in data:
                        self._support_gems[s['id']] = s

            # Load active skills
            with open(CACHE_PATH / 'active_skills.json', 'r', encoding='utf-8') as f:
                skills = json.load(f)
                for s in skills:
                    self._active_skills[s['id']] = s

            # Load granted effects
            with open(CACHE_PATH / 'granted_effects.json', 'r', encoding='utf-8') as f:
                effects = json.load(f)
                for e in effects:
                    self._granted_effects[e['id']] = e

            # Load stats
            with open(CACHE_PATH / 'stats.json', 'r', encoding='utf-8') as f:
                self._stats = {int(k): v for k, v in json.load(f).items()}

            # Load base items
            with open(CACHE_PATH / 'base_items.json', 'r', encoding='utf-8') as f:
                items = json.load(f)
                for i in items:
                    self._base_items[i['id']] = i

            return True
        except Exception as e:
            logger.warning(f"Failed to load from cache: {e}")
            return False

    def _save_to_cache(self):
        """Save extracted data to JSON cache."""
        CACHE_PATH.mkdir(parents=True, exist_ok=True)

        with open(CACHE_PATH / 'passive_skills.json', 'w', encoding='utf-8') as f:
            json.dump(list(self._passive_skills.values()), f, indent=2, ensure_ascii=False)

        # Other files are saved during extraction

    def _extract_passive_skills(self):
        """Extract passive skills from passiveskills.datc64."""
        filepath = EXTRACTED_DATA_PATH / 'passiveskills.datc64'
        if not filepath.exists():
            logger.error(f"File not found: {filepath}")
            return

        parser = Datc64Parser(filepath)
        logger.info(f"Parsing passiveskills: {parser.row_count} rows")

        for i in range(parser.row_count):
            row = parser.read_row(i)

            id_ptr = parser.read_int64(row, 0)
            name_ptr = parser.read_int64(row, 50)

            skill_id = parser.read_string(id_ptr)
            name = parser.read_string(name_ptr)

            is_keystone = row[74] == 1 if len(row) > 74 else False
            is_notable = row[75] == 1 if len(row) > 75 else False

            if not skill_id:
                continue

            passive = {
                'row_index': i,
                'id': skill_id,
                'name': name if name else skill_id,
                'is_keystone': is_keystone,
                'is_notable': is_notable,
            }

            self._passive_skills[i] = passive
            self._passive_by_id[skill_id] = passive
            if name:
                self._passive_by_name[name] = passive

    def _extract_support_gems(self):
        """Extract support gems from grantedeffects.datc64."""
        filepath = EXTRACTED_DATA_PATH / 'grantedeffects.datc64'
        if not filepath.exists():
            logger.error(f"File not found: {filepath}")
            return

        parser = Datc64Parser(filepath)

        for i in range(parser.row_count):
            row = parser.read_row(i)

            id_ptr = parser.read_int64(row, 0)
            skill_id = parser.read_string(id_ptr)

            is_support = row[8] == 1 if len(row) > 8 else False
            cast_time = parser.read_int32(row, 75) if len(row) > 79 else 0

            if is_support and skill_id and not skill_id.startswith('Art/'):
                name = skill_id.replace('Support', ' Support').replace('Player', '').strip()
                name = name.replace('  ', ' ')

                self._support_gems[skill_id] = {
                    'row_index': i,
                    'id': skill_id,
                    'name': name,
                    'cast_time_ms': cast_time if 0 < cast_time < 10000 else None,
                    'is_support': True,
                }

    def _extract_active_skills(self):
        """Extract active skills from activeskills.datc64."""
        filepath = EXTRACTED_DATA_PATH / 'activeskills.datc64'
        if not filepath.exists():
            return

        parser = Datc64Parser(filepath)

        for i in range(parser.row_count):
            row = parser.read_row(i)

            id_ptr = parser.read_int64(row, 0)
            name_ptr = parser.read_int64(row, 8)

            skill_id = parser.read_string(id_ptr)
            name = parser.read_string(name_ptr)

            if skill_id:
                self._active_skills[skill_id] = {
                    'row_index': i,
                    'id': skill_id,
                    'name': name if name else skill_id,
                }

    def _extract_granted_effects(self):
        """Extract granted effects from grantedeffects.datc64."""
        filepath = EXTRACTED_DATA_PATH / 'grantedeffects.datc64'
        if not filepath.exists():
            return

        parser = Datc64Parser(filepath)

        for i in range(parser.row_count):
            row = parser.read_row(i)

            id_ptr = parser.read_int64(row, 0)
            skill_id = parser.read_string(id_ptr)

            is_support = row[8] == 1 if len(row) > 8 else False
            cast_time = parser.read_int32(row, 75) if len(row) > 79 else 0

            if skill_id:
                self._granted_effects[skill_id] = {
                    'row_index': i,
                    'id': skill_id,
                    'is_support': is_support,
                    'cast_time_ms': cast_time if 0 < cast_time < 10000 else None,
                }

    def _extract_stats(self):
        """Extract stat definitions from stats.datc64."""
        filepath = EXTRACTED_DATA_PATH / 'stats.datc64'
        if not filepath.exists():
            return

        parser = Datc64Parser(filepath)

        for i in range(parser.row_count):
            row = parser.read_row(i)
            id_ptr = parser.read_int64(row, 0)
            stat_id = parser.read_string(id_ptr)
            if stat_id:
                self._stats[i] = stat_id

    def _extract_base_items(self):
        """Extract base item types from baseitemtypes.datc64."""
        filepath = EXTRACTED_DATA_PATH / 'baseitemtypes.datc64'
        if not filepath.exists():
            return

        parser = Datc64Parser(filepath)

        for i in range(parser.row_count):
            row = parser.read_row(i)
            id_ptr = parser.read_int64(row, 0)
            name_ptr = parser.read_int64(row, 8)

            item_id = parser.read_string(id_ptr)
            name = parser.read_string(name_ptr)

            if item_id:
                self._base_items[item_id] = {
                    'row_index': i,
                    'id': item_id,
                    'name': name if name else item_id,
                }

    # =========================================================================
    # PUBLIC API - These methods replace PoB JSON lookups
    # =========================================================================

    def get_passive_node_name(self, node_id: int) -> str:
        """Get passive node display name by row index."""
        if node_id in self._passive_skills:
            return self._passive_skills[node_id].get('name', f'Node_{node_id}')
        return f'Node_{node_id}'

    def get_passive_by_id(self, skill_id: str) -> Optional[Dict]:
        """Get passive node data by skill ID string."""
        return self._passive_by_id.get(skill_id)

    def get_passive_by_name(self, name: str) -> Optional[Dict]:
        """Get passive node data by display name."""
        return self._passive_by_name.get(name)

    def get_all_passive_nodes(self) -> Dict[int, Dict]:
        """Get all passive nodes indexed by row index."""
        return self._passive_skills.copy()

    def get_keystones(self) -> List[Dict]:
        """Get all keystone passives."""
        keystones = []
        for p in self._passive_skills.values():
            if p.get('is_keystone'):
                # Normalize field names for compatibility
                result = p.copy()
                if 'display_name' in result and 'name' not in result:
                    result['name'] = result['display_name']
                keystones.append(result)
        return keystones

    def get_notables(self) -> List[Dict]:
        """Get all notable passives."""
        notables = []
        for p in self._passive_skills.values():
            if p.get('is_notable'):
                # Normalize field names for compatibility
                result = p.copy()
                if 'display_name' in result and 'name' not in result:
                    result['name'] = result['display_name']
                notables.append(result)
        return notables

    def get_support_gem(self, gem_id: str) -> Optional[Dict]:
        """Get support gem data by ID."""
        return self._support_gems.get(gem_id)

    def get_support_gem_by_name(self, name: str) -> Optional[Dict]:
        """Get support gem data by display name (case-insensitive)."""
        name_lower = name.lower().replace(' support', '').replace('support ', '').strip()
        for gem_id, gem_data in self._support_gems.items():
            gem_name = gem_data.get('name', '').lower()
            # Check exact match
            if gem_name == name_lower or gem_name == name.lower():
                return gem_data
            # Check normalized match (remove common suffixes)
            gem_normalized = gem_name.replace(' player', '').replace('player', '').strip()
            if gem_normalized == name_lower or name_lower in gem_normalized:
                return gem_data
        return None

    def get_all_support_gems(self) -> Dict[str, Dict]:
        """Get all support gems."""
        return self._support_gems.copy()

    def search_support_gems(self, query: str) -> List[Dict]:
        """Search support gems by partial name match."""
        query_lower = query.lower()
        results = []
        for gem_id, gem_data in self._support_gems.items():
            name = gem_data.get('name', '').lower()
            if query_lower in name or query_lower in gem_id.lower():
                results.append(gem_data)
        return results

    def get_active_skill(self, skill_id: str) -> Optional[Dict]:
        """Get active skill data by ID."""
        return self._active_skills.get(skill_id)

    def get_all_active_skills(self) -> Dict[str, Dict]:
        """Get all active skills."""
        return self._active_skills.copy()

    def get_granted_effect(self, effect_id: str) -> Optional[Dict]:
        """Get granted effect data by ID."""
        return self._granted_effects.get(effect_id)

    def get_stat_name(self, stat_id: int) -> str:
        """Get stat name by ID."""
        return self._stats.get(stat_id, f'stat_{stat_id}')

    def get_base_item(self, item_id: str) -> Optional[Dict]:
        """Get base item data by ID."""
        return self._base_items.get(item_id)

    def get_all_base_items(self) -> Dict[str, Dict]:
        """Get all base items."""
        return self._base_items.copy()

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def get_stats_summary(self) -> Dict[str, int]:
        """Get summary of loaded data."""
        return {
            'passive_nodes': len(self._passive_skills),
            'keystones': len(self.get_keystones()),
            'notables': len(self.get_notables()),
            'support_gems': len(self._support_gems),
            'active_skills': len(self._active_skills),
            'granted_effects': len(self._granted_effects),
            'stats': len(self._stats),
            'base_items': len(self._base_items),
        }


# Singleton accessor
def get_fresh_data_provider() -> FreshDataProvider:
    """Get the singleton FreshDataProvider instance."""
    return FreshDataProvider()
