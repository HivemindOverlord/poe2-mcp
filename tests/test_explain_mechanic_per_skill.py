"""
Tests for the per-skill consult tier added to explain_mechanic (task #82).

Closes the follow-up from PR #129 (per-skill .csd extraction). After this
change, explain_mechanic walks four tiers:

  1a    - exact stat_id match in root-level canonical stat_descriptions
  1a-bis - exact match in per-skill bundle (NEW)
  2     - hand-authored mechanics_kb
  1b    - substring search across BOTH canonical sources (root + per-skill)
  miss  - all-tier exhausted message

Two test modes:
  - Helper-direct tests verify the per-skill helpers (already covered by PR
    #129's tests — light spot-check here that they're still wired).
  - Handler tests (methodology-rule-compliant lazy fixture) verify
    explain_mechanic surfaces per-skill records when a stat_id only exists
    in the per-skill bundle.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import pytest_asyncio

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

PER_SKILL_BUNDLE = (
    PROJECT_ROOT / "data" / "game" / "stat_descriptions" / "per_skill_stat_descriptions.json"
)
needs_per_skill = pytest.mark.skipif(
    not PER_SKILL_BUNDLE.exists(),
    reason="per_skill_stat_descriptions.json absent (PR #129 not yet on this checkout)",
)


# ---------------------------------------------------------------------------
# Light spot-checks of the per-skill helpers (already covered by #129's tests)
# ---------------------------------------------------------------------------


@needs_per_skill
def test_per_skill_helpers_importable():
    """Re-confirm the helpers explain_mechanic depends on are present."""
    from src.data.game_data import (
        find_per_skill_stat_description,
        search_per_skill_stat_descriptions,
    )

    assert callable(find_per_skill_stat_description)
    assert callable(search_per_skill_stat_descriptions)


@needs_per_skill
def test_per_skill_search_returns_tagged_hits():
    """Substring search should return hits tagged with source_csd + match_field
    (consumed by explain_mechanic's Tier 1b formatter)."""
    from src.data.game_data import search_per_skill_stat_descriptions

    hits = search_per_skill_stat_descriptions("damage", limit=3)
    assert hits, "expected at least one 'damage' hit in per-skill bundle"
    for h in hits:
        assert "source_csd" in h
        assert "match_field" in h
        assert "primary_stat_id" in h


# ---------------------------------------------------------------------------
# Handler tests — methodology-rule-compliant lazy fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module")
async def mcp():
    """Canonical lazy-import fixture per docs/TESTING.md."""
    from src.mcp_server import PoE2BuildOptimizerMCP

    instance = PoE2BuildOptimizerMCP()
    await instance.initialize()
    return instance


@needs_per_skill
@pytest.mark.asyncio
async def test_no_arg_overview_mentions_per_skill(mcp):
    """The overview (no mechanic_name arg) should advertise the per-skill tier."""
    r = await mcp._handle_explain_mechanic({})
    text = r[0].text
    # Should mention both record counts now
    assert "16,533" in text
    assert "1,240" in text or "1240" in text or "per-skill" in text


@needs_per_skill
@pytest.mark.asyncio
async def test_explain_mechanic_finds_per_skill_only_stat(mcp):
    """A stat_id that exists only in the per-skill bundle should resolve via
    Tier 1a-bis, NOT fall through to hand-authored Tier 2."""
    # Pick a real per-skill-only stat_id. We discover one by querying the
    # bundle directly: find any stat_id in the per-skill bundle that ISN'T
    # in the root index. (For test robustness, we just verify SOME per-skill
    # stat resolves cleanly — the handler should return Tier 1a-bis output.)
    from src.data.game_data import (
        find_stat_description,
        load_per_skill_stat_descriptions,
    )

    bundle = load_per_skill_stat_descriptions()
    assert bundle is not None
    # Walk the bundle for a stat_id that's NOT in the root dataset.
    candidate = None
    for rel_key, file_payload in (bundle.get("per_skill") or {}).items():
        for record in file_payload.get("descriptions") or []:
            for sid in record.get("stat_ids") or []:
                if find_stat_description(sid) is None:
                    candidate = sid
                    break
            if candidate:
                break
        if candidate:
            break
    if not candidate:
        pytest.skip("no per-skill-only stat_id found (root + per-skill overlap is total)")

    r = await mcp._handle_explain_mechanic({"mechanic_name": candidate})
    text = r[0].text
    # Should be a Tier 1 / canonical response, not a "not found" fall-through
    assert "Provenance" in text or "Canonical" in text or "stat_descriptions" in text
    # And should reference the per-skill bundle in some form
    assert "per-skill" in text.lower() or "specific_skill_stat_descriptions" in text


@needs_per_skill
@pytest.mark.asyncio
async def test_substring_search_includes_per_skill_hits(mcp):
    """A substring that hits the per-skill bundle should appear in suggestions."""
    # Pick a query that's only in the per-skill bundle. The per-skill .csd
    # files often have skill-specific tags — "soulthirst" or specific
    # named-skill stats. Fall back to a guaranteed-substring search if needed.
    r = await mcp._handle_explain_mechanic({"mechanic_name": "soulthirst"})
    text = r[0].text
    # Either the substring resolves and we see suggestions, or it's a total
    # miss with all four tiers exhausted. Both are valid handler responses;
    # we just want to verify the per-skill tier was CONSULTED (text mentions it).
    if "Suggestions for" in text:
        # Substring fallback: response mentions BOTH sources now
        assert "1,240" in text or "per-skill" in text.lower()
    elif "No match" in text:
        # All-tier-exhausted message: must list per-skill as one of the tiers
        assert "per-skill" in text.lower() or "Tier 1a-bis" in text


@needs_per_skill
@pytest.mark.asyncio
async def test_root_tier_1_still_works(mcp):
    """Regression: queries that hit Tier 1a (root canonical) must NOT be
    derailed by the per-skill consult."""
    # support_ignite_proliferation_radius is the canonical example from
    # PR #101's docstring — must continue resolving via Tier 1a.
    r = await mcp._handle_explain_mechanic({"mechanic_name": "support_ignite_proliferation_radius"})
    text = r[0].text
    assert "Provenance" in text
    # Should NOT have routed through per-skill bundle (root dataset hit wins)
    assert "per-skill bundle" not in text.lower()


@needs_per_skill
@pytest.mark.asyncio
async def test_total_miss_lists_all_tiers(mcp):
    """When everything misses (incl. the BM25 lexical tier added in #177),
    the failure message enumerates all tiers. Uses a tokenless garbage
    query — anything with real English words now falls to the BM25 tier
    rather than total-miss (by design)."""
    r = await mcp._handle_explain_mechanic({"mechanic_name": "zzqqxxvv_jkqwzx"})
    text = r[0].text
    assert "No match" in text
    assert "Tier 1a" in text and ("1a-bis" in text or "per-skill" in text.lower())
    assert "1c" in text or "BM25" in text  # the new lexical tier is listed


@pytest.mark.asyncio
async def test_bm25_tier_catches_morphological_miss(mcp):
    """A word that substring-misses but stems to a real stat returns the
    BM25 lexical tier, not total-miss."""
    r = await mcp._handle_explain_mechanic({"mechanic_name": "withering"})
    text = r[0].text
    # Either a canonical hit or the BM25 tier — never a total miss
    assert "No match" not in text
