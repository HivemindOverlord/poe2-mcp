"""
Comprehensive poe2db.tw Support Gem Scraper

Scrapes all support gems with complete data:
- Base effects and multipliers
- Spirit costs per tier
- Mana multipliers
- Quality bonuses
- Tag requirements
- Level requirements

Author: Claude
Date: 2025-10-24
"""

import asyncio
import httpx
import json
import re
import logging
from bs4 import BeautifulSoup
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PoE2DBSupportScraper:
    """Scrape support gems from poe2db.tw"""

    def __init__(self):
        self.base_url = "https://poe2db.tw"
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
        self.supports = {}

    async def scrape_all_supports(self) -> Dict[str, Any]:
        """
        Scrape all support gems from poe2db.tw

        Returns:
            Dictionary of support gems with complete data
        """
        logger.info("Starting support gem scraping from poe2db.tw...")

        # Main support gem list page
        list_url = f"{self.base_url}/us/Support_Skill_Gems"

        try:
            response = await self.client.get(list_url)
            if response.status_code != 200:
                logger.error(f"Failed to fetch support list: {response.status_code}")
                return {}

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find all support gem links
            support_links = self._extract_support_links(soup)
            logger.info(f"Found {len(support_links)} support gem links")

            # Scrape each support gem
            for i, (name, url) in enumerate(support_links.items(), 1):
                logger.info(f"[{i}/{len(support_links)}] Scraping {name}...")

                support_data = await self._scrape_support_detail(name, url)
                if support_data:
                    self.supports[self._normalize_id(name)] = support_data

                # Be nice to the server
                await asyncio.sleep(0.5)

            logger.info(f"Successfully scraped {len(self.supports)} support gems")
            return self.supports

        except Exception as e:
            logger.error(f"Error scraping supports: {e}", exc_info=True)
            return {}

    def _extract_support_links(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract support gem links from list page"""
        links = {}

        # Look for gem tables
        tables = soup.find_all('table', class_='item')

        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                # Find gem name link
                name_cell = row.find('td', class_='name')
                if name_cell:
                    link = name_cell.find('a')
                    if link and link.get('href'):
                        name = link.get_text(strip=True)
                        href = link['href']

                        # Make sure it's a support gem
                        if 'Support' in name or 'support' in href.lower():
                            full_url = f"{self.base_url}{href}" if href.startswith('/') else href
                            links[name] = full_url

        return links

    async def _scrape_support_detail(self, name: str, url: str) -> Optional[Dict[str, Any]]:
        """Scrape detailed data for a single support gem"""
        try:
            response = await self.client.get(url)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch {name}: {response.status_code}")
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract data
            support_data = {
                'name': name,
                'url': url,
                'scraped_at': datetime.utcnow().isoformat(),
                'tags': self._extract_tags(soup),
                'type': self._extract_gem_type(soup),
                'tier': self._extract_tier(soup),
                'effects': self._extract_effects(soup),
                'spirit_cost': self._extract_spirit_cost(soup),
                'mana_multiplier': self._extract_mana_multiplier(soup),
                'quality_bonus': self._extract_quality_bonus(soup),
                'requirements': self._extract_requirements(soup),
                'compatible_with': self._extract_compatible_tags(soup),
                'level_progression': self._extract_level_progression(soup)
            }

            return support_data

        except Exception as e:
            logger.error(f"Error scraping {name}: {e}", exc_info=True)
            return None

    def _extract_tags(self, soup: BeautifulSoup) -> List[str]:
        """Extract gem tags (Spell, Attack, Projectile, etc.)"""
        tags = []

        # Look for tag elements
        tag_elements = soup.find_all('span', class_='tag')
        for tag in tag_elements:
            tags.append(tag.get_text(strip=True))

        # Also check in gem description
        description = soup.find('div', class_='description')
        if description:
            text = description.get_text()
            # Common tags
            tag_keywords = ['Spell', 'Attack', 'Projectile', 'AoE', 'Melee', 'Fire', 'Cold', 'Lightning', 'Chaos', 'Physical', 'Duration', 'Minion']
            for keyword in tag_keywords:
                if keyword in text and keyword not in tags:
                    tags.append(keyword)

        return tags

    def _extract_gem_type(self, soup: BeautifulSoup) -> str:
        """Extract gem type (spell_support, attack_support, etc.)"""
        # Look in gem header
        header = soup.find('h1')
        if header:
            text = header.get_text().lower()
            if 'spell' in text:
                return 'spell_support'
            elif 'attack' in text:
                return 'attack_support'
            elif 'projectile' in text:
                return 'projectile_support'

        return 'support'

    def _extract_tier(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract tier number"""
        # Look for tier information
        text = soup.get_text()

        # Try to find "Tier X"
        tier_match = re.search(r'Tier\s+(\d+)', text, re.IGNORECASE)
        if tier_match:
            return int(tier_match.group(1))

        # Try to find in gem name
        if 'I' in soup.find('h1').get_text():
            name = soup.find('h1').get_text()
            if name.endswith(' I'):
                return 1
            elif name.endswith(' II'):
                return 2
            elif name.endswith(' III'):
                return 3
            elif name.endswith(' IV'):
                return 4
            elif name.endswith(' V'):
                return 5

        return None

    def _extract_effects(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract support gem effects and multipliers"""
        effects = {}

        # Look for stat blocks
        stat_blocks = soup.find_all('div', class_='stat')

        for stat in stat_blocks:
            text = stat.get_text(strip=True)

            # More multipliers
            if 'more' in text.lower():
                # Extract percentage
                match = re.search(r'(\d+(?:\.\d+)?)%\s+more', text, re.IGNORECASE)
                if match:
                    value = float(match.group(1))

                    if 'damage' in text.lower():
                        effects['more_damage'] = value
                    elif 'spell damage' in text.lower():
                        effects['more_spell_damage'] = value
                    elif 'attack damage' in text.lower():
                        effects['more_attack_damage'] = value
                    elif 'cast speed' in text.lower():
                        effects['more_cast_speed'] = value
                    elif 'attack speed' in text.lower():
                        effects['more_attack_speed'] = value
                    elif 'area' in text.lower() or 'aoe' in text.lower():
                        effects['more_area'] = value
                    elif 'crit' in text.lower() and 'damage' in text.lower():
                        effects['more_crit_damage'] = value
                    elif 'crit' in text.lower() and 'chance' in text.lower():
                        effects['more_crit_chance'] = value

            # Less multipliers (negative)
            elif 'less' in text.lower():
                match = re.search(r'(\d+(?:\.\d+)?)%\s+less', text, re.IGNORECASE)
                if match:
                    value = -float(match.group(1))

                    if 'damage' in text.lower():
                        effects['more_damage'] = value
                    elif 'cast speed' in text.lower():
                        effects['more_cast_speed'] = value
                    elif 'attack speed' in text.lower():
                        effects['more_attack_speed'] = value

            # Increased modifiers
            elif 'increased' in text.lower():
                match = re.search(r'(\d+(?:\.\d+)?)%\s+increased', text, re.IGNORECASE)
                if match:
                    value = float(match.group(1))

                    if 'damage' in text.lower():
                        effects['increased_damage'] = value
                    elif 'cast speed' in text.lower():
                        effects['increased_cast_speed'] = value
                    elif 'crit' in text.lower() and 'chance' in text.lower():
                        effects['increased_crit_chance'] = value

            # Added damage
            if 'adds' in text.lower() and 'to' in text.lower() and 'damage' in text.lower():
                # Example: "Adds 10 to 20 Fire Damage"
                match = re.search(r'adds\s+(\d+)\s+to\s+(\d+)\s+(\w+)\s+damage', text, re.IGNORECASE)
                if match:
                    min_dmg = int(match.group(1))
                    max_dmg = int(match.group(2))
                    dmg_type = match.group(3).lower()

                    effects[f'added_{dmg_type}_min'] = min_dmg
                    effects[f'added_{dmg_type}_max'] = max_dmg

            # Special mechanics
            if 'chain' in text.lower():
                effects['grants_chain'] = True
            if 'fork' in text.lower():
                effects['grants_fork'] = True
            if 'pierce' in text.lower():
                effects['grants_pierce'] = True
            if 'culling strike' in text.lower():
                effects['grants_culling'] = True

        return effects

    def _extract_spirit_cost(self, soup: BeautifulSoup) -> int:
        """Extract spirit cost"""
        text = soup.get_text()

        # Look for "Spirit Cost: X"
        match = re.search(r'spirit\s+cost:?\s*(\d+)', text, re.IGNORECASE)
        if match:
            return int(match.group(1))

        return 0

    def _extract_mana_multiplier(self, soup: BeautifulSoup) -> float:
        """Extract mana cost multiplier"""
        text = soup.get_text()

        # Look for mana multiplier
        match = re.search(r'(\d+)%\s+(?:of\s+)?mana\s+(?:cost|multiplier)', text, re.IGNORECASE)
        if match:
            return float(match.group(1))

        # Default multiplier
        return 100.0

    def _extract_quality_bonus(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract quality bonus description"""
        # Look for quality section
        quality_section = soup.find('div', class_='quality')
        if quality_section:
            return quality_section.get_text(strip=True)

        return None

    def _extract_requirements(self, soup: BeautifulSoup) -> Dict[str, int]:
        """Extract level and attribute requirements"""
        reqs = {}

        # Look for requirement section
        req_section = soup.find('div', class_='requirements')
        if req_section:
            text = req_section.get_text()

            # Level
            level_match = re.search(r'level:?\s*(\d+)', text, re.IGNORECASE)
            if level_match:
                reqs['level'] = int(level_match.group(1))

            # Str/Dex/Int
            str_match = re.search(r'str(?:ength)?:?\s*(\d+)', text, re.IGNORECASE)
            if str_match:
                reqs['str'] = int(str_match.group(1))

            dex_match = re.search(r'dex(?:terity)?:?\s*(\d+)', text, re.IGNORECASE)
            if dex_match:
                reqs['dex'] = int(dex_match.group(1))

            int_match = re.search(r'int(?:elligence)?:?\s*(\d+)', text, re.IGNORECASE)
            if int_match:
                reqs['int'] = int(int_match.group(1))

        return reqs

    def _extract_compatible_tags(self, soup: BeautifulSoup) -> List[str]:
        """Extract which tags this support works with"""
        compatible = []

        # Look in description for "Supports X skills"
        description = soup.find('div', class_='description')
        if description:
            text = description.get_text()

            if 'supports spell' in text.lower():
                compatible.append('spell')
            if 'supports attack' in text.lower():
                compatible.append('attack')
            if 'supports projectile' in text.lower():
                compatible.append('projectile')
            if 'supports melee' in text.lower():
                compatible.append('melee')
            if 'supports area' in text.lower():
                compatible.append('aoe')
            if 'supports minion' in text.lower():
                compatible.append('minion')

        return compatible

    def _extract_level_progression(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract gem stats at different levels"""
        progression = {}

        # Look for level table
        level_table = soup.find('table', class_='level')
        if level_table:
            # This is complex and would need detailed parsing
            # For now, we'll skip this and focus on max level stats
            pass

        return progression

    def _normalize_id(self, name: str) -> str:
        """Convert gem name to normalized ID"""
        # Remove tier suffix
        name = re.sub(r'\s+[IVX]+$', '', name)
        # Convert to lowercase, replace spaces
        return name.lower().replace(' ', '_').replace('-', '_')

    async def save_to_json(self, output_path: Path):
        """Save scraped data to JSON file"""
        output = {
            'metadata': {
                'game': 'Path of Exile 2',
                'scraped_at': datetime.utcnow().isoformat(),
                'total_supports': len(self.supports),
                'source': 'poe2db.tw',
                'scraper_version': '1.0'
            },
            'support_gems': self.supports
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(self.supports)} supports to {output_path}")

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


async def main():
    """Main scraping function"""
    print("="*80)
    print("poe2db.tw Support Gem Scraper")
    print("="*80)
    print()

    scraper = PoE2DBSupportScraper()

    try:
        # Scrape all supports
        supports = await scraper.scrape_all_supports()

        if supports:
            # Save to file
            output_file = Path(__file__).parent.parent / "poe2_support_gems_database_ENHANCED.json"
            await scraper.save_to_json(output_file)

            print()
            print("="*80)
            print("Scraping Complete!")
            print("="*80)
            print(f"Total supports scraped: {len(supports)}")
            print(f"Output file: {output_file}")
            print()

            # Show sample
            print("Sample support gems:")
            for i, (gem_id, gem_data) in enumerate(list(supports.items())[:5], 1):
                print(f"{i}. {gem_data['name']}")
                print(f"   Type: {gem_data['type']}")
                print(f"   Tier: {gem_data.get('tier', 'N/A')}")
                print(f"   Tags: {', '.join(gem_data['tags'])}")
                effects = gem_data.get('effects', {})
                if effects:
                    print(f"   Effects: {', '.join(f'{k}={v}' for k, v in list(effects.items())[:3])}")
                print()

        else:
            print("❌ No supports scraped. Check logs for errors.")

    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
