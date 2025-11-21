"""
Database Manager for PoE2 Build Optimizer
Handles database initialization, queries, and management
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from sqlalchemy import create_engine, select, and_, or_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session

from .models import Base, Item, UniqueItem, PassiveNode, SkillGem, SupportGem, SavedBuild
try:
    from ..config import settings, DATA_DIR
except ImportError:
    from src.config import settings, DATA_DIR

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations"""

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or settings.DATABASE_URL

        # Convert sqlite:/// to sqlite+aiosqlite:/// for async support
        if self.db_url.startswith("sqlite:///"):
            async_url = self.db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        else:
            async_url = self.db_url

        self.engine = create_async_engine(
            async_url,
            echo=settings.DB_ECHO,
            future=True
        )

        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def initialize(self):
        """Initialize database schema"""
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    async def search_items(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for items in the database"""
        async with self.async_session() as session:
            stmt = select(Item).where(Item.name.like(f"%{query}%"))

            if filters:
                if "item_class" in filters:
                    stmt = stmt.where(Item.item_class == filters["item_class"])
                if "rarity" in filters:
                    stmt = stmt.where(Item.rarity == filters["rarity"])

            result = await session.execute(stmt.limit(50))
            items = result.scalars().all()

            return [
                {
                    "id": item.id,
                    "name": item.name,
                    "base_type": item.base_type,
                    "item_class": item.item_class,
                    "rarity": item.rarity,
                    "properties": item.properties
                }
                for item in items
            ]

    async def get_all_items(self) -> List[Dict[str, Any]]:
        """Get all items from database"""
        async with self.async_session() as session:
            result = await session.execute(select(Item))
            items = result.scalars().all()
            return [{"name": item.name, "type": item.item_class} for item in items]

    async def get_passive_tree(self) -> Dict[str, Any]:
        """Get complete passive tree data"""
        async with self.async_session() as session:
            result = await session.execute(select(PassiveNode))
            nodes = result.scalars().all()

            return {
                "nodes": [
                    {
                        "id": node.node_id,
                        "name": node.name,
                        "isKeystone": node.is_keystone,
                        "stats": node.stats
                    }
                    for node in nodes
                ]
            }

    async def get_all_skills(self) -> List[Dict[str, Any]]:
        """Get all skill gems"""
        async with self.async_session() as session:
            result = await session.execute(select(SkillGem))
            skills = result.scalars().all()
            return [{"name": skill.name, "tags": skill.tags} for skill in skills]

    async def save_build(self, build_data: Dict[str, Any]) -> int:
        """Save a build to database"""
        async with self.async_session() as session:
            build = SavedBuild(
                build_name=build_data.get("name", "Unnamed Build"),
                character_data=build_data,
                user_id=build_data.get("user_id")
            )
            session.add(build)
            await session.commit()
            return build.id

    async def test_connection(self) -> bool:
        """Test database connection"""
        try:
            async with self.engine.connect() as conn:
                await conn.execute(select(1))
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    async def close(self):
        """Close database connections"""
        await self.engine.dispose()
