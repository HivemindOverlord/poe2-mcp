"""
Tests for the reverse stat-source lookup + explain_mechanic cluster mode
(field-feedback wishes, 2026-06-11) and the issue #155 fuzzy-matcher fixes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import pytest_asyncio

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.stat_source_index import StatSourceIndex, get_stat_source_index

# ---------------------------------------------------------------------------
# StatSourceIndex unit tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def index():
    idx = StatSourceIndex()
    idx._ensure_built()
    return idx


def test_index_builds_from_local_data(index):
    """Skill and mod indices populate from tracked game data."""
    assert len(index._skill_index) > 100
    assert len(index._mod_index) > 100
    assert len(index._passive_nodes) > 1000


def test_wither_skills_found(index):
    """The headline feedback case: wither sources are enumerable."""
    sources = index.find_sources("wither")
    assert sources["skills"], "wither stat_ids should map to skills"
    all_skills = {s for skills in sources["skills"].values() for s in skills}
    assert "Withering Touch" in all_skills


def test_passive_text_match(index):
    """Passive nodes match on stat TEXT, not just ids."""
    sources = index.find_sources("chance to Shock")
    assert sources["passive_nodes"]
    assert any("shock" in s.lower() for n in sources["passive_nodes"] for s in n["stats"])


def test_mod_stat_id_match(index):
    sources = index.find_sources("withered_magnitude")
    assert sources["mods"]
    mods = next(iter(sources["mods"].values()))
    assert any(m.get("display_name") for m in mods)


def test_exact_stat_id_skill_lookup(index):
    skills = index.skills_granting_stat("spell_minimum_base_fire_damage")
    assert "Fireball" in skills


def test_empty_display_name_mods_not_collapsed(index):
    """Field bug 2026-06-16: convert_to_fire mods are IMPLICITs with an empty
    display_name. The dedup must key on mod_id so distinct mods survive instead
    of collapsing into a single ('', generation_type) entry."""
    sources = index.find_sources("convert_to_fire")
    assert sources["mods"], "convert_to_fire stat_ids should map to mods"
    phys = sources["mods"].get("non_skill_base_physical_damage_%_to_convert_to_fire")
    assert phys, "the core phys->fire conversion stat must be present"
    # Pre-fix this collapsed to 1; there are many distinct unique/monster mods.
    assert len(phys) > 5, f"expected multiple distinct mods, got {len(phys)}"
    # Every entry must carry a usable label (mod_id, since display_name is blank)
    assert all(m.get("mod_id") for m in phys)


def test_empty_query_returns_empty(index):
    sources = index.find_sources("")
    assert sources["skills"] == {}
    assert sources["passive_nodes"] == []


def test_limit_respected(index):
    sources = index.find_sources("damage", limit_per_source=3)
    assert len(sources["skills"]) <= 3
    assert len(sources["passive_nodes"]) <= 3
    assert len(sources["mods"]) <= 3


def test_missing_data_dir_degrades_gracefully(tmp_path):
    idx = StatSourceIndex(data_dir=tmp_path)
    sources = idx.find_sources("wither")
    assert sources["skills"] == {}
    assert sources["ascendancy_data_available"] is False


def test_singleton_accessor():
    assert get_stat_source_index() is get_stat_source_index()


# ---------------------------------------------------------------------------
# Issue #155 — knowledge-base entries + matcher ranking
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def kb():
    from src.knowledge.poe2_mechanics import PoE2MechanicsKnowledgeBase

    return PoE2MechanicsKnowledgeBase()


def test_chaos_damage_entry_exists(kb):
    m = kb.get_mechanic("chaos damage")
    assert m is not None
    assert m.name == "Chaos Damage"


def test_wither_entry_exists(kb):
    m = kb.get_mechanic("wither")
    assert m is not None
    assert m.name == "Wither"


def test_search_ranks_name_matches_first(kb):
    """'chaos damage' must surface Chaos Damage, not Poison (#155)."""
    results = kb.search_mechanics("chaos damage")
    assert results
    assert results[0].name == "Chaos Damage"


def test_search_body_matches_still_found(kb):
    """Description-text matches remain reachable, just ranked lower."""
    results = kb.search_mechanics("chaos damage")
    names = [m.name for m in results]
    assert "Poison" in names
    assert names.index("Chaos Damage") < names.index("Poison")


# ---------------------------------------------------------------------------
# Handler integration
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module")
async def mcp():
    from src.mcp_server import PoE2BuildOptimizerMCP

    instance = PoE2BuildOptimizerMCP()
    await instance.initialize()
    return instance


@pytest.mark.asyncio
async def test_find_stat_sources_handler(mcp):
    r = await mcp._handle_find_stat_sources({"query": "wither"})
    text = r[0].text
    assert "Withering Touch" in text
    assert "## Skills" in text
    assert "## Passive tree nodes" in text


@pytest.mark.asyncio
async def test_find_stat_sources_renders_empty_display_name_mods(mcp):
    """Field bug 2026-06-16: mods with empty display_name were dropped by the
    `if m.get('display_name')` filter, leaving blank entries. The renderer must
    fall back to mod_id so item-mod sources are actually shown."""
    r = await mcp._handle_find_stat_sources({"query": "convert_to_fire"})
    text = r[0].text
    assert "## Item mods" in text
    # The mod_id fallback should appear in the output (not a blank entry).
    assert "ConvertPhysicalToFire" in text or "MapMonster" in text


@pytest.mark.asyncio
async def test_list_all_mods_filter_by_stat_id(mcp):
    """Field bug 2026-06-16: list_all_mods filter_stat only matched mod_id, so a
    stat-id query returned 0 results. It must now agree with find_stat_sources
    and match resolved stat_ids too."""
    r = await mcp._handle_list_all_mods({"filter_stat": "convert_to_fire", "limit": 5})
    text = r[0].text
    # Header is "# Mods (N of TOTAL)" — TOTAL must be non-zero now.
    import re

    m = re.search(r"# Mods \(\d+ of (\d+)\)", text)
    assert m, f"unexpected header: {text.splitlines()[0]!r}"
    assert int(m.group(1)) > 0, "filter_stat by stat_id must find conversion mods"


@pytest.mark.asyncio
async def test_find_stat_sources_completes_under_timeout(mcp):
    """Field bug #4 2026-06-16: a single query must never hang the session.
    The exact reported query should return promptly via the timeout guard."""
    import asyncio

    r = await asyncio.wait_for(
        mcp._handle_find_stat_sources(
            {"query": "corpse_explosion_monster_life_permillage_physical"}
        ),
        timeout=20.0,
    )
    assert r and r[0].text


@pytest.mark.asyncio
async def test_find_stat_sources_requires_query(mcp):
    r = await mcp._handle_find_stat_sources({})
    assert "Error" in r[0].text


@pytest.mark.asyncio
async def test_find_stat_sources_no_match(mcp):
    r = await mcp._handle_find_stat_sources({"query": "zzz_no_such_stat_xyz"})
    text = r[0].text
    assert "No skills" in text


@pytest.mark.asyncio
async def test_cluster_dump_mode(mcp):
    """The one-call cluster dump the feedback asked for."""
    r = await mcp._handle_explain_mechanic(
        {
            "mechanic_name": "infusion",
            "cluster": True,
        }
    )
    text = r[0].text
    assert "Cluster dump" in text
    assert "Canonical stat_ids" in text
    assert "Granted by skills:" in text


@pytest.mark.asyncio
async def test_explain_chaos_damage_returns_chaos_entry(mcp):
    """#155 acceptance: 'chaos damage' returns the chaos entry, not Poison."""
    r = await mcp._handle_explain_mechanic({"mechanic_name": "chaos damage"})
    text = r[0].text
    assert "CHAOS DAMAGE" in text.upper()
    assert "stack limit" not in text.lower()[:500]  # not the Poison entry


@pytest.mark.asyncio
async def test_explain_wither_returns_summary(mcp):
    """#155 acceptance: 'wither' returns a top-level summary."""
    r = await mcp._handle_explain_mechanic({"mechanic_name": "wither"})
    text = r[0].text
    assert "WITHER" in text.upper()
    assert "chaos damage" in text.lower()
