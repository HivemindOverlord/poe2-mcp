#!/usr/bin/env python3
"""
Setup script for PoE2 Build Optimizer
Initializes database and creates necessary structure
"""

import asyncio
import sys
import io
from pathlib import Path

# Fix Windows encoding issues
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


async def main():
    """Run setup"""
    print("=" * 60)
    print("PoE2 Build Optimizer - Setup")
    print("=" * 60)

    # Create directories
    print("\n[1/3] Creating directories...")
    dirs = ['data', 'cache', 'logs', 'web']
    for dir_name in dirs:
        dir_path = Path(dir_name)
        dir_path.mkdir(exist_ok=True)
        print(f"  ✓ {dir_name}/")

    # Create .env if it doesn't exist
    print("\n[2/3] Checking configuration...")
    env_file = Path('.env')
    if not env_file.exists():
        template = Path('.env.example')
        if template.exists():
            import shutil
            shutil.copy(template, env_file)
            print("  ✓ Created .env file")
            print("  ℹ Please edit .env and add your API keys")
        else:
            print("  ⚠ No .env.example found")
    else:
        print("  ✓ .env file exists")

    # Initialize database
    print("\n[3/3] Initializing database...")
    try:
        from src.database.manager import DatabaseManager
        db = DatabaseManager()
        await db.initialize()
        print("  ✓ Database schema created")
        await db.close()
    except Exception as e:
        print(f"  ✗ Database initialization failed: {e}")
        return False

    print("\n" + "=" * 60)
    print("Setup complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Edit .env and add your API keys (optional)")
    print("  2. Run: python launch.py")
    print("  3. Or add to Claude Desktop MCP configuration")
    print("\nFor detailed instructions, see QUICKSTART.md")

    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nSetup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
