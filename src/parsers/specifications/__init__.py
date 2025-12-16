"""
Datc64 Specifications Package

Contains reverse-engineered specifications for PoE2 binary game data files.
These specifications enable automated extraction from game files as the
authoritative data source.

Available Specifications:
- mods_spec: Item/passive modifier definitions (mods.datc64)
"""

from .mods_spec import (
    # Enums
    GenerationType,
    DomainFlag,

    # Constants
    MOD_ROW_SIZE,
    MOD_ROW_COUNT,
    STRING_POINTER_OFFSETS,
    STAT_SLOT_OFFSETS,
    CONSTANT_FIELDS,
    EMPTY_STRING_SENTINEL,

    # Data classes
    StatSlot,
    ModRecord,

    # Functions
    parse_mod_row,
    validate_constants,
    validate_empty_string_sentinel,
)

__all__ = [
    # Enums
    'GenerationType',
    'DomainFlag',

    # Constants
    'MOD_ROW_SIZE',
    'MOD_ROW_COUNT',
    'STRING_POINTER_OFFSETS',
    'STAT_SLOT_OFFSETS',
    'CONSTANT_FIELDS',
    'EMPTY_STRING_SENTINEL',

    # Data classes
    'StatSlot',
    'ModRecord',

    # Functions
    'parse_mod_row',
    'validate_constants',
    'validate_empty_string_sentinel',
]
