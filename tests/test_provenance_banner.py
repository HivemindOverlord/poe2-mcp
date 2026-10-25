"""
Tests for the P3 / Issue #116 provenance banner helper and its inspect_*
handler wiring.

Two test modes:
  - Helper-direct tests exercise src/provenance.py's format_banner() in
    isolation. They cover the tier vocab, ASCII-safety, version.json
    auto-load, and explicit-override paths. No MCP init required — fast.
  - Handler tests invoke the wired inspect_* handlers and assert that
    every successful response carries the banner with the right tier +
    source. Uses the methodology-rule-compliant lazy-fixture pattern
    documented in docs/TESTING.md (and PR #120 for the canonical template).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import pytest_asyncio

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.provenance import (  # noqa: E402
    CANONICAL,
    COMPUTED,
    EXTERNAL,
    INTERPRETED,
    format_banner,
)

# ---------------------------------------------------------------------------
# Helper-direct mode — no MCP init
# ---------------------------------------------------------------------------


def test_helper_tier_vocab_constants():
    """The four tier constants are stable, lowercase strings."""
    assert CANONICAL == "canonical"
    assert COMPUTED == "computed"
    assert INTERPRETED == "interpreted"
    assert EXTERNAL == "external"


def test_helper_banner_contains_tier_and_separator():
    """Format anchor — banner has a divider and a tier line in a known shape."""
    out = format_banner(CANONICAL, source="some/path")
    assert out.startswith("---\n")
    assert "**Tier**: canonical" in out
    assert "**Source**: some/path" in out


def test_helper_banner_no_source_when_missing():
    out = format_banner(CANONICAL)
    assert "**Source**" not in out
    # Still has the data + tier line
    assert "**Tier**: canonical" in out


def test_helper_interpreted_tier_adds_warning():
    out = format_banner(INTERPRETED, source="poe2_mechanics.py")
    assert "Warning:" in out
    assert "in-game tooltip" in out.lower()


def test_helper_external_tier_adds_note():
    out = format_banner(EXTERNAL, source="poe.ninja/api")
    assert "external source" in out.lower()
    assert "indexer recency" in out.lower()


def test_helper_canonical_tier_has_no_warning():
    """Canonical data needs no caveat."""
    out = format_banner(CANONICAL, source="data/game/passive_tree/")
    assert "Warning:" not in out
    assert "external source" not in out.lower()


def test_helper_pulls_version_from_data_game():
    """When version isn't supplied, helper reads data/game/version.json."""
    out = format_banner(CANONICAL)
    # Either the real version string surfaced, or fallback 'unknown' if the
    # file is somehow missing. Both must be ASCII.
    assert "**Data**:" in out
    assert "**Tier**: canonical" in out


def test_helper_explicit_version_override():
    """Caller-supplied version + extracted_at override the file lookup."""
    out = format_banner(CANONICAL, source="x", version="data-v9.9.9-r99", extracted_at="2099-12-31")
    assert "data-v9.9.9-r99" in out
    assert "2099-12-31" in out


def test_helper_ascii_safe_output():
    """No Unicode characters in any banner shape — Windows cp1252 logs.

    Previous attempt used U+00B7 (middle dot) and a Unicode warning emoji;
    both raised UnicodeEncodeError in the maintainer's terminal. ASCII-only
    is the contract."""
    for tier in (CANONICAL, COMPUTED, INTERPRETED, EXTERNAL):
        out = format_banner(tier, source="some/source")
        out.encode("ascii")  # Raises if non-ASCII present


# ---------------------------------------------------------------------------
# Handler mode — lazy fixture per docs/TESTING.md
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module")
async def mcp():
    """Canonical lazy-import fixture (see PR #120)."""
    from src.mcp_server import PoE2BuildOptimizerMCP

    instance = PoE2BuildOptimizerMCP()
    await instance.initialize()
    return instance


def _banner_present(text: str) -> bool:
    """Detect the banner footer in a handler response."""
    return "**Data**:" in text and "**Tier**:" in text


@pytest.mark.asyncio
async def test_inspect_passive_node_has_banner(mcp):
    """Pick a known passive — banner must trail the response."""
    # Use a permissive query — any keystone will do, the banner is what we test.
    keystones = mcp.passive_tree_resolver.get_all_keystones() if mcp.passive_tree_resolver else []
    if not keystones:
        pytest.skip("passive_tree_resolver has no keystones in this env")
    name = keystones[0].name
    r = await mcp._handle_inspect_passive_node({"node_name": name})
    text = r[0].text
    assert _banner_present(
        text
    ), f"banner missing from inspect_passive_node response: {text[-300:]}"
    assert "passive_tree" in text


@pytest.mark.asyncio
async def test_inspect_keystone_has_banner(mcp):
    keystones = mcp.passive_tree_resolver.get_all_keystones() if mcp.passive_tree_resolver else []
    if not keystones:
        pytest.skip("passive_tree_resolver has no keystones in this env")
    name = keystones[0].name
    r = await mcp._handle_inspect_keystone({"keystone_name": name})
    text = r[0].text
    assert _banner_present(text)
    assert "passive_tree" in text


@pytest.mark.asyncio
async def test_inspect_support_gem_has_banner(mcp):
    """Wildfire — known to be in canonical post-PR-#113."""
    r = await mcp._handle_inspect_support_gem({"support_name": "Wildfire"})
    text = r[0].text
    assert _banner_present(text)
    # Either main support_gems file or Tier-2 fallback — both surface in source
    assert "support_gems" in text or "skill_gems" in text


@pytest.mark.asyncio
async def test_inspect_spell_gem_has_banner(mcp):
    """Ice Nova — canonical spell in skill_gems."""
    r = await mcp._handle_inspect_spell_gem({"spell_name": "Ice Nova"})
    text = r[0].text
    assert _banner_present(text)


@pytest.mark.asyncio
async def test_banner_tier_is_canonical_on_inspect_handlers(mcp):
    """All inspect_* responses should carry CANONICAL tier (no INTERPRETED)."""
    keystones = mcp.passive_tree_resolver.get_all_keystones() if mcp.passive_tree_resolver else []
    if keystones:
        r = await mcp._handle_inspect_keystone({"keystone_name": keystones[0].name})
        text = r[0].text
        assert "**Tier**: canonical" in text
        assert "**Tier**: interpreted" not in text
