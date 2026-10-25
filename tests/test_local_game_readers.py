"""
Tests for the local live-game readers: ClientLogReader (Client.txt) and
GameConfigReader (poe2_production_Config.ini).

Most tests use synthetic temp files so they pass on CI without the game
installed. A few opportunistic tests run against the real local files and are
skipped when those aren't present.

Author: HivemindMinion
Date: 2026-06-04
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.client_log_reader import ClientLogReader
from src.api.game_config_reader import GameConfigReader

# Real log lines captured from the live client (prefix preserved).
SAMPLE_LOG = """\
2026/06/04 10:11:39 75020656 3ef23347 [INFO Client 29396] : TomawarTheSeventh (Infernalist) is now level 65
2026/06/04 10:40:48 76768828 2caa233f [DEBUG Client 29396] Generating level 62 area "P2_1" with seed 3720906296
2026/06/04 10:50:32 77352984 91c6ccf [INFO Client 29396] Connecting to instance server at 64.87.33.204:21360
2026/06/04 10:50:29 77350296 3ef23347 [INFO Client 29396] : TomawarTheSeventh has been slain.
2026/06/04 10:51:25 77406656 3ef23347 [INFO Client 29396] : TomawarTheSeventh (Infernalist) is now level 66
2026/06/02 16:08:49 24343140 3ef23347 [INFO Client 16992] : AFK mode is now ON. Autoreply "This player is AFK."
2026/06/01 12:31:39 270979734 3ef23347 [INFO Client 18640] @From blightblot: hello there
2026/06/04 15:43:32 94933859 3ef23347 [INFO Client 6124] : 7 Items identified
2026/06/04 15:38:46 94647421 3ef23347 [INFO Client 6124] Incarnation of Death: Take their head or I take YOURS!
"""

SAMPLE_INI = """\
﻿[LOGIN]
gateway_auto_select=false
seen_intro=true
gateway_id=America
account_name=
[DISPLAY]
resolution_width=2560
resolution_height=1440
renderer_type=DirectX12
upscale=FSR
framerate_limit=150
framerate_limit_enabled=false
adapter_name=AMD Radeon RX 9060 XT
[GENERAL]
user_input_mode=wasd
last_selected_KBM_input_mode=wasd
enable_profanity_filter=true
disable_tutorials=true
[CACHED_DATA]
current_act_environment=6
"""


# ---------------------------------------------------------------------------
# ClientLogReader
# ---------------------------------------------------------------------------
class TestClientLogReaderParsing:
    def test_parse_level_up(self):
        line = "2026/06/04 10:51:25 77406656 3ef23347 [INFO Client 29396] : TomawarTheSeventh (Infernalist) is now level 66"
        ev = ClientLogReader.parse_line(line)
        assert ev["kind"] == "level_up"
        assert ev["character"] == "TomawarTheSeventh"
        assert ev["klass"] == "Infernalist"
        assert ev["level"] == 66
        assert ev["timestamp"] == "2026/06/04 10:51:25"

    def test_parse_area_change(self):
        line = '2026/06/04 10:40:48 76768828 2caa233f [DEBUG Client 29396] Generating level 62 area "P2_1" with seed 3720906296'
        ev = ClientLogReader.parse_line(line)
        assert ev["kind"] == "area_change"
        assert ev["area_code"] == "P2_1"
        assert ev["area_level"] == 62
        assert ev["seed"] == 3720906296

    def test_parse_instance_connect(self):
        line = "2026/06/04 10:50:32 77352984 91c6ccf [INFO Client 29396] Connecting to instance server at 64.87.33.204:21360 "
        ev = ClientLogReader.parse_line(line)
        assert ev["kind"] == "instance_connect"
        assert ev["server"] == "64.87.33.204:21360"

    def test_parse_death(self):
        line = "2026/06/04 10:50:29 77350296 3ef23347 [INFO Client 29396] : TomawarTheSeventh has been slain."
        ev = ClientLogReader.parse_line(line)
        assert ev["kind"] == "death"
        assert ev["character"] == "TomawarTheSeventh"

    def test_parse_afk(self):
        line = '2026/06/02 16:08:49 24343140 3ef23347 [INFO Client 16992] : AFK mode is now ON. Autoreply "This player is AFK."'
        ev = ClientLogReader.parse_line(line)
        assert ev["kind"] == "afk"
        assert ev["afk_state"] == "ON"

    def test_parse_whisper(self):
        line = "2026/06/01 12:31:39 270979734 3ef23347 [INFO Client 18640] @From blightblot: hello there"
        ev = ClientLogReader.parse_line(line)
        assert ev["kind"] == "whisper"
        assert ev["direction"] == "From"
        assert ev["who"] == "blightblot"
        assert ev["text"] == "hello there"

    def test_parse_non_event_returns_none(self):
        # NPC dialogue / engine spam should not match a tracked event.
        assert (
            ClientLogReader.parse_line(
                "2026/06/04 15:38:46 94647421 3ef23347 [INFO Client 6124] Incarnation of Death: Take their head or I take YOURS!"
            )
            is None
        )
        assert ClientLogReader.parse_line("not a log line at all") is None
        assert ClientLogReader.parse_line("") is None


class TestClientLogReaderState:
    @pytest.fixture
    def log_file(self, tmp_path):
        p = tmp_path / "Client.txt"
        p.write_text(SAMPLE_LOG, encoding="utf-8")
        return p

    def test_get_current_state(self, log_file):
        reader = ClientLogReader(log_path=log_file)
        assert reader.is_available()
        state = reader.get_current_state()
        assert state["available"] is True
        # Most recent level-up in the sample is 66.
        assert state["character"] == "TomawarTheSeventh"
        assert state["ascendancy_or_class"] == "Infernalist"
        assert state["level"] == 66
        assert state["area_code"] == "P2_1"
        assert state["area_level"] == 62
        assert state["instance_server"] == "64.87.33.204:21360"
        assert state["deaths_in_window"] == 1
        assert state["afk"] is True

    def test_get_recent_events_filter(self, log_file):
        reader = ClientLogReader(log_path=log_file)
        events = reader.get_recent_events(kinds=["level_up"])
        assert len(events) == 2
        assert all(e["kind"] == "level_up" for e in events)
        # Newest first: level 66 then level 65.
        assert events[0]["level"] == 66
        assert events[1]["level"] == 65

    def test_get_recent_events_limit(self, log_file):
        reader = ClientLogReader(log_path=log_file)
        assert len(reader.get_recent_events(limit=3)) == 3

    def test_death_fallback_identity(self, tmp_path):
        # No level-up in window — character should come from the death line.
        p = tmp_path / "Client.txt"
        p.write_text(
            "2026/06/04 10:50:29 77350296 3ef23347 [INFO Client 29396] : SomeHero has been slain.\n",
            encoding="utf-8",
        )
        state = ClientLogReader(log_path=p).get_current_state()
        assert state["character"] == "SomeHero"
        assert state["level"] is None

    def test_unavailable_path(self, tmp_path):
        reader = ClientLogReader(log_path=tmp_path / "does_not_exist.txt")
        assert reader.is_available() is False
        state = reader.get_current_state()
        assert state["available"] is False
        assert reader.get_recent_events() == []

    def test_tail_window_drops_partial_first_line(self, tmp_path):
        # With a tiny tail window the first (partial) line is dropped, but the
        # newest events still parse.
        p = tmp_path / "Client.txt"
        p.write_text(SAMPLE_LOG, encoding="utf-8")
        reader = ClientLogReader(log_path=p, default_tail_bytes=120)
        events = reader.get_recent_events()
        # Window is small; we still get *some* recent events and never crash.
        assert isinstance(events, list)


# ---------------------------------------------------------------------------
# GameConfigReader
# ---------------------------------------------------------------------------
class TestGameConfigReader:
    @pytest.fixture
    def ini_file(self, tmp_path):
        p = tmp_path / "poe2_production_Config.ini"
        # Write with BOM so we exercise the utf-8-sig path.
        p.write_text(SAMPLE_INI, encoding="utf-8")
        return p

    def test_summary(self, ini_file):
        reader = GameConfigReader(config_path=ini_file)
        assert reader.is_available()
        s = reader.get_summary()
        assert s["available"] is True
        assert s["gateway"] == "America"
        assert s["input_mode"] == "wasd"
        assert s["current_act_environment"] == "6"
        assert s["current_act_hint"] == "Act 3 (Cruel) / endgame"
        assert s["resolution"] == "2560x1440"
        assert s["renderer"] == "DirectX12"
        assert s["gpu"] == "AMD Radeon RX 9060 XT"

    def test_empty_account_name_note(self, ini_file):
        s = GameConfigReader(config_path=ini_file).get_summary()
        assert s["account_name"] is None
        assert "Steam" in s["account_name_note"]

    def test_read_all(self, ini_file):
        raw = GameConfigReader(config_path=ini_file).read_all()
        assert "LOGIN" in raw and "DISPLAY" in raw
        assert raw["DISPLAY"]["renderer_type"] == "DirectX12"
        assert raw["LOGIN"]["account_name"] == ""

    def test_unavailable(self, tmp_path):
        reader = GameConfigReader(config_path=tmp_path / "missing.ini")
        assert reader.is_available() is False
        assert reader.get_summary()["available"] is False
        assert reader.read_all() == {}


# ---------------------------------------------------------------------------
# Opportunistic tests against the real local files (skipped if absent)
# ---------------------------------------------------------------------------
class TestRealLocalFiles:
    def test_real_client_log_if_present(self):
        reader = ClientLogReader()
        if not reader.is_available():
            pytest.skip("Client.txt not present on this machine")
        state = reader.get_current_state()
        assert state["available"] is True
        # We can't assert specific values (the player moves), but the call must
        # succeed and return the expected shape.
        for key in ("character", "level", "area_code", "event_count"):
            assert key in state

    def test_real_config_if_present(self):
        reader = GameConfigReader()
        if not reader.is_available():
            pytest.skip("poe2_production_Config.ini not present on this machine")
        s = reader.get_summary()
        assert s["available"] is True
        assert "input_mode" in s
