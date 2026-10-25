"""
Tests for the per-skill stat_descriptions dataset and helpers.

Closes the deferred-from-PR-#98 scope: PR #98 shipped 18 root-level .csd
files (16,533 descriptions). This dataset ships the per-skill subtree
(296 files under specific_skill_stat_descriptions/, 1,240 descriptions).

Two layers:
  - csd_parser helper tests against an embedded .csd fixture.
  - Real-data sanity tests against the shipped JSON output.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.game_data import (  # noqa: E402
    find_per_skill_stat_description,
    load_per_skill_stat_descriptions,
    search_per_skill_stat_descriptions,
)
from src.parsers.csd_parser import parse_csd  # noqa: E402

# ---------------------------------------------------------------------------
# Parser tests against an embedded fixture
# ---------------------------------------------------------------------------

FIXTURE = """description
\t1 test_stat_one
\t1
\t\t# "Test stat one template {0}" handler_a
description
\t2 test_multi_a test_multi_b
\t2
\t\t# "Multi-stat template {0} and {1}" handler_b handler_c
\t\t1 "Exact one: {0}"
no_description silent_stat
description
\t1 with_lang_test
\t1
\t\t# "English line"
\tlang "German"
\t1
\t\t# "German line"
"""


def test_parser_returns_two_lists():
    desc, no_desc = parse_csd(FIXTURE, "fixture.csd")
    assert isinstance(desc, list)
    assert isinstance(no_desc, list)


def test_parser_descriptions_count():
    desc, _ = parse_csd(FIXTURE, "fixture.csd")
    assert len(desc) == 3


def test_parser_no_description_captured():
    _, no_desc = parse_csd(FIXTURE, "fixture.csd")
    assert len(no_desc) == 1
    assert no_desc[0]["stat_id"] == "silent_stat"


def test_parser_extracts_stat_ids():
    desc, _ = parse_csd(FIXTURE, "fixture.csd")
    assert desc[0]["stat_ids"] == ["test_stat_one"]
    assert desc[0]["primary_stat_id"] == "test_stat_one"
    assert desc[1]["stat_ids"] == ["test_multi_a", "test_multi_b"]


def test_parser_extracts_variants():
    desc, _ = parse_csd(FIXTURE, "fixture.csd")
    variants = desc[1]["variants"]
    assert len(variants) == 2
    assert variants[0]["range"] == "#"
    assert variants[0]["template"] == "Multi-stat template {0} and {1}"
    assert variants[0]["handlers"] == ["handler_b", "handler_c"]
    assert variants[1]["range"] == "1"
    assert variants[1]["template"] == "Exact one: {0}"


def test_parser_only_collects_english_variants():
    """Other languages are skipped — only English templates ship in v1."""
    desc, _ = parse_csd(FIXTURE, "fixture.csd")
    # The third description has English + German; we keep only the English
    # variant template but record German in languages_available.
    rec = desc[2]
    assert rec["primary_template"] == "English line"
    assert "German" in rec["languages_available"]


def test_parser_handles_empty_input():
    desc, no_desc = parse_csd("", "fixture.csd")
    assert desc == []
    assert no_desc == []


# ---------------------------------------------------------------------------
# Real-data sanity tests against the shipped bundle
# ---------------------------------------------------------------------------

BUNDLE_PATH = (
    PROJECT_ROOT / "data" / "game" / "stat_descriptions" / "per_skill_stat_descriptions.json"
)
needs_bundle = pytest.mark.skipif(
    not BUNDLE_PATH.exists(),
    reason="per_skill_stat_descriptions.json not shipped in this checkout",
)


@needs_bundle
def test_bundle_loads():
    """Bundle loads via the convenience helper."""
    bundle = load_per_skill_stat_descriptions()
    assert bundle is not None
    assert "per_skill" in bundle
    assert bundle.get("schema_version") == 1


@needs_bundle
def test_bundle_record_count_consistent_with_metadata():
    """metadata.json's record_count should equal the actual description tally."""
    meta_path = PROJECT_ROOT / "data" / "game" / "stat_descriptions" / "per_skill_metadata.json"
    assert meta_path.exists()
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    bundle = load_per_skill_stat_descriptions()
    assert bundle is not None
    actual = sum(len(p.get("descriptions") or []) for p in bundle.get("per_skill", {}).values())
    assert actual == meta["description_count"]


@needs_bundle
def test_bundle_covers_known_skills():
    """Spot-check a few well-known skill files."""
    bundle = load_per_skill_stat_descriptions()
    assert bundle is not None
    keys = set(bundle.get("per_skill", {}).keys())
    # ball_lightning.csd at root level
    assert "ball_lightning.csd" in keys or any("ball_lightning" in k for k in keys)


@needs_bundle
def test_find_per_skill_unknown_returns_none():
    assert find_per_skill_stat_description("definitely_not_a_real_stat_id") is None
    assert find_per_skill_stat_description("") is None


@needs_bundle
def test_search_per_skill_empty_query_returns_empty():
    assert search_per_skill_stat_descriptions("") == []


@needs_bundle
def test_search_per_skill_finds_some_hits():
    """Substring search on a common token should find at least one hit."""
    hits = search_per_skill_stat_descriptions("damage", limit=5)
    assert isinstance(hits, list)
    # If the search returns nothing on 'damage' across 1240 records, the
    # bundle is empty or busted - flag clearly.
    assert len(hits) > 0
    # Each hit should be tagged with source_skill
    for h in hits:
        assert "source_skill" in h
        assert "match_field" in h


@needs_bundle
def test_version_json_includes_per_skill_dataset():
    """version.json should advertise the new dataset entry."""
    v_path = PROJECT_ROOT / "data" / "game" / "version.json"
    with open(v_path, "r", encoding="utf-8") as f:
        v = json.load(f)
    datasets = v.get("datasets") or {}
    assert "per_skill_stat_descriptions" in datasets
    entry = datasets["per_skill_stat_descriptions"]
    assert entry["record_count"] > 0
    assert "per_skill_stat_descriptions.json" in entry.get("files", [])
