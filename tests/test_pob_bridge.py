"""
Offline unit tests for the live Path of Building bridge.

Unlike test_pob_integration.py (which needs a real PoB running), these tests
use a mock TCP server and temp directories, so they run in CI with no PoB and
no network. They cover:

  * PoBClient JSON-RPC round-trips (ping / get_passive_tree / get_build /
    load_build / get_calcs) against a mock server speaking the addon's protocol.
  * installer.py: install detection, Launch.lua patch idempotency, and
    install/uninstall against a fake PoB tree.
"""

from __future__ import annotations

import json
import socket
import threading
from pathlib import Path

import pytest

from src.pob import installer
from src.pob.client import PoBClient, PoBCommandError

REPO_ROOT = Path(__file__).resolve().parent.parent
ADDON_SOURCE = REPO_ROOT / "pob_addon" / "src" / "Addons"


# ---------------------------------------------------------------------------
# Mock bridge server (mimics pob_addon/src/Addons/MCPBridge/bridge.lua)
# ---------------------------------------------------------------------------

# Canned responses keyed by JSON-RPC method, matching what commands.lua returns.
MOCK_RESPONSES = {
    "ping": {
        "status": "ok",
        "version": "1.1.0",
        "pob_version": "0.20.0",
        "build_loaded": True,
        "build_name": "Mock Build",
        "uptime": 1,
    },
    "get_passive_tree": {
        "class": "Ranger",
        "classId": 2,
        "ascendancy": "Deadeye",
        "ascendancyId": 1,
        "nodes": [{"id": 50459, "name": "RANGER", "type": "ClassStart", "stats": []}],
        "totalPoints": 1,
    },
    "get_build": {"code": "eNrMOCKCODE", "format": "pob_code", "name": "Mock Build"},
    "get_calcs": {"TotalDPS": 123456.0, "Life": 4200, "FireResist": 75},
    "load_build": {"success": True, "name": "Mock Import", "note": "queued"},
    "set_main_skill_group": {"success": True, "main_socket_group": 7},
    "set_displayed_skill": {"success": True, "group": 6, "mainActiveSkill": 2},
    "get_skill_parts": {
        "group": 6,
        "mainActiveSkill": 1,
        "skills": [
            {"index": 1, "name": "Cast on Minion Death", "is_main": True, "parts": []},
            {"index": 2, "name": "Bitter Dead", "is_main": False, "parts": []},
        ],
    },
    "set_group_gems": {
        "success": True,
        "index": 7,
        "gems": [{"name": "Detonate Dead", "valid": True}],
    },
    "set_config_input": {"success": True, "key": "detonateDeadCorpseLife", "value": 34963},
    "get_output": {"TotalDPS": 56530.0, "AverageDamage": 60299.0},
    "get_stat_breakdown": {
        "stat": "Life",
        "found": True,
        "lines": ["1915 (base)", "x 1.05 (increased)", "= 1910"],
    },
    "list_config_options": {
        "count": 1,
        "options": [
            {
                "var": "detonateDeadCorpseLife",
                "type": "count",
                "label": "Enemy Corpse Life:",
                "value": 34963,
            }
        ],
    },
    "search_tree_nodes": {
        "count": 1,
        "nodes": [
            {
                "id": 51184,
                "name": "Raw Destruction",
                "reachable": True,
                "allocated": False,
                "distance": 3,
                "stats": ["16% increased Spell Damage"],
            }
        ],
    },
}


class MockBridgeServer:
    """Single-threaded mock that accepts one connection per request (like the
    real addon — PoBClient opens a fresh socket per command)."""

    def __init__(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", 0))  # ephemeral port
        self._sock.listen(5)
        self._sock.settimeout(0.5)
        self.port = self._sock.getsockname()[1]
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self.last_request = None

    def start(self):
        self._thread.start()

    def _serve(self):
        while not self._stop.is_set():
            try:
                client, _ = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                client.settimeout(1.0)
                buf = b""
                while b"\n" not in buf:
                    chunk = client.recv(4096)
                    if not chunk:
                        break
                    buf += chunk
                req = json.loads(buf.decode("utf-8").strip())
                self.last_request = req
                method = req.get("method")
                if method in MOCK_RESPONSES:
                    payload = {
                        "jsonrpc": "2.0",
                        "id": req.get("id"),
                        "result": MOCK_RESPONSES[method],
                    }
                else:
                    payload = {
                        "jsonrpc": "2.0",
                        "id": req.get("id"),
                        "error": {"code": -32601, "message": f"Method not found: {method}"},
                    }
                client.sendall((json.dumps(payload) + "\n").encode("utf-8"))
            except Exception:
                pass
            finally:
                client.close()

    def stop(self):
        self._stop.set()
        try:
            self._sock.close()
        except OSError:
            pass
        self._thread.join(timeout=2.0)


@pytest.fixture
def mock_bridge():
    server = MockBridgeServer()
    server.start()
    yield server
    server.stop()


# ---------------------------------------------------------------------------
# PoBClient round-trip tests
# ---------------------------------------------------------------------------


def test_client_ping(mock_bridge):
    client = PoBClient(port=mock_bridge.port, timeout=2.0)
    assert client.is_connected() is True
    ping = client.ping()
    assert ping["status"] == "ok"
    assert ping["build_loaded"] is True


def test_client_get_passive_tree(mock_bridge):
    client = PoBClient(port=mock_bridge.port, timeout=2.0)
    tree = client.get_passive_tree()
    assert tree["class"] == "Ranger"
    assert tree["totalPoints"] == 1
    assert tree["nodes"][0]["id"] == 50459


def test_client_get_build_code(mock_bridge):
    client = PoBClient(port=mock_bridge.port, timeout=2.0)
    build = client.get_build(format="code")
    assert build["code"].startswith("eNr")
    # Verify the request actually asked for code format
    assert mock_bridge.last_request["params"]["format"] == "code"


def test_client_load_build_roundtrip(mock_bridge):
    client = PoBClient(port=mock_bridge.port, timeout=2.0)
    result = client.load_build(code="eNrSOMECODE", name="Mock Import")
    assert result["success"] is True
    assert mock_bridge.last_request["method"] == "load_build"
    assert mock_bridge.last_request["params"]["code"] == "eNrSOMECODE"


def test_client_get_calcs(mock_bridge):
    client = PoBClient(port=mock_bridge.port, timeout=2.0)
    calcs = client.get_calcs()
    assert calcs["TotalDPS"] == pytest.approx(123456.0)
    assert calcs["Life"] == 4200


def test_client_unknown_method_raises(mock_bridge):
    client = PoBClient(port=mock_bridge.port, timeout=2.0)
    with pytest.raises(PoBCommandError):
        client._send_command("does_not_exist")


def test_client_not_connected_when_no_server():
    # Nothing listening on this port -> is_connected False, never raises
    client = PoBClient(port=59999, timeout=0.5)
    assert client.is_connected() is False


# ---------------------------------------------------------------------------
# Installer tests (fake PoB tree in a tmp dir)
# ---------------------------------------------------------------------------

# A minimal Launch.lua containing the real patch anchor + surrounding block.
FAKE_LAUNCH_LUA = """\
function launch:OnInit()
\tlocal errMsg
\terrMsg, self.main = PLoadModule("Modules/Main")
\tif errMsg then
\t\tself:ShowErrMsg("Error loading main script: %s", errMsg)
\telseif self.main.Init then
\t\terrMsg = PCall(self.main.Init, self.main)
\t\tif errMsg then
\t\t\tself:ShowErrMsg("In 'Init': %s", errMsg)
\t\tend
\tend
end
"""


@pytest.fixture
def fake_pob(tmp_path):
    root = tmp_path / "PathOfBuilding-PoE2"
    (root / "src").mkdir(parents=True)
    (root / "src" / "Launch.lua").write_text(FAKE_LAUNCH_LUA, encoding="utf-8")
    return root


@pytest.fixture
def fake_pob_packaged(tmp_path):
    """Packaged Windows Community PoE2 release: flattened, no src/ subfolder (#206)."""
    root = tmp_path / "Path of Building Community (PoE2)"
    root.mkdir(parents=True)
    (root / "Launch.lua").write_text(FAKE_LAUNCH_LUA, encoding="utf-8")
    return root


def test_find_pob_installation(fake_pob):
    found = installer.find_pob_installation(extra_paths=[fake_pob])
    assert found == fake_pob


def test_non_pob_dir_not_detected(tmp_path):
    # A dir with no Launch.lua in either layout is not a PoB root. (We assert on
    # _is_pob_root rather than find_pob_installation, which intentionally falls
    # back to scanning common install paths and would find a real install on a
    # dev box.)
    assert installer._is_pob_root(tmp_path) is False
    assert installer._is_pob_root(tmp_path / "nope") is False


# ---------------------------------------------------------------------------
# Packaged Community PoE2 layout (root Launch.lua, no src/) — regression tests
# for #206, where the bridge failed to detect this install shape at all.
# ---------------------------------------------------------------------------


def test_packaged_layout_detected(fake_pob_packaged):
    assert installer._is_pob_root(fake_pob_packaged) is True
    assert installer._pob_layout(fake_pob_packaged) == "root"
    found = installer.find_pob_installation(extra_paths=[fake_pob_packaged])
    assert found == fake_pob_packaged


def test_packaged_layout_install_and_detect(fake_pob_packaged):
    before = installer.is_addon_installed(fake_pob_packaged)
    assert before["installed"] is False

    result = installer.install_addon(pob_path=fake_pob_packaged, source_dir=ADDON_SOURCE)
    assert result["success"] is True, result

    after = installer.is_addon_installed(fake_pob_packaged)
    assert after["installed"] is True

    # Addon files land at <root>/Addons, not <root>/src/Addons.
    assert (fake_pob_packaged / "Addons" / "MCPBridge" / "bridge.lua").is_file()
    assert not (fake_pob_packaged / "src").exists()

    launch_text = (fake_pob_packaged / "Launch.lua").read_text(encoding="utf-8")
    assert launch_text.count(installer.ADDON_LOADER_MARKER) == 1
    assert (fake_pob_packaged / "Launch.lua.mcp_backup").is_file()


def test_packaged_layout_uninstall_restores(fake_pob_packaged):
    installer.install_addon(pob_path=fake_pob_packaged, source_dir=ADDON_SOURCE)

    result = installer.uninstall_addon(pob_path=fake_pob_packaged)
    assert result["success"] is True

    assert not (fake_pob_packaged / "Addons" / "MCPBridge").exists()
    launch_text = (fake_pob_packaged / "Launch.lua").read_text(encoding="utf-8")
    assert installer.ADDON_LOADER_MARKER not in launch_text
    assert launch_text == FAKE_LAUNCH_LUA


def test_packaged_layout_ensure_installed_full_install(fake_pob_packaged):
    result = installer.ensure_installed(fake_pob_packaged)
    assert result["action"] == "installed", result
    assert installer.is_addon_installed(fake_pob_packaged)["installed"] is True


def test_src_layout_preferred_when_both_present(tmp_path):
    """If a root both has src/Launch.lua and a stray root Launch.lua, the src/
    layout wins (matches the source-of-truth checkout, not packaging leftovers)."""
    root = tmp_path / "Ambiguous"
    (root / "src").mkdir(parents=True)
    (root / "src" / "Launch.lua").write_text(FAKE_LAUNCH_LUA, encoding="utf-8")
    (root / "Launch.lua").write_text("-- stray file, not the real one\n", encoding="utf-8")
    assert installer._pob_layout(root) == "src"


def test_addon_source_resolves():
    assert ADDON_SOURCE.is_dir()
    assert (ADDON_SOURCE / "init.lua").is_file()
    assert (ADDON_SOURCE / "MCPBridge" / "bridge.lua").is_file()


def test_install_and_detect(fake_pob):
    before = installer.is_addon_installed(fake_pob)
    assert before["installed"] is False
    assert before["launch_patched"] is False

    result = installer.install_addon(pob_path=fake_pob, source_dir=ADDON_SOURCE)
    assert result["success"] is True, result
    assert result["launch_patch"] in ("patched", "already_patched")

    after = installer.is_addon_installed(fake_pob)
    assert after["installed"] is True
    assert after["files_present"] is True
    assert after["launch_patched"] is True

    # Loader line landed in Launch.lua exactly once
    launch_text = (fake_pob / "src" / "Launch.lua").read_text(encoding="utf-8")
    assert launch_text.count(installer.ADDON_LOADER_MARKER) == 1
    # Backup was created
    assert (fake_pob / "src" / "Launch.lua.mcp_backup").is_file()


def test_patch_idempotent(fake_pob):
    installer.install_addon(pob_path=fake_pob, source_dir=ADDON_SOURCE)
    # Re-running install must not duplicate the loader line
    installer.install_addon(pob_path=fake_pob, source_dir=ADDON_SOURCE)
    launch_text = (fake_pob / "src" / "Launch.lua").read_text(encoding="utf-8")
    assert launch_text.count(installer.ADDON_LOADER_MARKER) == 1

    # Direct patch call on an already-patched file reports already_patched
    status = installer._patch_launch_lua(fake_pob / "src" / "Launch.lua")
    assert status == "already_patched"


def test_patch_anchor_not_found(tmp_path):
    root = tmp_path / "NoAnchorPoB"
    (root / "src").mkdir(parents=True)
    (root / "src" / "Launch.lua").write_text("function launch:OnInit() end\n", encoding="utf-8")
    result = installer.install_addon(pob_path=root, source_dir=ADDON_SOURCE)
    # Files copy, but patch can't find the anchor -> reported, not silently OK
    assert result["success"] is False
    assert result["launch_patch"] == "anchor_not_found"


def test_uninstall_restores(fake_pob):
    installer.install_addon(pob_path=fake_pob, source_dir=ADDON_SOURCE)
    original = FAKE_LAUNCH_LUA

    result = installer.uninstall_addon(pob_path=fake_pob)
    assert result["success"] is True

    # Addon files gone
    assert not (fake_pob / "src" / "Addons" / "MCPBridge").exists()
    # Launch.lua restored from backup (loader line stripped)
    launch_text = (fake_pob / "src" / "Launch.lua").read_text(encoding="utf-8")
    assert installer.ADDON_LOADER_MARKER not in launch_text
    assert launch_text == original


def test_config_lua_uses_global_mcpconfig():
    """Regression guard for the bug that kept the bridge from ever binding:
    config.lua must declare MCPConfig as a GLOBAL, not local."""
    config_lua = (ADDON_SOURCE / "MCPBridge" / "config.lua").read_text(encoding="utf-8")
    assert "local MCPConfig" not in config_lua
    assert "MCPConfig = {}" in config_lua


def test_ensure_installed_repatches_after_update(fake_pob):
    """Simulate a PoB update that overwrites Launch.lua (wiping our hook) but
    leaves the Addons/ folder. ensure_installed should re-apply just the hook."""
    installer.install_addon(pob_path=fake_pob, source_dir=ADDON_SOURCE)
    launch = fake_pob / "src" / "Launch.lua"

    # PoB update: Launch.lua reverted to the un-patched original (addon files stay)
    launch.write_text(FAKE_LAUNCH_LUA, encoding="utf-8")
    assert installer.ADDON_LOADER_MARKER not in launch.read_text(encoding="utf-8")
    assert (fake_pob / "src" / "Addons" / "MCPBridge" / "bridge.lua").is_file()

    result = installer.ensure_installed(fake_pob)
    assert result["action"] == "repatched", result
    assert installer.is_addon_installed(fake_pob)["installed"] is True
    assert launch.read_text(encoding="utf-8").count(installer.ADDON_LOADER_MARKER) == 1


def test_ensure_installed_full_install_when_absent(fake_pob):
    result = installer.ensure_installed(fake_pob)  # nothing deployed yet
    assert result["action"] == "installed", result
    assert installer.is_addon_installed(fake_pob)["installed"] is True


def test_ensure_installed_noop_when_already_ok(fake_pob):
    installer.install_addon(pob_path=fake_pob, source_dir=ADDON_SOURCE)
    result = installer.ensure_installed(fake_pob)
    assert result["action"] == "ok", result


# ---------------------------------------------------------------------------
# Client wrappers for the build-editing / introspection commands
# ---------------------------------------------------------------------------


def test_client_set_displayed_skill(mock_bridge):
    client = PoBClient(port=mock_bridge.port, timeout=2.0)
    r = client.set_displayed_skill(group_index=6, skill_index=2)
    assert r["mainActiveSkill"] == 2
    req = mock_bridge.last_request
    assert req["method"] == "set_displayed_skill"
    assert req["params"] == {"group_index": 6, "skill_index": 2}


def test_client_get_skill_parts(mock_bridge):
    client = PoBClient(port=mock_bridge.port, timeout=2.0)
    r = client.get_skill_parts(6)
    names = [s["name"] for s in r["skills"]]
    assert "Bitter Dead" in names


def test_client_set_group_gems(mock_bridge):
    client = PoBClient(port=mock_bridge.port, timeout=2.0)
    gems = [{"name": "Detonate Dead", "level": 19, "quality": 20}]
    r = client.set_group_gems(7, gems)
    assert r["success"] is True
    assert mock_bridge.last_request["params"]["gems"] == gems


def test_client_get_stat_breakdown(mock_bridge):
    client = PoBClient(port=mock_bridge.port, timeout=2.0)
    r = client.get_stat_breakdown("Life")
    assert r["found"] is True
    assert any("base" in ln for ln in r["lines"])


def test_client_set_config_input(mock_bridge):
    client = PoBClient(port=mock_bridge.port, timeout=2.0)
    client.set_config_input("detonateDeadCorpseLife", 34963)
    assert mock_bridge.last_request["params"] == {"key": "detonateDeadCorpseLife", "value": 34963}


def test_client_list_config_options(mock_bridge):
    client = PoBClient(port=mock_bridge.port, timeout=2.0)
    r = client.list_config_options(filter="corpse")
    assert r["options"][0]["var"] == "detonateDeadCorpseLife"
    assert mock_bridge.last_request["params"]["filter"] == "corpse"


def test_client_search_tree_nodes_accepts_str(mock_bridge):
    client = PoBClient(port=mock_bridge.port, timeout=2.0)
    client.search_tree_nodes("spell damage", notables_only=True)
    # single string should be normalised to a list
    assert mock_bridge.last_request["params"]["keywords"] == ["spell damage"]
    assert mock_bridge.last_request["params"]["notables_only"] is True


def test_client_get_output_default_and_keys(mock_bridge):
    client = PoBClient(port=mock_bridge.port, timeout=2.0)
    client.get_output()
    assert mock_bridge.last_request["params"] == {}
    client.get_output(keys=["TotalDPS", "Life"])
    assert mock_bridge.last_request["params"]["keys"] == ["TotalDPS", "Life"]


# ---------------------------------------------------------------------------
# Review fixes: port discovery (#1) and encode robustness (#2)
# ---------------------------------------------------------------------------


def test_find_bridge_discovers_running_port(mock_bridge):
    # find_bridge across an explicit port list locates the live bridge
    client = PoBClient.find_bridge(ports=[59997, mock_bridge.port], timeout=1.0)
    assert client is not None
    assert client.port == mock_bridge.port
    assert client.ping()["status"] == "ok"


def test_find_bridge_none_when_unreachable():
    assert PoBClient.find_bridge(ports=[59997, 59998], timeout=0.4) is None


def test_bridge_ports_includes_fallback_range():
    # The addon falls back to 49086-49088; discovery must cover them
    assert PoBClient.BRIDGE_PORTS == (49085, 49086, 49087, 49088)
