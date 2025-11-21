#!/usr/bin/env python3
"""
Database Population Script for PoE2 MCP Server
Populates the database with game data from various sources:
- Unique items from poe2db.tw
- Base items from poe2db.tw
- Skill gems from poe2db.tw
- Support gems from poe2db.tw
- Item prices from poe.ninja
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.manager import DatabaseManager
from src.database.models import Item, UniqueItem, SkillGem, SupportGem, GameDataVersion
from src.utils.scraper import PoE2DataScraper
from src.api.poe_ninja_api import PoeNinjaAPI
from src.api.rate_limiter import RateLimiter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabasePopulator:
    """Populate database with PoE2 game data"""

    def __init__(self):
        self.db_manager = None
        self.scraper = None
        self.ninja_api = None
        self.rate_limiter = RateLimiter(rate_limit=30)

    async def initialize(self):
        """Initialize database and scraping tools"""
        logger.info("Initializing database and tools...")

        self.db_manager = DatabaseManager()
        await self.db_manager.initialize()

        self.scraper = PoE2DataScraper(rate_limiter=self.rate_limiter)
        self.ninja_api = PoeNinjaAPI(rate_limiter=self.rate_limiter)

        logger.info("Initialization complete")

    async def populate_all(self):
        """Populate all game data"""
        logger.info("=" * 60)
        logger.info("Starting database population")
        logger.info("=" * 60)

        try:
            # Check if data already exists
            if await self._check_existing_data():
                logger.info("Database already contains data")
                response = input("Do you want to re-populate? This will clear existing data. (y/N): ")
                if response.lower() != 'y':
                    logger.info("Skipping population")
                    return

            # Populate unique items
            await self.populate_unique_items()

            # Populate base items
            await self.populate_base_items()

            # Populate skill gems
            await self.populate_skill_gems()

            # Populate support gems
            await self.populate_support_gems()

            # Populate item prices from poe.ninja
            await self.populate_item_prices()

            # Record data version
            await self._record_data_version()

            logger.info("=" * 60)
            logger.info("Database population completed successfully!")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Error during population: {e}", exc_info=True)
            raise

    async def _check_existing_data(self) -> bool:
        """Check if database already has data"""
        async with self.db_manager.async_session() as session:
            from sqlalchemy import select, func
            from src.database.models import Item

            result = await session.execute(select(func.count(Item.id)))
            count = result.scalar()
            return count > 0

    async def populate_unique_items(self):
        """Populate unique items from poe2db.tw"""
        logger.info("Populating unique items...")

        try:
            # Scrape unique items
            unique_items = await self.scraper.scrape_unique_items(limit=100)
            logger.info(f"Scraped {len(unique_items)} unique items")

            if not unique_items:
                logger.warning("No unique items scraped")
                return

            # Insert into database
            async with self.db_manager.async_session() as session:
                for item_data in unique_items:
                    try:
                        # Create UniqueItem record
                        unique_item = UniqueItem(
                            name=item_data["name"],
                            base_type=item_data.get("base_type", ""),
                            item_class=item_data.get("item_class", "Other"),
                            level_requirement=item_data.get("level_requirement", 0),
                            stats={},
                            mods={},
                            description=f"Source: {item_data.get('source', 'unknown')}",
                            flavor_text=""
                        )

                        session.add(unique_item)

                    except Exception as e:
                        logger.error(f"Failed to add unique item {item_data.get('name')}: {e}")
                        continue

                await session.commit()

            logger.info(f"Successfully added {len(unique_items)} unique items to database")

        except Exception as e:
            logger.error(f"Error populating unique items: {e}")

    async def populate_base_items(self):
        """Populate base items from poe2db.tw"""
        logger.info("Populating base items...")

        try:
            base_items = await self.scraper.scrape_base_items()
            logger.info(f"Scraped {len(base_items)} base items")

            if not base_items:
                logger.warning("No base items scraped")
                return

            async with self.db_manager.async_session() as session:
                for item_data in base_items:
                    try:
                        item = Item(
                            name=item_data["name"],
                            base_type=item_data["name"],
                            item_class=item_data.get("item_class", "Other"),
                            level_requirement=item_data.get("level_requirement", 0),
                            stats={},
                            mods={}
                        )

                        session.add(item)

                    except Exception as e:
                        logger.error(f"Failed to add base item {item_data.get('name')}: {e}")
                        continue

                await session.commit()

            logger.info(f"Successfully added {len(base_items)} base items to database")

        except Exception as e:
            logger.error(f"Error populating base items: {e}")

    async def populate_skill_gems(self):
        """Populate skill gems from poe2db.tw"""
        logger.info("Populating skill gems...")

        try:
            skills = await self.scraper.scrape_skill_gems()
            logger.info(f"Scraped {len(skills)} skill gems")

            if not skills:
                logger.warning("No skill gems scraped")
                return

            async with self.db_manager.async_session() as session:
                for skill_data in skills:
                    try:
                        skill = SkillGem(
                            name=skill_data["name"],
                            tags=skill_data.get("tags", []),
                            description="",
                            level_requirement=1,
                            stats={}
                        )

                        session.add(skill)

                    except Exception as e:
                        logger.error(f"Failed to add skill gem {skill_data.get('name')}: {e}")
                        continue

                await session.commit()

            logger.info(f"Successfully added {len(skills)} skill gems to database")

        except Exception as e:
            logger.error(f"Error populating skill gems: {e}")

    async def populate_support_gems(self):
        """Populate support gems from poe2db.tw"""
        logger.info("Populating support gems...")

        try:
            supports = await self.scraper.scrape_support_gems()
            logger.info(f"Scraped {len(supports)} support gems")

            if not supports:
                logger.warning("No support gems scraped")
                return

            async with self.db_manager.async_session() as session:
                for support_data in supports:
                    try:
                        support = SupportGem(
                            name=support_data["name"],
                            tags=support_data.get("tags", []),
                            description="",
                            level_requirement=1,
                            stats={}
                        )

                        session.add(support)

                    except Exception as e:
                        logger.error(f"Failed to add support gem {support_data.get('name')}: {e}")
                        continue

                await session.commit()

            logger.info(f"Successfully added {len(supports)} support gems to database")

        except Exception as e:
            logger.error(f"Error populating support gems: {e}")

    async def populate_item_prices(self):
        """Populate item prices from poe.ninja"""
        logger.info("Populating item prices from poe.ninja...")

        try:
            # Fetch prices for different item types
            item_types = [
                "UniqueWeapon",
                "UniqueArmour",
                "UniqueAccessory",
                "UniqueFlask",
                "UniqueJewel"
            ]

            total_prices = 0

            for item_type in item_types:
                try:
                    items = await self.ninja_api.get_item_prices(
                        league="Standard",
                        item_type=item_type
                    )

                    if items:
                        logger.info(f"Got {len(items)} prices for {item_type}")

                        # Update items in database with price information
                        async with self.db_manager.async_session() as session:
                            for item in items:
                                try:
                                    # Find matching unique item and update
                                    from sqlalchemy import select
                                    from src.database.models import UniqueItem

                                    result = await session.execute(
                                        select(UniqueItem).where(
                                            UniqueItem.name == item.get("name")
                                        )
                                    )
                                    db_item = result.scalar_one_or_none()

                                    if db_item:
                                        # Update stats with pricing info
                                        stats = db_item.stats or {}
                                        stats["chaos_value"] = item.get("chaosValue", 0)
                                        stats["divine_value"] = item.get("divineValue", 0)
                                        db_item.stats = stats

                                        total_prices += 1

                                except Exception as e:
                                    logger.debug(f"Failed to update price for {item.get('name')}: {e}")
                                    continue

                            await session.commit()

                    await asyncio.sleep(1)  # Rate limiting

                except Exception as e:
                    logger.error(f"Error fetching prices for {item_type}: {e}")
                    continue

            logger.info(f"Updated prices for {total_prices} items")

        except Exception as e:
            logger.error(f"Error populating item prices: {e}")

    async def _record_data_version(self):
        """Record the data version in database"""
        try:
            async with self.db_manager.async_session() as session:
                version = GameDataVersion(
                    version=datetime.utcnow().strftime("%Y%m%d_%H%M%S"),
                    source="poe2db.tw + poe.ninja",
                    notes="Automated population via scraper"
                )
                session.add(version)
                await session.commit()

            logger.info("Recorded data version")

        except Exception as e:
            logger.error(f"Error recording data version: {e}")

    async def cleanup(self):
        """Cleanup resources"""
        if self.scraper:
            await self.scraper.close()
        if self.ninja_api:
            await self.ninja_api.close()
        if self.db_manager:
            await self.db_manager.close()


async def main():
    """Main entry point"""
    populator = DatabasePopulator()

    try:
        await populator.initialize()
        await populator.populate_all()

    except KeyboardInterrupt:
        logger.info("Population interrupted by user")

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

    finally:
        await populator.cleanup()


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║    PoE2 MCP Server - Database Population Script             ║
║                                                              ║
║  This script will populate the database with:                ║
║  - Unique items from poe2db.tw                              ║
║  - Base items from poe2db.tw                                ║
║  - Skill gems from poe2db.tw                                ║
║  - Support gems from poe2db.tw                              ║
║  - Item prices from poe.ninja                               ║
║                                                              ║
║  Note: This process may take 5-10 minutes depending on      ║
║        network speed and rate limiting.                      ║
╚══════════════════════════════════════════════════════════════╝
    """)

    asyncio.run(main())
