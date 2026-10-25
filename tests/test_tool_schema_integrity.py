"""
Recurrence guard: every registered MCP tool's inputSchema must be accepted by
the Anthropic Messages API.

Context (2026-07-06): three tools (`inspect_spell_gem`,
`validate_support_combination`, `inspect_keystone`) shipped a top-level
`oneOf` in their `inputSchema`. The Anthropic Messages API rejects top-level
`oneOf`/`allOf`/`anyOf` with a 400 during `tools/list` validation — which fails
the ENTIRE conversation, not just the offending tool, for every Anthropic-backed
client (Claude Code, Claude Desktop, SDK). External contributor Thiago Noronha
(@3lackd-projetos) reported it; the schema constraints were redundant because the
handlers already do alias OR-fallback and return a friendly error when none is
supplied.

These tests walk the tools the server ACTUALLY registers (not the source text)
and assert each schema stays inside the API's accepted shape, so the whole class
of bug can't silently return via a new tool.

Ref: https://docs.anthropic.com/en/docs/build-with-claude/tool-use
"""

import sys
from pathlib import Path

import mcp.types as types
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.mcp_server import PoE2BuildOptimizerMCP

# Keys the Anthropic Messages API rejects at the TOP level of input_schema.
# (They remain legal nested inside `properties` — only the top level is checked.)
FORBIDDEN_TOP_LEVEL_KEYS = ("oneOf", "allOf", "anyOf")


async def _registered_tools():
    """Return the tool list the server actually hands to clients via tools/list."""
    server = PoE2BuildOptimizerMCP()
    handler = server.server.request_handlers[types.ListToolsRequest]
    result = await handler(types.ListToolsRequest(method="tools/list"))
    return result.root.tools


@pytest.mark.asyncio
async def test_no_top_level_schema_combinators():
    """No registered tool may carry a top-level oneOf/allOf/anyOf (Anthropic 400)."""
    tools = await _registered_tools()
    assert tools, "expected the server to register at least one tool"

    offenders = {
        tool.name: [k for k in FORBIDDEN_TOP_LEVEL_KEYS if k in tool.inputSchema] for tool in tools
    }
    offenders = {name: keys for name, keys in offenders.items() if keys}

    assert not offenders, (
        "These tools use a top-level oneOf/allOf/anyOf, which the Anthropic "
        "Messages API rejects with a 400 during tools/list — breaking every "
        f"Anthropic-backed conversation, not just the tool: {offenders}. "
        "Express 'at least one alias required' in the handler (OR-fallback + a "
        "friendly error) instead of the schema."
    )


@pytest.mark.asyncio
async def test_every_input_schema_is_a_typed_object():
    """The API also requires input_schema to be a top-level {'type': 'object'}."""
    tools = await _registered_tools()

    bad = {
        tool.name: tool.inputSchema.get("type")
        for tool in tools
        if tool.inputSchema.get("type") != "object"
    }

    assert not bad, (
        "Every tool inputSchema must be a top-level object "
        f"(type == 'object'). Offenders → declared type: {bad}"
    )
