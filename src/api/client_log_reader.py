"""
Live PoE2 game-state reader — tails the client log (Client.txt).

The PoE2 client appends a structured, timestamped event stream to
`logs/Client.txt` while the game runs (verified via ProcMon: ~450 WriteFile
ops per session). This is a LOCAL data source — no API, no network — and the
only way to know the player's *current* character / zone without poe.ninja
(which is broken for patch 0.5 per CLAUDE.md CRITICAL #4).

Data flow:
    Client.txt (118MB+, append-only)
        -> _read_tail()        # seek to EOF, read last N bytes only (never the whole file)
        -> parse_line()        # regex each line into a typed event dict
        -> get_recent_events() # newest-first list of parsed events
        -> get_current_state() # collapse events into {character, level, area, ...}

Line format (after the timestamp/uptime/hash/level prefix):
    2026/06/04 10:51:25 77406656 3ef23347 [INFO Client 29396] : Name (Class) is now level 66
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Candidate install locations. Steam is the common case on this machine; the
# standalone client and a couple of alternate Steam library roots are included
# so the reader works on other users' boxes without configuration.
_DEFAULT_LOG_CANDIDATES = [
    r"C:\Program Files (x86)\Steam\steamapps\common\Path of Exile 2\logs\Client.txt",
    r"C:\Program Files\Steam\steamapps\common\Path of Exile 2\logs\Client.txt",
    r"C:\Program Files (x86)\Grinding Gear Games\Path of Exile 2\logs\Client.txt",
    r"C:\Program Files\Grinding Gear Games\Path of Exile 2\logs\Client.txt",
    r"D:\SteamLibrary\steamapps\common\Path of Exile 2\logs\Client.txt",
    r"E:\SteamLibrary\steamapps\common\Path of Exile 2\logs\Client.txt",
]

# The shared line prefix: date, uptime-ms counter, hex hash, [LEVEL Client PID].
# We capture the timestamp and the trailing message body for further matching.
_PREFIX_RE = re.compile(
    r"^(?P<ts>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}) "
    r"\d+ [0-9a-fA-F]+ \[(?P<level>\w+) Client \d+\] (?P<body>.*)$"
)

# Message-body patterns, mapped to an event "kind". Order matters: the first
# match wins, so put the most specific patterns first.
_EVENT_PATTERNS = [
    # ": TomawarTheSeventh (Infernalist) is now level 66"
    (
        "level_up",
        re.compile(r"^: (?P<character>[^\s(]+) \((?P<klass>[^)]+)\) is now level (?P<level>\d+)"),
    ),
    # 'Generating level 62 area "P2_1" with seed 3720906296'
    (
        "area_change",
        re.compile(
            r'Generating level (?P<area_level>\d+) area "(?P<area_code>[^"]+)" with seed (?P<seed>\d+)'
        ),
    ),
    # "Connecting to instance server at 64.87.33.204:21360"
    ("instance_connect", re.compile(r"Connecting to instance server at (?P<server>[\d.]+:\d+)")),
    # ": TomawarTheSeventh has been slain."
    ("death", re.compile(r"^: (?P<character>[^\s(]+) has been slain\.")),
    # ": AFK mode is now ON. ..." / ": AFK mode is now OFF."
    ("afk", re.compile(r"^: AFK mode is now (?P<afk_state>ON|OFF)")),
    # "@From blightblot: text"  /  "@To someone: text"
    ("whisper", re.compile(r"^@(?P<direction>From|To) (?P<who>[^:]+): (?P<text>.*)$")),
    # ": 7 Items identified"
    ("items_identified", re.compile(r"^: (?P<count>\d+) Items? identified")),
]

# Events that establish "where/who" for current-state collapsing.
_STATE_KINDS = {"level_up", "area_change", "instance_connect", "death", "afk"}


class ClientLogReader:
    """Tail-and-parse reader for the PoE2 client log.

    Stateless w.r.t. file position: every call re-reads a bounded tail window,
    so it is safe to construct once and call repeatedly. It never loads the
    full multi-hundred-MB log into memory.
    """

    def __init__(
        self, log_path: Optional[str | Path] = None, default_tail_bytes: int = 1_048_576
    ) -> None:
        """
        Args:
            log_path: explicit path to Client.txt. If None, auto-discovers.
            default_tail_bytes: how many trailing bytes to scan by default
                (1 MiB ~= several thousand lines, comfortably covers a play
                session's recent zone/level/death events).
        """
        self.default_tail_bytes = default_tail_bytes
        self.log_path: Optional[Path] = Path(log_path) if log_path else self._discover_log_path()

    @staticmethod
    def _discover_log_path() -> Optional[Path]:
        """Return the first existing candidate Client.txt, or None."""
        for candidate in _DEFAULT_LOG_CANDIDATES:
            p = Path(candidate)
            if p.exists():
                return p
        return None

    def is_available(self) -> bool:
        """True if a Client.txt was located and is readable."""
        return self.log_path is not None and self.log_path.exists()

    def _read_tail(self, max_bytes: Optional[int] = None) -> List[str]:
        """Read the last `max_bytes` of the log as decoded lines.

        Seeks to EOF-max_bytes and reads forward, dropping the (likely
        partial) first line. Decodes with errors='replace' because the log is
        UTF-8 but can contain stray bytes from chat.
        """
        if not self.is_available():
            return []
        max_bytes = max_bytes or self.default_tail_bytes
        try:
            size = self.log_path.stat().st_size
            start = max(0, size - max_bytes)
            with open(self.log_path, "rb") as f:
                f.seek(start)
                chunk = f.read()
        except OSError:
            return []

        text = chunk.decode("utf-8", errors="replace")
        lines = text.splitlines()
        # Drop the first fragment if we started mid-file (it's a partial line).
        if start > 0 and lines:
            lines = lines[1:]
        return lines

    @staticmethod
    def parse_line(line: str) -> Optional[Dict[str, Any]]:
        """Parse one raw log line into a typed event dict, or None if it isn't
        one of the events we track."""
        pm = _PREFIX_RE.match(line)
        if not pm:
            return None
        body = pm.group("body")
        for kind, pattern in _EVENT_PATTERNS:
            m = pattern.search(body)
            if not m:
                continue
            event: Dict[str, Any] = {
                "kind": kind,
                "timestamp": pm.group("ts"),
                "log_level": pm.group("level"),
            }
            event.update(m.groupdict())
            # Normalize numeric fields where present.
            for num_key in ("level", "area_level", "seed", "count"):
                if num_key in event and event[num_key] is not None:
                    try:
                        event[num_key] = int(event[num_key])
                    except (TypeError, ValueError):
                        pass
            return event
        return None

    def get_recent_events(
        self, limit: int = 50, kinds: Optional[List[str]] = None, max_bytes: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Return up to `limit` most-recent parsed events (newest first).

        Args:
            limit: max events to return.
            kinds: optional whitelist of event kinds to include.
            max_bytes: tail window size override.
        """
        kind_filter = set(kinds) if kinds else None
        events: List[Dict[str, Any]] = []
        for line in self._read_tail(max_bytes):
            ev = self.parse_line(line)
            if ev is None:
                continue
            if kind_filter and ev["kind"] not in kind_filter:
                continue
            events.append(ev)
        events.reverse()  # newest first
        return events[:limit]

    def get_current_state(self, max_bytes: Optional[int] = None) -> Dict[str, Any]:
        """Collapse the recent event stream into the player's current state.

        Walks events oldest->newest so later events overwrite earlier ones,
        yielding the most recent known value for each field. Character identity
        falls back to death lines when no recent level-up is in the window.

        Returns a dict with: available, log_path, character, ascendancy_or_class,
        level, area_code, area_level, area_seed, instance_server, afk,
        deaths_in_window, last_event_time, event_count.
        """
        if not self.is_available():
            return {
                "available": False,
                "reason": "Client.txt not found. Game install not at a known "
                "path — pass an explicit log_path.",
                "log_path": None,
            }

        # Scan oldest->newest; tail window is already chronological.
        state: Dict[str, Any] = {
            "available": True,
            "log_path": str(self.log_path),
            "character": None,
            "ascendancy_or_class": None,
            "level": None,
            "area_code": None,
            "area_level": None,
            "area_seed": None,
            "instance_server": None,
            "afk": None,
            "deaths_in_window": 0,
            "last_event_time": None,
            "event_count": 0,
        }

        for line in self._read_tail(max_bytes):
            ev = self.parse_line(line)
            if ev is None:
                continue
            state["event_count"] += 1
            state["last_event_time"] = ev["timestamp"]

            kind = ev["kind"]
            if kind == "level_up":
                state["character"] = ev["character"]
                state["ascendancy_or_class"] = ev["klass"]
                state["level"] = ev["level"]
            elif kind == "area_change":
                state["area_code"] = ev["area_code"]
                state["area_level"] = ev["area_level"]
                state["area_seed"] = ev["seed"]
            elif kind == "instance_connect":
                state["instance_server"] = ev["server"]
            elif kind == "afk":
                state["afk"] = ev["afk_state"] == "ON"
            elif kind == "death":
                state["deaths_in_window"] += 1
                # Fallback identity source when no level-up is in the window.
                if not state["character"]:
                    state["character"] = ev["character"]

        return state

    @staticmethod
    def _parse_ts(ts: str) -> Optional[datetime]:
        """Parse the log timestamp 'YYYY/MM/DD HH:MM:SS' into a datetime."""
        try:
            return datetime.strptime(ts, "%Y/%m/%d %H:%M:%S")
        except (TypeError, ValueError):
            return None
