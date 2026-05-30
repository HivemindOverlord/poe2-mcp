#!/usr/bin/env python3
"""
Publish a centralized PoE2 game-data bundle as a GitHub Release asset.

This is the operator side of the data distribution pipeline. Pairs with
src/data/data_distributor.py which is the user-side downloader.

Workflow
========
1. HivemindMinion runs the extraction pipeline against the patched local
   PoE2 install (scripts/extract_poe2_data.py + sub-extractors).
2. This script bundles the canonical extracted files into `poe2-data.zip`,
   writes `data/version.json` with metadata + SHA-256 of every file, and
   creates a GitHub Release tagged `data-v<patch>-<rev>` with the zip
   attached as an asset.
3. Users running the MCP get the bundle automatically via
   data_distributor.ensure_data_current() on next startup. Resolves #53.

Per the data policy in CLAUDE.md: the bundle published here MUST be
extracted exclusively from the maintainer's licensed PoE2 install via
the in-repo extraction scripts. NEVER bundle data sourced from third-party
wikis or APIs.

Requirements:
- `gh` CLI authenticated as HivemindMinion (already configured in repo)
- Extracted data already present in `data/` (the canonical JSON files)

Usage:
    python scripts/publish_data_release.py --patch 0.5.0 --revision 1
    python scripts/publish_data_release.py --patch 0.5.0 --revision 1 --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# Canonical files to include in the bundle. Add new ones here as the
# extraction pipeline grows. Keep this list TIGHT — only files the MCP
# actually consumes at runtime. Scratch / research / backup files stay out.
CANONICAL_FILES = [
    # Item modifiers
    "poe2_mods_extracted.json",
    # Support gems
    "poe2_support_gems_database.json",
    "complete_models/support_gems.json",
    # Passive tree
    "psg_passive_nodes.json",
    "complete_models/passive_tree_complete.json",
    "merged_passive_tree.json",
    # Ascendancy
    "complete_models/all_ascendancies.json",
    # PoB-sourced skill data
    "pob_active_skills.json",
    # Other extracted reference data
    "abyss_spawn_weights.json",
    "extracted_mod_stats.json",
    "extracted_passive_stats.json",
]


def sha256_of(path: Path) -> str:
    """Return hex SHA-256 of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def gather_files() -> Dict[str, Path]:
    """Return {bundle_relative_path: absolute_path} for files that exist."""
    found = {}
    missing = []
    for rel in CANONICAL_FILES:
        abs_path = DATA_DIR / rel
        if abs_path.exists():
            found[rel] = abs_path
        else:
            missing.append(rel)
    if missing:
        print(f"WARNING: {len(missing)} canonical file(s) missing from data/:")
        for m in missing:
            print(f"  - {m}")
    return found


def build_version_json(found: Dict[str, Path], release_tag: str, patch: str) -> Dict:
    """Construct the version.json metadata payload."""
    files_meta = {}
    total_bytes = 0
    for rel, abs_path in found.items():
        size = abs_path.stat().st_size
        total_bytes += size
        files_meta[rel] = {
            "sha256": sha256_of(abs_path),
            "bytes": size,
        }
    return {
        "release_tag": release_tag,
        "patch_version": patch,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "extracted_by": "HivemindMinion (Claude Code) from HivemindOverlord's licensed PoE2 install",
        "extractor_chain": [
            "scripts/extract_poe2_data.py  (LibBundle3 + pythonnet/CoreCLR)",
            "scripts/extract_mods_datc64.py",
            "scripts/extract_complete_passive_tree.py",
            "scripts/extract_ascendancy_passives.py",
            "scripts/extract_support_gem_effects.py",
            "scripts/extract_all_passive_stats.py",
        ],
        "data_policy": (
            "Per CLAUDE.md: extracted exclusively from the maintainer's licensed "
            "PoE2 install. No third-party wiki / scraped data is bundled."
        ),
        "total_bytes": total_bytes,
        "file_count": len(files_meta),
        "files": files_meta,
    }


def build_bundle(found: Dict[str, Path], out_zip: Path, version_payload: Dict) -> None:
    """Write the data bundle zip, embedding version.json inside it as well."""
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # version.json at bundle root so it's the first thing extracted
        zf.writestr("version.json", json.dumps(version_payload, indent=2))
        # canonical files preserve their data/ subpath
        for rel, abs_path in found.items():
            zf.write(abs_path, arcname=rel)


def create_release(tag: str, title: str, notes: str, asset: Path, dry_run: bool) -> bool:
    """Create the release + upload the asset via gh CLI. Returns True on success."""
    if dry_run:
        print(f"\n[DRY RUN] Would run:")
        print(f"  gh release create {tag} --title {title!r} --notes-file <notes>")
        print(f"  gh release upload {tag} {asset}")
        return True
    notes_file = Path(tempfile.mkstemp(suffix=".md")[1])
    try:
        notes_file.write_text(notes, encoding="utf-8")
        subprocess.run(
            ["gh", "release", "create", tag, "--title", title, "--notes-file", str(notes_file), str(asset)],
            check=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: gh release create failed: {e}")
        return False
    finally:
        notes_file.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Publish PoE2 game-data bundle to GitHub Releases")
    ap.add_argument("--patch", required=True, help='Patch version (e.g. "0.5.0")')
    ap.add_argument("--revision", type=int, default=1, help="Bundle revision within this patch (default 1)")
    ap.add_argument("--patch-name", default="", help='Optional patch name (e.g. "Return of the Ancients")')
    ap.add_argument("--dry-run", action="store_true", help="Build the bundle but don't create a GitHub Release")
    ap.add_argument("--keep-bundle", action="store_true", help="Don't delete the local bundle zip after upload")
    args = ap.parse_args()

    release_tag = f"data-v{args.patch}-{args.revision}"
    title = f"Game data bundle {release_tag}"
    if args.patch_name:
        title += f' ({args.patch_name})'

    print(f"=== Building data bundle for {release_tag} ===")
    found = gather_files()
    if not found:
        print("ERROR: no canonical files found; run the extraction pipeline first")
        return 1
    print(f"Including {len(found)} files")

    version_payload = build_version_json(found, release_tag, args.patch)
    # Write version.json to data/ as well, so a fresh checkout knows what it has
    (DATA_DIR / "version.json").write_text(json.dumps(version_payload, indent=2))
    print(f"Wrote data/version.json")

    bundle_path = BASE_DIR / f"poe2-data.zip"
    build_bundle(found, bundle_path, version_payload)
    size_mb = bundle_path.stat().st_size / (1024 * 1024)
    print(f"Built bundle: {bundle_path} ({size_mb:.1f} MB)")

    notes = (
        f"# {title}\n\n"
        f"PoE2 game-data bundle for Patch {args.patch}"
        f"{' ' + args.patch_name if args.patch_name else ''}.\n\n"
        f"**File count:** {len(found)}\n"
        f"**Bundle size:** {size_mb:.1f} MB\n"
        f"**Extracted at:** {version_payload['extracted_at']}\n\n"
        f"## Install\n\n"
        f"Users running `poe2-mcp` get this bundle automatically via "
        f"`src/data/data_distributor.py` on next startup. To force a check:\n"
        f"```bash\npython -m src.data.data_distributor\n```\n\n"
        f"## Data policy\n\n"
        f"{version_payload['data_policy']}\n\n"
        f"## Files included\n\n"
        + "\n".join(f"- `{rel}`" for rel in sorted(found.keys()))
    )

    ok = create_release(release_tag, title, notes, bundle_path, args.dry_run)
    if not args.keep_bundle and bundle_path.exists() and not args.dry_run:
        bundle_path.unlink()
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
