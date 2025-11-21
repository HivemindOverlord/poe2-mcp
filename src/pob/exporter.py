"""Path of Building export functionality"""

import base64
import zlib
import logging
from typing import Dict, Any
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


class PoBExporter:
    """Export builds to Path of Building format"""

    async def export_build(self, character_data: Dict[str, Any]) -> str:
        """
        Export character to PoB format

        Args:
            character_data: Character data to export

        Returns:
            Base64-encoded PoB build code
        """
        try:
            # Create XML structure
            root = ET.Element('PathOfBuilding')

            # Add character data
            build = ET.SubElement(root, 'Build')
            build.set('name', character_data.get('name', 'Exported Build'))
            build.set('className', character_data.get('class', 'Unknown'))
            build.set('level', str(character_data.get('level', 1)))

            # Convert to string
            xml_str = ET.tostring(root, encoding='utf-8')

            # Compress and encode
            compressed = zlib.compress(xml_str)
            encoded = base64.b64encode(compressed).decode('utf-8')

            return encoded

        except Exception as e:
            logger.error(f"PoB export failed: {e}")
            raise ValueError(f"Export failed: {str(e)}")
