"""
tests/test_offline_appinstances.py — offline tests for `drove appinstances` and
`drove describe instance` commands.

All tests use the mock Drove server; no live cluster is required.
Run with:  pytest -m offline tests/test_offline_appinstances.py

The mock server seeds TEST_APP-1 with one HEALTHY instance (AI-test-app-inst-001).
"""
import json
import pytest

pytestmark = pytest.mark.offline

SEEDED_APP_ID   = "TEST_APP-1"
SEEDED_INST_ID  = "AI-test-app-inst-001"


def _get_instance_id(app_id: str) -> str:
    """Return the first AI- instance ID for the given app from mock server."""
    from conftest import drove_ok
    out = drove_ok("appinstances", "list", app_id)
    for line in out.strip().splitlines():
        parts = line.split()
        if parts and parts[0].startswith("AI-"):
            return parts[0]
    pytest.skip(f"No app instances found for {app_id} in mock")


class TestOfflineAppInstancesList:
    def test_list_seeded_app(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("appinstances", "list", SEEDED_APP_ID)
        assert len(out.strip()) > 0

    def test_list_contains_instance_id(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("appinstances", "list", SEEDED_APP_ID)
        assert "AI-" in out, f"Expected AI- instance IDs:\n{out}"

    def test_list_has_header(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("appinstances", "list", SEEDED_APP_ID)
        assert any(h in out for h in ["Instance", "State", "Host"])

    def test_list_with_old_flag(self, offline_env):
        from conftest import drove
        result = drove("appinstances", "list", SEEDED_APP_ID, "--old", check=False)
        assert result.returncode == 0

    def test_list_sort_and_reverse(self, offline_env):
        from conftest import drove
        result = drove("appinstances", "list", SEEDED_APP_ID,
                       "--sort", "3", "--reverse", check=False)
        assert result.returncode == 0

    def test_list_nonexistent_app_empty(self, offline_env):
        from conftest import drove
        result = drove("appinstances", "list", "NONEXISTENT-99", check=False)
        assert result.returncode == 0
        assert "AI-" not in result.stdout


class TestOfflineAppInstancesInfo:
    def test_info_succeeds(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("appinstances", "info", SEEDED_APP_ID, SEEDED_INST_ID)
        assert len(out.strip()) > 0

    def test_info_contains_state(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("appinstances", "info", SEEDED_APP_ID, SEEDED_INST_ID)
        assert "HEALTHY" in out or "State" in out or "state" in out.lower()

    def test_info_contains_host(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("appinstances", "info", SEEDED_APP_ID, SEEDED_INST_ID)
        assert "Host" in out or "host" in out.lower()


class TestOfflineAppInstancesLogs:
    def test_logs_list_succeeds(self, offline_env):
        from conftest import drove
        result = drove("appinstances", "logs", SEEDED_APP_ID, SEEDED_INST_ID,
                       check=False)
        assert result.returncode == 0


class TestOfflineDescribeInstance:
    def test_describe_instance_succeeds(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("describe", "instance", SEEDED_APP_ID, SEEDED_INST_ID)
        assert len(out.strip()) > 0

    def test_describe_instance_json(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("describe", "instance", SEEDED_APP_ID, SEEDED_INST_ID,
                       "--json")
        data = json.loads(out)
        assert isinstance(data, dict)

    def test_describe_instance_contains_app_id(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("describe", "instance", SEEDED_APP_ID, SEEDED_INST_ID)
        assert "TEST_APP" in out or SEEDED_INST_ID in out
