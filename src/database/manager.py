"""
Database Manager for PoE2 Build Optimizer
Handles database initialization, queries, and management
"""

import logging
import re
import json
from typing import List, Dict, Any, Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from pydantic import BaseModel, Field, field_validator

from .models import Base, Item, PassiveNode, SkillGem, SavedBuild
try:
    from ..config import settings, DATA_DIR
except ImportError:
    from src.config import settings, DATA_DIR

logger = logging.getLogger(__name__)


class ItemSearchInput(BaseModel):
    """Input validation for item search queries"""
    query: str = Field(..., min_length=1, max_length=100)
    item_class: Optional[str] = Field(None, max_length=50)
    rarity: Optional[str] = Field(None, max_length=20)

    @field_validator('query', 'item_class', 'rarity')
    @classmethod
    def sanitize_input(cls, v):
        """Sanitize input to prevent injection attacks"""
        if v is None:
            return v
        # Remove null bytes and control characters
        v = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', v)
        # Limit to alphanumeric, spaces, and common punctuation
        v = re.sub(r'[^a-zA-Z0-9\s\-_\',.]', '', v)
        return v.strip()


class SaveBuildInput(BaseModel):
    """Input validation for saving builds"""
    name: str = Field(..., min_length=1, max_length=100)
    user_id: Optional[str] = Field(None, max_length=50)
    character_data: Dict[str, Any]

    @field_validator('name', 'user_id')
    @classmethod
    def sanitize_string(cls, v):
        """Sanitize string inputs"""
        if v is None:
            return v
        # Remove null bytes and control characters
        v = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', v)
        return v.strip()


class DatabaseManager:
    """Manages database connections and operations"""

    def __init__(self, db_url: Optional[str] = None) -> None:
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

    @staticmethod
    def _escape_like_pattern(pattern: str) -> str:
        """
        Escape special LIKE wildcards to prevent LIKE injection.

        Escapes % and _ characters that have special meaning in SQL LIKE patterns.
        This prevents users from injecting wildcards into search queries.

        Args:
            pattern: The user input pattern to escape

        Returns:
            Escaped pattern safe for use in LIKE queries
        """
        # Escape backslash first (the escape character itself)
        pattern = pattern.replace('\\', '\\\\')
        # Escape LIKE wildcards
        pattern = pattern.replace('%', '\\%')
        pattern = pattern.replace('_', '\\_')
        return pattern

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
        """
        Search for items in the .datc64 game database with input validation.

        Args:
            query: Search term for item name or ID
            filters: Optional filters (item_class)

        Returns:
            List of matching items (max 50 results)

        Raises:
            ValueError: If input validation fails
        """
        # Validate and sanitize inputs using Pydantic
        try:
            search_input = ItemSearchInput(
                query=query,
                item_class=filters.get("item_class") if filters else None,
                rarity=None  # Not applicable for .datc64 base items
            )
        except Exception as e:
            logger.warning(f"Invalid search input: {e}")
            raise ValueError(f"Invalid search input: {e}")

        # Escape LIKE wildcards to prevent LIKE injection
        safe_query = self._escape_like_pattern(search_input.query)

        async with self.async_session() as session:
            # Attach the .datc64 database for querying
            datc64_db_path = DATA_DIR / "poe2_datc64.db"
            await session.execute(text(f"ATTACH DATABASE '{datc64_db_path}' AS datc64"))

            try:
                # Query baseitemtypes with join to itemclasses
                # Extract name from Id if Name is empty (known .datc64 issue)
                sql_query = text("""
                    SELECT
                        b.data,
                        i.data as class_data
                    FROM datc64.baseitemtypes b
                    LEFT JOIN datc64.itemclasses i
                        ON i.row_index = CAST(json_extract(b.data, '$.ItemClassesKey') AS INTEGER)
                    WHERE (
                        json_extract(b.data, '$.Name') LIKE :term
                        OR json_extract(b.data, '$.InheritsFrom') LIKE :term
                        OR json_extract(b.data, '$.Id') LIKE :term
                    )
                    LIMIT 50
                """)

                result = await session.execute(sql_query, {"term": f"%{safe_query}%"})
                rows = result.fetchall()

                items = []
                for row in rows:
                    base_data = json.loads(row[0])
                    class_data = json.loads(row[1]) if row[1] else {}

                    # Extract name from Id if Name is empty
                    item_name = base_data.get("Name", "")
                    if not item_name:
                        # Try InheritsFrom first (often has better name)
                        item_name = base_data.get("InheritsFrom", "")

                        # If still no name, extract from Id
                        if not item_name:
                            item_id = base_data.get("Id", "")
                            if item_id:
                                item_name = item_id.split("/")[-1]

                    # Convert camelCase to Title Case (e.g., "SkillGemIceNova" -> "Ice Nova")
                    if item_name and not " " in item_name:
                        # Remove common prefixes
                        for prefix in ["SkillGem", "SupportGem", "CurrencyAdd", "Currency", "OneHand", "TwoHand"]:
                            if item_name.startswith(prefix):
                                item_name = item_name[len(prefix):]
                                break

                        # Add spaces before capital letters
                        import re
                        item_name = re.sub(r'([A-Z])', r' \1', item_name).strip()

                    # Get item class name
                    item_class = class_data.get("Name", "Unknown")

                    # Apply item_class filter if specified
                    if search_input.item_class and item_class.lower() != search_input.item_class.lower():
                        continue

                    items.append({
                        "id": base_data.get("Id", ""),
                        "name": item_name,
                        "base_type": base_data.get("InheritsFrom", ""),
                        "item_class": item_class,
                        "width": base_data.get("Width", 1),
                        "height": base_data.get("Height", 1),
                        "drop_level": base_data.get("DropLevel", 0),
                        "row_index": base_data.get("row_index", 0),
                        "properties": {
                            "tags": base_data.get("TagsKeys", []),
                            "implicit_mods": base_data.get("Implicit_ModsKeys", [])
                        }
                    })

                return items

            finally:
                # Always detach the database
                await session.execute(text("DETACH DATABASE datc64"))

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
        """
        Save a build to database with input validation.

        Args:
            build_data: Build data containing name, user_id, and character_data

        Returns:
            ID of the saved build

        Raises:
            ValueError: If input validation fails
        """
        # Validate and sanitize inputs using Pydantic
        try:
            build_input = SaveBuildInput(
                name=build_data.get("name", "Unnamed Build"),
                user_id=build_data.get("user_id"),
                character_data=build_data
            )
        except Exception as e:
            logger.warning(f"Invalid build data: {e}")
            raise ValueError(f"Invalid build data: {e}")

        async with self.async_session() as session:
            build = SavedBuild(
                build_name=build_input.name,
                character_data=build_input.character_data,
                user_id=build_input.user_id
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
