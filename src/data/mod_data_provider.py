"""
Mod Data Provider for Path of Exile 2

Provides efficient access to mod (affix) data extracted from mods.datc64.
Supports filtering, searching, tier lookups, and validation of mod combinations.

Author: HivemindMinion
Date: 2025-12-16
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from functools import lru_cache
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Base directory for data files
try:
    from ..config import BASE_DIR, DATA_DIR
except ImportError:
    BASE_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = BASE_DIR / 'data'


@dataclass
class ModFilter:
    """Filter parameters for mod queries"""
    generation_type: Optional[str] = None  # PREFIX, SUFFIX, IMPLICIT, CORRUPTED
    min_level: Optional[int] = None
    max_level: Optional[int] = None
    domain_flag: Optional[int] = None
    mod_family: Optional[str] = None  # Base name without tier number (e.g., "Strength")
    limit: int = 100
    offset: int = 0


class ModDataProvider:
    """
    Provides access to Path of Exile 2 mod (affix) data.

    Single Source of Truth for item modifiers - loads from poe2_mods_extracted.json.
    Implements singleton pattern for memory efficiency.

    Usage:
        >>> provider = ModDataProvider()
        >>> mod = provider.get_mod("Strength1")
        >>> prefixes = provider.list_mods(ModFilter(generation_type="PREFIX", min_level=30))
        >>> strength_mods = provider.search_by_stat("strength")
        >>> tiers = provider.get_mod_tiers("Strength")
    """

    _instance = None
    _initialized = False

    # Generation type constants
    GENERATION_TYPES = {
        1: "PREFIX",
        2: "SUFFIX",
        3: "IMPLICIT",
        9: "CORRUPTED"
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, data_path: Optional[Path] = None):
        """
        Initialize mod data provider.

        Args:
            data_path: Optional path to mod JSON file. Defaults to data/poe2_mods_extracted.json
        """
        if self._initialized:
            return
        self._initialized = True

        # Data storage
        self._mods_by_id: Dict[str, Dict] = {}
        self._mods_by_index: Dict[int, Dict] = {}
        self._mods_by_type: Dict[str, List[Dict]] = {}
        self._mod_families: Dict[str, List[Dict]] = {}  # Group mods by base name
        self._metadata: Dict[str, Any] = {}

        # Set data path
        if data_path is None:
            data_path = DATA_DIR / 'poe2_mods_extracted.json'
        self.data_path = data_path

        # Load data
        self._load_mod_data()

    def _load_mod_data(self):
        """Load mod data from JSON file"""
        try:
            if not self.data_path.exists():
                logger.error(f"Mod data file not found: {self.data_path}")
                return

            logger.info(f"Loading mod data from {self.data_path}")

            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Store metadata
            self._metadata = data.get('metadata', {})

            # Load mods
            mods = data.get('mods', [])
            for mod in mods:
                mod_id = mod.get('mod_id')
                row_index = mod.get('row_index')

                if not mod_id:
                    continue

                # Index by ID
                self._mods_by_id[mod_id] = mod

                # Index by row index
                if row_index is not None:
                    self._mods_by_index[row_index] = mod

                # Index by generation type
                gen_type = mod.get('generation_type_name', 'UNKNOWN')
                if gen_type not in self._mods_by_type:
                    self._mods_by_type[gen_type] = []
                self._mods_by_type[gen_type].append(mod)

                # Index by mod family (base name without tier number)
                family = self._extract_mod_family(mod_id)
                if family not in self._mod_families:
                    self._mod_families[family] = []
                self._mod_families[family].append(mod)

            logger.info(f"Loaded {len(self._mods_by_id)} mods: "
                       f"Prefix={len(self._mods_by_type.get('PREFIX', []))}, "
                       f"Suffix={len(self._mods_by_type.get('SUFFIX', []))}, "
                       f"Implicit={len(self._mods_by_type.get('IMPLICIT', []))}, "
                       f"Corrupted={len(self._mods_by_type.get('CORRUPTED', []))}")

        except Exception as e:
            logger.error(f"Failed to load mod data: {e}", exc_info=True)

    def _extract_mod_family(self, mod_id: str) -> str:
        """
        Extract mod family name by removing tier suffix.

        Examples:
            "Strength1" -> "Strength"
            "LightningDamage7" -> "LightningDamage"
            "LifeRegen" -> "LifeRegen"
        """
        # Remove trailing digits
        family = mod_id.rstrip('0123456789')

        # Handle edge case where mod_id is all digits
        if not family:
            return mod_id

        return family

    # =========================================================================
    # PUBLIC API - Core retrieval methods
    # =========================================================================

    def get_mod(self, mod_id: str) -> Optional[Dict]:
        """
        Get mod by ID.

        Args:
            mod_id: Mod identifier (e.g., "Strength1", "LightningDamage7")

        Returns:
            Mod dictionary or None if not found
        """
        return self._mods_by_id.get(mod_id)

    def get_mod_by_index(self, row_index: int) -> Optional[Dict]:
        """
        Get mod by row index in the datc64 file.

        Args:
            row_index: Row index (0-based)

        Returns:
            Mod dictionary or None if not found
        """
        return self._mods_by_index.get(row_index)

    def list_mods(
        self,
        filters: Optional[ModFilter] = None,
        sort_by: str = "level_requirement"
    ) -> List[Dict]:
        """
        List mods with optional filtering and sorting.

        Args:
            filters: Optional ModFilter object with filter parameters
            sort_by: Field to sort by ("level_requirement", "mod_id", "generation_type")

        Returns:
            List of mod dictionaries matching filters
        """
        if filters is None:
            filters = ModFilter()

        # Start with all mods or filtered by type
        if filters.generation_type:
            result = self._mods_by_type.get(filters.generation_type, []).copy()
        else:
            result = list(self._mods_by_id.values())

        # Apply filters
        if filters.min_level is not None:
            result = [m for m in result if m.get('level_requirement', 0) >= filters.min_level]

        if filters.max_level is not None:
            result = [m for m in result if m.get('level_requirement', 0) <= filters.max_level]

        if filters.domain_flag is not None:
            result = [m for m in result if m.get('domain_flag', 0) == filters.domain_flag]

        if filters.mod_family:
            result = [m for m in result if self._extract_mod_family(m.get('mod_id', '')) == filters.mod_family]

        # Sort
        if sort_by == "level_requirement":
            result.sort(key=lambda m: m.get('level_requirement', 0))
        elif sort_by == "mod_id":
            result.sort(key=lambda m: m.get('mod_id', ''))
        elif sort_by == "generation_type":
            result.sort(key=lambda m: m.get('generation_type', 0))

        # Pagination
        offset = filters.offset
        limit = filters.limit
        return result[offset:offset + limit]

    def search_by_stat(
        self,
        stat_keyword: str,
        case_sensitive: bool = False,
        limit: int = 100
    ) -> List[Dict]:
        """
        Search mods by keyword in mod_id.

        Note: String fields contain internal cross-references (not human-readable stat text),
        so we only search the mod_id which contains the mod name/type.

        Args:
            stat_keyword: Keyword to search for (e.g., "strength", "lightning", "resist")
            case_sensitive: Whether to use case-sensitive matching
            limit: Maximum number of results to return

        Returns:
            List of matching mod dictionaries
        """
        results = []
        search_term = stat_keyword if case_sensitive else stat_keyword.lower()

        for mod_id, mod in self._mods_by_id.items():
            # Search in mod_id only (string fields contain cross-references, not stat text)
            search_id = mod_id if case_sensitive else mod_id.lower()
            if search_term in search_id:
                results.append(mod)
                if len(results) >= limit:
                    break

        return results

    def get_mod_tiers(self, mod_base_name: str) -> List[Dict]:
        """
        Get all tier variants of a mod family.

        Args:
            mod_base_name: Base name without tier number (e.g., "Strength", "LightningDamage")

        Returns:
            List of mod dictionaries for all tiers, sorted by level requirement
        """
        family_mods = self._mod_families.get(mod_base_name, [])

        # Sort by level requirement (ascending)
        sorted_mods = sorted(family_mods, key=lambda m: m.get('level_requirement', 0))

        return sorted_mods

    def get_mods_for_item_type(
        self,
        item_type: str,
        generation_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Get mods that can roll on a specific item type.

        Note: This is a simplified implementation. Full implementation would require
        mod spawn weight tables and item class restrictions from additional datc64 files.

        Args:
            item_type: Item type identifier (e.g., "weapon", "armor", "jewellery")
            generation_type: Optional filter by PREFIX, SUFFIX, IMPLICIT, CORRUPTED

        Returns:
            List of applicable mods
        """
        # For now, return all mods of the specified generation type
        # TODO: Implement proper item class restrictions when spawn weight data is available
        logger.warning("get_mods_for_item_type is simplified - spawn weights not implemented")

        if generation_type:
            return self._mods_by_type.get(generation_type, [])
        else:
            return list(self._mods_by_id.values())

    def validate_mod_combination(self, mod_ids: List[str]) -> Dict[str, Any]:
        """
        Validate if a combination of mods can exist together on an item.

        Checks:
        - Mod family conflicts (can't have multiple tiers of same mod)
        - Generation type limits (max prefixes/suffixes)
        - Mod group exclusivity (placeholder for future implementation)

        Args:
            mod_ids: List of mod IDs to validate

        Returns:
            {
                "valid": bool,
                "errors": List[str],
                "warnings": List[str],
                "conflicts": List[Tuple[str, str]]
            }
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "conflicts": []
        }

        if not mod_ids:
            result["errors"].append("No mods provided")
            result["valid"] = False
            return result

        # Get all mods
        mods = []
        for mod_id in mod_ids:
            mod = self.get_mod(mod_id)
            if not mod:
                result["errors"].append(f"Mod not found: {mod_id}")
                result["valid"] = False
            else:
                mods.append(mod)

        if not result["valid"]:
            return result

        # Check mod family conflicts (can't have Strength1 and Strength2)
        families_seen = {}
        for mod in mods:
            mod_id = mod.get('mod_id')
            family = self._extract_mod_family(mod_id)

            if family in families_seen:
                conflict_mod = families_seen[family]
                result["errors"].append(
                    f"Multiple tiers of same mod: {conflict_mod} and {mod_id}"
                )
                result["conflicts"].append((conflict_mod, mod_id))
                result["valid"] = False
            else:
                families_seen[family] = mod_id

        # Check prefix/suffix limits
        prefix_count = sum(1 for m in mods if m.get('generation_type_name') == 'PREFIX')
        suffix_count = sum(1 for m in mods if m.get('generation_type_name') == 'SUFFIX')
        implicit_count = sum(1 for m in mods if m.get('generation_type_name') == 'IMPLICIT')

        # PoE2 typical limits (can vary by item type)
        MAX_PREFIXES = 3
        MAX_SUFFIXES = 3
        MAX_IMPLICITS = 2  # Can vary

        if prefix_count > MAX_PREFIXES:
            result["errors"].append(f"Too many prefixes: {prefix_count} > {MAX_PREFIXES}")
            result["valid"] = False

        if suffix_count > MAX_SUFFIXES:
            result["errors"].append(f"Too many suffixes: {suffix_count} > {MAX_SUFFIXES}")
            result["valid"] = False

        if implicit_count > MAX_IMPLICITS:
            result["warnings"].append(
                f"High implicit count: {implicit_count} (typical max: {MAX_IMPLICITS})"
            )

        return result

    # =========================================================================
    # STATISTICS AND METADATA
    # =========================================================================

    def get_stats_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics about loaded mod data.

        Returns:
            Dictionary with counts and metadata
        """
        return {
            "total_mods": len(self._mods_by_id),
            "prefix_count": len(self._mods_by_type.get('PREFIX', [])),
            "suffix_count": len(self._mods_by_type.get('SUFFIX', [])),
            "implicit_count": len(self._mods_by_type.get('IMPLICIT', [])),
            "corrupted_count": len(self._mods_by_type.get('CORRUPTED', [])),
            "mod_families": len(self._mod_families),
            "metadata": self._metadata
        }

    def get_metadata(self) -> Dict[str, Any]:
        """Get extraction metadata (source file, date, validation errors, etc.)"""
        return self._metadata.copy()

    def get_generation_types(self) -> Dict[int, str]:
        """Get mapping of generation type codes to names"""
        return self.GENERATION_TYPES.copy()

    # =========================================================================
    # CONVENIENCE METHODS
    # =========================================================================

    def get_prefixes(self, min_level: int = 0, max_level: int = 100) -> List[Dict]:
        """Get all prefix mods within level range"""
        return self.list_mods(ModFilter(
            generation_type="PREFIX",
            min_level=min_level,
            max_level=max_level,
            limit=1000
        ))

    def get_suffixes(self, min_level: int = 0, max_level: int = 100) -> List[Dict]:
        """Get all suffix mods within level range"""
        return self.list_mods(ModFilter(
            generation_type="SUFFIX",
            min_level=min_level,
            max_level=max_level,
            limit=1000
        ))

    def get_implicits(self, min_level: int = 0, max_level: int = 100) -> List[Dict]:
        """Get all implicit mods within level range"""
        return self.list_mods(ModFilter(
            generation_type="IMPLICIT",
            min_level=min_level,
            max_level=max_level,
            limit=1000
        ))

    def get_corrupted_mods(self) -> List[Dict]:
        """Get all corrupted implicit mods"""
        return self._mods_by_type.get('CORRUPTED', [])

    def get_all_families(self) -> List[str]:
        """Get list of all mod family names"""
        return sorted(self._mod_families.keys())

    @lru_cache(maxsize=128)
    def get_level_range(self, generation_type: Optional[str] = None) -> Tuple[int, int]:
        """
        Get min and max level requirements for mods.

        Args:
            generation_type: Optional filter by type

        Returns:
            Tuple of (min_level, max_level)
        """
        if generation_type:
            mods = self._mods_by_type.get(generation_type, [])
        else:
            mods = list(self._mods_by_id.values())

        if not mods:
            return (0, 0)

        levels = [m.get('level_requirement', 0) for m in mods]
        return (min(levels), max(levels))


# Singleton accessor
def get_mod_data_provider() -> ModDataProvider:
    """Get the singleton ModDataProvider instance"""
    return ModDataProvider()


if __name__ == "__main__":
    # Configure logging for testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 80)
    print("Path of Exile 2 Mod Data Provider - Test Suite")
    print("=" * 80)
    print()

    # Initialize provider
    provider = get_mod_data_provider()

    # Print statistics
    stats = provider.get_stats_summary()
    print("Statistics:")
    print(f"  Total mods: {stats['total_mods']}")
    print(f"  Prefixes: {stats['prefix_count']}")
    print(f"  Suffixes: {stats['suffix_count']}")
    print(f"  Implicits: {stats['implicit_count']}")
    print(f"  Corrupted: {stats['corrupted_count']}")
    print(f"  Mod families: {stats['mod_families']}")
    print()

    # Test get_mod
    print("Test 1: Get specific mod")
    mod = provider.get_mod("Strength1")
    if mod:
        print(f"  Found: {mod['mod_id']} (Level {mod['level_requirement']}, {mod['generation_type_name']})")
    print()

    # Test get_mod_tiers
    print("Test 2: Get all Strength tiers")
    strength_tiers = provider.get_mod_tiers("Strength")
    print(f"  Found {len(strength_tiers)} tiers:")
    for tier in strength_tiers[:5]:
        print(f"    {tier['mod_id']}: Level {tier['level_requirement']}, "
              f"Min={tier.get('min_value', 0)}, Max={tier.get('max_value', 0)}")
    if len(strength_tiers) > 5:
        print(f"    ... and {len(strength_tiers) - 5} more")
    print()

    # Test search_by_stat
    print("Test 3: Search for 'Lightning' mods")
    lightning_mods = provider.search_by_stat("Lightning", limit=10)
    print(f"  Found {len(lightning_mods)} mods:")
    for mod in lightning_mods[:5]:
        print(f"    {mod['mod_id']}: {mod['generation_type_name']}, Level {mod['level_requirement']}")
    print()

    # Test list_mods with filters
    print("Test 4: List high-level prefixes")
    high_prefixes = provider.list_mods(ModFilter(
        generation_type="PREFIX",
        min_level=50,
        limit=5
    ))
    print(f"  Found {len(high_prefixes)} prefixes (level 50+):")
    for mod in high_prefixes:
        print(f"    {mod['mod_id']}: Level {mod['level_requirement']}")
    print()

    # Test validate_mod_combination
    print("Test 5: Validate mod combination")
    test_mods = ["Strength1", "Strength2", "LightningDamage7"]
    validation = provider.validate_mod_combination(test_mods)
    print(f"  Combination: {', '.join(test_mods)}")
    print(f"  Valid: {validation['valid']}")
    if validation['errors']:
        print(f"  Errors: {', '.join(validation['errors'])}")
    if validation['warnings']:
        print(f"  Warnings: {', '.join(validation['warnings'])}")
    print()

    # Test level range
    print("Test 6: Get level ranges")
    for gen_type in ['PREFIX', 'SUFFIX', 'IMPLICIT']:
        min_lvl, max_lvl = provider.get_level_range(gen_type)
        print(f"  {gen_type}: Level {min_lvl} to {max_lvl}")
    print()

    print("=" * 80)
    print("All tests complete!")
    print("=" * 80)
