#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reinitialize Database
Drops and recreates all tables with the updated schema
Use this after making changes to database models
"""

import asyncio
import sys
import io
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.manager import DatabaseManager
from src.config import DATA_DIR


async def reinitialize_database():
    """Drop and recreate database tables"""
    print("=" * 60)
    print("Database Reinitialization")
    print("=" * 60)

    db_path = DATA_DIR / "poe2_optimizer.db"

    print(f"\nDatabase location: {db_path}")

    if db_path.exists():
        response = input("\nDatabase exists. Delete and recreate? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return

        # Try to delete existing database
        try:
            db_path.unlink()
            print("✓ Deleted existing database")
        except PermissionError:
            print("\n⚠ Database is locked by another process.")
            print("Please close any applications using the database and try again.")
            print("\nAlternatively, manually delete:")
            print(f"  {db_path}")
            return

    # Initialize new database
    print("\nCreating new database with updated schema...")
    db_manager = DatabaseManager()
    await db_manager.initialize()

    print("✓ Database initialized successfully")

    # Verify tables
    async with db_manager.async_session() as session:
        from sqlalchemy import text

        result = await session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        )
        tables = result.fetchall()

        print(f"\n✓ Created {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")

    await db_manager.close()

    print("\n" + "=" * 60)
    print("Database reinitialization complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run: python scripts/populate_database.py")
    print("2. Or manually add data through the MCP server")


if __name__ == "__main__":
    asyncio.run(reinitialize_database())
