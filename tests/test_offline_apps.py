"""
tests/test_offline_apps.py — offline tests for `drove apps` and `drove describe app`
commands.

All tests use the mock Drove server; no live cluster is required.
Run with:  pytest -m offline tests/test_offline_apps.py
"""
import json
import pytest

pytestmark = pytest.mark.offline

# App IDs seeded in mock_server.py
EXISTING_APP  = "TEST_APP-1"
CLI_APP_ID    = "CLI_TEST_APP-1"
CLI_APP_SPEC  = None  # resolved at module level inside tests via FIXTURES_DIR


class TestOfflineAppsList:
    def test_apps_list_succeeds(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("apps", "list")
        assert len(out.strip()) > 0

    def test_apps_list_contains_known_app(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("apps", "list")
        assert "TEST_APP" in out, f"Expected TEST_APP in apps list:\n{out}"

    def test_apps_list_has_header_columns(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("apps", "list")
        for col in ["Id", "Name", "State"]:
            assert col in out, f"Column '{col}' missing from apps list:\n{out}"

    def test_apps_list_sort_by_name(self, offline_env):
        from conftest import drove
        result = drove("apps", "list", "--sort", "1", check=False)
        assert result.returncode == 0

    def test_apps_list_sort_reverse(self, offline_env):
        from conftest import drove
        result = drove("apps", "list", "--sort", "1", "--reverse", check=False)
        assert result.returncode == 0


class TestOfflineAppsSummary:
    def test_summary_existing_app(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("apps", "summary", EXISTING_APP)
        assert "TEST_APP" in out

    def test_summary_contains_state(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("apps", "summary", EXISTING_APP)
        assert "state" in out.lower()

    def test_summary_contains_instances(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("apps", "summary", EXISTING_APP)
        assert "Instance" in out or "instance" in out.lower()

    def test_summary_nonexistent_app_not_found(self, offline_env):
        from conftest import drove
        result = drove("apps", "summary", "NONEXISTENT_APP_XYZ-99", check=False)
        assert result.returncode == 0
        assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()


class TestOfflineAppsSpec:
    def test_spec_returns_json(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("apps", "spec", EXISTING_APP)
        data = json.loads(out)
        assert isinstance(data, dict)

    def test_spec_contains_name(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("apps", "spec", EXISTING_APP)
        data = json.loads(out)
        assert "name" in data

    def test_spec_contains_executable(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("apps", "spec", EXISTING_APP)
        data = json.loads(out)
        assert "executable" in data

    def test_spec_contains_resources(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("apps", "spec", EXISTING_APP)
        data = json.loads(out)
        assert "resources" in data


class TestOfflineDescribeApp:
    def test_describe_app_existing(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("describe", "app", EXISTING_APP)
        assert len(out.strip()) > 0

    def test_describe_app_json(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("describe", "app", EXISTING_APP, "--json")
        data = json.loads(out)
        assert isinstance(data, dict)

    def test_describe_app_nonexistent_not_found(self, offline_env):
        from conftest import drove
        result = drove("describe", "app", "NONEXISTENT_APP_XYZ-99", check=False)
        assert result.returncode == 0
        assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()


class TestOfflineAppsLifecycle:
    """
    Full create → scale → restart → suspend → destroy lifecycle via mock.

    Because the mock server is stateful (in-process dict), each operation is
    immediately visible to subsequent GETs — no polling delays needed.
    """

    def test_app_create(self, offline_env):
        from conftest import drove_ok, FIXTURES_DIR
        spec = str(FIXTURES_DIR / "cli_test_app.json")
        out = drove_ok("apps", "create", spec, timeout=10)
        # drove prints a success line or the app ID; either is fine
        assert len(out.strip()) >= 0  # just verify no crash

    def test_created_app_listed(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("apps", "list")
        assert CLI_APP_ID in out, f"{CLI_APP_ID} not in apps list:\n{out}"

    def test_app_scale_up(self, offline_env):
        from conftest import drove_ok
        drove_ok("apps", "scale", CLI_APP_ID, "2", timeout=10)
        out = drove_ok("apps", "summary", CLI_APP_ID)
        assert "RUNNING" in out

    def test_app_has_instances_after_scale(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("appinstances", "list", CLI_APP_ID)
        assert "AI-" in out, f"Expected app instance IDs:\n{out}"

    def test_app_describe_after_scale(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("describe", "app", CLI_APP_ID)
        assert CLI_APP_ID in out or "CLI_TEST_APP" in out

    def test_app_restart(self, offline_env):
        from conftest import drove_ok
        drove_ok("apps", "restart", CLI_APP_ID, timeout=10)
        out = drove_ok("apps", "summary", CLI_APP_ID)
        assert "RUNNING" in out

    def test_app_scale_down(self, offline_env):
        from conftest import drove_ok
        drove_ok("apps", "scale", CLI_APP_ID, "1", timeout=10)
        out = drove_ok("apps", "summary", CLI_APP_ID)
        assert "RUNNING" in out

    def test_app_suspend(self, offline_env):
        from conftest import drove_ok
        drove_ok("apps", "suspend", CLI_APP_ID, timeout=10)
        out = drove_ok("apps", "summary", CLI_APP_ID)
        assert "MONITORING" in out

    def test_app_destroy(self, offline_env):
        from conftest import drove
        # App is in MONITORING after suspend — destroy should succeed
        result = drove("apps", "destroy", CLI_APP_ID, check=False, timeout=10)
        assert result.returncode == 0

    def test_destroyed_app_not_listed(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("apps", "list")
        assert CLI_APP_ID not in out, f"{CLI_APP_ID} still appears after destroy"
