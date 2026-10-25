"""
Tests for PoB import robustness (field feedback, 2026-06-11).

``import_pob`` was effectively unusable by an LLM agent: the only input was
an ~11K-char base64 string passed inline, and any corruption produced a raw
zlib error with no diagnosis. The importer now supports:

  - ``import_from_file`` — raw XML or share code in a local file (auto-detect)
  - ``import_xml_sync`` / ``import_xml`` — uncompressed XML directly
  - hardened ``import_build_sync`` — whitespace strip, URL-safe base64,
    missing padding, and actionable ValueError diagnostics on corruption
"""

from __future__ import annotations

import base64
import sys
import zlib
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.pob.importer import PoBImporter

SAMPLE_XML = """<PathOfBuilding version="2">
  <Build level="92" className="Witch" ascendClassName="Lich" name="DoT Test Build"/>
  <Skills>
    <SkillSet>
      <Skill label="Main" slot="Weapon 1" enabled="true">
        <Gem nameSpec="Essence Drain" level="20" quality="20" enabled="true"/>
        <Gem nameSpec="Swift Affliction" level="20" quality="0" enabled="true"/>
      </Skill>
    </SkillSet>
  </Skills>
  <Tree>
    <Spec nodes="1234,5678,9012"/>
  </Tree>
  <Items>
    <Item id="1" slot="Body Armour">Rarity: RARE
Test Robe
Item Level: 80
+100 to maximum Life</Item>
  </Items>
  <Notes>test notes</Notes>
</PathOfBuilding>"""


def _make_code(xml: str = SAMPLE_XML) -> str:
    return base64.b64encode(zlib.compress(xml.encode("utf-8"))).decode("ascii")


def _assert_build_ok(build: dict):
    assert build["name"] == "DoT Test Build"
    assert build["level"] == 92
    assert build["class"] == "Witch"
    assert build["ascendancy"] == "Lich"
    assert build["tree"]["allocated_nodes"] == [1234, 5678, 9012]
    gem_names = [g["name"] for s in build["skills"] for g in s["gems"]]
    assert "Essence Drain" in gem_names


# ---------------------------------------------------------------------------
# Share-code path
# ---------------------------------------------------------------------------


def test_clean_code_roundtrip():
    _assert_build_ok(PoBImporter().import_build_sync(_make_code()))


def test_code_with_whitespace_and_newlines():
    """Codes pasted from terminals/editors arrive line-wrapped."""
    code = _make_code()
    wrapped = "\n".join(code[i : i + 76] for i in range(0, len(code), 76))
    _assert_build_ok(PoBImporter().import_build_sync("  " + wrapped + "\n"))


def test_urlsafe_base64_variant():
    """PoB share codes use '-'/'_' in place of '+'/'/'."""
    code = _make_code().replace("+", "-").replace("/", "_")
    _assert_build_ok(PoBImporter().import_build_sync(code))


def test_code_missing_padding():
    code = _make_code().rstrip("=")
    _assert_build_ok(PoBImporter().import_build_sync(code))


def test_truncated_code_reports_truncation():
    """Mid-stream truncation must say so, not dump a raw zlib error."""
    code = _make_code()
    with pytest.raises(ValueError, match="truncated or corrupted"):
        PoBImporter().import_build_sync(code[: len(code) // 2])


def test_corrupt_character_reports_position():
    """A non-base64 char gets pinpointed by position."""
    code = _make_code()
    corrupted = code[:50] + "!" + code[51:]
    with pytest.raises(ValueError, match=r"position 50"):
        PoBImporter().import_build_sync(corrupted)


def test_empty_code_rejected():
    with pytest.raises(ValueError, match="empty"):
        PoBImporter().import_build_sync("   \n  ")


# ---------------------------------------------------------------------------
# Raw-XML path
# ---------------------------------------------------------------------------


def test_import_xml_sync():
    _assert_build_ok(PoBImporter().import_xml_sync(SAMPLE_XML))


def test_import_xml_with_bom():
    _assert_build_ok(PoBImporter().import_xml_sync("﻿" + SAMPLE_XML))


def test_import_xml_invalid():
    with pytest.raises(ValueError, match="Invalid PoB XML"):
        PoBImporter().import_xml_sync("<PathOfBuilding><unclosed>")


@pytest.mark.asyncio
async def test_import_xml_async_wrapper():
    _assert_build_ok(await PoBImporter().import_xml(SAMPLE_XML))


# ---------------------------------------------------------------------------
# File path (the agent-preferred route)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_from_file_xml(tmp_path):
    f = tmp_path / "build.xml"
    f.write_text(SAMPLE_XML, encoding="utf-8")
    _assert_build_ok(await PoBImporter().import_from_file(str(f)))


@pytest.mark.asyncio
async def test_import_from_file_xml_with_bom(tmp_path):
    """Notepad saves UTF-8 with a BOM; must not break detection or parse."""
    f = tmp_path / "build_bom.xml"
    f.write_bytes(b"\xef\xbb\xbf" + SAMPLE_XML.encode("utf-8"))
    _assert_build_ok(await PoBImporter().import_from_file(str(f)))


@pytest.mark.asyncio
async def test_import_from_file_share_code(tmp_path):
    """A .txt containing the share code is auto-detected as code, not XML."""
    f = tmp_path / "build_code.txt"
    f.write_text(_make_code() + "\n", encoding="utf-8")
    _assert_build_ok(await PoBImporter().import_from_file(str(f)))


@pytest.mark.asyncio
async def test_import_from_file_missing(tmp_path):
    with pytest.raises(ValueError, match="Cannot read"):
        await PoBImporter().import_from_file(str(tmp_path / "nope.xml"))


@pytest.mark.asyncio
async def test_import_from_file_corrupt_code_keeps_diagnostics(tmp_path):
    """File wrapper must preserve the inner truncation diagnosis."""
    code = _make_code()
    f = tmp_path / "truncated.txt"
    f.write_text(code[: len(code) // 2], encoding="utf-8")
    with pytest.raises(ValueError, match="truncated or corrupted"):
        await PoBImporter().import_from_file(str(f))
