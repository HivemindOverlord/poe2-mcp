"""
Path of Building Integration Tests

These tests require PoB to be running with the MCP Bridge addon installed.
Tests will be skipped if PoB is not running.

Run with: pytest tests/test_pob_integration.py -v
Skip if offline: pytest tests/test_pob_integration.py -v -m "not pob_required"
"""

import time
from typing import Optional

import pytest

# Skip all tests if PoB client cannot be imported
try:
    from src.pob.client import PoBClient, PoBCommandError, PoBConnectionError

    POB_CLIENT_AVAILABLE = True
except ImportError:
    POB_CLIENT_AVAILABLE = False


# Sample PoB code for testing (simple build)
SAMPLE_POB_CODE = """eNrtVk1v2zAMvQ_YfxB0TuzYTZoGRYYOxQpsmAdYbSmDHOPkxPLi39-ktiOjXYKtWB"""


def get_pob_client() -> Optional[PoBClient]:
    """Get a connected PoB client, or None if PoB is not running."""
    if not POB_CLIENT_AVAILABLE:
        return None
    try:
        client = PoBClient(timeout=2.0)
        if client.is_connected():
            return client
    except Exception:
        pass
    return None


def pob_is_running() -> bool:
    """Check if PoB is running and responsive."""
    client = get_pob_client()
    return client is not None


# Skip decorator for tests that require PoB
pob_required = pytest.mark.skipif(
    not pob_is_running(), reason="Path of Building is not running or MCP Bridge addon not installed"
)


class TestPoBConnection:
    """Test basic connection to PoB."""

    @pob_required
    def test_ping(self):
        """Test ping returns expected fields."""
        client = get_pob_client()
        result = client.ping()

        assert result["status"] == "ok"
        assert "version" in result
        assert "pob_version" in result
        assert "build_loaded" in result
        assert "uptime" in result

    @pob_required
    def test_status(self):
        """Test status returns server info."""
        client = get_pob_client()
        result = client.status()

        assert result["running"] is True
        assert "port" in result
        assert "host" in result
        assert result["host"] == "127.0.0.1"

    def test_connection_error_when_offline(self):
        """Test that connection error is raised when PoB is offline."""
        # Use a port that's definitely not PoB
        client = PoBClient(port=49999, timeout=0.5)
        with pytest.raises(PoBConnectionError):
            client.ping()


class TestPoBBuildCommands:
    """Test build-related commands."""

    @pob_required
    def test_get_build_when_loaded(self):
        """Test get_build returns build data when a build is loaded."""
        client = get_pob_client()
        ping_result = client.ping()

        if not ping_result.get("build_loaded"):
            pytest.skip("No build loaded in PoB")

        result = client.get_build(format="xml")
        assert "xml" in result
        assert "format" in result
        assert result["format"] == "xml"

    @pob_required
    def test_get_build_as_code(self):
        """Test get_build with code format."""
        client = get_pob_client()
        ping_result = client.ping()

        if not ping_result.get("build_loaded"):
            pytest.skip("No build loaded in PoB")

        result = client.get_build(format="code")
        assert "code" in result
        assert result["format"] == "pob_code"
        # PoB codes are base64-ish
        assert len(result["code"]) > 10


class TestPoBCalculations:
    """Test calculation commands."""

    @pob_required
    def test_get_calcs(self):
        """Test get_calcs returns expected fields."""
        client = get_pob_client()
        ping_result = client.ping()

        if not ping_result.get("build_loaded"):
            pytest.skip("No build loaded in PoB")

        result = client.get_calcs()

        # Character info
        assert "level" in result
        assert "class" in result

        # Offensive stats
        assert "TotalDPS" in result or "CombinedDPS" in result

        # Defensive stats
        assert "Life" in result

        # Resistances
        assert "FireResist" in result
        assert "ColdResist" in result
        assert "LightningResist" in result

    @pob_required
    def test_get_full_calcs(self):
        """Test get_full_calcs returns comprehensive data."""
        client = get_pob_client()
        ping_result = client.ping()

        if not ping_result.get("build_loaded"):
            pytest.skip("No build loaded in PoB")

        result = client.get_full_calcs()

        assert "main" in result
        assert "calcs" in result
        assert "summary" in result

        summary = result["summary"]
        assert "total_dps" in summary or summary.get("total_dps") is None
        assert "life" in summary

    @pob_required
    def test_get_defense_stats(self):
        """Test get_defense_stats returns defense data."""
        client = get_pob_client()
        ping_result = client.ping()

        if not ping_result.get("build_loaded"):
            pytest.skip("No build loaded in PoB")

        result = client.get_defense_stats()

        assert "life" in result
        assert "energy_shield" in result
        assert "armour" in result
        assert "resistances" in result

        # Check nested structure
        assert "total" in result["life"]
        assert "fire" in result["resistances"]

    @pob_required
    def test_get_skill_dps(self):
        """Test get_skill_dps returns skill breakdown."""
        client = get_pob_client()
        ping_result = client.ping()

        if not ping_result.get("build_loaded"):
            pytest.skip("No build loaded in PoB")

        result = client.get_skill_dps()

        assert "skills" in result
        assert "main_skill_index" in result
        assert isinstance(result["skills"], list)

    @pob_required
    def test_recalculate(self):
        """Test recalculate forces calculation refresh."""
        client = get_pob_client()
        ping_result = client.ping()

        if not ping_result.get("build_loaded"):
            pytest.skip("No build loaded in PoB")

        result = client.recalculate()
        assert result["success"] is True


class TestPoBSkillsAndTree:
    """Test skill and passive tree commands."""

    @pob_required
    def test_get_skills(self):
        """Test get_skills returns skill groups."""
        client = get_pob_client()
        ping_result = client.ping()

        if not ping_result.get("build_loaded"):
            pytest.skip("No build loaded in PoB")

        result = client.get_skills()

        assert "skillGroups" in result
        assert "mainSocketGroup" in result
        assert isinstance(result["skillGroups"], list)

    @pob_required
    def test_get_passive_tree(self):
        """Test get_passive_tree returns node data."""
        client = get_pob_client()
        ping_result = client.ping()

        if not ping_result.get("build_loaded"):
            pytest.skip("No build loaded in PoB")

        result = client.get_passive_tree()

        assert "class" in result
        assert "nodes" in result
        assert "totalPoints" in result
        assert isinstance(result["nodes"], list)


class TestPoBItems:
    """Test item commands."""

    @pob_required
    def test_get_items(self):
        """Test get_items returns equipped items."""
        client = get_pob_client()
        ping_result = client.ping()

        if not ping_result.get("build_loaded"):
            pytest.skip("No build loaded in PoB")

        result = client.get_items()

        assert "items" in result
        assert isinstance(result["items"], list)


class TestPoBConfig:
    """Test configuration commands."""

    @pob_required
    def test_get_config(self):
        """Test get_config returns build configuration."""
        client = get_pob_client()
        ping_result = client.ping()

        if not ping_result.get("build_loaded"):
            pytest.skip("No build loaded in PoB")

        result = client.get_config()
        assert "config" in result

    @pob_required
    def test_get_custom_mods(self):
        """Test get_custom_mods returns custom mod text."""
        client = get_pob_client()
        ping_result = client.ping()

        if not ping_result.get("build_loaded"):
            pytest.skip("No build loaded in PoB")

        result = client.get_custom_mods()
        assert "mods" in result


class TestPoBConvenienceMethods:
    """Test convenience methods on the client."""

    @pob_required
    def test_get_dps(self):
        """Test get_dps convenience method."""
        client = get_pob_client()
        ping_result = client.ping()

        if not ping_result.get("build_loaded"):
            pytest.skip("No build loaded in PoB")

        dps = client.get_dps()
        # DPS could be None if no skill is selected
        assert dps is None or isinstance(dps, (int, float))

    @pob_required
    def test_get_ehp(self):
        """Test get_ehp convenience method."""
        client = get_pob_client()
        ping_result = client.ping()

        if not ping_result.get("build_loaded"):
            pytest.skip("No build loaded in PoB")

        ehp = client.get_ehp()
        assert ehp is not None
        assert "life" in ehp
        assert "es" in ehp
        assert "armour" in ehp

    @pob_required
    def test_get_resistances(self):
        """Test get_resistances convenience method."""
        client = get_pob_client()
        ping_result = client.ping()

        if not ping_result.get("build_loaded"):
            pytest.skip("No build loaded in PoB")

        res = client.get_resistances()
        assert res is not None
        assert "fire" in res
        assert "cold" in res
        assert "lightning" in res
        assert "chaos" in res


class TestPoBWaitForBuild:
    """Test wait_for_build helper."""

    def test_wait_for_build_timeout(self):
        """Test wait_for_build returns False when build not loaded."""
        if not POB_CLIENT_AVAILABLE:
            pytest.skip("PoBClient not available")

        # Use wrong port to ensure it fails
        client = PoBClient(port=49999, timeout=0.1)
        result = client.wait_for_build(max_attempts=2, delay=0.05)
        assert result is False
