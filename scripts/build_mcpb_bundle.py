#!/usr/bin/env python3
"""Assemble mcpb_bundle/server/ from repo sources + canonical data, then pack the .mcpb.

Why this exists
===============
mcpb_bundle/server/ is gitignored — it is a *generated* staging tree, not a
source of truth. Historically it was assembled by hand and drifted from the
repo (the committed bundle shipped a stale launch.py missing the #157 MCP-stdout
and repo-anchor fixes, plus a 1.3 GB data/ dir full of dev-machine scratch: raw
.datc64 tables, a 442 MB datc64 DB mirror, fresh_*/backup JSON). This script
rebuilds the bundle deterministically so CI can produce a correct .mcpb on every
merge (issue #185 follow-up).

What ships in the bundle
========================
ONLY runtime-needed files:
  - the MCP source tree (src/), launcher, config, requirements
  - the curated canonical game-data set — the SAME list publish_data_release.py
    distributes as poe2-data.zip ("only files the MCP actually consumes")
  - every git-tracked file under data/ (data/game/, complete_models/, etc.)

Deliberately EXCLUDED: raw extracted/ .datc64, *.db (poe2_optimizer.db is created
at runtime on first launch; poe2_datc64.db is a non-canonical search_items
optimization that degrades gracefully when absent), fresh_*/backup/scratch JSON,
__pycache__. A supported install obtains game data via data_distributor, so the
bundle mirrors that canonical set rather than the maintainer's full data/ dir.

Data flow
=========
  src/ + launch.py + config.yaml + requirements.txt + .env.example
    + (git-tracked data/**) + (CANONICAL_FILES from data/) + version.json
  -> mcpb_bundle/server/  ->  pack_mcpb.pack()  ->  <name>-<version>.mcpb

Usage
=====
  python scripts/build_mcpb_bundle.py            # assemble + pack
  python scripts/build_mcpb_bundle.py --no-pack  # assemble only
  python scripts/build_mcpb_bundle.py --out x.mcpb
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Reuse the single canonical-file list so the bundle and the data release can
# never disagree about what the runtime consumes.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.pack_mcpb import pack  # noqa: E402
from scripts.publish_data_release import CANONICAL_FILES  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
DATA_DIR = REPO_ROOT / "data"
BUNDLE_DIR = REPO_ROOT / "mcpb_bundle"
SERVER_DIR = BUNDLE_DIR / "server"

# Top-level files copied verbatim from repo root into server/.
ROOT_FILES = ["launch.py", "config.yaml", "requirements.txt", ".env.example"]

# Ignored when copying the source tree — never belong in a shipped bundle.
SRC_IGNORE = shutil.ignore_patterns(
    "__pycache__", "*.pyc", "*.pyo", ".pytest_cache", "*.log", ".DS_Store"
)


def _git_tracked_data_files() -> list[str]:
    """Return data/-relative paths of every git-tracked file under data/."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "data/"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    rels = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("data/"):
            rels.append(line[len("data/") :])
    return rels


def _copy_data_file(rel: str, copied: set[str]) -> bool:
    """Copy data/<rel> into server/data/<rel>. Returns True if copied."""
    if rel in copied:
        return False
    src = DATA_DIR / rel
    if not src.is_file():
        return False
    dst = SERVER_DIR / "data" / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    copied.add(rel)
    return True


def assemble() -> None:
    """Rebuild mcpb_bundle/server/ from scratch."""
    # Clean slate so removed source files don't linger in the bundle.
    if SERVER_DIR.exists():
        shutil.rmtree(SERVER_DIR)
    SERVER_DIR.mkdir(parents=True)

    # 1. Source tree
    shutil.copytree(SRC_DIR, SERVER_DIR / "src", ignore=SRC_IGNORE)

    # 2. Launcher + config (root copies carry the current #157 fixes)
    for name in ROOT_FILES:
        src = REPO_ROOT / name
        if src.exists():
            shutil.copy2(src, SERVER_DIR / name)
        else:
            print(f"  warn: root file missing, skipped: {name}", file=sys.stderr)

    # 2b. Live PoB bridge addon — ship the Lua addon + install scripts so the
    # MCP can deploy it (src/pob/installer.py locates pob_addon/src/Addons here).
    # Skip the pre-built .zip artifacts; the addon source is what we install from.
    pob_addon_src = REPO_ROOT / "pob_addon"
    if pob_addon_src.is_dir():
        shutil.copytree(
            pob_addon_src,
            SERVER_DIR / "pob_addon",
            ignore=shutil.ignore_patterns("*.zip", "__pycache__", "*.pyc"),
        )
    else:
        print("  warn: pob_addon/ missing, live PoB bridge addon not bundled", file=sys.stderr)

    # 3. Runtime data: git-tracked data/** UNION the canonical generated set.
    copied: set[str] = set()
    tracked = _git_tracked_data_files()
    for rel in tracked:
        _copy_data_file(rel, copied)

    missing_canonical = []
    for rel in CANONICAL_FILES:
        if not _copy_data_file(rel, copied):
            # Already copied (tracked) is fine; truly absent is a problem.
            if not (SERVER_DIR / "data" / rel).exists():
                missing_canonical.append(rel)

    # version.json (written by data_distributor / publish_data_release)
    _copy_data_file("version.json", copied)

    if missing_canonical:
        print(
            "  WARNING: canonical runtime files absent from data/ "
            "(run data sync / extract first):",
            file=sys.stderr,
        )
        for m in missing_canonical:
            print(f"    - {m}", file=sys.stderr)

    n_files = sum(1 for _ in SERVER_DIR.rglob("*") if _.is_file())
    total = sum(p.stat().st_size for p in SERVER_DIR.rglob("*") if p.is_file())
    print(f"Assembled server/ : {n_files} files, {total/1e6:.1f} MB " f"({len(copied)} data files)")


def assemble_returns_missing() -> list[str]:
    """Run assemble() and return the list of absent canonical files."""
    # assemble() prints its own warnings; re-derive the missing set here so
    # callers (CI guard) can act on it without parsing stdout.
    assemble()
    missing = []
    for rel in CANONICAL_FILES:
        if not (SERVER_DIR / "data" / rel).exists():
            missing.append(rel)
    return missing


def main() -> None:
    ap = argparse.ArgumentParser(description="Assemble + pack the .mcpb bundle")
    ap.add_argument("--no-pack", action="store_true", help="assemble only, skip packing")
    ap.add_argument("--out", type=Path, default=None, help="output .mcpb path")
    ap.add_argument(
        "--require-canonical",
        action="store_true",
        help="exit non-zero if any canonical runtime file is missing "
        "(CI guard: never publish a data-less bundle)",
    )
    args = ap.parse_args()

    missing = assemble_returns_missing()
    if args.require_canonical and missing:
        print(
            f"ERROR: {len(missing)} canonical file(s) missing — refusing to "
            f"build a degraded bundle. Publish/download poe2-data.zip first.",
            file=sys.stderr,
        )
        sys.exit(2)

    if args.no_pack:
        return

    import json

    manifest = json.loads((BUNDLE_DIR / "manifest.json").read_text(encoding="utf-8"))
    out = args.out or REPO_ROOT / f"{manifest['name']}-{manifest['version']}.mcpb"
    pack(out)


if __name__ == "__main__":
    main()
