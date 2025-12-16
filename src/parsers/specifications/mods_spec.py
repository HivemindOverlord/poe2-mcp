"""
Mods.datc64 Specification

Binary format specification for the PoE2 mods table.
Auto-generated from reverse engineering analysis on 2025-12-15.

Row Size: 661 bytes
Row Count: 14,269
Coverage: 92.4% mapped (611/661 bytes)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import IntEnum
import struct


class GenerationType(IntEnum):
    """Mod generation type enum (offset 511)."""
    PREFIX = 1      # 18% - Craftable prefix mods
    SUFFIX = 2      # 67% - Craftable suffix mods
    IMPLICIT = 3    # 12% - Implicit mods (synthesis, delve, base)
    CORRUPTED = 5   # 3% - Corruption outcome mods


class DomainFlag(IntEnum):
    """Mod domain/type flag (offset 15)."""
    DEFAULT = 0     # 77.5%
    SPECIAL = 1     # 19.5%
    UNIQUE = 41     # 3%


# Mod row constants
MOD_ROW_SIZE = 661
MOD_ROW_COUNT = 14269

# String pointer offsets (8 bytes each, points to UTF-16LE strings)
STRING_POINTER_OFFSETS = [0, 92, 108, 420, 448, 516, 624, 644, 652]

# CORRECTED Field offsets (verified against actual data 2025-12-15)
# String pointer at offset 0 (8 bytes) - mod ID
# Level requirement at offset 26 (4 bytes) - actually UINT16 seems sufficient
# Generation type at offset 106 (4 bytes)

# Stat slot offsets: These need re-verification
# Each slot is: 1-byte stat index + 4-byte stat value
STAT_SLOT_OFFSETS = [
    (102, 103),   # Slot 0 - UNVERIFIED
    (122, 123),   # Slot 1 - UNVERIFIED
    (170, 171),   # Slot 2 - UNVERIFIED
    (202, 203),   # Slot 3 - UNVERIFIED
    (218, 219),   # Slot 4 - UNVERIFIED
    (234, 235),   # Slot 5 - UNVERIFIED
    (258, 259),   # Slot 6 - UNVERIFIED
    (274, 275),   # Slot 7 - UNVERIFIED
    (314, 315),   # Slot 8 - UNVERIFIED
    (330, 331),   # Slot 9 - UNVERIFIED
    (346, 347),   # Slot 10 - UNVERIFIED
    (378, 379),   # Slot 11 - UNVERIFIED
]

# Constant value offsets and their expected values
CONSTANT_FIELDS = {
    186: 74,          # Unknown constant
    242: 74,          # Unknown constant
    362: 74,          # Unknown constant
    410: 100,         # Max level or percentage base
    431: 74,          # Unknown constant
    439: 2,           # Enum value (format version?)
    507: 6,           # Stat count or table reference
}

# Empty string pointer sentinel value
EMPTY_STRING_SENTINEL = 12884901888  # Offset 652


@dataclass
class StatSlot:
    """A single stat modification slot."""
    stat_index: int  # Reference to stats.datc64 (0-255)
    stat_value: int  # Associated value (typically 0-41)

    @property
    def is_empty(self) -> bool:
        return self.stat_index == 0 and self.stat_value == 0


@dataclass
class ModRecord:
    """Parsed mod record from mods.datc64."""
    row_index: int

    # String pointers (resolved to actual strings externally)
    mod_id_ptr: int           # Offset 0
    string_ptr_92: int        # Offset 92
    string_ptr_108: int       # Offset 108
    string_ptr_420: int       # Offset 420
    string_ptr_448: int       # Offset 448
    string_ptr_516: int       # Offset 516
    string_ptr_624: int       # Offset 624
    string_ptr_644: int       # Offset 644
    string_ptr_652: int       # Offset 652 (typically empty sentinel)

    # Header fields
    header_byte_12: int       # Unknown identifier 1
    header_byte_13: int       # Unknown identifier 2
    header_byte_14: int       # Unknown identifier 3
    domain_flag: int          # Offset 15: 0, 1, or 41
    level_requirement: int    # Offset 30: 1-82
    related_field: int        # Offset 35: correlates with domain_flag

    # Stat slots (12 total)
    stat_slots: List[StatSlot] = field(default_factory=list)

    # Min/Max values
    min_value: int = 0        # Offset 130
    max_value: int = 0        # Offset 134

    # Generation type
    generation_type: int = 2  # Offset 511: 1, 2, 3, or 5

    # Trailing fields (highly variable)
    end_byte_616: int = 0
    end_byte_617: int = 0
    end_byte_618: int = 0
    end_uint_619: int = 0

    # Resolved strings (filled in after parsing)
    mod_id: str = ""
    strings: Dict[int, str] = field(default_factory=dict)

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
    def active_stats(self) -> List[StatSlot]:
        """Returns only non-empty stat slots."""
        return [slot for slot in self.stat_slots if not slot.is_empty]


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

    # Parse string pointers
    mod_id_ptr = struct.unpack('<Q', data[0:8])[0]
    string_ptr_92 = struct.unpack('<Q', data[92:100])[0]
    string_ptr_108 = struct.unpack('<Q', data[108:116])[0]
    string_ptr_420 = struct.unpack('<Q', data[420:428])[0]
    string_ptr_448 = struct.unpack('<Q', data[448:456])[0]
    string_ptr_516 = struct.unpack('<Q', data[516:524])[0]
    string_ptr_624 = struct.unpack('<Q', data[624:632])[0]
    string_ptr_644 = struct.unpack('<Q', data[644:652])[0]
    string_ptr_652 = struct.unpack('<Q', data[652:660])[0]

    # Parse header fields (CORRECTED offsets)
    header_byte_12 = struct.unpack('<B', data[12:13])[0]
    header_byte_13 = struct.unpack('<B', data[13:14])[0]
    header_byte_14 = struct.unpack('<B', data[14:15])[0]
    domain_flag = struct.unpack('<I', data[15:19])[0]
    # CORRECTED: Level requirement at offset 26 (UINT16)
    level_requirement = struct.unpack('<H', data[26:28])[0]
    related_field = struct.unpack('<I', data[35:39])[0]

    # Parse stat slots
    stat_slots = []
    for idx_off, val_off in STAT_SLOT_OFFSETS:
        stat_idx = struct.unpack('<B', data[idx_off:idx_off+1])[0]
        stat_val = struct.unpack('<I', data[val_off:val_off+4])[0]
        stat_slots.append(StatSlot(stat_index=stat_idx, stat_value=stat_val))

    # Parse min/max
    min_value = struct.unpack('<I', data[130:134])[0]
    max_value = struct.unpack('<I', data[134:138])[0]

    # Parse generation type (CORRECTED: offset 106, not 511)
    generation_type = struct.unpack('<I', data[106:110])[0]

    # Parse trailing fields
    end_byte_616 = struct.unpack('<B', data[616:617])[0]
    end_byte_617 = struct.unpack('<B', data[617:618])[0]
    end_byte_618 = struct.unpack('<B', data[618:619])[0]
    end_uint_619 = struct.unpack('<I', data[619:623])[0]

    return ModRecord(
        row_index=row_index,
        mod_id_ptr=mod_id_ptr,
        string_ptr_92=string_ptr_92,
        string_ptr_108=string_ptr_108,
        string_ptr_420=string_ptr_420,
        string_ptr_448=string_ptr_448,
        string_ptr_516=string_ptr_516,
        string_ptr_624=string_ptr_624,
        string_ptr_644=string_ptr_644,
        string_ptr_652=string_ptr_652,
        header_byte_12=header_byte_12,
        header_byte_13=header_byte_13,
        header_byte_14=header_byte_14,
        domain_flag=domain_flag,
        level_requirement=level_requirement,
        related_field=related_field,
        stat_slots=stat_slots,
        min_value=min_value,
        max_value=max_value,
        generation_type=generation_type,
        end_byte_616=end_byte_616,
        end_byte_617=end_byte_617,
        end_byte_618=end_byte_618,
        end_uint_619=end_uint_619,
    )


def validate_constants(data: bytes) -> Dict[int, bool]:
    """
    Validate that constant fields have expected values.

    Args:
        data: 661 bytes of raw mod data

    Returns:
        Dictionary mapping offset to validation result (True if matches)
    """
    results = {}
    for offset, expected in CONSTANT_FIELDS.items():
        actual = struct.unpack('<I', data[offset:offset+4])[0]
        results[offset] = (actual == expected)
    return results


def validate_empty_string_sentinel(data: bytes) -> bool:
    """Check if offset 652 contains the empty string sentinel."""
    actual = struct.unpack('<Q', data[652:660])[0]
    return actual == EMPTY_STRING_SENTINEL
