"""
Path of Building import functionality
Complete XML parser for PoB builds
"""

import base64
import binascii
import logging
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Standard base64 alphabet (post URL-safe normalisation) — used to pinpoint
# corrupt characters in share codes instead of surfacing a raw binascii error.
_B64_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")


class PoBImporter:
    """Import builds from Path of Building format"""

    def _decode_pob_code(self, pob_code: str) -> str:
        """
        Decode a PoB share code (base64 + zlib) into the XML string.

        Tolerates whitespace/newlines and PoB's URL-safe base64 variant
        ('-'/'_' for '+'/'/') and missing padding. Failures raise ValueError
        with diagnostics (length, corrupt-char position, truncation hint)
        rather than raw binascii/zlib errors — agent callers reproduce long
        codes imperfectly and need to know WHERE it broke.
        """
        code = "".join(pob_code.split())
        if not code:
            raise ValueError("PoB code is empty after stripping whitespace")

        # PoB share codes use URL-safe base64; standard alphabet never
        # contains '-'/'_' so this translation is lossless either way.
        code = code.replace("-", "+").replace("_", "/")

        bad = [(i, c) for i, c in enumerate(code) if c not in _B64_CHARS]
        if bad:
            idx, char = bad[0]
            raise ValueError(
                f"PoB code contains {len(bad)} non-base64 character(s); first is "
                f"{char!r} at position {idx} of {len(code)}. The code was corrupted "
                f"in transit — pass the export via a file (pob_file_path) instead "
                f"of inline text."
            )

        code += "=" * (-len(code) % 4)

        try:
            decoded = base64.b64decode(code)
        except binascii.Error as e:
            raise ValueError(f"Base64 decode failed for PoB code ({len(code)} chars): {e}")

        try:
            decompressed = zlib.decompress(decoded)
        except zlib.error as e:
            raise ValueError(
                f"PoB code base64-decoded cleanly ({len(decoded)} bytes) but zlib "
                f"decompression failed: {e}. The code is truncated or corrupted "
                f"mid-stream — a single wrong character breaks the whole stream. "
                f"Save the exact export to a file and import via pob_file_path, "
                f"or supply the uncompressed XML directly."
            )

        return decompressed.decode("utf-8")

    def _build_data_from_root(self, root: ET.Element) -> Dict[str, Any]:
        """Extract the build dictionary from a parsed PoB XML root."""
        return {
            "name": self._get_build_name(root),
            "level": self._get_build_level(root),
            "class": self._get_build_class(root),
            "ascendancy": self._get_ascendancy(root),
            "items": self._parse_items(root),
            "skills": self._parse_skills(root),
            "tree": self._parse_tree(root),
            "config": self._parse_config(root),
            "stats": self._extract_stats(root),
            "notes": self._get_notes(root),
            "version": root.get("version", "Unknown"),
        }

    def import_build_sync(self, pob_code: str) -> Dict[str, Any]:
        """
        Synchronously import a PoB build code. PoB import is entirely
        CPU-bound (base64 + zlib + XML parsing), so a sync entry point lets
        callers invoke it from sync code paths (e.g. the character data
        normaliser at fetch time, #132). Same return shape as ``import_build``.

        Args:
            pob_code: Base64-encoded PoB build (whitespace and URL-safe
                base64 tolerated)

        Returns:
            Build data dictionary
        """
        try:
            xml_str = self._decode_pob_code(pob_code)
            return self.import_xml_sync(xml_str)
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"PoB import failed: {e}", exc_info=True)
            raise ValueError(f"Invalid PoB code: {str(e)}")

    def import_xml_sync(self, xml_str: str) -> Dict[str, Any]:
        """
        Import a build from raw (uncompressed) PoB XML.

        Args:
            xml_str: PoB build XML as a string (BOM tolerated)

        Returns:
            Build data dictionary
        """
        try:
            root = ET.fromstring(xml_str.lstrip("﻿").strip())
        except ET.ParseError as e:
            raise ValueError(f"Invalid PoB XML: {e}")

        try:
            build_data = self._build_data_from_root(root)
        except Exception as e:
            logger.error(f"PoB XML parse failed: {e}", exc_info=True)
            raise ValueError(f"Failed to parse PoB build XML: {str(e)}")

        logger.info(f"Successfully imported build: {build_data['name']}")
        return build_data

    async def import_build(self, pob_code: str) -> Dict[str, Any]:
        """
        Import a PoB build code (async wrapper around ``import_build_sync``).

        Args:
            pob_code: Base64-encoded PoB build

        Returns:
            Build data dictionary
        """
        return self.import_build_sync(pob_code)

    async def import_xml(self, xml_str: str) -> Dict[str, Any]:
        """Import raw PoB XML (async wrapper around ``import_xml_sync``)."""
        return self.import_xml_sync(xml_str)

    async def import_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Import a PoB build from a local file. The file may contain either
        the raw build XML (a saved .xml build) or a base64 share code
        (e.g. a .txt the export was pasted into) — auto-detected.

        Args:
            file_path: Path to the PoB build file

        Returns:
            Build data dictionary
        """
        path = Path(file_path).expanduser()
        try:
            # utf-8-sig strips a BOM if present (Notepad saves leave one)
            content = path.read_text(encoding="utf-8-sig")
        except OSError as e:
            raise ValueError(f"Cannot read PoB file {path}: {e}")

        try:
            if content.lstrip().startswith("<"):
                build_data = self.import_xml_sync(content)
            else:
                build_data = self.import_build_sync(content)
        except ValueError as e:
            raise ValueError(f"Failed to import build from {path}: {e}")

        logger.info(f"Successfully imported build from file: {file_path}")
        return build_data

    def _get_build_name(self, root: ET.Element) -> str:
        """Extract build name"""
        build_elem = root.find("./Build")
        if build_elem is not None:
            return build_elem.get("name", "Unnamed Build")
        return root.get("name", "Unnamed Build")

    def _get_build_level(self, root: ET.Element) -> int:
        """Extract character level"""
        build_elem = root.find("./Build")
        if build_elem is not None:
            return int(build_elem.get("level", 0))
        return 0

    def _get_build_class(self, root: ET.Element) -> str:
        """Extract character class"""
        build_elem = root.find("./Build")
        if build_elem is not None:
            return build_elem.get("className", "Unknown")
        return "Unknown"

    def _get_ascendancy(self, root: ET.Element) -> Optional[str]:
        """Extract ascendancy class"""
        build_elem = root.find("./Build")
        if build_elem is not None:
            return build_elem.get("ascendClassName")
        return None

    def _get_notes(self, root: ET.Element) -> str:
        """Extract build notes"""
        notes_elem = root.find("./Notes")
        if notes_elem is not None and notes_elem.text:
            return notes_elem.text
        return ""

    def _parse_items(self, root: ET.Element) -> List[Dict[str, Any]]:
        """
        Parse items from PoB XML.

        Items live in <Items> as <Item id=N> elements WITHOUT slot
        attributes — the equipped-slot assignments live separately in
        <ItemSet><Slot name="Gloves" itemId="9"/>. Build the id->slot map
        from the (first/default) ItemSet so equipped items carry their
        slot; unassigned items (spares/swaps) keep slot=None.
        """
        items = []
        items_elem = root.find("./Items")

        if items_elem is None:
            return items

        # id -> slot name from the default ItemSet's Slot assignments
        slot_by_item_id: Dict[str, str] = {}
        item_set = items_elem.find("ItemSet") or root.find(".//ItemSet")
        if item_set is not None:
            for slot_elem in item_set.findall("Slot"):
                item_id = slot_elem.get("itemId")
                slot_name = slot_elem.get("name")
                if item_id and item_id != "0" and slot_name:
                    slot_by_item_id[item_id] = slot_name

        for item_elem in items_elem.findall("Item"):
            item_id = item_elem.get("id")
            slot = self._get_item_slot(item_elem) or slot_by_item_id.get(item_id)
            item_data = {
                "id": item_id,
                "slot": slot,
                "weapon_set": self._weapon_set_for_slot(slot),
                "raw_text": item_elem.text or "",
                "enabled": item_elem.get("enabled", "1") == "1",
            }

            # Parse item text to extract properties
            if item_data["raw_text"]:
                item_data.update(self._parse_item_text(item_data["raw_text"]))

            items.append(item_data)

        return items

    @staticmethod
    def _weapon_set_for_slot(slot: Optional[str]) -> Optional[int]:
        """Map a PoB slot name to its weapon set.

        PoE2 weapon swap: "Weapon 1"/"Weapon 2" are weapon set 1;
        "Weapon 1 Swap"/"Weapon 2 Swap" are weapon set 2. Only ONE set is
        active at a time, so set-specific weapon stats (e.g. a staff's
        +%% chaos, +spirit) apply only while that set is equipped — a
        consumer flattening both sets into one gear list will wrongly
        attribute swap-set stats to the active build (the #182-era
        analyze_character bug). Non-weapon slots return None (always
        equipped, set-independent).
        """
        if not slot:
            return None
        if slot.startswith("Weapon") and "Swap" in slot:
            return 2
        if slot.startswith("Weapon"):
            return 1
        return None

    def _get_item_slot(self, item_elem: ET.Element) -> Optional[str]:
        """Determine which slot an item is equipped in"""
        # PoB uses item set slots like "Weapon 1", "Body Armour", etc.
        return item_elem.get("slot")

    def _parse_item_text(self, text: str) -> Dict[str, Any]:
        """
        Parse PoB item text format (in-game tooltip shape):

            Rarity: UNIQUE
            The Dark Defiler          <- item NAME
            Rattling Sceptre          <- base type
            ...stats/mods...

        The name is the line AFTER the Rarity line (the old code took the
        first line, which IS the Rarity line — every item rendered as
        'Rarity: UNIQUE'). Lines arrive indented/blank-padded in real
        exports, so each is stripped first.
        """
        lines = [ln.strip() for ln in text.strip().split("\n") if ln.strip()]
        if not lines:
            return {}

        name = "Unknown"
        base_type = ""
        # Locate the Rarity line; name and base type follow it
        rarity_idx = next(
            (i for i, ln in enumerate(lines) if ln.lower().startswith("rarity:")),
            None,
        )
        if rarity_idx is not None and rarity_idx + 1 < len(lines):
            name = lines[rarity_idx + 1]
            candidate = lines[rarity_idx + 2] if rarity_idx + 2 < len(lines) else ""
            # The base-type line never contains ':' (metadata lines do) and
            # Normal/Magic items have no separate name line to follow
            if candidate and ":" not in candidate:
                base_type = candidate
        elif lines:
            name = lines[0]

        return {
            "name": name,
            "type_line": base_type,
            "base_type": base_type,
            "item_level": self._extract_item_level(text),
            "rarity": self._extract_rarity(text),
            "requirements": self._extract_requirements(text),
            "mods": self._extract_mods(text),
            "full_text": text,
        }

    def _extract_item_level(self, text: str) -> int:
        """Extract item level from text"""
        import re

        match = re.search(r"Item Level: (\d+)", text)
        return int(match.group(1)) if match else 0

    def _extract_rarity(self, text: str) -> str:
        """Extract item rarity"""
        if "Rarity: UNIQUE" in text or "Rarity: Unique" in text:
            return "Unique"
        elif "Rarity: RARE" in text or "Rarity: Rare" in text:
            return "Rare"
        elif "Rarity: MAGIC" in text or "Rarity: Magic" in text:
            return "Magic"
        return "Normal"

    def _extract_requirements(self, text: str) -> Dict[str, int]:
        """Extract stat requirements"""
        import re

        reqs = {}

        str_match = re.search(r"Requires Level \d+.*?(\d+) Str", text)
        if str_match:
            reqs["strength"] = int(str_match.group(1))

        dex_match = re.search(r"(\d+) Dex", text)
        if dex_match:
            reqs["dexterity"] = int(dex_match.group(1))

        int_match = re.search(r"(\d+) Int", text)
        if int_match:
            reqs["intelligence"] = int(int_match.group(1))

        return reqs

    def _extract_mods(self, text: str) -> List[str]:
        """Extract item mods/affixes"""
        # This is simplified - full implementation would parse all mod lines
        lines = text.split("\n")
        mods = []

        # Skip header lines and find mod lines (usually between separators)
        in_mods = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Mod lines typically contain numbers and stats
            if any(char.isdigit() for char in line) and "+" in line or "%" in line:
                mods.append(line)

        return mods

    def _parse_skills(self, root: ET.Element) -> List[Dict[str, Any]]:
        """
        Parse skills from PoB XML
        Skills are grouped with their support gems
        """
        skills = []
        skills_elem = root.find("./Skills")

        if skills_elem is None:
            return skills

        for skill_set in skills_elem.findall("SkillSet"):
            for skill in skill_set.findall("Skill"):
                skill_data = {
                    "label": skill.get("label", ""),
                    "enabled": skill.get("enabled", "true") == "true",
                    "slot": skill.get("slot"),
                    "gems": [],
                }

                # Parse gems in this skill group
                for gem in skill.findall("Gem"):
                    gem_data = {
                        "name": gem.get("nameSpec", gem.get("gemId", "Unknown")),
                        "level": int(gem.get("level", 1)),
                        "quality": int(gem.get("quality", 0)),
                        "enabled": gem.get("enabled", "true") == "true",
                        "skill_id": gem.get("skillId"),
                    }
                    skill_data["gems"].append(gem_data)

                skills.append(skill_data)

        return skills

    def _parse_tree(self, root: ET.Element) -> Dict[str, Any]:
        """
        Parse passive tree data
        """
        tree_elem = root.find("./Tree")
        if tree_elem is None:
            return {}

        # Parse allocated nodes
        spec_elem = tree_elem.find("Spec")
        allocated_nodes = []

        if spec_elem is not None:
            nodes_str = spec_elem.get("nodes", "")
            if nodes_str:
                allocated_nodes = [int(node) for node in nodes_str.split(",") if node.strip()]

        tree_data = {
            "allocated_nodes": allocated_nodes,
            "total_points": len(allocated_nodes),
            "ascendancy_nodes": [],  # Could parse separately
            "mastery_effects": {},  # PoE 2 masteries
        }

        return tree_data

    def _parse_config(self, root: ET.Element) -> Dict[str, Any]:
        """
        Parse configuration options
        These affect calculations (boss, map mods, etc.)
        """
        config = {}
        config_elem = root.find("./Config")

        if config_elem is not None:
            for input_elem in config_elem.findall("Input"):
                name = input_elem.get("name")
                value = (
                    input_elem.get("string")
                    or input_elem.get("number")
                    or input_elem.get("boolean")
                )
                if name:
                    config[name] = value

        return config

    def _extract_stats(self, root: ET.Element) -> Dict[str, Any]:
        """
        Extract calculated stats if available
        Note: PoB calculates these, they're not always in the XML
        """
        # This is a placeholder - actual stat extraction would require
        # running PoB's calculation engine or parsing build notes
        return {"note": "Stats must be calculated using PoB engine or extracted from character API"}
