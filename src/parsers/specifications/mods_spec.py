"""
Mods.datc64 Specification

Binary format specification for the PoE2 mods table.
CORRECTED based on Path of Building spec.lua (authoritative source).

Row Size: 661 bytes
Row Count: 14,269

Field layout verified against PoB's Data/spec.lua on 2025-12-16.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import IntEnum
import struct


class GenerationType(IntEnum):
    """Mod generation type enum (offset 106, 4 bytes)."""
    PREFIX = 1      # Craftable prefix mods
    SUFFIX = 2      # Craftable suffix mods
    IMPLICIT = 3    # Implicit mods (synthesis, delve, base)
    CORRUPTED = 5   # Corruption outcome mods


class DomainFlag(IntEnum):
    """Mod domain/type flag (offset 94, 4 bytes)."""
    DEFAULT = 0
    SPECIAL = 1
    UNIQUE = 41


# Mod row constants
MOD_ROW_SIZE = 661
MOD_ROW_COUNT = 14269

# =============================================================================
# FIELD LAYOUT (from PoB spec.lua)
# =============================================================================
# Field 0:  Id (String, 8 bytes)           -> offset 0
# Field 1:  Hash (UInt16, 2 bytes)         -> offset 8
# Field 2:  Type (Key, 16 bytes)           -> offset 10
# Field 3:  Level (Int, 4 bytes)           -> offset 26
# Field 4:  Stat1 (Key, 16 bytes)          -> offset 30   <- STAT KEY
# Field 5:  Stat2 (Key, 16 bytes)          -> offset 46   <- STAT KEY
# Field 6:  Stat3 (Key, 16 bytes)          -> offset 62   <- STAT KEY
# Field 7:  Stat4 (Key, 16 bytes)          -> offset 78   <- STAT KEY
# Field 8:  Domain (Enum, 4 bytes)         -> offset 94
# Field 9:  Name (String, 8 bytes)         -> offset 98
# Field 10: GenerationType (Enum, 4 bytes) -> offset 106
# Field 11: Family (List, 16 bytes)        -> offset 110
# Field 12: Stat1Value (Interval, 8 bytes) -> offset 126  <- STAT VALUE (min+max)
# Field 13: Stat2Value (Interval, 8 bytes) -> offset 134  <- STAT VALUE
# Field 14: Stat3Value (Interval, 8 bytes) -> offset 142  <- STAT VALUE
# Field 15: Stat4Value (Interval, 8 bytes) -> offset 150  <- STAT VALUE
# ... (fields 16-23 are lists/other data)
# Field 24: Stat5Value (Interval, 8 bytes) -> offset varies (later in record)
# Field 25: Stat5 (Key, 16 bytes)          -> offset varies
# Field 31: Stat6Value (Interval, 8 bytes) -> offset varies
# Field 32: Stat6 (Key, 16 bytes)          -> offset varies
# =============================================================================

# Key field offsets (16-byte Key references to Stats table)
# A Key in .datc64 format is 16 bytes: 8-byte row index + 8-byte table reference
# Empty keys are marked with 0xFEFEFEFEFEFEFEFE patterns
STAT_KEY_OFFSETS = [30, 46, 62, 78]  # Stat1-4

# Value field offsets (8-byte Interval: INT32 min + INT32 max)
STAT_VALUE_OFFSETS = [126, 134, 142, 150]  # Stat1Value-4Value

# Core field offsets
FIELD_OFFSETS = {
    'id_ptr': 0,           # String pointer (8 bytes)
    'hash': 8,             # UInt16 (2 bytes)
    'type_key': 10,        # Key reference (16 bytes)
    'level': 26,           # Int (4 bytes) - level requirement
    'stat1_key': 30,       # Key to Stats table (16 bytes)
    'stat2_key': 46,       # Key to Stats table (16 bytes)
    'stat3_key': 62,       # Key to Stats table (16 bytes)
    'stat4_key': 78,       # Key to Stats table (16 bytes)
    'domain': 94,          # Enum (4 bytes)
    'name_ptr': 98,        # String pointer (8 bytes)
    'generation_type': 106, # Enum (4 bytes)
    'family_list': 110,    # List (16 bytes: 8-byte count + 8-byte offset)
    'stat1_value': 126,    # Interval (8 bytes: min INT32 + max INT32)
    'stat2_value': 134,    # Interval (8 bytes)
    'stat3_value': 142,    # Interval (8 bytes)
    'stat4_value': 150,    # Interval (8 bytes)
}

# Null key marker (used when stat slot is empty)
NULL_KEY_MARKER = 0xFEFEFEFEFEFEFEFE


@dataclass
class StatEntry:
    """A single stat modification with key reference and value range."""
    stat_key: int          # Row index in stats.datc64 (0 = empty, else 1-based index)
    stat_key_high: int     # High 8 bytes of Key (usually table reference or padding)
    min_value: int         # Minimum roll value (INT32)
    max_value: int         # Maximum roll value (INT32)

    @property
    def is_empty(self) -> bool:
        """Check if this stat slot is empty (no stat assigned)."""
        return self.stat_key == 0 or self.stat_key == NULL_KEY_MARKER

    @property
    def stat_index(self) -> int:
        """Get the stat row index (for cross-referencing with stats.datc64)."""
        if self.is_empty:
            return 0
        return self.stat_key


@dataclass
class ModRecord:
    """Parsed mod record from mods.datc64."""
    row_index: int

    # Core fields
    mod_id_ptr: int           # Offset 0: String pointer to mod ID
    hash_value: int           # Offset 8: UInt16 hash
    type_key: int             # Offset 10: Key to ModType table
    level_requirement: int    # Offset 26: Minimum item level required
    domain: int               # Offset 94: Domain enum
    name_ptr: int             # Offset 98: String pointer to display name
    generation_type: int      # Offset 106: PREFIX/SUFFIX/IMPLICIT/CORRUPTED

    # Stat entries (up to 4 stats, Stat5/6 require additional parsing)
    stats: List[StatEntry] = field(default_factory=list)

    # Resolved strings (filled in after parsing)
    mod_id: str = ""
    display_name: str = ""

    @property
    def is_prefix(self) -> bool:
        return self.generation_type == GenerationType.PREFIX

    @property
    def is_suffix(self) -> bool:
        return self.generation_type == GenerationType.SUFFIX

    @property
    def is_implicit(self) -> bool:
        return self.generation_type == GenerationType.IMPLICIT

    @property
    def is_corrupted(self) -> bool:
        return self.generation_type == GenerationType.CORRUPTED

    @property
    def generation_type_name(self) -> str:
        """Human-readable generation type."""
        try:
            return GenerationType(self.generation_type).name
        except ValueError:
            return f"UNKNOWN({self.generation_type})"

    @property
    def active_stats(self) -> List[StatEntry]:
        """Returns only non-empty stat entries."""
        return [stat for stat in self.stats if not stat.is_empty]

    @property
    def stat_count(self) -> int:
        """Number of active stats on this mod."""
        return len(self.active_stats)


def read_key(data: bytes, offset: int) -> Tuple[int, int]:
    """
    Read a 16-byte Key field.

    Returns:
        Tuple of (row_index, high_bytes)
        - row_index: First 8 bytes as unsigned long (row reference)
        - high_bytes: Second 8 bytes (usually table ref or padding)
    """
    low = struct.unpack('<Q', data[offset:offset+8])[0]
    high = struct.unpack('<Q', data[offset+8:offset+16])[0]
    return (low, high)


def read_interval(data: bytes, offset: int) -> Tuple[int, int]:
    """
    Read an 8-byte Interval field (min/max pair).

    Returns:
        Tuple of (min_value, max_value) as signed INT32
    """
    min_val = struct.unpack('<i', data[offset:offset+4])[0]
    max_val = struct.unpack('<i', data[offset+4:offset+8])[0]
    return (min_val, max_val)


def parse_mod_row(data: bytes, row_index: int = 0) -> ModRecord:
    """
    Parse a single 661-byte mod row.

    Args:
        data: 661 bytes of raw mod data
        row_index: Row index in the table

    Returns:
        ModRecord with parsed fields
    """
    if len(data) != MOD_ROW_SIZE:
        raise ValueError(f"Expected {MOD_ROW_SIZE} bytes, got {len(data)}")

    # Parse core fields
    mod_id_ptr = struct.unpack('<Q', data[0:8])[0]
    hash_value = struct.unpack('<H', data[8:10])[0]
    type_key, _ = read_key(data, 10)
    level_requirement = struct.unpack('<i', data[26:30])[0]
    domain = struct.unpack('<i', data[94:98])[0]
    name_ptr = struct.unpack('<Q', data[98:106])[0]
    generation_type = struct.unpack('<i', data[106:110])[0]

    # Parse stat entries (4 slots)
    stats = []
    for i in range(4):
        key_offset = STAT_KEY_OFFSETS[i]
        value_offset = STAT_VALUE_OFFSETS[i]

        stat_key, stat_key_high = read_key(data, key_offset)
        min_val, max_val = read_interval(data, value_offset)

        stats.append(StatEntry(
            stat_key=stat_key,
            stat_key_high=stat_key_high,
            min_value=min_val,
            max_value=max_val
        ))

    return ModRecord(
        row_index=row_index,
        mod_id_ptr=mod_id_ptr,
        hash_value=hash_value,
        type_key=type_key,
        level_requirement=level_requirement,
        domain=domain,
        name_ptr=name_ptr,
        generation_type=generation_type,
        stats=stats,
    )


def extract_mod_family(mod_id: str) -> Tuple[str, int]:
    """
    Extract mod family name and tier from mod ID.

    Example: "Strength5" -> ("Strength", 5)
             "LocalIncreasedPhysicalDamagePercent" -> ("LocalIncreasedPhysicalDamagePercent", 0)

    Returns:
        Tuple of (family_name, tier_number)
    """
    import re
    match = re.match(r'^(.+?)(\d+)$', mod_id)
    if match:
        return (match.group(1), int(match.group(2)))
    return (mod_id, 0)


# =============================================================================
# VALIDATION UTILITIES
# =============================================================================

def validate_stat_key(stat_key: int) -> bool:
    """
    Validate that a stat key is within valid range.

    Stats table has 24,155 entries (indices 0-24154).
    """
    if stat_key == 0 or stat_key == NULL_KEY_MARKER:
        return True  # Empty slot is valid
    return 0 < stat_key <= 24155


def validate_generation_type(gen_type: int) -> bool:
    """Validate generation type enum value."""
    return gen_type in [1, 2, 3, 5]


def validate_mod_record(record: ModRecord) -> List[str]:
    """
    Validate a parsed mod record.

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check generation type
    if not validate_generation_type(record.generation_type):
        errors.append(f"Invalid generation_type: {record.generation_type}")

    # Check level requirement (should be 1-100)
    if not (0 <= record.level_requirement <= 100):
        errors.append(f"Invalid level_requirement: {record.level_requirement}")

    # Check stat keys
    for i, stat in enumerate(record.stats):
        if not validate_stat_key(stat.stat_key):
            errors.append(f"Invalid stat{i+1}_key: {stat.stat_key}")

    return errors
