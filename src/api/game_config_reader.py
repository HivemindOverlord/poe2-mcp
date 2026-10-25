"""
Local PoE2 client-config reader (poe2_production_Config.ini).

The game persists user settings to an INI under the user's Documents/My Games
folder. This is a LOCAL data source providing playstyle/context the API never
exposes: input mode (WASD vs click-to-move), current act, gateway, display,
and hardware.

IMPORTANT (verified via the captured config on this machine):
    [LOGIN] account_name is EMPTY under Steam authentication — Steam handles
    the login, so the game never writes the account name. Do NOT rely on this
    for account identity; use ClientLogReader (Client.txt) for live character
    identity instead. account_name is only populated for standalone-client
    (non-Steam) logins.

Data flow:
    poe2_production_Config.ini
        -> configparser (utf-8-sig, strips BOM)
        -> read_all()      # full {section: {key: value}}
        -> get_summary()   # the handful of fields useful to a build optimizer
"""

from __future__ import annotations

import configparser
import os
from pathlib import Path
from typing import Any, Dict, Optional

_CONFIG_FILENAME = "poe2_production_Config.ini"
_MY_GAMES_SUFFIX = Path("My Games") / "Path of Exile 2" / _CONFIG_FILENAME

# Map of internal current_act_environment values to human context. PoE2 acts
# are numbered; environment 6 corresponds to late Act content. We surface the
# raw value plus this best-effort label (kept conservative — game data is the
# authority, this is just a hint).
_ACT_ENV_HINTS = {
    "1": "Act 1",
    "2": "Act 2",
    "3": "Act 3",
    "4": "Act 1 (Cruel)",
    "5": "Act 2 (Cruel)",
    "6": "Act 3 (Cruel) / endgame",
}


class GameConfigReader:
    """Reader for the PoE2 client config INI.

    Discovers the config across OneDrive-redirected and standard Documents
    folders. Parsing is tolerant of the UTF-8 BOM the game writes and of
    valueless keys (e.g. ``account_name=``).
    """

    def __init__(self, config_path: Optional[str | Path] = None) -> None:
        self.config_path: Optional[Path] = (
            Path(config_path) if config_path else self._discover_config_path()
        )

    @staticmethod
    def _candidate_paths() -> list[Path]:
        """Build the ordered list of likely config locations for this user."""
        candidates: list[Path] = []
        userprofile = os.environ.get("USERPROFILE")
        if userprofile:
            base = Path(userprofile)
            # OneDrive-redirected Documents takes precedence on this machine.
            candidates.append(base / "OneDrive" / "Documents" / _MY_GAMES_SUFFIX)
            candidates.append(base / "Documents" / _MY_GAMES_SUFFIX)
        # Explicit OneDrive env var as a fallback.
        onedrive = os.environ.get("OneDrive")
        if onedrive:
            candidates.append(Path(onedrive) / "Documents" / _MY_GAMES_SUFFIX)
        return candidates

    @classmethod
    def _discover_config_path(cls) -> Optional[Path]:
        for candidate in cls._candidate_paths():
            if candidate.exists():
                return candidate
        return None

    def is_available(self) -> bool:
        return self.config_path is not None and self.config_path.exists()

    def _load(self) -> Optional[configparser.ConfigParser]:
        """Parse the INI. Returns None if unavailable/unparseable.

        Uses interpolation=None (values may contain '%' / special chars) and
        preserves key case.
        """
        if not self.is_available():
            return None
        parser = configparser.ConfigParser(
            interpolation=None,
            strict=False,  # tolerate duplicate keys rather than raising
        )
        parser.optionxform = str  # preserve original key casing
        try:
            # utf-8-sig strips the BOM the game writes before "[LOGIN]".
            with open(self.config_path, "r", encoding="utf-8-sig") as f:
                parser.read_file(f)
        except (OSError, configparser.Error):
            return None
        return parser

    def read_all(self) -> Dict[str, Dict[str, str]]:
        """Return the full config as {section: {key: value}}."""
        parser = self._load()
        if parser is None:
            return {}
        return {section: dict(parser.items(section)) for section in parser.sections()}

    def get_summary(self) -> Dict[str, Any]:
        """Return the build-relevant subset of the config.

        Surfaces: gateway, account_name (often empty under Steam), input mode
        (wasd vs click — affects playstyle/skill recommendations), current act,
        resolution, renderer, framerate cap, and GPU.
        """
        parser = self._load()
        if parser is None:
            return {
                "available": False,
                "reason": "poe2_production_Config.ini not found at a known path.",
                "config_path": None,
            }

        def get(section: str, key: str, default: Optional[str] = None) -> Optional[str]:
            try:
                return parser.get(section, key)
            except (configparser.NoSectionError, configparser.NoOptionError):
                return default

        account_name = get("LOGIN", "account_name") or None
        input_mode = get("GENERAL", "user_input_mode") or get(
            "GENERAL", "last_selected_KBM_input_mode"
        )
        act_env = get("CACHED_DATA", "current_act_environment")

        res_w = get("DISPLAY", "resolution_width")
        res_h = get("DISPLAY", "resolution_height")
        resolution = f"{res_w}x{res_h}" if res_w and res_h else None

        return {
            "available": True,
            "config_path": str(self.config_path),
            # Identity / account
            "account_name": account_name,
            "account_name_note": (
                "empty — Steam auth does not write account_name; use the live "
                "client log (Client.txt) for character identity"
                if not account_name
                else None
            ),
            "gateway": get("LOGIN", "gateway_id"),
            "gateway_auto_select": get("LOGIN", "gateway_auto_select"),
            # Playstyle / build-relevant context
            "input_mode": input_mode,  # 'wasd' or 'click'
            "current_act_environment": act_env,
            "current_act_hint": _ACT_ENV_HINTS.get(act_env) if act_env else None,
            "profanity_filter": get("GENERAL", "enable_profanity_filter"),
            "tutorials_disabled": get("GENERAL", "disable_tutorials"),
            # Display / hardware (perf context)
            "resolution": resolution,
            "renderer": get("DISPLAY", "renderer_type"),
            "upscale": get("DISPLAY", "upscale"),
            "framerate_limit": get("DISPLAY", "framerate_limit"),
            "framerate_limit_enabled": get("DISPLAY", "framerate_limit_enabled"),
            "gpu": get("DISPLAY", "adapter_name"),
        }
