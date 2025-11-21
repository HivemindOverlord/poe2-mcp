"""
Path of Building import functionality
Complete XML parser for PoB builds
"""

import base64
import zlib
import logging
from typing import Dict, Any, List, Optional
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


class PoBImporter:
    """Import builds from Path of Building format"""

    async def import_build(self, pob_code: str) -> Dict[str, Any]:
        """
        Import a PoB build code

        Args:
            pob_code: Base64-encoded PoB build

        Returns:
            Build data dictionary
        """
        try:
            # Decode and decompress
            decoded = base64.b64decode(pob_code)
            decompressed = zlib.decompress(decoded)
            xml_str = decompressed.decode('utf-8')

            # Parse XML
            root = ET.fromstring(xml_str)

            # Extract all build components
            build_data = {
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
                "version": root.get('version', 'Unknown')
            }

            logger.info(f"Successfully imported build: {build_data['name']}")
            return build_data

        except Exception as e:
            logger.error(f"PoB import failed: {e}", exc_info=True)
            raise ValueError(f"Invalid PoB code: {str(e)}")

    async def import_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Import a PoB build from an XML file

        Args:
            file_path: Path to the PoB XML file

        Returns:
            Build data dictionary
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                xml_str = f.read()

            root = ET.fromstring(xml_str)

            # Use the same parsing logic as import_build
            build_data = {
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
                "version": root.get('version', 'Unknown')
            }

            logger.info(f"Successfully imported build from file: {file_path}")
            return build_data

        except Exception as e:
            logger.error(f"Failed to import build from file: {e}", exc_info=True)
            raise ValueError(f"Failed to import build from {file_path}: {str(e)}")

    def _get_build_name(self, root: ET.Element) -> str:
        """Extract build name"""
        build_elem = root.find('./Build')
        if build_elem is not None:
            return build_elem.get('name', 'Unnamed Build')
        return root.get('name', 'Unnamed Build')

    def _get_build_level(self, root: ET.Element) -> int:
        """Extract character level"""
        build_elem = root.find('./Build')
        if build_elem is not None:
            return int(build_elem.get('level', 0))
        return 0

    def _get_build_class(self, root: ET.Element) -> str:
        """Extract character class"""
        build_elem = root.find('./Build')
        if build_elem is not None:
            return build_elem.get('className', 'Unknown')
        return 'Unknown'

    def _get_ascendancy(self, root: ET.Element) -> Optional[str]:
        """Extract ascendancy class"""
        build_elem = root.find('./Build')
        if build_elem is not None:
            return build_elem.get('ascendClassName')
        return None

    def _get_notes(self, root: ET.Element) -> str:
        """Extract build notes"""
        notes_elem = root.find('./Notes')
        if notes_elem is not None and notes_elem.text:
            return notes_elem.text
        return ""

    def _parse_items(self, root: ET.Element) -> List[Dict[str, Any]]:
        """
        Parse items from PoB XML
        Items are stored in <Items> section with individual <Item> elements
        """
        items = []
        items_elem = root.find('./Items')

        if items_elem is None:
            return items

        for item_elem in items_elem.findall('Item'):
            item_data = {
                'id': item_elem.get('id'),
                'slot': self._get_item_slot(item_elem),
                'raw_text': item_elem.text or '',
                'enabled': item_elem.get('enabled', '1') == '1'
            }

            # Parse item text to extract properties
            if item_data['raw_text']:
                item_data.update(self._parse_item_text(item_data['raw_text']))

            items.append(item_data)

        return items

    def _get_item_slot(self, item_elem: ET.Element) -> Optional[str]:
        """Determine which slot an item is equipped in"""
        # PoB uses item set slots like "Weapon 1", "Body Armour", etc.
        return item_elem.get('slot')

    def _parse_item_text(self, text: str) -> Dict[str, Any]:
        """
        Parse PoB item text format
        Format is similar to in-game item tooltips
        """
        lines = text.strip().split('\n')
        if not lines:
            return {}

        return {
            'name': lines[0] if lines else 'Unknown',
            'item_level': self._extract_item_level(text),
            'rarity': self._extract_rarity(text),
            'requirements': self._extract_requirements(text),
            'mods': self._extract_mods(text),
            'full_text': text
        }

    def _extract_item_level(self, text: str) -> int:
        """Extract item level from text"""
        import re
        match = re.search(r'Item Level: (\d+)', text)
        return int(match.group(1)) if match else 0

    def _extract_rarity(self, text: str) -> str:
        """Extract item rarity"""
        if 'Rarity: UNIQUE' in text or 'Rarity: Unique' in text:
            return 'Unique'
        elif 'Rarity: RARE' in text or 'Rarity: Rare' in text:
            return 'Rare'
        elif 'Rarity: MAGIC' in text or 'Rarity: Magic' in text:
            return 'Magic'
        return 'Normal'

    def _extract_requirements(self, text: str) -> Dict[str, int]:
        """Extract stat requirements"""
        import re
        reqs = {}

        str_match = re.search(r'Requires Level \d+.*?(\d+) Str', text)
        if str_match:
            reqs['strength'] = int(str_match.group(1))

        dex_match = re.search(r'(\d+) Dex', text)
        if dex_match:
            reqs['dexterity'] = int(dex_match.group(1))

        int_match = re.search(r'(\d+) Int', text)
        if int_match:
            reqs['intelligence'] = int(int_match.group(1))

        return reqs

    def _extract_mods(self, text: str) -> List[str]:
        """Extract item mods/affixes"""
        # This is simplified - full implementation would parse all mod lines
        lines = text.split('\n')
        mods = []

        # Skip header lines and find mod lines (usually between separators)
        in_mods = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Mod lines typically contain numbers and stats
            if any(char.isdigit() for char in line) and '+' in line or '%' in line:
                mods.append(line)

        return mods

    def _parse_skills(self, root: ET.Element) -> List[Dict[str, Any]]:
        """
        Parse skills from PoB XML
        Skills are grouped with their support gems
        """
        skills = []
        skills_elem = root.find('./Skills')

        if skills_elem is None:
            return skills

        for skill_set in skills_elem.findall('SkillSet'):
            for skill in skill_set.findall('Skill'):
                skill_data = {
                    'label': skill.get('label', ''),
                    'enabled': skill.get('enabled', 'true') == 'true',
                    'slot': skill.get('slot'),
                    'gems': []
                }

                # Parse gems in this skill group
                for gem in skill.findall('Gem'):
                    gem_data = {
                        'name': gem.get('nameSpec', gem.get('gemId', 'Unknown')),
                        'level': int(gem.get('level', 1)),
                        'quality': int(gem.get('quality', 0)),
                        'enabled': gem.get('enabled', 'true') == 'true',
                        'skill_id': gem.get('skillId')
                    }
                    skill_data['gems'].append(gem_data)

                skills.append(skill_data)

        return skills

    def _parse_tree(self, root: ET.Element) -> Dict[str, Any]:
        """
        Parse passive tree data
        """
        tree_elem = root.find('./Tree')
        if tree_elem is None:
            return {}

        # Parse allocated nodes
        spec_elem = tree_elem.find('Spec')
        allocated_nodes = []

        if spec_elem is not None:
            nodes_str = spec_elem.get('nodes', '')
            if nodes_str:
                allocated_nodes = [int(node) for node in nodes_str.split(',') if node.strip()]

        tree_data = {
            'allocated_nodes': allocated_nodes,
            'total_points': len(allocated_nodes),
            'ascendancy_nodes': [],  # Could parse separately
            'mastery_effects': {}     # PoE 2 masteries
        }

        return tree_data

    def _parse_config(self, root: ET.Element) -> Dict[str, Any]:
        """
        Parse configuration options
        These affect calculations (boss, map mods, etc.)
        """
        config = {}
        config_elem = root.find('./Config')

        if config_elem is not None:
            for input_elem in config_elem.findall('Input'):
                name = input_elem.get('name')
                value = input_elem.get('string') or input_elem.get('number') or input_elem.get('boolean')
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
        return {
            'note': 'Stats must be calculated using PoB engine or extracted from character API'
        }
