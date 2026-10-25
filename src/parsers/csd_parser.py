"""
Parser for PoE2 Compiled Stat Description (.csd) files.

The .csd files at data/extracted/Data/statdescriptions/ are UTF-16-LE
text files that follow a small declarative grammar (described in PoB's
Modules/StatDescriber.lua). This module is the structural parser:
walks the lines, recognizes `description` / `no_description` / `lang`
constructs, and emits structured Python dicts.

Lives in its own light module (no SQLAlchemy / no mcp_server imports)
so both the gitignored extractor at scripts/extract_stat_descriptions.py
AND the per-skill extractor (PR #129) can reuse the same parse contract,
and so unit tests don't pay any heavy import cost.

Grammar (single root-level .csd file):

    description
    \\t<stat_count> <stat_id_1> [<stat_id_2> ...]
    \\t<variant_count>
    \\t\\t<range> "<template>" [handler1 handler2 ...]
    \\t...                              # <variant_count> lines total
    \\tlang "LanguageName"
    \\t<variant_count>
    \\t\\t<range> "<template>" [handlers]
    \\t...

Where:
  - <range> = `#` (default), `1`, `10`, `1|#` (>=1), `#|0` (<=0), `1|99` (1..99)
  - <template> uses `{0}`, `{1}` placeholders, `\\n` for newlines,
    `[InternalName|DisplayText]` for hyperlinks
  - <handler> is a value transform (divide_by_ten_1dp_if_required,
    negate, 60%_of_value, etc.) - preserved verbatim

Other top-level constructs:
  - `include "..."`           - pulls in another file's descriptions
  - `no_description <stat_id>` - stat exists with no display text
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

VARIANT_LINE_RE = re.compile(
    r"^\s*"
    r"(?P<range>\S+)"  # range token
    r"\s+"
    r'"(?P<template>(?:[^"\\]|\\.)*)"'  # quoted template
    r"(?:\s+(?P<handlers>.+))?"  # optional handler list
    r"\s*$"
)


def parse_csd(text: str, source_relpath: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Parse one .csd file's text content.

    Args:
        text: UTF-16-decoded contents of the .csd file.
        source_relpath: Path string used in error messages / not returned in the
            output — caller writes it to metadata if needed.

    Returns:
        Tuple (descriptions, no_descriptions):
          descriptions    = [{stat_ids, primary_stat_id, variants,
                              primary_template, languages_available,
                              source_line}, ...]
          no_descriptions = [{stat_id, source_line}, ...]
        Both lists in source order.
    """
    lines = text.splitlines()
    n = len(lines)
    i = 0
    descriptions: List[Dict[str, Any]] = []
    no_descriptions: List[Dict[str, Any]] = []

    while i < n:
        raw = lines[i]
        stripped = raw.strip()

        # Skip blank lines + include directives.
        if not stripped or stripped.startswith("include "):
            i += 1
            continue

        # no_description one-liner.
        if stripped.startswith("no_description "):
            no_descriptions.append(
                {
                    "stat_id": stripped[len("no_description ") :].strip(),
                    "source_line": i + 1,
                }
            )
            i += 1
            continue

        # description block.
        if stripped == "description":
            block_start_line = i + 1
            i += 1
            if i >= n:
                break

            # Header: <stat_count> <stat_id_1> [<stat_id_2> ...]
            header = lines[i].strip().split()
            try:
                stat_count = int(header[0])
            except (ValueError, IndexError):
                i += 1
                continue
            stat_ids = header[1 : 1 + stat_count]
            i += 1

            english_variants: List[Dict[str, Any]] = []
            other_languages: List[str] = []
            current_lang = "English"  # implicit default before any `lang` line

            while i < n:
                vline = lines[i]
                vstrip = vline.strip()

                # Block-end conditions.
                if vstrip == "description" or vstrip.startswith("no_description "):
                    break
                if not vstrip:
                    # Single blank within a block is tolerated; double or
                    # next-is-top-level ends the block.
                    j = i + 1
                    while j < n and not lines[j].strip():
                        j += 1
                    if j >= n:
                        i = j
                        break
                    next_nonblank = lines[j].strip()
                    if next_nonblank == "description" or next_nonblank.startswith(
                        "no_description "
                    ):
                        i = j
                        break
                    i = j
                    continue

                # lang "Foo" - language switch; we collect English variants
                # only but track which other languages are declared.
                if vstrip.startswith("lang "):
                    m = re.match(r'lang\s+"([^"]*)"', vstrip)
                    if m:
                        current_lang = m.group(1)
                        if (
                            current_lang
                            and current_lang not in other_languages
                            and current_lang != "English"
                        ):
                            other_languages.append(current_lang)
                    i += 1
                    continue

                # Variant line.
                vmatch = VARIANT_LINE_RE.match(vline)
                if vmatch and current_lang == "English":
                    english_variants.append(
                        {
                            "range": vmatch.group("range"),
                            "template": vmatch.group("template"),
                            "handlers": (vmatch.group("handlers") or "").split(),
                        }
                    )
                    i += 1
                    continue
                elif vmatch:
                    # Non-English variant - skip silently.
                    i += 1
                    continue

                # Not a variant line - likely a variant_count line.
                # We already collect variants by walking until block end;
                # the count is informational.
                i += 1

            if stat_ids:
                descriptions.append(
                    {
                        "stat_ids": stat_ids,
                        "primary_stat_id": stat_ids[0],
                        "variants": english_variants,
                        "primary_template": (
                            english_variants[0]["template"] if english_variants else None
                        ),
                        "languages_available": ["English"] + other_languages,
                        "source_line": block_start_line,
                    }
                )
            continue

        # Unrecognized top-level line - skip.
        i += 1

    return descriptions, no_descriptions
