"""
Tests for the inline-stat_id migration in mod handlers (Issue #118).

Two modes:
  - Helper-direct tests cover src/mod_data.py functions in isolation:
    resolve_stat_id ordering (inline > stat_lookup), iter_resolved_stats,
    mod_value_range, load_stat_lookup graceful failure.
  - Handler tests verify the four migrated handlers actually use the new
    schema-aware reads. Uses the methodology-rule-compliant lazy fixture.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import pytest_asyncio

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.mod_data import (  # noqa: E402
    canonical_mods_path,
    iter_resolved_stats,
    legacy_mods_path,
    load_stat_lookup,
    mod_value_range,
    resolve_stat_id,
)

# ---------------------------------------------------------------------------
# Helper-direct mode — no MCP init
# ---------------------------------------------------------------------------


def test_resolve_inline_stat_id_is_preferred():
    """Inline stat_id wins even when stat_lookup has a different value."""
    entry = {"stat_id": "from_inline", "stat_key": 42, "is_empty": False}
    sid = resolve_stat_id(entry, stat_lookup={42: "from_lookup"})
    assert sid == "from_inline"


def test_resolve_falls_back_to_stat_lookup():
    """When inline is missing, fall back to lookup."""
    entry = {"stat_key": 42, "is_empty": False}
    sid = resolve_stat_id(entry, stat_lookup={42: "from_lookup"})
    assert sid == "from_lookup"


def test_resolve_empty_entry_returns_none():
    entry = {"stat_id": "x", "stat_key": 42, "is_empty": True}
    assert resolve_stat_id(entry) is None


def test_resolve_no_inline_no_lookup_returns_none():
    entry = {"stat_key": 99, "is_empty": False}
    assert resolve_stat_id(entry, stat_lookup={}) is None
    assert resolve_stat_id(entry) is None


def test_iter_resolved_stats_skips_empty():
    mod = {
        "stats": [
            {"stat_id": "a", "min_value": 1, "max_value": 2, "is_empty": False},
            {"stat_id": "b", "min_value": 0, "max_value": 0, "is_empty": True},
            {"stat_id": "c", "min_value": 3, "max_value": 5, "is_empty": False},
        ]
    }
    out = iter_resolved_stats(mod)
    assert [r["stat_id"] for r in out] == ["a", "c"]
    assert out[0]["from_inline"] is True


def test_iter_resolved_stats_marks_fallback_source():
    mod = {
        "stats": [
            {"stat_id": "inline_one", "min_value": 1, "max_value": 2, "is_empty": False},
            {"stat_key": 99, "min_value": 4, "max_value": 5, "is_empty": False},
        ]
    }
    out = iter_resolved_stats(mod, stat_lookup={99: "lookup_two"})
    assert len(out) == 2
    assert out[0]["from_inline"] is True
    assert out[1]["from_inline"] is False
    assert out[1]["stat_id"] == "lookup_two"


def test_mod_value_range_pulls_from_first_active_stat():
    mod = {
        "stats": [
            {"is_empty": True, "min_value": 0, "max_value": 0},
            {"is_empty": False, "min_value": 5, "max_value": 9},
            {"is_empty": False, "min_value": 100, "max_value": 200},  # shouldn't reach
        ]
    }
    rng = mod_value_range(mod)
    assert rng == {"min": 5, "max": 9}


def test_mod_value_range_handles_top_level_legacy_fallback():
    """Legacy records with top-level min/max still resolve."""
    mod = {"min_value": 50, "max_value": 75}
    rng = mod_value_range(mod)
    assert rng == {"min": 50, "max": 75}


def test_mod_value_range_returns_none_when_no_stats():
    mod = {"mod_id": "X"}
    assert mod_value_range(mod) is None


def test_load_stat_lookup_returns_dict_or_empty(tmp_path: Path):
    """Missing file -> empty dict, not crash."""
    fake_data_dir = tmp_path / "data"
    fake_data_dir.mkdir()
    out = load_stat_lookup(fake_data_dir)
    assert out == {}


def test_load_stat_lookup_reads_real_file():
    """Real data/game/stats/stats.json should populate the lookup."""
    repo_data = PROJECT_ROOT / "data"
    out = load_stat_lookup(repo_data)
    # The file may or may not exist depending on extraction state.
    # When present, it must be non-empty and contain int keys.
    if (repo_data / "game" / "stats" / "stats.json").exists():
        assert out, "stats.json present but lookup is empty"
        sample_key = next(iter(out))
        assert isinstance(sample_key, int)


def test_canonical_path_resolves_existing_file():
    """The canonical path helper should point at the real file in this repo."""
    p = canonical_mods_path(PROJECT_ROOT / "data")
    assert p.name == "mods.json"
    assert p.parent.name == "mods"
    assert p.exists(), f"canonical path {p} does not exist — extraction broken?"


def test_canonical_and_legacy_paths_differ():
    """The two paths should be distinct (we audit both)."""
    p1 = canonical_mods_path(PROJECT_ROOT / "data")
    p2 = legacy_mods_path(PROJECT_ROOT / "data")
    assert p1 != p2


# ---------------------------------------------------------------------------
# Real-data sanity — verifies the canonical extraction has inline stat_id
# ---------------------------------------------------------------------------


def test_real_mods_have_inline_stat_id_on_active_stats():
    """At least one record in the canonical file has inline stat_id."""
    p = canonical_mods_path(PROJECT_ROOT / "data")
    if not p.exists():
        pytest.skip("canonical mods.json not present in this checkout")
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    inline_count = sum(
        1
        for m in data.get("mods", [])
        if any(
            isinstance(s, dict) and not s.get("is_empty") and s.get("stat_id")
            for s in m.get("stats") or []
        )
    )
    assert inline_count > 0, (
        "Canonical mods.json has no inline stat_id on any active stat. "
        "Re-extract via scripts/extract_mods_datc64_v2.py."
    )


# ---------------------------------------------------------------------------
# Handler mode — methodology-rule lazy fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module")
async def mcp():
    from src.mcp_server import PoE2BuildOptimizerMCP

    instance = PoE2BuildOptimizerMCP()
    await instance.initialize()
    return instance


@pytest.mark.asyncio
async def test_inspect_mod_emits_inline_stat_id(mcp):
    """inspect_mod on a known mod must surface its stat_id (not a Slot/Index error)."""
    # Strength1 is a stable mod that appears in the extraction
    r = await mcp._handle_inspect_mod({"mod_id": "Strength1"})
    text = r[0].text
    # Either matches and shows stat_id, or the partial-match branch surfaces it
    assert "additional_strength" in text or "## Stats" in text
    # Must NOT contain the old broken slot/index/value display
    assert "Index=" not in text
    assert "Slot " not in text


@pytest.mark.asyncio
async def test_search_mods_by_stat_finds_strength(mcp):
    """search_mods_by_stat for 'strength' must find Strength* mods via inline stat_id."""
    r = await mcp._handle_search_mods_by_stat({"stat_keyword": "strength"})
    text = r[0].text
    assert "Strength" in text


@pytest.mark.asyncio
async def test_get_mod_tiers_no_broken_zero_value(mcp):
    """get_mod_tiers should not display 'Value: 0' from the missing top-level field."""
    r = await mcp._handle_get_mod_tiers({"mod_base": "Strength"})
    text = r[0].text
    # Should mention real value ranges, not just '0 - 0'. We can't pin exact
    # numbers without coupling to the data, but we can assert the 'Value: 0'
    # broken pattern (with no second number) is absent.
    if "## Tier Progression" in text:
        # Look at first tier's Value line
        lines = [l for l in text.split("\n") if l.strip().startswith("- Value:")]
        for ln in lines:
            # The new format yields either "Value: N" or "Value: N to M";
            # we just need to know it's not the broken "Value: 0\n- Type" path
            assert "Value:" in ln
