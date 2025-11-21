#!/usr/bin/env python3
"""
PoE2 Build Optimizer - Quick Launch Script
Handles setup and launches the MCP server
"""

import os
import sys
import io
import asyncio
import subprocess
from pathlib import Path

# Fix Windows encoding issues
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ANSI color codes for pretty output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text):
    """Print colored header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")


def print_success(text):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_info(text):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def print_warning(text):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def print_error(text):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def check_python_version():
    """Check if Python version is sufficient"""
    if sys.version_info < (3, 9):
        print_error(f"Python 3.9+ required. You have {sys.version}")
        return False
    print_success(f"Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True


def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        'fastapi',
        'uvicorn',
        'sqlalchemy',
        'httpx',
        'pydantic',
        'mcp'
    ]

    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    if missing:
        print_warning(f"Missing packages: {', '.join(missing)}")
        print_info("Installing missing dependencies...")
        try:
            subprocess.check_call([
                sys.executable,
                '-m',
                'pip',
                'install',
                '-r',
                'requirements.txt'
            ])
            print_success("Dependencies installed successfully")
            return True
        except subprocess.CalledProcessError:
            print_error("Failed to install dependencies")
            print_info("Please run: pip install -r requirements.txt")
            return False
    else:
        print_success("All dependencies installed")
        return True


def setup_directories():
    """Create necessary directories"""
    dirs = ['data', 'cache', 'logs']
    for dir_name in dirs:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(parents=True)
            print_success(f"Created {dir_name}/ directory")
        else:
            print_info(f"{dir_name}/ directory exists")


def check_env_file():
    """Check if .env file exists"""
    env_file = Path('.env')
    if not env_file.exists():
        print_warning(".env file not found")
        print_info("Creating .env from template...")
        template = Path('.env.example')
        if template.exists():
            import shutil
            shutil.copy(template, env_file)
            print_success("Created .env file")
            print_info("Please edit .env and add your API keys if you want AI features")
        else:
            print_warning("No .env.example template found")
    else:
        print_success(".env file exists")


async def initialize_database():
    """Initialize the database"""
    print_info("Initializing database...")
    try:
        from src.database.manager import DatabaseManager
        db = DatabaseManager()
        await db.initialize()
        print_success("Database initialized")
        await db.close()
        return True
    except Exception as e:
        print_error(f"Database initialization failed: {e}")
        return False


def show_welcome():
    """Show welcome message"""
    print_header("PoE2 Build Optimizer")
    print(f"{Colors.OKBLUE}")
    print("  An AI-powered Path of Exile 2 build optimization server")
    print("  Built with MCP (Model Context Protocol)")
    print(f"{Colors.ENDC}")
    print_info("This launcher will set up and start the MCP server")
    print()


def show_usage_instructions():
    """Show usage instructions"""
    print_header("Usage Instructions")

    print(f"{Colors.OKGREEN}{Colors.BOLD}Option 1: Use with Claude Desktop{Colors.ENDC}")
    print("Add this to your Claude Desktop MCP configuration:")
    print(f"{Colors.OKCYAN}")
    config_path = Path.cwd() / "src" / "mcp_server.py"
    print('{')
    print('  "mcpServers": {')
    print('    "poe2-optimizer": {')
    print('      "command": "python",')
    print(f'      "args": ["{config_path}"]')
    print('    }')
    print('  }')
    print('}')
    print(f"{Colors.ENDC}")

    print(f"\n{Colors.OKGREEN}{Colors.BOLD}Option 2: Run Standalone{Colors.ENDC}")
    print("The server is now running. Use the MCP protocol to interact with it.")

    print(f"\n{Colors.OKGREEN}{Colors.BOLD}Example Queries (in Claude Desktop):{Colors.ENDC}")
    print("  • Analyze my PoE2 character: AccountName/CharacterName")
    print("  • How can I increase my DPS?")
    print("  • What gear should I upgrade next?")
    print("  • Optimize my passive tree for survivability")

    print(f"\n{Colors.WARNING}Press Ctrl+C to stop the server{Colors.ENDC}\n")


async def start_mcp_server():
    """Start the MCP server"""
    print_info("Starting MCP server...")

    try:
        from src.mcp_server import main
        await main()
    except KeyboardInterrupt:
        print_info("\nShutting down server...")
    except Exception as e:
        print_error(f"Server error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main launcher function"""
    show_welcome()

    # Pre-flight checks
    print_header("Pre-flight Checks")

    if not check_python_version():
        return

    if not check_dependencies():
        print_error("Please install dependencies first")
        return

    setup_directories()
    check_env_file()

    # Initialize database
    print_header("Database Setup")
    if not await initialize_database():
        print_warning("Database initialization failed, but continuing...")

    # Show instructions
    show_usage_instructions()

    # Start server
    print_header("Starting Server")
    await start_mcp_server()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.OKGREEN}Goodbye!{Colors.ENDC}")
    except Exception as e:
        print_error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
