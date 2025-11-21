#!/usr/bin/env python3
"""
Simple wrapper for MCP server to ensure proper execution from Claude Desktop
"""
import sys
import traceback
from pathlib import Path

def log_to_stderr(message):
    """Log to stderr for Claude Desktop to capture"""
    print(f"[WRAPPER] {message}", file=sys.stderr, flush=True)

try:
    log_to_stderr("=== MCP Server Wrapper Starting ===")
    log_to_stderr(f"Python version: {sys.version}")
    log_to_stderr(f"Script location: {__file__}")

    # Add project root to path
    project_root = Path(__file__).parent
    log_to_stderr(f"Project root: {project_root}")
    sys.path.insert(0, str(project_root))
    log_to_stderr(f"sys.path updated: {sys.path[0]}")

    # Now run the actual server
    if __name__ == "__main__":
        log_to_stderr("Importing mcp_server module...")
        from src import mcp_server

        log_to_stderr("Importing asyncio...")
        import asyncio

        log_to_stderr("Starting async main function...")
        asyncio.run(mcp_server.main())

except ImportError as e:
    log_to_stderr(f"IMPORT ERROR: {e}")
    log_to_stderr(f"Traceback:\n{traceback.format_exc()}")
    sys.exit(1)
except Exception as e:
    log_to_stderr(f"FATAL ERROR: {e}")
    log_to_stderr(f"Traceback:\n{traceback.format_exc()}")
    sys.exit(1)
