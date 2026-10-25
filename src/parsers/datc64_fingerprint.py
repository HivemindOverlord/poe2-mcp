"""
.datc64 schema fingerprinting (campaign C3 — futureproofing mandate).

The 0.4→0.5 jump and the mid-0.5 hotfix both proved GGG adds tables,
adds rows, and can move columns between patches — silently, from the
consumer's perspective. This module makes that drift LOUD:

  - fingerprint_balance_dir(): one record per table — row_count,
    row_size (the schema-shape signal: a row_size change means columns
    were added/moved and every spec touching the table needs review),
    file size, and sha256.
  - diff_fingerprints(): classifies drift between two fingerprint sets
    into added / removed / layout_changed / rows_changed /
    content_changed — the gate the extraction pipeline runs after every
    re-extract.

The baseline ships as data/game/schema_fingerprints.json and is
regenerated alongside every extraction; the diff against the previous
baseline goes in the extraction report. The live-index-count check in
scripts/extract_balance_tables_v1.py (which caught the 1,017→1,019
hotfix) is the upstream half of this gate; this is the per-table half.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import struct
from pathlib import Path
from typing import Any, Dict

MAGIC = b"\xbb" * 8


def fingerprint_table(path: Path) -> Dict[str, Any]:
    """Fingerprint a single .datc64 table. Geometry failures are recorded
    rather than raised — a malformed table is itself drift worth seeing."""
    data = path.read_bytes()
    record: Dict[str, Any] = {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest()[:16],
    }
    try:
        row_count = struct.unpack_from("<I", data, 0)[0]
        magic_pos = data.find(MAGIC)
        if magic_pos < 4 or row_count == 0:
            record["geometry"] = "no-magic-or-empty"
            record["row_count"] = row_count
            return record
        row_size, rem = divmod(magic_pos - 4, row_count)
        record["row_count"] = row_count
        record["row_size"] = row_size
        if rem:
            record["geometry"] = f"irregular-remainder-{rem}"
    except struct.error:
        record["geometry"] = "unreadable-header"
    return record


def fingerprint_balance_dir(balance_dir: Path | str) -> Dict[str, Any]:
    """Fingerprint every .datc64 in a balance directory."""
    balance = Path(balance_dir)
    tables = {}
    for f in sorted(balance.glob("*.datc64")):
        tables[f.stem] = fingerprint_table(f)
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "table_count": len(tables),
        "tables": tables,
    }


def diff_fingerprints(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Classify drift between two fingerprint sets.

    Returns dict with:
      added            — tables present only in new (GGG added content)
      removed          — tables present only in old
      layout_changed   — row_size differs: COLUMNS MOVED/ADDED, every
                         spec reading the table needs review (loudest)
      rows_changed     — same layout, row_count differs (balance edits)
      content_changed  — same geometry, different hash (value edits)
      clean            — True iff nothing above fired
    """
    ot, nt = old.get("tables", {}), new.get("tables", {})
    added = sorted(set(nt) - set(ot))
    removed = sorted(set(ot) - set(nt))
    layout_changed, rows_changed, content_changed = [], [], []
    for name in sorted(set(ot) & set(nt)):
        o, n = ot[name], nt[name]
        if o.get("row_size") != n.get("row_size"):
            layout_changed.append(
                {
                    "table": name,
                    "row_size": [o.get("row_size"), n.get("row_size")],
                    "row_count": [o.get("row_count"), n.get("row_count")],
                }
            )
        elif o.get("row_count") != n.get("row_count"):
            rows_changed.append(
                {"table": name, "row_count": [o.get("row_count"), n.get("row_count")]}
            )
        elif o.get("sha256") != n.get("sha256"):
            content_changed.append(name)
    return {
        "added": added,
        "removed": removed,
        "layout_changed": layout_changed,
        "rows_changed": rows_changed,
        "content_changed": content_changed,
        "clean": not (added or removed or layout_changed or rows_changed or content_changed),
    }


def format_diff_report(diff: Dict[str, Any]) -> str:
    """Human-readable drift report for extraction logs / PR bodies."""
    if diff["clean"]:
        return "Schema fingerprints: CLEAN (no drift vs baseline)"
    lines = ["Schema fingerprint drift detected:"]
    if diff["layout_changed"]:
        lines.append("  !! LAYOUT CHANGED (specs need review):")
        for e in diff["layout_changed"]:
            lines.append(
                f"     {e['table']}: row_size {e['row_size'][0]} -> "
                f"{e['row_size'][1]} (rows {e['row_count'][0]} -> {e['row_count'][1]})"
            )
    if diff["added"]:
        lines.append(f"  + added tables ({len(diff['added'])}): " + ", ".join(diff["added"][:10]))
    if diff["removed"]:
        lines.append(
            f"  - removed tables ({len(diff['removed'])}): " + ", ".join(diff["removed"][:10])
        )
    if diff["rows_changed"]:
        lines.append(
            f"  ~ row-count changes ({len(diff['rows_changed'])}): "
            + ", ".join(e["table"] for e in diff["rows_changed"][:10])
        )
    if diff["content_changed"]:
        lines.append(f"  ~ content-only changes ({len(diff['content_changed'])})")
    return "\n".join(lines)
