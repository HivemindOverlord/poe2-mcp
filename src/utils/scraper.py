"""
Web Scraper for PoE2 Game Data
Scrapes item data, skill gems, and passive tree information from poe2db.tw and other sources
"""

import asyncio
import httpx
import json
import re
import logging
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
from datetime import datetime

try:
    from ..config import settings
    from ..api.rate_limiter import RateLimiter
except ImportError:
    from src.config import settings
    from src.api.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class PoE2DataScraper:
    """
    Scrapes Path of Exile 2 game data from various sources
    Primary source: poe2db.tw
    """

    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        self.base_url = settings.POE2DB_BASE_URL
        self.rate_limiter = rate_limiter or RateLimiter(rate_limit=30)
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/json",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    async def scrape_unique_items(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Scrape unique items from poe2db.tw

        Args:
            limit: Maximum number of items to scrape (None for all)

        Returns:
            List of unique item dictionaries
        """
        logger.info("Scraping unique items from poe2db.tw")
        items = []

        try:
            # poe2db.tw unique items URL
            url = f"{self.base_url}/us/Unique_items"
            await self.rate_limiter.acquire()

            response = await self.client.get(url)
            if response.status_code != 200:
                logger.error(f"Failed to fetch unique items: {response.status_code}")
                return []

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find item tables
            tables = soup.find_all('table', class_=['item', 'wikitable'])

            for table in tables:
                rows = table.find_all('tr')[1:]  # Skip header

                for row in rows:
                    try:
                        item = self._parse_item_row(row)
                        if item:
                            items.append(item)

                            if limit and len(items) >= limit:
                                break

                    except Exception as e:
                        logger.debug(f"Failed to parse item row: {e}")
                        continue

                if limit and len(items) >= limit:
                    break

            logger.info(f"Scraped {len(items)} unique items")
            return items

        except Exception as e:
            logger.error(f"Error scraping unique items: {e}")
            return []

    def _parse_item_row(self, row) -> Optional[Dict[str, Any]]:
        """Parse a single item row from table"""
        try:
            cols = row.find_all(['td', 'th'])
            if len(cols) < 2:
                return None

            # Extract item name
            name_cell = cols[0]
            item_link = name_cell.find('a')
            if not item_link:
                return None

            item_name = item_link.text.strip()
            item_url = item_link.get('href', '')

            # Extract item type/base
            base_type = cols[1].text.strip() if len(cols) > 1 else ""

            # Extract level requirement if present
            level_req = 0
            for col in cols:
                level_match = re.search(r'Level[:\s]*(\d+)', col.text, re.IGNORECASE)
                if level_match:
                    level_req = int(level_match.group(1))
                    break

            return {
                "name": item_name,
                "base_type": base_type,
                "item_class": self._classify_item(base_type),
                "level_requirement": level_req,
                "rarity": "Unique",
                "url": f"{self.base_url}{item_url}" if item_url else None,
                "source": "poe2db.tw",
                "scraped_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.debug(f"Error parsing item row: {e}")
            return None

    def _classify_item(self, base_type: str) -> str:
        """Classify item based on base type"""
        base_lower = base_type.lower()

        if any(x in base_lower for x in ['sword', 'axe', 'mace', 'dagger', 'claw', 'bow', 'wand', 'staff']):
            return "Weapon"
        elif any(x in base_lower for x in ['helmet', 'helm', 'hood', 'crown']):
            return "Helmet"
        elif any(x in base_lower for x in ['chest', 'armour', 'armor', 'robe', 'vest', 'coat']):
            return "Body Armour"
        elif any(x in base_lower for x in ['gloves', 'gauntlets', 'mitts']):
            return "Gloves"
        elif any(x in base_lower for x in ['boots', 'greaves', 'slippers']):
            return "Boots"
        elif any(x in base_lower for x in ['ring']):
            return "Ring"
        elif any(x in base_lower for x in ['amulet', 'talisman']):
            return "Amulet"
        elif any(x in base_lower for x in ['belt', 'sash']):
            return "Belt"
        elif any(x in base_lower for x in ['shield', 'buckler']):
            return "Shield"
        elif any(x in base_lower for x in ['quiver']):
            return "Quiver"
        else:
            return "Other"

    async def scrape_skill_gems(self) -> List[Dict[str, Any]]:
        """
        Scrape skill gem data from poe2db.tw

        Returns:
            List of skill gem dictionaries
        """
        logger.info("Scraping skill gems from poe2db.tw")
        skills = []

        try:
            url = f"{self.base_url}/us/Skill_Gems"
            await self.rate_limiter.acquire()

            response = await self.client.get(url)
            if response.status_code != 200:
                logger.error(f"Failed to fetch skill gems: {response.status_code}")
                return []

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find skill gem tables
            tables = soup.find_all('table')

            for table in tables:
                rows = table.find_all('tr')[1:]  # Skip header

                for row in rows:
                    try:
                        skill = self._parse_skill_row(row)
                        if skill:
                            skills.append(skill)
                    except Exception as e:
                        logger.debug(f"Failed to parse skill row: {e}")
                        continue

            logger.info(f"Scraped {len(skills)} skill gems")
            return skills

        except Exception as e:
            logger.error(f"Error scraping skill gems: {e}")
            return []

    def _parse_skill_row(self, row) -> Optional[Dict[str, Any]]:
        """Parse a single skill gem row"""
        try:
            cols = row.find_all(['td', 'th'])
            if len(cols) < 2:
                return None

            # Extract skill name
            name_cell = cols[0]
            skill_link = name_cell.find('a')
            if not skill_link:
                return None

            skill_name = skill_link.text.strip()

            # Extract tags/type
            tags = []
            for col in cols:
                # Look for tags like "Fire", "Spell", "AoE", etc.
                tag_matches = re.findall(r'\b(Fire|Cold|Lightning|Physical|Chaos|Spell|Attack|AoE|Projectile|Duration|Minion)\b', col.text, re.IGNORECASE)
                tags.extend(tag_matches)

            return {
                "name": skill_name,
                "tags": list(set(tags)),  # Remove duplicates
                "gem_type": "Active",
                "source": "poe2db.tw",
                "scraped_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.debug(f"Error parsing skill row: {e}")
            return None

    async def scrape_support_gems(self) -> List[Dict[str, Any]]:
        """
        Scrape support gem data from poe2db.tw

        Returns:
            List of support gem dictionaries
        """
        logger.info("Scraping support gems from poe2db.tw")
        supports = []

        try:
            url = f"{self.base_url}/us/Support_Gems"
            await self.rate_limiter.acquire()

            response = await self.client.get(url)
            if response.status_code != 200:
                logger.error(f"Failed to fetch support gems: {response.status_code}")
                return []

            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')

            for table in tables:
                rows = table.find_all('tr')[1:]

                for row in rows:
                    try:
                        support = self._parse_skill_row(row)
                        if support:
                            support["gem_type"] = "Support"
                            supports.append(support)
                    except Exception as e:
                        logger.debug(f"Failed to parse support row: {e}")
                        continue

            logger.info(f"Scraped {len(supports)} support gems")
            return supports

        except Exception as e:
            logger.error(f"Error scraping support gems: {e}")
            return []

    async def scrape_passive_tree_data(self) -> Optional[Dict[str, Any]]:
        """
        Scrape passive tree data from poe2db.tw

        Returns:
            Passive tree data structure
        """
        logger.info("Scraping passive tree data from poe2db.tw")

        try:
            url = f"{self.base_url}/us/Passive_Skill_Tree"
            await self.rate_limiter.acquire()

            response = await self.client.get(url)
            if response.status_code != 200:
                logger.error(f"Failed to fetch passive tree: {response.status_code}")
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for embedded passive tree JSON data
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'passiveSkillTree' in script.string:
                    try:
                        # Extract JSON data
                        json_match = re.search(r'passiveSkillTree\s*=\s*({.*?});', script.string, re.DOTALL)
                        if json_match:
                            tree_data = json.loads(json_match.group(1))
                            logger.info("Successfully extracted passive tree data")
                            return tree_data
                    except json.JSONDecodeError:
                        continue

            logger.warning("Could not find passive tree JSON data")
            return None

        except Exception as e:
            logger.error(f"Error scraping passive tree: {e}")
            return None

    async def scrape_base_items(self) -> List[Dict[str, Any]]:
        """
        Scrape base item types from poe2db.tw

        Returns:
            List of base item dictionaries
        """
        logger.info("Scraping base items from poe2db.tw")
        base_items = []

        item_categories = [
            "Weapons",
            "Armours",
            "Accessories",
        ]

        for category in item_categories:
            try:
                url = f"{self.base_url}/us/{category}"
                await self.rate_limiter.acquire()

                response = await self.client.get(url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    tables = soup.find_all('table')

                    for table in tables:
                        rows = table.find_all('tr')[1:]

                        for row in rows:
                            try:
                                item = self._parse_base_item_row(row, category)
                                if item:
                                    base_items.append(item)
                            except Exception as e:
                                logger.debug(f"Failed to parse base item: {e}")
                                continue

            except Exception as e:
                logger.error(f"Error scraping {category}: {e}")
                continue

        logger.info(f"Scraped {len(base_items)} base items")
        return base_items

    def _parse_base_item_row(self, row, category: str) -> Optional[Dict[str, Any]]:
        """Parse a single base item row"""
        try:
            cols = row.find_all(['td', 'th'])
            if len(cols) < 2:
                return None

            name_cell = cols[0]
            item_link = name_cell.find('a')
            if not item_link:
                return None

            item_name = item_link.text.strip()

            # Extract level requirement
            level_req = 0
            for col in cols:
                level_match = re.search(r'(\d+)', col.text)
                if level_match and 'level' in col.text.lower():
                    level_req = int(level_match.group(1))
                    break

            return {
                "name": item_name,
                "category": category,
                "item_class": self._classify_item(item_name),
                "level_requirement": level_req,
                "rarity": "Normal",
                "source": "poe2db.tw",
                "scraped_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.debug(f"Error parsing base item: {e}")
            return None

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
