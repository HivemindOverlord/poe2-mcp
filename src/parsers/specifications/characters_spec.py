"""
Characters.datc64 Specification

Binary format specification for the PoE2 characters table.
Reverse-engineered from game data on 2025-01-16.

Row Size: 656 bytes
Row Count: 12 (6 base classes + 6 ascendancy classes)

The characters table contains character class definitions. In PoE2, each attribute
combination has two variants:
  - Base class (PoE1 naming): Marauder, Witch, Ranger, Duelist, Shadow, Templar
  - Ascendancy class (PoE2 naming): Warrior, Sorceress, Huntress, Mercenary, Monk, Druid

Starting node IDs are NOT stored in this table - they come from passiveskillgraph.psg
header at offset 17 (6 entries, 8 bytes each as uint64 LE).
"""

import struct
from dataclasses import dataclass
from typing import List, Optional, Tuple

# Character row constants
CHARACTER_ROW_SIZE = 656
CHARACTER_ROW_COUNT = 12

# PSG starting node header location
PSG_STARTING_NODES_OFFSET = 17
PSG_STARTING_NODES_COUNT = 6
PSG_STARTING_NODE_SIZE = 8  # uint64 little-endian

# =============================================================================
# FIELD LAYOUT (reverse-engineered)
# =============================================================================
# Field 0:  MetadataPath (String, 8 bytes)    -> offset 0
#           Example: "Metadata/Characters/Str/StrFour"
# Field 1:  ClassName (String, 8 bytes)       -> offset 8
#           Points INTO the class name string (corrupted pointer pattern)
#           Need to scan backwards for full name
# Field 2:  AnimationPath (String, 8 bytes)   -> offset 16
#           Example: "Metadata/Characters/Str/StrFour.ao"
# Field 3:  ActorPath (String, 8 bytes)       -> offset 24
#           Example: "Metadata/Characters/Str/StrFour.act"
# Field 4:  Unknown1 (Int32, 4 bytes)         -> offset 32, always 16
# Field 5:  Unknown2 (Int32, 4 bytes)         -> offset 36, always 30
# Field 6:  Unknown3 (Int32, 4 bytes)         -> offset 40, always 714
# Field 7:  Unknown4 (Int32, 4 bytes)         -> offset 44, always 2
# Field 8:  AttributeCount (Int32, 4 bytes)   -> offset 48
#           5 = single attribute (Int/Dex), 6 = dual attribute, 8 = Str
# Field 9:  Unknown5 (Int32, 4 bytes)         -> offset 52, always 8
# Field 10: Unknown6 (Int32, 4 bytes)         -> offset 56, usually 240
# Field 11: Unknown7 (Int32, 4 bytes)         -> offset 60, 0
# Field 12: RowIndex (Int32, 4 bytes)         -> offset 64, 0-11
# ... (remaining 592 bytes contain various string ptrs, stats, etc.)
# =============================================================================

FIELD_OFFSETS = {
    "metadata_path_ptr": 0,  # String pointer (8 bytes)
    "class_name_ptr": 8,  # String pointer, points into middle of name
    "animation_path_ptr": 16,  # String pointer (8 bytes)
    "actor_path_ptr": 24,  # String pointer (8 bytes)
    "unknown1": 32,  # Int32, always 16
    "unknown2": 36,  # Int32, always 30
    "unknown3": 40,  # Int32, always 714
    "unknown4": 44,  # Int32, always 2
    "attribute_count": 48,  # Int32, attribute count indicator
    "unknown5": 52,  # Int32, always 8
    "unknown6": 56,  # Int32, usually 240
    "unknown7": 60,  # Int32, usually 0
    "row_index": 64,  # Int32, row index 0-11
}


# Attribute path to PSG class index mapping
# PSG indices correspond to starting node order in passiveskillgraph.psg
ATTRIBUTE_TO_PSG_INDEX = {
    "Dex": 0,  # Ranger/Huntress
    "Str": 1,  # Marauder/Warrior
    "DexInt": 2,  # Shadow/Monk
    "Int": 3,  # Witch/Sorceress
    "StrInt": 4,  # Templar/Druid
    "StrDex": 5,  # Duelist/Mercenary
}


# PSG class index to starting node ID
# These are the node IDs from passiveskillgraph.psg header
PSG_STARTING_NODES = {
    0: 50459,  # Ranger/Huntress (Dex)
    1: 47175,  # Warrior/Marauder (Str)
    2: 50986,  # Monk/Shadow (DexInt)
    3: 61525,  # Witch/Sorceress (Int) - NOTE: poe.ninja may call this "WITCH"
    4: 54447,  # Druid/Templar (StrInt) - NOTE: poe.ninja may call this "SORCERESS"
    5: 44683,  # Mercenary/Duelist (StrDex)
}


# poe.ninja uses different naming conventions for some classes
# This maps poe.ninja class names to PSG indices
POE_NINJA_CLASS_TO_PSG_INDEX = {
    "Ranger": 0,  # Dex - same as game
    "Warrior": 1,  # Str - same as game
    "Monk": 2,  # DexInt - same as game
    "Witch": 3,  # Int - same as game
    "Sorceress": 4,  # StrInt - poe.ninja calls Druid/Templar "Sorceress"
    "Mercenary": 5,  # StrDex - same as game
}


# Map poe.ninja class names to starting node IDs
POE_NINJA_CLASS_TO_STARTING_NODE = {
    "Ranger": 50459,
    "Warrior": 47175,
    "Monk": 50986,
    "Witch": 61525,
    "Sorceress": 54447,  # This is StrInt (Druid/Templar in game files)
    "Mercenary": 44683,
}


# Class display names
# Row indices 0-5 are base classes (PoE1 naming)
# Row indices 6-11 are ascendancy classes (PoE2 naming)
CLASS_NAMES = {
    0: "Marauder",  # Base Str
    1: "Witch",  # Base Int
    2: "Ranger",  # Base Dex
    3: "Duelist",  # Base StrDex
    4: "Shadow",  # Base DexInt
    5: "Templar",  # Base StrInt
    6: "Warrior",  # Ascendancy Str
    7: "Sorceress",  # Ascendancy Int
    8: "Huntress",  # Ascendancy Dex
    9: "Mercenary",  # Ascendancy StrDex
    10: "Monk",  # Ascendancy DexInt
    11: "Druid",  # Ascendancy StrInt
}


@dataclass
class CharacterRecord:
    """Parsed character record from characters.datc64."""

    row_index: int

    # Core fields
    metadata_path_ptr: int
    class_name_ptr: int
    animation_path_ptr: int
    actor_path_ptr: int
    attribute_count: int

    # Resolved strings (filled in after parsing)
    metadata_path: str = ""
    class_name: str = ""
    animation_path: str = ""
    actor_path: str = ""

    # Computed fields
    attribute_type: str = ""
    psg_class_index: int = -1
    starting_node_id: int = -1
    is_ascendancy: bool = False

    @property
    def base_class_index(self) -> int:
        """Get the index of the base class for this character."""
        if self.is_ascendancy:
            return self.row_index - 6
        return self.row_index


def extract_attribute_type(metadata_path: str) -> str:
    """
    Extract attribute type from metadata path.

    Examples:
        "Metadata/Characters/Str/StrFour" -> "Str"
        "Metadata/Characters/DexInt/DexIntFour" -> "DexInt"
    """
    path_parts = metadata_path.split("/")
    if len(path_parts) >= 3:
        return path_parts[2]  # e.g., "Str", "Int", "Dex", "StrDex", etc.
    return ""


def parse_character_row(data: bytes, row_index: int = 0) -> CharacterRecord:
    """
    Parse a single 656-byte character row.

    Args:
        data: 656 bytes of raw character data
        row_index: Row index in the table

    Returns:
        CharacterRecord with parsed fields
    """
    if len(data) != CHARACTER_ROW_SIZE:
        raise ValueError(f"Expected {CHARACTER_ROW_SIZE} bytes, got {len(data)}")

    # Parse core fields
    metadata_path_ptr = struct.unpack("<Q", data[0:8])[0]
    class_name_ptr = struct.unpack("<Q", data[8:16])[0]
    animation_path_ptr = struct.unpack("<Q", data[16:24])[0]
    actor_path_ptr = struct.unpack("<Q", data[24:32])[0]
    attribute_count = struct.unpack("<i", data[48:52])[0]

    return CharacterRecord(
        row_index=row_index,
        metadata_path_ptr=metadata_path_ptr,
        class_name_ptr=class_name_ptr,
        animation_path_ptr=animation_path_ptr,
        actor_path_ptr=actor_path_ptr,
        attribute_count=attribute_count,
    )


def read_psg_starting_nodes(psg_path: str) -> List[int]:
    """
    Read starting node IDs from passiveskillgraph.psg header.

    Args:
        psg_path: Path to passiveskillgraph.psg file

    Returns:
        List of 6 starting node IDs (indexed by PSG class index)
    """
    with open(psg_path, "rb") as f:
        data = f.read(PSG_STARTING_NODES_OFFSET + PSG_STARTING_NODES_COUNT * PSG_STARTING_NODE_SIZE)

    nodes = []
    for i in range(PSG_STARTING_NODES_COUNT):
        offset = PSG_STARTING_NODES_OFFSET + (i * PSG_STARTING_NODE_SIZE)
        node_id = struct.unpack("<Q", data[offset : offset + 8])[0]
        nodes.append(node_id)

    return nodes


def get_class_to_starting_node_mapping() -> dict:
    """
    Get the complete mapping of class names to starting node IDs.

    Returns:
        Dictionary mapping class name to starting node ID
    """
    mapping = {}

    for row_index, class_name in CLASS_NAMES.items():
        # Determine attribute type from row index
        if row_index < 6:
            # Base classes: 0=Str, 1=Int, 2=Dex, 3=StrDex, 4=DexInt, 5=StrInt
            attr_map = {
                0: "Str",
                1: "Int",
                2: "Dex",
                3: "StrDex",
                4: "DexInt",
                5: "StrInt",
            }
        else:
            # Ascendancy classes share same attributes as base
            attr_map = {
                6: "Str",
                7: "Int",
                8: "Dex",
                9: "StrDex",
                10: "DexInt",
                11: "StrInt",
            }

        attr_type = attr_map.get(row_index, "")
        psg_index = ATTRIBUTE_TO_PSG_INDEX.get(attr_type, -1)

        if psg_index >= 0:
            starting_node = PSG_STARTING_NODES[psg_index]
            mapping[class_name] = starting_node

    return mapping


def print_class_starting_nodes():
    """Print all class-to-starting-node mappings."""
    mapping = get_class_to_starting_node_mapping()

    print("=" * 60)
    print("CLASS-TO-STARTING-NODE MAPPING")
    print("=" * 60)
    print()
    print("Game Data (from characters.datc64 + passiveskillgraph.psg):")
    print("-" * 60)
    print()
    print("Base Classes (PoE1 internal naming):")
    base_classes = [
        ("Marauder", "Str"),
        ("Witch", "Int"),
        ("Ranger", "Dex"),
        ("Duelist", "StrDex"),
        ("Shadow", "DexInt"),
        ("Templar", "StrInt"),
    ]
    for name, attr in base_classes:
        node_id = mapping.get(name, "Unknown")
        print(f"  {name:15s} ({attr:6s}) -> starting node {node_id}")

    print()
    print("Ascendancy Classes (PoE2 display naming):")
    asc_classes = [
        ("Warrior", "Str"),
        ("Sorceress", "Int"),
        ("Huntress", "Dex"),
        ("Mercenary", "StrDex"),
        ("Monk", "DexInt"),
        ("Druid", "StrInt"),
    ]
    for name, attr in asc_classes:
        node_id = mapping.get(name, "Unknown")
        print(f"  {name:15s} ({attr:6s}) -> starting node {node_id}")

    print()
    print("=" * 60)
    print("poe.ninja API Naming (for compatibility):")
    print("-" * 60)
    for name, node_id in POE_NINJA_CLASS_TO_STARTING_NODE.items():
        print(f"  {name:15s} -> starting node {node_id}")

    print()
    print("=" * 60)
    print("PSG File Structure:")
    print("-" * 60)
    print("  Location: data/extracted/metadata/passiveskillgraph.psg")
    print("  Starting node offset: 17 bytes")
    print("  Format: 6 x uint64 little-endian (8 bytes each)")
    print()
    print("  PSG Index -> Node ID -> Attribute")
    for i in range(6):
        node_id = PSG_STARTING_NODES[i]
        attr = [k for k, v in ATTRIBUTE_TO_PSG_INDEX.items() if v == i][0]
        print(f"    {i}: {node_id:5d} -> {attr}")


if __name__ == "__main__":
    print_class_starting_nodes()
