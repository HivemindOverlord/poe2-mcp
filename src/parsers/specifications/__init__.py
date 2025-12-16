"""
Datc64 Specifications Package

Contains reverse-engineered specifications for PoE2 binary game data files.
These specifications enable automated extraction from game files as the
authoritative data source.

Available Specifications:
- mods_spec: Item/passive modifier definitions (mods.datc64)
             CORRECTED 2025-12-16 based on PoB spec.lua
"""

from .mods_spec import (
    # Enums
    GenerationType,
    DomainFlag,

    # Constants
    MOD_ROW_SIZE,
    MOD_ROW_COUNT,
    STAT_KEY_OFFSETS,
    STAT_VALUE_OFFSETS,
    FIELD_OFFSETS,
    NULL_KEY_MARKER,

    # Data classes
    StatEntry,
    ModRecord,

    # Functions
    parse_mod_row,
    read_key,
    read_interval,
    extract_mod_family,
    validate_stat_key,
    validate_generation_type,
    validate_mod_record,
)

__all__ = [
    # Enums
    'GenerationType',
    'DomainFlag',

    # Constants
    'MOD_ROW_SIZE',
    'MOD_ROW_COUNT',
    'STAT_KEY_OFFSETS',
    'STAT_VALUE_OFFSETS',
    'FIELD_OFFSETS',
    'NULL_KEY_MARKER',

    # Data classes
    'StatEntry',
    'ModRecord',

    # Functions
    'parse_mod_row',
    'read_key',
    'read_interval',
    'extract_mod_family',
    'validate_stat_key',
    'validate_generation_type',
    'validate_mod_record',
]
