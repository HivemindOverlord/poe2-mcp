"""
Path of Building TCP Client
Communicates with the MCP Bridge addon installed in PoB.

https://github.com/HivemindOverlord/poe2-mcp
"""

import json
import logging
import socket
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


class PoBConnectionError(Exception):
    """Raised when connection to PoB fails."""

    pass


class PoBCommandError(Exception):
    """Raised when a PoB command returns an error."""

    pass


class PoBClient:
    """
    Client for communicating with Path of Building's MCP Bridge addon.

    The MCP Bridge addon must be installed in PoB for this client to work.
    See pob_addon/README.md for installation instructions.

    Example:
        client = PoBClient()
        if client.is_connected():
            calcs = client.get_calcs()
            print(f"DPS: {calcs.get('TotalDPS')}")
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 49085, timeout: float = 5.0):
        """
        Initialize PoB client.

        Args:
            host: PoB bridge host (should always be localhost)
            port: PoB bridge port (default: 49085)
            timeout: Socket timeout in seconds
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self._request_id = 0
        self._connected = False
        self._last_error: Optional[str] = None

    def _send_command(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a JSON-RPC command to PoB.

        Args:
            method: Command method name
            params: Optional command parameters

        Returns:
            Result from PoB

        Raises:
            PoBConnectionError: If connection fails
            PoBCommandError: If command returns an error
        """
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {},
        }

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.timeout)
                sock.connect((self.host, self.port))

                # Send request
                request_bytes = (json.dumps(request) + "\n").encode("utf-8")
                sock.sendall(request_bytes)

                # Receive response
                response_bytes = b""
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response_bytes += chunk
                    if b"\n" in response_bytes:
                        break

                if not response_bytes:
                    raise PoBConnectionError("Empty response from PoB")

                response = json.loads(response_bytes.decode("utf-8"))

                # Check for error
                if "error" in response:
                    error = response["error"]
                    self._last_error = error.get("message", str(error))
                    raise PoBCommandError(self._last_error)

                self._connected = True
                return response.get("result", {})

        except socket.timeout:
            self._connected = False
            self._last_error = "Connection timed out"
            raise PoBConnectionError(self._last_error)
        except socket.error as e:
            self._connected = False
            self._last_error = f"Socket error: {e}"
            raise PoBConnectionError(self._last_error)
        except json.JSONDecodeError as e:
            self._last_error = f"Invalid JSON response: {e}"
            raise PoBCommandError(self._last_error)

    # The addon binds 49085, but falls back to 49086-49088 if that port is busy
    # (and updates its own config.PORT). A single hardwired port can therefore
    # miss a running bridge, so discovery scans the whole range.
    BRIDGE_PORTS = (49085, 49086, 49087, 49088)

    @classmethod
    def find_bridge(
        cls,
        host: str = "127.0.0.1",
        ports: Optional[tuple] = None,
        timeout: float = 1.5,
    ) -> Optional["PoBClient"]:
        """
        Find a running PoB bridge across the default + fallback ports.

        Returns a connected PoBClient on the first port that answers ping(), or
        None if nothing is reachable. Use this instead of assuming 49085.
        """
        for port in ports or cls.BRIDGE_PORTS:
            client = cls(host=host, port=port, timeout=timeout)
            if client.is_connected():
                return client
        return None

    def is_connected(self) -> bool:
        """Check if PoB is running and responsive."""
        try:
            result = self.ping()
            return result.get("status") == "ok"
        except (PoBConnectionError, PoBCommandError):
            return False

    def get_last_error(self) -> Optional[str]:
        """Get the last error message."""
        return self._last_error

    # =========================================================================
    # System Commands
    # =========================================================================

    def ping(self) -> Dict[str, Any]:
        """
        Check if PoB is running and get status.

        Returns:
            Dict with status, version, build_loaded, uptime
        """
        return self._send_command("ping")

    def status(self) -> Dict[str, Any]:
        """
        Get detailed server status.

        Returns:
            Dict with running, port, host, uptime, requests, version
        """
        return self._send_command("status")

    # =========================================================================
    # Build Commands
    # =========================================================================

    def get_build(self, format: str = "xml") -> Dict[str, Any]:
        """
        Get current build from PoB.

        Args:
            format: "xml" for raw XML, "code" for PoB share code

        Returns:
            Dict with xml/code and format fields
        """
        return self._send_command("get_build", {"format": format})

    def load_build(
        self, xml: Optional[str] = None, code: Optional[str] = None, name: str = "MCP Build"
    ) -> Dict[str, Any]:
        """
        Load a build into PoB.

        Args:
            xml: Build XML string
            code: PoB share code (alternative to xml)
            name: Build name to display

        Returns:
            Dict with success status
        """
        params = {"name": name}
        if xml:
            params["xml"] = xml
        elif code:
            params["code"] = code
        else:
            raise ValueError("Must provide either xml or code")
        return self._send_command("load_build", params)

    def new_build(self, name: str = "MCP New Build") -> Dict[str, Any]:
        """
        Create a new empty build in PoB.

        Args:
            name: Build name

        Returns:
            Dict with success status
        """
        return self._send_command("new_build", {"name": name})

    # =========================================================================
    # Calculation Commands
    # =========================================================================

    def get_calcs(self) -> Dict[str, Any]:
        """
        Get calculation results from PoB.

        Returns:
            Dict with TotalDPS, Life, EnergyShield, resistances, etc.
        """
        return self._send_command("get_calcs")

    def get_raw_output(self) -> Dict[str, Any]:
        """
        Get full raw calculation output for advanced analysis.

        Returns:
            Dict with mainOutput and calcsOutput tables
        """
        return self._send_command("get_raw_output")

    # =========================================================================
    # Skill Commands
    # =========================================================================

    def get_skills(self) -> Dict[str, Any]:
        """
        Get all skill groups and gems.

        Returns:
            Dict with skillGroups list and mainSocketGroup index
        """
        return self._send_command("get_skills")

    def set_skill_group(self, skills: str, replace_all: bool = False) -> Dict[str, Any]:
        """
        Add or replace skill groups.

        Args:
            skills: Skill text in PoB format:
                    "SkillName Level/Quality\nSupportName Level/Quality"
            replace_all: If True, removes all existing skills first

        Returns:
            Dict with success status
        """
        return self._send_command("set_skill_group", {"skills": skills, "replace_all": replace_all})

    # =========================================================================
    # Passive Tree Commands
    # =========================================================================

    def get_passive_tree(self) -> Dict[str, Any]:
        """
        Get allocated passive nodes.

        Returns:
            Dict with class, ascendancy, nodes list, totalPoints
        """
        return self._send_command("get_passive_tree")

    def set_passive_node(self, node_id: int, allocate: bool = True) -> Dict[str, Any]:
        """
        Allocate or deallocate a passive node.

        Args:
            node_id: Passive node ID
            allocate: True to allocate, False to deallocate

        Returns:
            Dict with success status
        """
        return self._send_command("set_passive_node", {"node_id": node_id, "allocate": allocate})

    # =========================================================================
    # Item Commands
    # =========================================================================

    def get_items(self) -> Dict[str, Any]:
        """
        Get equipped items.

        Returns:
            Dict with items list (slot, name, rarity, base, etc.)
        """
        return self._send_command("get_items")

    # =========================================================================
    # Config Commands
    # =========================================================================

    def set_custom_mods(self, mods: str) -> Dict[str, Any]:
        """
        Set custom modifiers text.

        Args:
            mods: Custom mod text (one mod per line)

        Returns:
            Dict with success status
        """
        return self._send_command("set_custom_mods", {"mods": mods})

    def get_custom_mods(self) -> Dict[str, Any]:
        """
        Get current custom modifiers text.

        Returns:
            Dict with mods string
        """
        return self._send_command("get_custom_mods")

    def set_config(self, **config) -> Dict[str, Any]:
        """
        Set configuration options.

        Args:
            **config: Configuration key-value pairs

        Returns:
            Dict with success status
        """
        return self._send_command("set_config", config)

    def get_config(self) -> Dict[str, Any]:
        """
        Get current configuration.

        Returns:
            Dict with config options
        """
        return self._send_command("get_config")

    # =========================================================================
    # Comparison Commands
    # =========================================================================

    def compare_with_snapshot(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare current build with a previous calculation snapshot.

        Args:
            snapshot: Previous calcs result to compare against

        Returns:
            Dict with diff (old, new, delta, percent for each stat)
        """
        return self._send_command("compare_with_snapshot", {"snapshot": snapshot})

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def get_dps(self) -> Optional[float]:
        """Get total DPS from current build."""
        try:
            calcs = self.get_calcs()
            return calcs.get("TotalDPS") or calcs.get("CombinedDPS")
        except (PoBConnectionError, PoBCommandError):
            return None

    def get_ehp(self) -> Optional[Dict[str, float]]:
        """Get effective HP stats from current build."""
        try:
            calcs = self.get_calcs()
            return {
                "life": calcs.get("Life", 0),
                "es": calcs.get("EnergyShield", 0),
                "armour": calcs.get("Armour", 0),
                "evasion": calcs.get("Evasion", 0),
                "phys_reduction": calcs.get("PhysicalDamageReduction", 0),
            }
        except (PoBConnectionError, PoBCommandError):
            return None

    def get_resistances(self) -> Optional[Dict[str, float]]:
        """Get resistance values from current build."""
        try:
            calcs = self.get_calcs()
            return {
                "fire": calcs.get("FireResist", 0),
                "cold": calcs.get("ColdResist", 0),
                "lightning": calcs.get("LightningResist", 0),
                "chaos": calcs.get("ChaosResist", 0),
            }
        except (PoBConnectionError, PoBCommandError):
            return None

    # =========================================================================
    # Enhanced Commands (v1.1.0)
    # =========================================================================

    def load_build_direct(
        self, xml: Optional[str] = None, code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load build XML directly into existing build (faster, no mode switch).

        Requires a build to already be loaded in PoB. This is faster than
        load_build() when you want to swap builds quickly.

        Args:
            xml: Build XML string
            code: PoB share code (alternative to xml)

        Returns:
            Dict with success status and method used
        """
        params = {}
        if xml:
            params["xml"] = xml
        elif code:
            params["code"] = code
        else:
            raise ValueError("Must provide either xml or code")
        return self._send_command("load_build_direct", params)

    def recalculate(self) -> Dict[str, Any]:
        """
        Force full calculation refresh.

        Use this after making changes to ensure calculations are up to date.

        Returns:
            Dict with success status
        """
        return self._send_command("recalculate")

    def get_full_calcs(self) -> Dict[str, Any]:
        """
        Get comprehensive calculation data.

        Returns merged mainOutput + calcsOutput with a summary section
        for quick access to key stats.

        Returns:
            Dict with main, calcs, and summary sections
        """
        return self._send_command("get_full_calcs")

    def get_skill_dps(self) -> Dict[str, Any]:
        """
        Get DPS breakdown per skill group.

        Returns:
            Dict with skills list and main_skill_index
        """
        return self._send_command("get_skill_dps")

    def get_defense_stats(self) -> Dict[str, Any]:
        """
        Get focused defense statistics.

        Returns comprehensive defense data including life, ES, armour,
        evasion, block, resistances, and max hit taken.

        Returns:
            Dict with life, energy_shield, armour, evasion, block,
            resistances, max_hit, and stun sections
        """
        return self._send_command("get_defense_stats")

    def wait_for_build(self, max_attempts: int = 10, delay: float = 0.1) -> bool:
        """
        Wait for a build to be loaded after load_build() or new_build().

        Since mode switching is async in PoB, this polls ping() until
        build_loaded becomes True.

        Args:
            max_attempts: Maximum number of attempts
            delay: Delay between attempts in seconds

        Returns:
            True if build loaded, False if timeout
        """
        import time

        for _ in range(max_attempts):
            try:
                result = self.ping()
                if result.get("build_loaded"):
                    return True
            except (PoBConnectionError, PoBCommandError):
                pass
            time.sleep(delay)
        return False

    # =========================================================================
    # Build editing (added during the bridge build-out)
    # =========================================================================

    def set_main_skill_group(self, index: int) -> Dict[str, Any]:
        """Set which socket group is the main skill (drives DPS/Average Hit)."""
        return self._send_command("set_main_skill_group", {"index": index})

    def set_displayed_skill(
        self, group_index: int, skill_index: Optional[int] = None, part: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Set the DISPLAYED active skill (and skill part) within a group.

        Essential for trigger / multi-stage skills: PoB otherwise shows the
        trigger gem (0 damage) instead of the real damaging skill.
        """
        params: Dict[str, Any] = {"group_index": group_index}
        if skill_index is not None:
            params["skill_index"] = skill_index
        if part is not None:
            params["part"] = part
        return self._send_command("set_displayed_skill", params)

    def get_skill_parts(self, group_index: int) -> Dict[str, Any]:
        """List the active skills (and parts) in a group + which is displayed."""
        return self._send_command("get_skill_parts", {"group_index": group_index})

    def set_group_gems(self, index: int, gems: list) -> Dict[str, Any]:
        """
        Replace a socket group's gems in place (keeps the rest of the build).

        Args:
            index: socket group index (1-based)
            gems: list of {"name": str, "level": int, "quality": int}
        """
        return self._send_command("set_group_gems", {"index": index, "gems": gems})

    def set_character_level(self, level: int) -> Dict[str, Any]:
        """Set the character level (controls the passive-point budget)."""
        return self._send_command("set_character_level", {"level": level})

    def set_config_input(self, key: str, value: Any) -> Dict[str, Any]:
        """Set a configTab input (e.g. detonateDeadCorpseLife, enemy settings)."""
        return self._send_command("set_config_input", {"key": key, "value": value})

    # =========================================================================
    # Introspection
    # =========================================================================

    def get_output(self, keys: Optional[list] = None) -> Dict[str, Any]:
        """Return specific output fields (avoids dumping the whole table)."""
        params = {"keys": keys} if keys else {}
        return self._send_command("get_output", params)

    def get_full_dps(self) -> Dict[str, Any]:
        """PoB Full DPS (sum of all damaging skills incl. triggered DoTs)."""
        return self._send_command("get_full_dps")

    def get_stat_breakdown(self, stat: str, minion: bool = False) -> Dict[str, Any]:
        """
        Explain WHY an output stat is what it is — PoB's modifier-by-modifier
        breakdown. Works for defensive/attribute/resist stats (e.g. "Life",
        "Armour", "FireResist"). Returns {found, lines} or {found: False,
        available: [...]}.
        """
        return self._send_command("get_stat_breakdown", {"stat": stat, "minion": minion})

    def list_config_options(self, filter: Optional[str] = None, limit: int = 400) -> Dict[str, Any]:
        """Enumerate PoB's available config options + current values."""
        params: Dict[str, Any] = {"limit": limit}
        if filter:
            params["filter"] = filter
        return self._send_command("list_config_options", params)

    def search_tree_nodes(
        self, keywords, notables_only: bool = False, limit: int = 200
    ) -> Dict[str, Any]:
        """Search the full passive tree for nodes whose stats match keyword(s)."""
        if isinstance(keywords, str):
            keywords = [keywords]
        return self._send_command(
            "search_tree_nodes",
            {"keywords": keywords, "notables_only": notables_only, "limit": limit},
        )
