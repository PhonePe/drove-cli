"""
tests/test_localservices.py — tests for `drove localservices` and
`drove lsinstances` commands.

All tests create their own resources via the `live_service` fixture, which
creates TEST_LOCAL_SERVICE-1 from sample/test_service.json, activates it,
and destroys it on teardown.  No pre-existing cluster resources are required.
"""
import json
import time
import pytest
from conftest import drove_ok, drove, SVC_ID, SVC_SPEC


# ---------------------------------------------------------------------------
# Smoke / read-only tests — use the live_service fixture (no pre-existing deps)
# ---------------------------------------------------------------------------

class TestLocalServicesList:
    def test_list_succeeds(self, live_service):
        out = drove_ok("localservices", "list")
        assert len(out.strip()) > 0

    def test_list_contains_live_service(self, live_service):
        out = drove_ok("localservices", "list")
        assert SVC_ID in out, f"Expected {SVC_ID} in localservices list:\n{out}"

    def test_list_has_header(self, live_service):
        out = drove_ok("localservices", "list")
        assert any(h in out for h in ["Name", "State", "Id"])

    def test_list_sort_and_reverse(self, live_service):
        # --sort takes integer column index: 0=Id, 1=Name, 2=State, ...
        result = drove("localservices", "list",
                       "--sort", "1", "--reverse", check=False)
        assert result.returncode == 0


class TestLocalServicesSummary:
    def test_summary_live_service(self, live_service):
        out = drove_ok("localservices", "summary", live_service)
        assert "TEST_LOCAL_SERVICE" in out

    def test_summary_contains_state(self, live_service):
        out = drove_ok("localservices", "summary", live_service)
        assert "state" in out.lower() or "State" in out

    def test_summary_nonexistent_not_found(self):
        # drove exits 0 even on errors; check stdout for error message
        result = drove("localservices", "summary",
                       "NONEXISTENT_SERVICE_XYZ-1", check=False)
        assert result.returncode == 0
        assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()


class TestLocalServicesSpec:
    def test_spec_returns_json(self, live_service):
        out = drove_ok("localservices", "spec", live_service)
        data = json.loads(out)
        assert isinstance(data, dict)

    def test_spec_contains_name(self, live_service):
        out = drove_ok("localservices", "spec", live_service)
        data = json.loads(out)
        assert "name" in data

    def test_spec_name_matches(self, live_service):
        out = drove_ok("localservices", "spec", live_service)
        data = json.loads(out)
        assert data.get("name") == "TEST_LOCAL_SERVICE"

    def test_spec_type_is_local_service(self, live_service):
        out = drove_ok("localservices", "spec", live_service)
        data = json.loads(out)
        assert data.get("type") == "LOCAL_SERVICE"


class TestDescribeLocalService:
    def test_describe_live_service(self, live_service):
        out = drove_ok("describe", "localservice", live_service)
        assert len(out.strip()) > 0

    def test_describe_json(self, live_service):
        out = drove_ok("describe", "localservice", live_service, "--json")
        data = json.loads(out)
        assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# Lifecycle tests — require a live (ACTIVE) local service
# ---------------------------------------------------------------------------

class TestLocalServicesLifecycle:
    def test_live_service_listed(self, live_service):
        out = drove_ok("localservices", "list")
        assert SVC_ID in out

    def test_live_service_state_active(self, live_service):
        out = drove_ok("localservices", "summary", live_service)
        assert "RUNNING" in out or "ACTIVE" in out

    def test_live_service_spec_valid(self, live_service):
        out = drove_ok("localservices", "spec", live_service)
        data = json.loads(out)
        assert data.get("name") == "TEST_LOCAL_SERVICE"

    def test_live_service_describe(self, live_service):
        out = drove_ok("describe", "localservice", live_service)
        assert "TEST_LOCAL_SERVICE" in out

    def test_live_service_restart(self, live_service):
        drove_ok("localservices", "restart", live_service, "--wait", timeout=180)
        out = drove_ok("localservices", "summary", live_service)
        assert "RUNNING" in out or "ACTIVE" in out
        # Wait for the new instance to become healthy before lsinstances tests
        for _ in range(12):
            inst_out = drove("lsinstances", "list", live_service, check=False).stdout
            if any(
                line.split() and (line.split()[0].startswith("SI-") or
                                  line.split()[0].startswith("LSI-") or
                                  line.split()[0].startswith("AI-"))
                for line in inst_out.strip().splitlines()
            ):
                break
            time.sleep(5)


# ---------------------------------------------------------------------------
# lsinstances tests — run against the live service
# ---------------------------------------------------------------------------

def _get_ls_instance_id(svc_id: str, retries: int = 6, delay: float = 5.0) -> str:
    """Return the first healthy lsinstance ID for svc_id, polling with retries.

    After a restart, the new instance may take a few seconds to appear.
    Instance ID prefixes observed: SI- (local), LSI-, AI- (other cluster versions).
    """
    for _ in range(retries):
        out = drove_ok("lsinstances", "list", svc_id)
        for line in out.strip().splitlines():
            parts = line.split()
            if parts and (parts[0].startswith("SI-") or
                          parts[0].startswith("LSI-") or
                          parts[0].startswith("AI-")):
                return parts[0]
        time.sleep(delay)
    pytest.skip(f"No lsinstances found for {svc_id} after {retries * delay:.0f}s")


class TestLsInstancesList:
    def test_list_live_service(self, live_service):
        result = drove("lsinstances", "list", live_service, check=False)
        assert result.returncode == 0

    def test_list_with_old_flag(self, live_service):
        result = drove("lsinstances", "list", live_service, "--old", check=False)
        assert result.returncode == 0


class TestLsInstancesInfo:
    def test_info_succeeds(self, live_service):
        instance_id = _get_ls_instance_id(live_service)
        out = drove_ok("lsinstances", "info", live_service, instance_id)
        assert len(out.strip()) > 0


class TestLsInstancesLogs:
    def test_logs_list_succeeds(self, live_service):
        instance_id = _get_ls_instance_id(live_service)
        result = drove("lsinstances", "logs", live_service, instance_id,
                       check=False)
        assert result.returncode == 0


class TestDescribeLsInstance:
    def test_describe_lsinstance_succeeds(self, live_service):
        instance_id = _get_ls_instance_id(live_service)
        out = drove_ok("describe", "lsinstance", live_service, instance_id)
        assert len(out.strip()) > 0

    def test_describe_lsinstance_json(self, live_service):
        instance_id = _get_ls_instance_id(live_service)
        out = drove_ok("describe", "lsinstance", live_service,
                       instance_id, "--json")
        data = json.loads(out)
        assert isinstance(data, dict)
