"""
Tests for src/parsers/specifications/characters_spec.py.

Covers the pure-function public API:
  - Row-size + PSG-header constants
  - FIELD_OFFSETS
  - ATTRIBUTE_TO_PSG_INDEX, PSG_STARTING_NODES, CLASS_NAMES, POE_NINJA_* dicts
  - Cross-consistency (poe.ninja name -> PSG index -> starting node ID round trip)
  - CharacterRecord dataclass + .base_class_index property
  - extract_attribute_type from metadata paths
  - parse_character_row: rejects wrong-size rows, reads core fields
  - read_psg_starting_nodes via tmp_path with a synthesized PSG header
  - get_class_to_starting_node_mapping returns expected base + ascendancy names

Pure-function tests using synthesized binary rows / PSG headers — no real
.datc64 or .psg file I/O.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.parsers.specifications.characters_spec import (
    ATTRIBUTE_TO_PSG_INDEX,
    CHARACTER_ROW_COUNT,
    CHARACTER_ROW_SIZE,
    CLASS_NAMES,
    FIELD_OFFSETS,
    POE_NINJA_CLASS_TO_PSG_INDEX,
    POE_NINJA_CLASS_TO_STARTING_NODE,
    PSG_STARTING_NODE_SIZE,
    PSG_STARTING_NODES,
    PSG_STARTING_NODES_COUNT,
    PSG_STARTING_NODES_OFFSET,
    CharacterRecord,
    extract_attribute_type,
    get_class_to_starting_node_mapping,
    parse_character_row,
    read_psg_starting_nodes,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_character_row(
    *,
    size: int = CHARACTER_ROW_SIZE,
    metadata_path_ptr: int = 0,
    class_name_ptr: int = 0,
    animation_path_ptr: int = 0,
    actor_path_ptr: int = 0,
    attribute_count: int = 0,
) -> bytes:
    """Construct a synthetic 656-byte character row with the named fields."""
    buf = bytearray(size)
    struct.pack_into("<Q", buf, 0, metadata_path_ptr)
    struct.pack_into("<Q", buf, 8, class_name_ptr)
    struct.pack_into("<Q", buf, 16, animation_path_ptr)
    struct.pack_into("<Q", buf, 24, actor_path_ptr)
    struct.pack_into("<i", buf, 48, attribute_count)
    return bytes(buf)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_character_row_size_constant():
    assert CHARACTER_ROW_SIZE == 656


def test_character_row_count_constant():
    """12 = 6 base classes + 6 ascendancy classes."""
    assert CHARACTER_ROW_COUNT == 12
    assert len(CLASS_NAMES) == CHARACTER_ROW_COUNT


def test_psg_header_constants():
    """The 6 starting node IDs live at offset 17, packed as uint64 LE."""
    assert PSG_STARTING_NODES_OFFSET == 17
    assert PSG_STARTING_NODES_COUNT == 6
    assert PSG_STARTING_NODE_SIZE == 8


def test_field_offsets_documented_layout():
    """The first 65 bytes of every row follow this fixed layout."""
    assert FIELD_OFFSETS["metadata_path_ptr"] == 0
    assert FIELD_OFFSETS["class_name_ptr"] == 8
    assert FIELD_OFFSETS["animation_path_ptr"] == 16
    assert FIELD_OFFSETS["actor_path_ptr"] == 24
    assert FIELD_OFFSETS["attribute_count"] == 48
    assert FIELD_OFFSETS["row_index"] == 64


# ---------------------------------------------------------------------------
# Class / attribute / PSG dicts
# ---------------------------------------------------------------------------


def test_attribute_to_psg_index_complete_six():
    """All six attribute combinations map to distinct PSG indices 0..5."""
    assert set(ATTRIBUTE_TO_PSG_INDEX.values()) == {0, 1, 2, 3, 4, 5}
    assert set(ATTRIBUTE_TO_PSG_INDEX.keys()) == {"Dex", "Str", "DexInt", "Int", "StrInt", "StrDex"}


def test_psg_starting_nodes_six_distinct_ids():
    """Six classes, six unique starting node IDs."""
    assert set(PSG_STARTING_NODES.keys()) == {0, 1, 2, 3, 4, 5}
    assert len(set(PSG_STARTING_NODES.values())) == 6


def test_class_names_base_and_ascendancy_split():
    """Row 0-5 are base (PoE1 names), 6-11 are ascendancy (PoE2 names)."""
    base = {CLASS_NAMES[i] for i in range(6)}
    asc = {CLASS_NAMES[i] for i in range(6, 12)}
    assert base == {"Marauder", "Witch", "Ranger", "Duelist", "Shadow", "Templar"}
    assert asc == {"Warrior", "Sorceress", "Huntress", "Mercenary", "Monk", "Druid"}
    # No overlap between base and ascendancy names
    assert base.isdisjoint(asc)


def test_poe_ninja_mapping_round_trip_consistency():
    """For every poe.ninja class name, the documented starting node must equal
    PSG_STARTING_NODES[POE_NINJA_CLASS_TO_PSG_INDEX[name]]. If they drift, the
    poe.ninja-fed tools will return wrong starting nodes."""
    for name, expected_node_id in POE_NINJA_CLASS_TO_STARTING_NODE.items():
        psg_index = POE_NINJA_CLASS_TO_PSG_INDEX[name]
        assert PSG_STARTING_NODES[psg_index] == expected_node_id, (
            f"poe.ninja {name!r}: declared starting node {expected_node_id} "
            f"!= PSG_STARTING_NODES[{psg_index}] = {PSG_STARTING_NODES[psg_index]}"
        )


def test_poe_ninja_sorceress_is_strint():
    """Documented quirk: poe.ninja calls Druid/Templar 'Sorceress'. Lock this
    in so a future 'fix' doesn't break character lookup."""
    assert POE_NINJA_CLASS_TO_PSG_INDEX["Sorceress"] == 4  # StrInt
    # And ATTRIBUTE_TO_PSG_INDEX agrees that StrInt -> 4
    assert ATTRIBUTE_TO_PSG_INDEX["StrInt"] == 4


# ---------------------------------------------------------------------------
# CharacterRecord
# ---------------------------------------------------------------------------


def test_character_record_base_class_index_for_base_row():
    rec = CharacterRecord(
        row_index=2,  # Ranger (base)
        metadata_path_ptr=0,
        class_name_ptr=0,
        animation_path_ptr=0,
        actor_path_ptr=0,
        attribute_count=5,
        is_ascendancy=False,
    )
    assert rec.base_class_index == 2


def test_character_record_base_class_index_for_ascendancy_row():
    """row_index 8 = Huntress (ascendancy); base class is Ranger (index 2)."""
    rec = CharacterRecord(
        row_index=8,
        metadata_path_ptr=0,
        class_name_ptr=0,
        animation_path_ptr=0,
        actor_path_ptr=0,
        attribute_count=5,
        is_ascendancy=True,
    )
    assert rec.base_class_index == 2  # 8 - 6


# ---------------------------------------------------------------------------
# extract_attribute_type
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path, expected",
    [
        ("Metadata/Characters/Str/StrFour", "Str"),
        ("Metadata/Characters/DexInt/DexIntFour", "DexInt"),
        ("Metadata/Characters/Int/IntFour", "Int"),
        ("Metadata/Characters/StrDex/StrDexFour", "StrDex"),
        # Malformed paths return empty string, don't raise
        ("Short", ""),
        ("Foo/Bar", ""),
        ("", ""),
    ],
)
def test_extract_attribute_type(path, expected):
    assert extract_attribute_type(path) == expected


# ---------------------------------------------------------------------------
# parse_character_row
# ---------------------------------------------------------------------------


def test_parse_character_row_rejects_too_small():
    """Unlike mods_spec (which uses `<` for 0.5 growth), characters_spec uses
    strict `!=` — the format hasn't changed and any size mismatch is a real bug."""
    with pytest.raises(ValueError, match="Expected 656"):
        parse_character_row(b"\x00" * (CHARACTER_ROW_SIZE - 1))


def test_parse_character_row_rejects_too_large():
    """Strict equality, not >= — oversized data also rejected."""
    with pytest.raises(ValueError, match="Expected 656"):
        parse_character_row(b"\x00" * (CHARACTER_ROW_SIZE + 1))


def test_parse_character_row_accepts_exact_size():
    row = make_character_row()
    rec = parse_character_row(row, row_index=3)
    assert rec.row_index == 3


def test_parse_character_row_reads_core_fields():
    row = make_character_row(
        metadata_path_ptr=0xABCD,
        class_name_ptr=0x1234,
        animation_path_ptr=0x5678,
        actor_path_ptr=0x9ABC,
        attribute_count=8,  # Str
    )
    rec = parse_character_row(row, row_index=0)
    assert rec.metadata_path_ptr == 0xABCD
    assert rec.class_name_ptr == 0x1234
    assert rec.animation_path_ptr == 0x5678
    assert rec.actor_path_ptr == 0x9ABC
    assert rec.attribute_count == 8


# ---------------------------------------------------------------------------
# read_psg_starting_nodes
# ---------------------------------------------------------------------------


def test_read_psg_starting_nodes_returns_six_uint64s(tmp_path):
    """Synthesize a PSG header with known node IDs and verify the reader."""
    fake_node_ids = [11, 22, 33, 44, 55, 66]
    psg = tmp_path / "fake.psg"
    # 17 leading bytes of garbage, then 6 uint64 LE
    buf = bytearray(PSG_STARTING_NODES_OFFSET)
    for nid in fake_node_ids:
        buf += struct.pack("<Q", nid)
    psg.write_bytes(bytes(buf))

    result = read_psg_starting_nodes(str(psg))
    assert result == fake_node_ids


def test_read_psg_starting_nodes_matches_documented_ids(tmp_path):
    """Round-trip: a PSG written with PSG_STARTING_NODES values must read back
    identically."""
    psg = tmp_path / "real_like.psg"
    buf = bytearray(PSG_STARTING_NODES_OFFSET)
    for i in range(PSG_STARTING_NODES_COUNT):
        buf += struct.pack("<Q", PSG_STARTING_NODES[i])
    psg.write_bytes(bytes(buf))

    result = read_psg_starting_nodes(str(psg))
    for i, node_id in enumerate(result):
        assert (
            node_id == PSG_STARTING_NODES[i]
        ), f"PSG index {i}: read {node_id}, expected {PSG_STARTING_NODES[i]}"


# ---------------------------------------------------------------------------
# get_class_to_starting_node_mapping
# ---------------------------------------------------------------------------


def test_get_class_to_starting_node_mapping_includes_all_class_names():
    """Function should produce an entry for every name in CLASS_NAMES."""
    mapping = get_class_to_starting_node_mapping()
    # All 12 class names should appear as keys
    for class_name in CLASS_NAMES.values():
        assert class_name in mapping, f"{class_name} missing from class->node mapping"


def test_get_class_to_starting_node_mapping_base_and_ascendancy_share_node():
    """Base class and its corresponding ascendancy share starting node:
    Marauder (Str base) <-> Warrior (Str ascendancy) -> 47175."""
    mapping = get_class_to_starting_node_mapping()
    # Marauder/Warrior both Str
    assert mapping["Marauder"] == mapping["Warrior"]
    # Witch/Sorceress both Int
    assert mapping["Witch"] == mapping["Sorceress"]
    # Ranger/Huntress both Dex
    assert mapping["Ranger"] == mapping["Huntress"]
    # Duelist/Mercenary both StrDex
    assert mapping["Duelist"] == mapping["Mercenary"]
    # Shadow/Monk both DexInt
    assert mapping["Shadow"] == mapping["Monk"]
    # Templar/Druid both StrInt
    assert mapping["Templar"] == mapping["Druid"]


def test_get_class_to_starting_node_mapping_matches_psg_table():
    """For every name in the mapping, the node ID must be one of the documented
    PSG_STARTING_NODES values."""
    mapping = get_class_to_starting_node_mapping()
    valid_node_ids = set(PSG_STARTING_NODES.values())
    for class_name, node_id in mapping.items():
        assert (
            node_id in valid_node_ids
        ), f"{class_name} -> {node_id}, not in PSG_STARTING_NODES values {valid_node_ids}"
