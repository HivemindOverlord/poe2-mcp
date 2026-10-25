"""
Path of Building XML Generator
Converts character data to PoB-compatible XML format.

https://github.com/HivemindOverlord/poe2-mcp
"""

import base64
import logging
import xml.etree.ElementTree as ET
import zlib
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PoBXMLGenerator:
    """
    Generates Path of Building XML from character data.

    Supports conversion from poe.ninja character format to PoB XML.
    """

    # Class name to ID mapping
    CLASS_IDS = {
        "Warrior": 0,
        "Ranger": 1,
        "Witch": 2,
        "Duelist": 3,
        "Marauder": 4,
        "Shadow": 5,
        "Templar": 6,
        "Mercenary": 7,
        "Monk": 8,
        "Huntress": 9,
        "Sorceress": 10,
        "Druid": 11,
    }

    # Ascendancy to ID mapping (within class)
    ASCENDANCY_IDS = {
        # Warrior
        "Titan": 1,
        "Warbringer": 2,
        # Ranger
        "Deadeye": 1,
        "Pathfinder": 2,
        # Witch
        "Lich": 1,
        "Infernalist": 2,
        # Mercenary
        "Witchhunter": 1,
        "Gemling Legionnaire": 2,
        # Monk
        "Invoker": 1,
        "Acolyte of Chayula": 2,
        # Sorceress
        "Stormweaver": 1,
        "Chronomancer": 2,
    }

    # Slot name mapping from poe.ninja to PoB
    SLOT_MAPPING = {
        "Helm": "Helmet",
        "BodyArmour": "Body Armour",
        "Gloves": "Gloves",
        "Boots": "Boots",
        "Weapon": "Weapon 1",
        "Weapon2": "Weapon 1 Swap",
        "Offhand": "Weapon 2",
        "Offhand2": "Weapon 2 Swap",
        "Amulet": "Amulet",
        "Ring": "Ring 1",
        "Ring2": "Ring 2",
        "Belt": "Belt",
    }

    def __init__(self):
        """Initialize the XML generator."""
        pass

    def generate(self, character_data: Dict[str, Any]) -> str:
        """
        Generate PoB XML from character data.

        Args:
            character_data: Character data dict with keys:
                - name: Character name
                - level: Character level
                - class: Class name
                - ascendancy: Ascendancy name (optional)
                - account: Account name (optional)
                - passives: Dict with 'hashes' list of node IDs
                - equipment: List of item dicts
                - skills: List of skill group dicts

        Returns:
            XML string compatible with Path of Building
        """
        root = ET.Element("PathOfBuilding2")

        # Build section
        self._add_build_section(root, character_data)

        # Import section (for reference)
        self._add_import_section(root, character_data)

        # Spec section (passive tree)
        if "passives" in character_data:
            self._add_spec_section(root, character_data)

        # Tree section (wrapper for multiple specs)
        self._add_tree_section(root, character_data)

        # Items section
        if "equipment" in character_data:
            self._add_items_section(root, character_data)

        # Skills section
        if "skills" in character_data:
            self._add_skills_section(root, character_data)

        # Config section
        self._add_config_section(root, character_data)

        # Notes section
        self._add_notes_section(root, character_data)

        # Convert to string
        return ET.tostring(root, encoding="unicode")

    def _add_build_section(self, root: ET.Element, data: Dict[str, Any]):
        """Add Build element with character metadata."""
        build = ET.SubElement(root, "Build")
        build.set("targetVersion", "0_3")
        build.set("level", str(data.get("level", 1)))
        build.set("className", data.get("class", "Warrior"))

        ascendancy = data.get("ascendancy", "")
        if ascendancy:
            build.set("ascendClassName", ascendancy)

        build.set("mainSocketGroup", "1")
        build.set("viewMode", "TREE")

    def _add_import_section(self, root: ET.Element, data: Dict[str, Any]):
        """Add Import element with source reference."""
        import_elem = ET.SubElement(root, "Import")
        account = data.get("account", "")
        character = data.get("name", "")
        if account and character:
            import_elem.set(
                "importLink", f"https://poe.ninja/poe2/builds/char/{account}/{character}"
            )

    def _add_spec_section(self, root: ET.Element, data: Dict[str, Any]):
        """Add Spec element with passive tree allocation."""
        spec = ET.SubElement(root, "Spec")

        passives = data.get("passives", {})
        hashes = passives.get("hashes", [])

        # Convert to comma-separated string
        spec.set("nodes", ",".join(str(h) for h in hashes))

        class_name = data.get("class", "Warrior")
        spec.set("classId", str(self.CLASS_IDS.get(class_name, 0)))

        ascendancy = data.get("ascendancy", "")
        spec.set("ascendClassId", str(self.ASCENDANCY_IDS.get(ascendancy, 0)))

        spec.set("treeVersion", "0_3")

        # Add jewel sockets if present
        jewel_data = passives.get("jewel_data", {})
        if jewel_data:
            sockets = ET.SubElement(spec, "Sockets")
            for node_id, jewel_info in jewel_data.items():
                socket_elem = ET.SubElement(sockets, "Socket")
                socket_elem.set("nodeId", str(node_id))
                if "itemId" in jewel_info:
                    socket_elem.set("itemId", str(jewel_info["itemId"]))

    def _add_tree_section(self, root: ET.Element, data: Dict[str, Any]):
        """Add Tree element (wrapper for spec list)."""
        tree = ET.SubElement(root, "Tree")
        tree.set("activeSpec", "1")

        # Create spec entry
        passives = data.get("passives", {})
        hashes = passives.get("hashes", [])

        spec = ET.SubElement(tree, "Spec")
        spec.set("title", "Main")
        spec.set("nodes", ",".join(str(h) for h in hashes))

        class_name = data.get("class", "Warrior")
        spec.set("classId", str(self.CLASS_IDS.get(class_name, 0)))

        ascendancy = data.get("ascendancy", "")
        spec.set("ascendClassId", str(self.ASCENDANCY_IDS.get(ascendancy, 0)))

    def _add_items_section(self, root: ET.Element, data: Dict[str, Any]):
        """Add Items element with equipment."""
        items_elem = ET.SubElement(root, "Items")
        items_elem.set("activeItemSet", "1")

        equipment = data.get("equipment", [])

        # Create item set
        item_set = ET.SubElement(items_elem, "ItemSet")
        item_set.set("id", "1")
        item_set.set("title", "Default")

        # Add each item
        for idx, item in enumerate(equipment, 1):
            # Create Item element with full text
            item_elem = ET.SubElement(items_elem, "Item")
            item_elem.set("id", str(idx))
            item_elem.text = self._format_item_text(item)

            # Create Slot reference
            slot_name = item.get("inventoryId", "")
            pob_slot = self.SLOT_MAPPING.get(slot_name, slot_name)

            if pob_slot:
                slot = ET.SubElement(item_set, "Slot")
                slot.set("name", pob_slot)
                slot.set("itemId", str(idx))

    def _format_item_text(self, item: Dict[str, Any]) -> str:
        """Format item data as PoB item text block."""
        lines = []

        # Rarity
        rarity = item.get("frameType", 0)
        rarity_names = {0: "NORMAL", 1: "MAGIC", 2: "RARE", 3: "UNIQUE"}
        lines.append(f"Rarity: {rarity_names.get(rarity, 'RARE')}")

        # Name (for rares/uniques)
        name = item.get("name", "")
        if name:
            # Strip prefix like "<<set:MS>><<set:M>><<set:S>>"
            name = name.split(">>")[-1] if ">>" in name else name
            lines.append(name)

        # Base type
        base_type = item.get("typeLine", "")
        if base_type:
            base_type = base_type.split(">>")[-1] if ">>" in base_type else base_type
            lines.append(base_type)

        # Level requirement
        requirements = item.get("requirements", [])
        for req in requirements:
            if req.get("name") == "Level":
                values = req.get("values", [])
                if values:
                    lines.append(f"LevelReq: {values[0][0]}")
                break

        # Implicits
        implicit_mods = item.get("implicitMods", [])
        if implicit_mods:
            lines.append(f"Implicits: {len(implicit_mods)}")
            for mod in implicit_mods:
                lines.append(mod)

        # Explicit mods
        explicit_mods = item.get("explicitMods", [])
        for mod in explicit_mods:
            lines.append(mod)

        # Crafted mods
        crafted_mods = item.get("craftedMods", [])
        for mod in crafted_mods:
            lines.append(f"{{crafted}}{mod}")

        return "\n".join(lines)

    def _add_skills_section(self, root: ET.Element, data: Dict[str, Any]):
        """Add Skills element with gem setups."""
        skills_elem = ET.SubElement(root, "Skills")
        skills_elem.set("activeSkillSet", "1")
        skills_elem.set("defaultGemLevel", "20")
        skills_elem.set("defaultGemQuality", "0")

        skill_set = ET.SubElement(skills_elem, "SkillSet")
        skill_set.set("id", "1")
        skill_set.set("title", "Default")

        skills = data.get("skills", [])

        for group_idx, skill_group in enumerate(skills, 1):
            skill = ET.SubElement(skill_set, "Skill")
            skill.set("slot", skill_group.get("slot", ""))
            skill.set("enabled", "true")
            skill.set("mainActiveSkill", "1")

            gems = skill_group.get("gems", [])
            for gem_data in gems:
                gem = ET.SubElement(skill, "Gem")
                gem.set("nameSpec", gem_data.get("name", ""))
                gem.set("level", str(gem_data.get("level", 20)))
                gem.set("quality", str(gem_data.get("quality", 0)))
                gem.set("enabled", "true")

                if gem_data.get("skillId"):
                    gem.set("skillId", gem_data["skillId"])

    def _add_config_section(self, root: ET.Element, data: Dict[str, Any]):
        """Add Config element with build configuration."""
        config = ET.SubElement(root, "Config")

        # Default boss setting
        input_elem = ET.SubElement(config, "Input")
        input_elem.set("name", "enemyIsBoss")
        input_elem.set("string", "Pinnacle")

        # Add any custom config from data
        config_data = data.get("config", {})
        for key, value in config_data.items():
            inp = ET.SubElement(config, "Input")
            inp.set("name", key)
            if isinstance(value, bool):
                inp.set("boolean", str(value).lower())
            elif isinstance(value, (int, float)):
                inp.set("number", str(value))
            else:
                inp.set("string", str(value))

    def _add_notes_section(self, root: ET.Element, data: Dict[str, Any]):
        """Add Notes element with build description."""
        notes = ET.SubElement(root, "Notes")

        account = data.get("account", "Unknown")
        name = data.get("name", "Unknown")
        level = data.get("level", 1)
        char_class = data.get("class", "Unknown")
        ascendancy = data.get("ascendancy", "")

        notes_text = f"""Generated by poe2-mcp
Account: {account}
Character: {name}
Level {level} {ascendancy + ' ' if ascendancy else ''}{char_class}

https://github.com/HivemindOverlord/poe2-mcp"""

        notes.text = notes_text

    def to_pob_code(self, xml_text: str) -> str:
        """
        Convert XML to PoB share code.

        Args:
            xml_text: XML string

        Returns:
            Base64-encoded, compressed PoB code
        """
        # Compress with zlib
        compressed = zlib.compress(xml_text.encode("utf-8"), 9)

        # Encode to base64
        encoded = base64.b64encode(compressed).decode("ascii")

        # Convert to URL-safe base64 (PoB format)
        return encoded.replace("+", "-").replace("/", "_")

    def from_pob_code(self, code: str) -> str:
        """
        Convert PoB share code to XML.

        Args:
            code: PoB share code

        Returns:
            XML string
        """
        # Reverse URL-safe base64
        encoded = code.replace("-", "+").replace("_", "/")

        # Decode base64
        compressed = base64.b64decode(encoded)

        # Decompress
        return zlib.decompress(compressed).decode("utf-8")

    def generate_pob_code(self, character_data: Dict[str, Any]) -> str:
        """
        Generate a PoB share code from character data.

        Convenience method that combines generate() and to_pob_code().

        Args:
            character_data: Character data dict

        Returns:
            PoB share code string
        """
        xml = self.generate(character_data)
        return self.to_pob_code(xml)
