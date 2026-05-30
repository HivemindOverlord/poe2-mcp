"""
Centralized game-data distributor.

Pulls authoritative `.datc64`-extracted game data from this repo's GitHub
Releases assets, replacing the user-extracts-from-Steam workflow. Resolves #53.

Data lifecycle
==============
1. HivemindMinion runs scripts/extract_poe2_data.py + sub-extractors after each
   patch on the maintainer's licensed PoE2 install.
2. `scripts/publish_data_release.py` bundles the canonical files into
   `poe2-data.zip` and attaches it to a GitHub Release tag like
   `data-v0.5.0-1` (patch.minor + bundle revision).
3. This module checks the local `data/version.json` against the latest release
   on startup / on demand, and downloads the bundle if newer.
4. Users may override with their own freshly-extracted data by setting
   `POE2_MCP_NO_DATA_FETCH=1` and dropping files into `data/` themselves.

Per the data policy in CLAUDE.md, this is the ONLY allowed external source
for PoE2 game-mechanics data. NEVER pull game data from third-party wikis
or APIs. The data published here is extracted exclusively from the
maintainer's licensed PoE2 install via the in-repo extraction scripts.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

GITHUB_REPO = "HivemindOverlord/poe2-mcp"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
LATEST_RELEASE_API = f"{RELEASES_API}/latest"
BUNDLE_ASSET_NAME = "poe2-data.zip"

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_DATA_DIR = _BASE_DIR / "data"
_VERSION_FILE = _DATA_DIR / "version.json"


def get_local_data_version() -> Optional[Dict[str, Any]]:
    """Read data/version.json describing the locally-installed data bundle.

    Returns None if no version file exists (fresh install) or it's unreadable.
    """
    if not _VERSION_FILE.exists():
        return None
    try:
        return json.loads(_VERSION_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Failed to read local data version: %s", e)
        return None


def get_latest_release_info() -> Optional[Dict[str, Any]]:
    """Query the GitHub Releases API for the latest data-bundle release.

    Filters for releases tagged `data-*` so non-data releases (eg. code-only
    `v1.0.1`) aren't mistaken for data bundles.
    """
    try:
        req = urllib.request.Request(
            RELEASES_API,
            headers={
                "User-Agent": "poe2-mcp-data-distributor",
                "Accept": "application/vnd.github+json",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            releases = json.loads(r.read())
    except Exception as e:
        logger.warning("Failed to query GitHub Releases: %s", e)
        return None

    for rel in releases:
        if rel.get("draft") or rel.get("prerelease"):
            continue
        tag = rel.get("tag_name", "")
        if tag.startswith("data-"):
            return rel
    logger.info("No `data-*` releases found yet on %s", GITHUB_REPO)
    return None


def find_bundle_asset(release: Dict[str, Any]) -> Optional[str]:
    """Return the download URL for the data bundle asset in a release."""
    for asset in release.get("assets", []):
        if asset.get("name") == BUNDLE_ASSET_NAME:
            return asset.get("browser_download_url")
    return None


def needs_update() -> Tuple[bool, str]:
    """Check whether local data is older than the latest release.

    Returns (needs_update: bool, reason: str). The reason is suitable for
    logging or for inclusion in a `health_check` MCP tool response.
    """
    local = get_local_data_version()
    remote = get_latest_release_info()

    if not local and remote:
        return True, f"no local data/version.json (fresh install) — latest is {remote.get('tag_name')}"
    if not local and not remote:
        # Project hasn't published any data-* releases yet; nothing to do
        return False, "no local data/version.json and no data-* releases published yet — using whatever is in data/"
    if local and not remote:
        return False, f"keeping local data {local.get('release_tag', '?')!r} (no newer data-* release found upstream)"

    local_tag = local.get("release_tag")
    remote_tag = remote.get("tag_name")
    if not local_tag or not remote_tag:
        return False, "incomplete version info; keeping local data"

    if local_tag != remote_tag:
        return (
            True,
            f"local data {local_tag!r} != latest released {remote_tag!r}",
        )
    return False, f"data {local_tag!r} is current"


def download_and_install(release: Dict[str, Any]) -> bool:
    """Download the bundle asset for `release` and unzip it into data/.

    Returns True on success, False if the bundle asset is missing or the
    download/unzip failed.
    """
    url = find_bundle_asset(release)
    tag = release.get("tag_name", "unknown")
    if not url:
        logger.error("Release %s has no %s asset", tag, BUNDLE_ASSET_NAME)
        return False

    tmp_path = Path(tempfile.mkstemp(suffix=".zip")[1])
    try:
        logger.info("Downloading data bundle %s from %s", tag, url)
        urllib.request.urlretrieve(url, tmp_path)
        size_mb = tmp_path.stat().st_size / (1024 * 1024)
        logger.info("Downloaded %.1f MB; extracting to %s", size_mb, _DATA_DIR)
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(tmp_path) as zf:
            zf.extractall(_DATA_DIR)
        logger.info("Data bundle %s installed successfully", tag)
        return True
    except Exception as e:
        logger.error("Failed to install bundle %s: %s", tag, e)
        return False
    finally:
        tmp_path.unlink(missing_ok=True)


def ensure_data_current(allow_network: bool = True) -> Tuple[bool, str]:
    """Top-level entry: check freshness, download if needed.

    Returns (success: bool, status_msg: str). `success=True` means data is
    current (either was already, or was successfully updated). `success=False`
    means an update was needed but failed (offline, no bundle, etc.) — the
    MCP should continue with stale data and surface the status_msg to the user.

    Honors `POE2_MCP_NO_DATA_FETCH=1` to skip the check entirely (for users
    running their own local extraction).
    """
    if os.environ.get("POE2_MCP_NO_DATA_FETCH"):
        return True, "POE2_MCP_NO_DATA_FETCH set; using local data without freshness check"
    if not allow_network:
        return True, "network disabled; using local data without freshness check"

    update, reason = needs_update()
    if not update:
        return True, reason

    release = get_latest_release_info()
    if not release:
        return False, f"update needed ({reason}) but releases API unreachable"

    ok = download_and_install(release)
    if ok:
        return True, f"updated to {release.get('tag_name')}"
    return False, f"update needed ({reason}) but download/install failed"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    ok, msg = ensure_data_current()
    print(f"[{'OK' if ok else 'FAIL'}] {msg}")
