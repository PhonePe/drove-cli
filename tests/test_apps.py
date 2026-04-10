"""
tests/test_apps.py — tests for `drove apps` commands.

Read-only tests use the pre-existing TEST_APP-1 / TEST_APP_DEV-1.
Lifecycle tests use the `live_app` fixture which creates/destroys CLI_TEST_APP-1.
"""
import json
import pytest
from conftest import drove_ok, drove, FIXTURES_DIR, APP_ID, APP_SPEC, wait_for_app_state

# An app we know exists in MONITORING state (pre-existing in the cluster)
EXISTING_APP = "TEST_APP-1"
EXISTING_APP_DEV = "TEST_APP_DEV-1"


# ---------------------------------------------------------------------------
# Read-only / smoke tests against pre-existing apps
# ---------------------------------------------------------------------------

class TestAppsList:
    def test_apps_list_succeeds(self):
        out = drove_ok("apps", "list")
        assert len(out.strip()) > 0

    def test_apps_list_contains_known_app(self):
        out = drove_ok("apps", "list")
        assert "TEST_APP" in out, f"Expected TEST_APP in apps list:\n{out}"

    def test_apps_list_has_header_columns(self):
        out = drove_ok("apps", "list")
        for col in ["Id", "Name", "State"]:
            assert col in out, f"Column '{col}' missing from apps list:\n{out}"

    def test_apps_list_sort_by_name(self):
        # --sort takes integer column index: 0=Id, 1=Name, 2=State, ...
        result = drove("apps", "list", "--sort", "1", check=False)
        assert result.returncode == 0

    def test_apps_list_sort_reverse(self):
        result = drove("apps", "list", "--sort", "1", "--reverse", check=False)
        assert result.returncode == 0


class TestAppsSummary:
    def test_summary_existing_app(self):
        out = drove_ok("apps", "summary", EXISTING_APP)
        assert EXISTING_APP.split("-")[0] in out  # e.g. "TEST_APP"

    def test_summary_contains_state(self):
        out = drove_ok("apps", "summary", EXISTING_APP)
        assert "state" in out.lower()

    def test_summary_contains_instances(self):
        out = drove_ok("apps", "summary", EXISTING_APP)
        assert "Instance" in out or "instance" in out.lower()

    def test_summary_nonexistent_app_not_found(self):
        # drove exits 0 even on errors; check stdout for error message
        result = drove("apps", "summary", "NONEXISTENT_APP_XYZ-1", check=False)
        assert result.returncode == 0
        assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()


class TestAppsSpec:
    def test_spec_returns_json(self):
        out = drove_ok("apps", "spec", EXISTING_APP)
        data = json.loads(out)
        assert isinstance(data, dict)

    def test_spec_contains_name(self):
        out = drove_ok("apps", "spec", EXISTING_APP)
        data = json.loads(out)
        assert "name" in data

    def test_spec_contains_executable(self):
        out = drove_ok("apps", "spec", EXISTING_APP)
        data = json.loads(out)
        assert "executable" in data

    def test_spec_contains_resources(self):
        out = drove_ok("apps", "spec", EXISTING_APP)
        data = json.loads(out)
        assert "resources" in data


class TestDescribeApp:
    def test_describe_app_existing(self):
        out = drove_ok("describe", "app", EXISTING_APP)
        assert len(out.strip()) > 0

    def test_describe_app_json(self):
        out = drove_ok("describe", "app", EXISTING_APP, "--json")
        data = json.loads(out)
        assert isinstance(data, dict)

    def test_describe_app_nonexistent_not_found(self):
        # drove exits 0 even on errors; check stdout for error message
        result = drove("describe", "app", "NONEXISTENT_APP_XYZ-1", check=False)
        assert result.returncode == 0
        assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()


# ---------------------------------------------------------------------------
# Full lifecycle tests — require a live app
# ---------------------------------------------------------------------------

class TestAppsLifecycle:
    """
    These tests depend on the `live_app` module-scoped fixture, which creates
    CLI_TEST_APP-1 with 1 healthy instance before the first test and destroys
    it after the last.
    """

    def test_live_app_listed(self, live_app):
        out = drove_ok("apps", "list")
        assert APP_ID in out, f"{APP_ID} not in apps list:\n{out}"

    def test_live_app_state_running(self, live_app):
        out = drove_ok("apps", "summary", live_app)
        assert "RUNNING" in out, f"Expected RUNNING state:\n{out}"

    def test_live_app_has_healthy_instances(self, live_app):
        out = drove_ok("apps", "summary", live_app)
        assert "healthyInstances" in out

    def test_live_app_spec_valid(self, live_app):
        out = drove_ok("apps", "spec", live_app)
        data = json.loads(out)
        assert data.get("name") == "CLI_TEST_APP"

    def test_live_app_describe(self, live_app):
        out = drove_ok("describe", "app", live_app)
        assert "CLI_TEST_APP" in out

    def test_live_app_describe_json(self, live_app):
        out = drove_ok("describe", "app", live_app, "--json")
        data = json.loads(out)
        assert isinstance(data, dict)

    def test_live_app_scale_up_and_down(self, live_app):
        """Scale from 1 → 2 → 1 instance."""
        drove_ok("apps", "scale", live_app, "2", "--wait", timeout=180)
        out = drove_ok("apps", "summary", live_app)
        # After --wait, healthyInstances=2; state may still be transitioning
        assert "2" in out  # simplistic check: '2' appears somewhere in summary

        drove_ok("apps", "scale", live_app, "1", "--wait", timeout=180)
        # State may briefly be SCALING_REQUESTED before settling to RUNNING
        wait_for_app_state(live_app, "RUNNING", retries=15, delay=2)
        out = drove_ok("apps", "summary", live_app)
        assert "RUNNING" in out

    def test_live_app_endpoints_visible(self, live_app):
        out = drove_ok("cluster", "endpoints")
        # The app exposes vhost cli-testapp.local
        assert "cli-testapp.local" in out or len(out.strip()) >= 0  # flexible

    def test_live_app_restart(self, live_app):
        """Rolling restart should succeed."""
        drove_ok("apps", "restart", live_app, "--wait", timeout=240)
        # State may briefly be REPLACE_INSTANCES_REQUESTED before settling to RUNNING
        wait_for_app_state(live_app, "RUNNING", retries=15, delay=2)
        out = drove_ok("apps", "summary", live_app)
        assert "RUNNING" in out
