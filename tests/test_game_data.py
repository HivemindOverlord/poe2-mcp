"""
Tests for src/data/game_data.py — the canonical-paths module for data/game/.

Covers the base API that's on main:
  - Path constants point at data/game/ and the dataset folders that exist
  - load_*() helpers return parsed JSON of the expected shape
  - get_version() returns a sane manifest
  - load_stats() returns the {row_index: stat_id} dict form (not the raw envelope)
  - load_metadata() reads per-dataset metadata.json files
  - describe() returns a non-empty human-readable summary

These tests deliberately do NOT exercise the convenience-lookup helpers
(find_ascendancies_by_base_class, find_mods_by_stat_id, get_keystones, etc.)
— those live on PR #80 and will get their own test file once that lands.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the project root importable so `from src.data.game_data import ...` works
# regardless of how pytest is invoked.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data import game_data

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------


def test_game_data_dir_is_under_repo():
    """GAME_DATA_DIR resolves to <repo>/data/game/ — not somewhere unexpected."""
    assert game_data.GAME_DATA_DIR == PROJECT_ROOT / "data" / "game"


def test_game_data_dir_exists():
    """The data/game/ directory ships in the repo — it should always exist."""
    assert game_data.GAME_DATA_DIR.is_dir(), (
        f"Expected {game_data.GAME_DATA_DIR} to be a directory — is the data/game/ "
        "tree missing from the repo?"
    )


def test_version_json_path_exists():
    """version.json is the global manifest and ships in the repo."""
    assert (
        game_data.VERSION_JSON.exists()
    ), "data/game/version.json missing — every data revision must update it."


def test_dataset_dir_constants_match_folder_names():
    """The *_DIR constants resolve to the folder names documented in version.json."""
    expected_pairs = [
        (game_data.MODS_DIR, "mods"),
        (game_data.PASSIVE_TREE_DIR, "passive_tree"),
        (game_data.SUPPORT_GEMS_DIR, "support_gems"),
        (game_data.ASCENDANCIES_DIR, "ascendancies"),
        (game_data.STATS_DIR, "stats"),
        (game_data.SKILL_GEMS_DIR, "skill_gems"),
    ]
    for path, expected_name in expected_pairs:
        assert (
            path.name == expected_name
        ), f"{path} ends in '{path.name}', expected '{expected_name}'"
        assert path.parent == game_data.GAME_DATA_DIR, f"{path} not parented under GAME_DATA_DIR"


def test_dataset_data_files_under_their_dirs():
    """*_JSON constants live inside the matching *_DIR — not floating in the repo."""
    pairs = [
        (game_data.MODS_JSON, game_data.MODS_DIR),
        (game_data.PASSIVE_TREE_JSON, game_data.PASSIVE_TREE_DIR),
        (game_data.SUPPORT_GEMS_JSON, game_data.SUPPORT_GEMS_DIR),
        (game_data.ASCENDANCIES_JSON, game_data.ASCENDANCIES_DIR),
        (game_data.STATS_JSON, game_data.STATS_DIR),
    ]
    for data_file, parent_dir in pairs:
        assert data_file.parent == parent_dir
        assert data_file.suffix == ".json"


def test_metadata_path_constants_consistent():
    """Each *_META points at <dataset>/metadata.json."""
    for meta in (
        game_data.MODS_META,
        game_data.PASSIVE_TREE_META,
        game_data.SUPPORT_GEMS_META,
        game_data.ASCENDANCIES_META,
        game_data.STATS_META,
    ):
        assert meta.name == "metadata.json", f"{meta} not named metadata.json"


# ---------------------------------------------------------------------------
# get_version()
# ---------------------------------------------------------------------------


def test_get_version_returns_dict():
    v = game_data.get_version()
    assert isinstance(v, dict)


def test_get_version_has_required_fields():
    v = game_data.get_version()
    # These fields are load-bearing for the data lifecycle — describe()
    # and downstream callers all assume they're present.
    for field in ("patch_version", "data_revision", "released_as", "datasets"):
        assert field in v, f"version.json missing required field '{field}'"


def test_get_version_datasets_match_dir_constants():
    """Each `datasets` entry should match one of our *_DIR constants by path."""
    v = game_data.get_version()
    dataset_names = set(v["datasets"].keys())
    # The shipped datasets we have constants for. skill_gems is intentionally
    # excluded — it lives under datasets_pending_0_5_reextract, not datasets.
    expected_subset = {"mods", "passive_tree", "support_gems", "ascendancies", "stats"}
    assert expected_subset.issubset(
        dataset_names
    ), f"version.json datasets {dataset_names} missing one of {expected_subset}"


# ---------------------------------------------------------------------------
# load_*() — shape checks only; we trust the JSON contents
# ---------------------------------------------------------------------------


def test_load_mods_returns_dict_with_records():
    mods = game_data.load_mods()
    assert isinstance(mods, dict)
    # Per data/game/mods/metadata.json, this is a wrapped payload with a
    # records-like array under one of the conventional keys.
    assert any(
        isinstance(mods.get(k), list) and mods[k] for k in ("mods", "records", "rows", "entries")
    ), "load_mods() returned no list payload under any conventional key"


def test_load_passive_tree_returns_dict():
    tree = game_data.load_passive_tree()
    assert isinstance(tree, dict)
    assert tree, "load_passive_tree() returned an empty dict"


def test_load_support_gems_returns_dict():
    sg = game_data.load_support_gems()
    assert isinstance(sg, dict)
    assert sg, "load_support_gems() returned an empty dict"


def test_load_ascendancies_returns_dict():
    asc = game_data.load_ascendancies()
    assert isinstance(asc, dict)
    assert asc, "load_ascendancies() returned an empty dict"


def test_load_stats_returns_int_keyed_dict():
    """load_stats() is documented to flatten to {row_index: stat_id} — verify."""
    stats = game_data.load_stats()
    assert isinstance(stats, dict)
    assert stats, "load_stats() returned an empty dict"

    # Sample a few entries to confirm shape
    sample_keys = list(stats.keys())[:5]
    for k in sample_keys:
        assert isinstance(k, int), f"stats key {k!r} not an int (got {type(k).__name__})"
        assert (
            isinstance(stats[k], str) and stats[k]
        ), f"stats[{k}] not a non-empty string (got {stats[k]!r})"


def test_load_stats_record_count_matches_version_manifest():
    """The {row_index: stat_id} dict size should match version.json's record_count."""
    v = game_data.get_version()
    expected = v["datasets"]["stats"]["record_count"]
    actual = len(game_data.load_stats())
    assert (
        actual == expected
    ), f"load_stats() returned {actual} entries; version.json says {expected}"


# ---------------------------------------------------------------------------
# load_metadata()
# ---------------------------------------------------------------------------


def test_load_metadata_for_each_dataset():
    """Every shipped dataset should have a readable metadata.json."""
    for dataset_dir in (
        game_data.MODS_DIR,
        game_data.PASSIVE_TREE_DIR,
        game_data.SUPPORT_GEMS_DIR,
        game_data.ASCENDANCIES_DIR,
        game_data.STATS_DIR,
    ):
        meta = game_data.load_metadata(dataset_dir)
        assert isinstance(meta, dict) and meta, f"load_metadata({dataset_dir}) returned no data"
        # Per-dataset metadata always names the dataset and the filename so
        # consumers can cross-reference back to data/game/.
        assert (
            "dataset" in meta or "filename" in meta
        ), f"{dataset_dir}/metadata.json missing both 'dataset' and 'filename' keys"


def test_load_metadata_returns_none_for_missing_dir():
    """load_metadata() on a folder without metadata.json returns None — not raises."""
    missing = game_data.GAME_DATA_DIR / "__definitely_not_a_real_dataset__"
    assert game_data.load_metadata(missing) is None


# ---------------------------------------------------------------------------
# describe()
# ---------------------------------------------------------------------------


def test_describe_returns_non_empty_string():
    out = game_data.describe()
    assert isinstance(out, str)
    assert out.strip(), "describe() returned only whitespace"


def test_describe_mentions_patch_version_from_manifest():
    """describe() output should at minimum contain the patch_version from version.json."""
    v = game_data.get_version()
    out = game_data.describe()
    assert (
        v["patch_version"] in out
    ), f"describe() output doesn't include patch_version {v['patch_version']!r}"
