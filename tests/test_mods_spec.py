"""
Tests for src/parsers/specifications/mods_spec.py.

Covers the pure-function public API:
  - Enum values (GenerationType, DomainFlag)
  - Constants (MOD_ROW_SIZE, MOD_ROW_COUNT, MOD_ROW_SIZE_0_5, MOD_ROW_COUNT_0_5,
    STAT_KEY_OFFSETS, STAT_VALUE_OFFSETS, FIELD_OFFSETS, NULL_KEY_MARKER)
  - StatEntry / ModRecord dataclasses + their derived properties
  - read_key / read_interval helpers
  - parse_mod_row — happy path, truncation rejection, 0.5 oversized acceptance
  - extract_mod_family
  - validate_stat_key / validate_generation_type / validate_mod_record

These are pure binary-format tests — synthesize known-value rows with struct.pack
and assert the parser reads the expected fields at the documented offsets. No
.datc64 file I/O.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.parsers.specifications import mods_spec
from src.parsers.specifications.mods_spec import (
    FIELD_OFFSETS,
    MAX_SPAWN_TAGS,
    MOD_ROW_COUNT,
    MOD_ROW_COUNT_0_5,
    MOD_ROW_SIZE,
    MOD_ROW_SIZE_0_5,
    NULL_KEY_MARKER,
    SPAWN_TAGS_LIST_OFFSET,
    STAT_KEY_OFFSETS,
    STAT_VALUE_OFFSETS,
    DomainFlag,
    GenerationType,
    ModRecord,
    StatEntry,
    extract_mod_family,
    parse_mod_row,
    parse_spawn_tag_indices,
    read_interval,
    read_key,
    read_list_header,
    validate_generation_type,
    validate_mod_record,
    validate_stat_key,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_row(
    *,
    size: int = MOD_ROW_SIZE,
    mod_id_ptr: int = 0,
    hash_value: int = 0,
    type_key_low: int = 0,
    level: int = 0,
    domain: int = 0,
    name_ptr: int = 0,
    gen_type: int = int(GenerationType.PREFIX),
    stat_keys: tuple = (0, 0, 0, 0),
    stat_values: tuple = ((0, 0), (0, 0), (0, 0), (0, 0)),
) -> bytes:
    """Construct a synthetic mod row of `size` bytes with named fields populated.

    Any field left at default writes zeros. Stat slots not provided default to
    empty. Returns a bytearray-derived bytes object — caller can pass directly to
    parse_mod_row.
    """
    buf = bytearray(size)
    struct.pack_into("<Q", buf, 0, mod_id_ptr)
    struct.pack_into("<H", buf, 8, hash_value)
    struct.pack_into("<Q", buf, 10, type_key_low)  # low 8 of 16-byte key
    # offsets 18..25 (high 8 of type_key) left zero
    struct.pack_into("<i", buf, 26, level)
    for i, key in enumerate(stat_keys):
        struct.pack_into("<Q", buf, STAT_KEY_OFFSETS[i], key)
    struct.pack_into("<i", buf, 94, domain)
    struct.pack_into("<Q", buf, 98, name_ptr)
    struct.pack_into("<i", buf, 106, gen_type)
    for i, (mn, mx) in enumerate(stat_values):
        struct.pack_into("<i", buf, STAT_VALUE_OFFSETS[i], mn)
        struct.pack_into("<i", buf, STAT_VALUE_OFFSETS[i] + 4, mx)
    return bytes(buf)


# ---------------------------------------------------------------------------
# Enum values
# ---------------------------------------------------------------------------


def test_generation_type_values():
    """The four documented generation types — these are wire values from the
    game, changing them silently misreads every mod."""
    assert GenerationType.PREFIX == 1
    assert GenerationType.SUFFIX == 2
    assert GenerationType.IMPLICIT == 3
    assert GenerationType.CORRUPTED == 5


def test_domain_flag_values():
    assert DomainFlag.DEFAULT == 0
    assert DomainFlag.SPECIAL == 1
    assert DomainFlag.UNIQUE == 41


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_row_size_constants():
    """Documented pre-0.5 and 0.5 row sizes — both must hold or extractors will
    misparse the data section."""
    assert MOD_ROW_SIZE == 661
    assert MOD_ROW_SIZE_0_5 == 677
    assert MOD_ROW_SIZE_0_5 > MOD_ROW_SIZE  # 0.5 must be growth, not shrink


def test_row_count_constants():
    assert MOD_ROW_COUNT == 14269
    assert MOD_ROW_COUNT_0_5 == 16788


def test_stat_key_offsets():
    """Stat key offsets are 16-byte-spaced starting at 30 — per PoB spec.lua."""
    assert STAT_KEY_OFFSETS == [30, 46, 62, 78]
    # Each adjacent pair is 16 apart (Key field width)
    for a, b in zip(STAT_KEY_OFFSETS, STAT_KEY_OFFSETS[1:]):
        assert b - a == 16


def test_stat_value_offsets():
    """Stat value offsets are 8-byte-spaced starting at 126 (Interval = 2x INT32)."""
    assert STAT_VALUE_OFFSETS == [126, 134, 142, 150]
    for a, b in zip(STAT_VALUE_OFFSETS, STAT_VALUE_OFFSETS[1:]):
        assert b - a == 8


def test_field_offsets_match_constants():
    """FIELD_OFFSETS dict should be consistent with STAT_KEY_OFFSETS / STAT_VALUE_OFFSETS."""
    for i, off in enumerate(STAT_KEY_OFFSETS, start=1):
        assert FIELD_OFFSETS[f"stat{i}_key"] == off
    for i, off in enumerate(STAT_VALUE_OFFSETS, start=1):
        assert FIELD_OFFSETS[f"stat{i}_value"] == off
    # Core fields documented in the spec header
    assert FIELD_OFFSETS["id_ptr"] == 0
    assert FIELD_OFFSETS["hash"] == 8
    assert FIELD_OFFSETS["level"] == 26
    assert FIELD_OFFSETS["domain"] == 94
    assert FIELD_OFFSETS["generation_type"] == 106


def test_null_key_marker():
    """Empty stat slots are marked with 0xFE...FE — must stay exactly 8 0xFE bytes."""
    assert NULL_KEY_MARKER == 0xFEFEFEFEFEFEFEFE


# ---------------------------------------------------------------------------
# StatEntry
# ---------------------------------------------------------------------------


def test_stat_entry_is_empty_for_zero_key():
    assert StatEntry(stat_key=0, stat_key_high=0, min_value=0, max_value=0).is_empty


def test_stat_entry_is_empty_for_null_marker():
    assert StatEntry(stat_key=NULL_KEY_MARKER, stat_key_high=0, min_value=0, max_value=0).is_empty


def test_stat_entry_not_empty_for_real_key():
    assert not StatEntry(stat_key=42, stat_key_high=0, min_value=1, max_value=5).is_empty


def test_stat_entry_stat_index():
    assert StatEntry(stat_key=42, stat_key_high=0, min_value=0, max_value=0).stat_index == 42
    # Empty slots return 0
    assert StatEntry(stat_key=0, stat_key_high=0, min_value=0, max_value=0).stat_index == 0
    assert (
        StatEntry(stat_key=NULL_KEY_MARKER, stat_key_high=0, min_value=0, max_value=0).stat_index
        == 0
    )


# ---------------------------------------------------------------------------
# ModRecord properties
# ---------------------------------------------------------------------------


def _make_record(gen_type: int, stats: list = None) -> ModRecord:
    return ModRecord(
        row_index=0,
        mod_id_ptr=0,
        hash_value=0,
        type_key=0,
        level_requirement=0,
        domain=0,
        name_ptr=0,
        generation_type=gen_type,
        stats=stats or [],
    )


@pytest.mark.parametrize(
    "gen_type, prop",
    [
        (GenerationType.PREFIX, "is_prefix"),
        (GenerationType.SUFFIX, "is_suffix"),
        (GenerationType.IMPLICIT, "is_implicit"),
        (GenerationType.CORRUPTED, "is_corrupted"),
    ],
)
def test_mod_record_generation_props_set_for_matching_type(gen_type, prop):
    rec = _make_record(int(gen_type))
    assert getattr(rec, prop) is True
    # Other three props should be False
    others = {"is_prefix", "is_suffix", "is_implicit", "is_corrupted"} - {prop}
    for o in others:
        assert getattr(rec, o) is False, f"{o} should be False when gen_type={gen_type}"


def test_mod_record_generation_type_name_known():
    assert _make_record(int(GenerationType.PREFIX)).generation_type_name == "PREFIX"
    assert _make_record(int(GenerationType.CORRUPTED)).generation_type_name == "CORRUPTED"


def test_mod_record_generation_type_name_unknown():
    """Unknown gen types render as UNKNOWN(N) — handler shouldn't crash on bad data."""
    assert _make_record(999).generation_type_name == "UNKNOWN(999)"


def test_mod_record_active_stats_filters_empty():
    stats = [
        StatEntry(stat_key=10, stat_key_high=0, min_value=1, max_value=3),
        StatEntry(stat_key=0, stat_key_high=0, min_value=0, max_value=0),  # empty
        StatEntry(stat_key=NULL_KEY_MARKER, stat_key_high=0, min_value=0, max_value=0),  # empty
        StatEntry(stat_key=42, stat_key_high=0, min_value=5, max_value=7),
    ]
    rec = _make_record(int(GenerationType.PREFIX), stats=stats)
    active = rec.active_stats
    assert len(active) == 2
    assert active[0].stat_key == 10
    assert active[1].stat_key == 42
    assert rec.stat_count == 2


# ---------------------------------------------------------------------------
# read_key / read_interval
# ---------------------------------------------------------------------------


def test_read_key_unpacks_two_uint64():
    buf = struct.pack("<QQ", 0xDEADBEEF, 0xCAFEBABE)
    low, high = read_key(buf, 0)
    assert low == 0xDEADBEEF
    assert high == 0xCAFEBABE


def test_read_key_respects_offset():
    buf = b"\x00" * 16 + struct.pack("<QQ", 7, 11)
    low, high = read_key(buf, 16)
    assert (low, high) == (7, 11)


def test_read_interval_unpacks_two_int32():
    buf = struct.pack("<ii", -5, 100)
    mn, mx = read_interval(buf, 0)
    assert mn == -5
    assert mx == 100


def test_read_interval_respects_offset():
    buf = b"\xff" * 8 + struct.pack("<ii", 0, 42)
    mn, mx = read_interval(buf, 8)
    assert (mn, mx) == (0, 42)


# ---------------------------------------------------------------------------
# parse_mod_row
# ---------------------------------------------------------------------------


def test_parse_mod_row_rejects_truncated():
    """Anything shorter than MOD_ROW_SIZE must raise — silent acceptance would
    misalign all downstream parses."""
    with pytest.raises(ValueError, match="Expected >= 661"):
        parse_mod_row(b"\x00" * (MOD_ROW_SIZE - 1))


def test_parse_mod_row_accepts_exact_pre_0_5_size():
    row = make_row(size=MOD_ROW_SIZE)
    rec = parse_mod_row(row, row_index=42)
    assert rec.row_index == 42


def test_parse_mod_row_accepts_oversized_0_5_row():
    """0.5 row is 677 bytes. Strict `!=` check would have rejected this — the
    relaxation is the bug fix from PR #68. Don't regress."""
    row = make_row(size=MOD_ROW_SIZE_0_5)
    rec = parse_mod_row(row)
    # Should parse cleanly without raising
    assert isinstance(rec, ModRecord)


def test_parse_mod_row_reads_core_fields():
    row = make_row(
        mod_id_ptr=0xCAFEBABE,
        hash_value=0x1234,
        type_key_low=0xAABB,
        level=85,
        domain=int(DomainFlag.UNIQUE),
        name_ptr=0xF00D,
        gen_type=int(GenerationType.SUFFIX),
    )
    rec = parse_mod_row(row, row_index=7)
    assert rec.row_index == 7
    assert rec.mod_id_ptr == 0xCAFEBABE
    assert rec.hash_value == 0x1234
    assert rec.type_key == 0xAABB
    assert rec.level_requirement == 85
    assert rec.domain == int(DomainFlag.UNIQUE)
    assert rec.name_ptr == 0xF00D
    assert rec.generation_type == int(GenerationType.SUFFIX)
    assert rec.is_suffix


def test_parse_mod_row_reads_all_four_stat_slots():
    row = make_row(
        stat_keys=(100, 200, 0, NULL_KEY_MARKER),
        stat_values=((1, 5), (10, 20), (0, 0), (0, 0)),
    )
    rec = parse_mod_row(row)
    assert len(rec.stats) == 4
    # Slot 0 — real stat
    assert rec.stats[0].stat_key == 100
    assert (rec.stats[0].min_value, rec.stats[0].max_value) == (1, 5)
    assert not rec.stats[0].is_empty
    # Slot 1 — real stat
    assert rec.stats[1].stat_key == 200
    assert (rec.stats[1].min_value, rec.stats[1].max_value) == (10, 20)
    # Slot 2 — empty (zero key)
    assert rec.stats[2].is_empty
    # Slot 3 — empty (NULL_KEY_MARKER)
    assert rec.stats[3].is_empty
    # active_stats should filter to 2
    assert rec.stat_count == 2


def test_parse_mod_row_handles_negative_value_range():
    """Stat values are signed INT32 — some mods roll negative (e.g. -resistance mods)."""
    row = make_row(stat_values=((-30, -10), (0, 0), (0, 0), (0, 0)))
    rec = parse_mod_row(row)
    assert rec.stats[0].min_value == -30
    assert rec.stats[0].max_value == -10


# ---------------------------------------------------------------------------
# extract_mod_family
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mod_id, expected",
    [
        ("Strength5", ("Strength", 5)),
        ("Strength1", ("Strength", 1)),
        ("LifeRegeneration12", ("LifeRegeneration", 12)),
        # Mods without trailing digits → tier 0, full ID as family
        ("LocalIncreasedPhysicalDamagePercent", ("LocalIncreasedPhysicalDamagePercent", 0)),
        ("", ("", 0)),
    ],
)
def test_extract_mod_family(mod_id, expected):
    assert extract_mod_family(mod_id) == expected


# ---------------------------------------------------------------------------
# Validation functions
# ---------------------------------------------------------------------------


def test_validate_stat_key_empty_slots_valid():
    assert validate_stat_key(0)
    assert validate_stat_key(NULL_KEY_MARKER)


def test_validate_stat_key_in_range():
    assert validate_stat_key(1)
    assert validate_stat_key(24155)


def test_validate_stat_key_out_of_range():
    assert not validate_stat_key(-1)
    assert not validate_stat_key(24156)


@pytest.mark.parametrize(
    "gen_type, expected",
    [
        (1, True),  # PREFIX
        (2, True),  # SUFFIX
        (3, True),  # IMPLICIT
        (4, False),  # no such enum
        (5, True),  # CORRUPTED
        (0, False),
        (999, False),
    ],
)
def test_validate_generation_type(gen_type, expected):
    assert validate_generation_type(gen_type) is expected


def test_validate_mod_record_clean_record_has_no_errors():
    rec = ModRecord(
        row_index=0,
        mod_id_ptr=0,
        hash_value=0,
        type_key=0,
        level_requirement=85,
        domain=0,
        name_ptr=0,
        generation_type=int(GenerationType.PREFIX),
        stats=[StatEntry(stat_key=42, stat_key_high=0, min_value=1, max_value=5)],
    )
    assert validate_mod_record(rec) == []


def test_validate_mod_record_flags_bad_generation_type():
    rec = ModRecord(
        row_index=0,
        mod_id_ptr=0,
        hash_value=0,
        type_key=0,
        level_requirement=10,
        domain=0,
        name_ptr=0,
        generation_type=999,
        stats=[],
    )
    errors = validate_mod_record(rec)
    assert any("generation_type" in e for e in errors)


def test_validate_mod_record_flags_bad_level_requirement():
    rec = ModRecord(
        row_index=0,
        mod_id_ptr=0,
        hash_value=0,
        type_key=0,
        level_requirement=150,  # > 100
        domain=0,
        name_ptr=0,
        generation_type=int(GenerationType.PREFIX),
        stats=[],
    )
    errors = validate_mod_record(rec)
    assert any("level_requirement" in e for e in errors)


def test_validate_mod_record_flags_bad_stat_key():
    rec = ModRecord(
        row_index=0,
        mod_id_ptr=0,
        hash_value=0,
        type_key=0,
        level_requirement=10,
        domain=0,
        name_ptr=0,
        generation_type=int(GenerationType.PREFIX),
        stats=[StatEntry(stat_key=99999, stat_key_high=0, min_value=0, max_value=0)],
    )
    errors = validate_mod_record(rec)
    assert any("stat1_key" in e for e in errors)


# ---------------------------------------------------------------------------
# SpawnTags parsing (Bug 3 — item-class eligibility, 2026-06-16)
# ---------------------------------------------------------------------------


def test_read_list_header_unpacks_count_and_offset():
    buf = bytearray(32)
    struct.pack_into("<Q", buf, 0, 16)  # count
    struct.pack_into("<Q", buf, 8, 74)  # data offset
    count, off = read_list_header(buf, 0)
    assert count == 16
    assert off == 74


def test_spawn_tags_offset_is_after_stat4_value():
    # Stat4Value is the last documented field at offset 150 (8-byte interval),
    # so SpawnTags must begin immediately after at 158.
    assert SPAWN_TAGS_LIST_OFFSET == 150 + 8


def _build_mod_with_spawn_tags(tag_indices):
    """Synthesize (row_data, full_data, data_section_start) where the row's
    SpawnTags list at offset 158 points at `tag_indices` in the data section."""
    row = bytearray(MOD_ROW_SIZE)
    # Data section: place the 16-byte tag keys at data offset 0.
    keys = bytearray()
    for ti in tag_indices:
        keys += struct.pack("<Q", ti) + struct.pack("<Q", 0)
    data_section_start = 1000
    full = bytearray(data_section_start) + keys
    struct.pack_into("<Q", row, SPAWN_TAGS_LIST_OFFSET, len(tag_indices))  # count
    struct.pack_into("<Q", row, SPAWN_TAGS_LIST_OFFSET + 8, 0)  # data offset
    return bytes(row), bytes(full), data_section_start


def test_parse_spawn_tag_indices_resolves_keys():
    row, full, dss = _build_mod_with_spawn_tags([2, 3, 9, 1015])
    assert parse_spawn_tag_indices(row, full, dss) == [2, 3, 9, 1015]


def test_parse_spawn_tag_indices_empty_list():
    row, full, dss = _build_mod_with_spawn_tags([])
    assert parse_spawn_tag_indices(row, full, dss) == []


def test_parse_spawn_tag_indices_rejects_implausible_count():
    row = bytearray(MOD_ROW_SIZE)
    struct.pack_into("<Q", row, SPAWN_TAGS_LIST_OFFSET, MAX_SPAWN_TAGS + 1)
    struct.pack_into("<Q", row, SPAWN_TAGS_LIST_OFFSET + 8, 0)
    assert parse_spawn_tag_indices(bytes(row), b"\x00" * 2000, 1000) == []


def test_parse_spawn_tag_indices_rejects_out_of_range_offset():
    row = bytearray(MOD_ROW_SIZE)
    struct.pack_into("<Q", row, SPAWN_TAGS_LIST_OFFSET, 4)
    struct.pack_into("<Q", row, SPAWN_TAGS_LIST_OFFSET + 8, 10**9)  # way past EOF
    assert parse_spawn_tag_indices(bytes(row), b"\x00" * 2000, 1000) == []
