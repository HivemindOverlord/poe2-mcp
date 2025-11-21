#!/usr/bin/env python3
"""
Simple setup script with ASCII-only output
"""

import asyncio
import sys
from pathlib import Path


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
        print(f"  [OK] {dir_name}/")

    # Create .env if it doesn't exist
    print("\n[2/3] Checking configuration...")
    env_file = Path('.env')
    if not env_file.exists():
        template = Path('.env.example')
        if template.exists():
            import shutil
            shutil.copy(template, env_file)
            print("  [OK] Created .env file")
            print("  [INFO] Please edit .env and add your API keys")
        else:
            print("  [WARNING] No .env.example found")
    else:
        print("  [OK] .env file exists")

    # Initialize database
    print("\n[3/3] Initializing database...")
    try:
        from src.database.manager import DatabaseManager
        db = DatabaseManager()
        await db.initialize()
        print("  [OK] Database schema created")
        await db.close()
    except Exception as e:
        print(f"  [ERROR] Database initialization failed: {e}")
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
