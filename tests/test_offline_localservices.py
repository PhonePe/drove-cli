"""
tests/test_offline_localservices.py — offline tests for `drove localservices`,
`drove lsinstances`, and `drove describe localservice/lsinstance` commands.

All tests use the mock Drove server; no live cluster is required.
Run with:  pytest -m offline tests/test_offline_localservices.py

The mock server seeds TEST_LOCAL_SERVICE-1 in INACTIVE state.
Lifecycle tests create CLI_TEST_SERVICE-1 via the fixtures spec.
"""
import json
import pytest

pytestmark = pytest.mark.offline

EXISTING_SVC = "TEST_LOCAL_SERVICE-1"
CLI_SVC_ID   = "CLI_TEST_SERVICE-1"


# ---------------------------------------------------------------------------
# Smoke / read-only tests against the seeded inactive service
# ---------------------------------------------------------------------------

class TestOfflineLocalServicesList:
    def test_list_succeeds(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("localservices", "list")
        assert len(out.strip()) > 0

    def test_list_contains_known_service(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("localservices", "list")
        assert "TEST_LOCAL_SERVICE" in out

    def test_list_has_header(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("localservices", "list")
        assert any(h in out for h in ["Name", "State", "Id"])

    def test_list_sort_and_reverse(self, offline_env):
        from conftest import drove
        result = drove("localservices", "list",
                       "--sort", "1", "--reverse", check=False)
        assert result.returncode == 0


class TestOfflineLocalServicesSummary:
    def test_summary_existing_service(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("localservices", "summary", EXISTING_SVC)
        assert "TEST_LOCAL_SERVICE" in out

    def test_summary_contains_state(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("localservices", "summary", EXISTING_SVC)
        assert "state" in out.lower() or "State" in out

    def test_summary_nonexistent_not_found(self, offline_env):
        from conftest import drove
        result = drove("localservices", "summary",
                       "NONEXISTENT_SERVICE_XYZ-99", check=False)
        assert result.returncode == 0
        assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()


class TestOfflineLocalServicesSpec:
    def test_spec_returns_json(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("localservices", "spec", EXISTING_SVC)
        data = json.loads(out)
        assert isinstance(data, dict)

    def test_spec_contains_name(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("localservices", "spec", EXISTING_SVC)
        data = json.loads(out)
        assert "name" in data

    def test_spec_type_is_local_service(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("localservices", "spec", EXISTING_SVC)
        data = json.loads(out)
        assert data.get("type") == "LOCAL_SERVICE"


class TestOfflineDescribeLocalService:
    def test_describe_existing_service(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("describe", "localservice", EXISTING_SVC)
        assert len(out.strip()) > 0

    def test_describe_json(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("describe", "localservice", EXISTING_SVC, "--json")
        data = json.loads(out)
        assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# Lifecycle tests — create → activate → inspect → restart → deactivate → destroy
# ---------------------------------------------------------------------------

class TestOfflineLocalServicesLifecycle:
    def test_service_create(self, offline_env):
        from conftest import drove_ok, FIXTURES_DIR
        spec = str(FIXTURES_DIR / "cli_test_service.json")
        drove_ok("localservices", "create", spec, timeout=10)

    def test_created_service_listed(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("localservices", "list")
        assert CLI_SVC_ID in out, f"{CLI_SVC_ID} not in list:\n{out}"

    def test_service_activate(self, offline_env):
        from conftest import drove_ok
        drove_ok("localservices", "activate", CLI_SVC_ID, timeout=10)

    def test_service_active_after_activate(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("localservices", "summary", CLI_SVC_ID)
        assert "ACTIVE" in out, f"Expected ACTIVE state:\n{out}"

    def test_service_has_instances(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("lsinstances", "list", CLI_SVC_ID)
        assert "SI-" in out, f"Expected SI- instance IDs:\n{out}"

    def test_service_spec_valid(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("localservices", "spec", CLI_SVC_ID)
        data = json.loads(out)
        assert data.get("name") == "CLI_TEST_SERVICE"

    def test_service_describe(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("describe", "localservice", CLI_SVC_ID)
        assert "CLI_TEST_SERVICE" in out

    def test_service_restart(self, offline_env):
        from conftest import drove_ok
        drove_ok("localservices", "restart", CLI_SVC_ID, timeout=10)
        out = drove_ok("localservices", "summary", CLI_SVC_ID)
        assert "ACTIVE" in out, f"Expected ACTIVE after restart:\n{out}"

    def test_service_deactivate(self, offline_env):
        from conftest import drove_ok
        drove_ok("localservices", "deactivate", CLI_SVC_ID, timeout=10)
        out = drove_ok("localservices", "summary", CLI_SVC_ID)
        assert "INACTIVE" in out, f"Expected INACTIVE after deactivate:\n{out}"

    def test_service_destroy(self, offline_env):
        from conftest import drove
        result = drove("localservices", "destroy", CLI_SVC_ID,
                       check=False, timeout=10)
        assert result.returncode == 0

    def test_destroyed_service_not_listed(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("localservices", "list")
        assert CLI_SVC_ID not in out, f"{CLI_SVC_ID} still listed after destroy"


# ---------------------------------------------------------------------------
# lsinstances tests against the seeded active service
# (re-activate EXISTING_SVC for instance inspection)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="class")
def seeded_active_svc(offline_env):
    """Activate the seeded service and return its ID; deactivate after."""
    from conftest import drove_ok, drove
    drove_ok("localservices", "activate", EXISTING_SVC, timeout=10)
    yield EXISTING_SVC
    drove("localservices", "deactivate", EXISTING_SVC, check=False, timeout=10)


class TestOfflineLsInstancesList:
    def test_list_active_service(self, seeded_active_svc):
        from conftest import drove
        result = drove("lsinstances", "list", seeded_active_svc, check=False)
        assert result.returncode == 0

    def test_list_contains_instance(self, seeded_active_svc):
        from conftest import drove_ok
        out = drove_ok("lsinstances", "list", seeded_active_svc)
        assert "SI-" in out, f"Expected SI- instance IDs:\n{out}"

    def test_list_with_old_flag(self, seeded_active_svc):
        from conftest import drove
        result = drove("lsinstances", "list", seeded_active_svc,
                       "--old", check=False)
        assert result.returncode == 0


def _get_ls_instance_id(svc_id: str) -> str:
    from conftest import drove_ok
    out = drove_ok("lsinstances", "list", svc_id)
    for line in out.strip().splitlines():
        parts = line.split()
        if parts and parts[0].startswith("SI-"):
            return parts[0]
    pytest.skip(f"No lsinstances found for {svc_id} in mock")


class TestOfflineLsInstancesInfo:
    def test_info_succeeds(self, seeded_active_svc):
        inst_id = _get_ls_instance_id(seeded_active_svc)
        from conftest import drove_ok
        out = drove_ok("lsinstances", "info", seeded_active_svc, inst_id)
        assert len(out.strip()) > 0


class TestOfflineLsInstancesLogs:
    def test_logs_list_succeeds(self, seeded_active_svc):
        inst_id = _get_ls_instance_id(seeded_active_svc)
        from conftest import drove
        result = drove("lsinstances", "logs", seeded_active_svc, inst_id,
                       check=False)
        assert result.returncode == 0


class TestOfflineDescribeLsInstance:
    def test_describe_lsinstance_succeeds(self, seeded_active_svc):
        inst_id = _get_ls_instance_id(seeded_active_svc)
        from conftest import drove_ok
        out = drove_ok("describe", "lsinstance", seeded_active_svc, inst_id)
        assert len(out.strip()) > 0

    def test_describe_lsinstance_json(self, seeded_active_svc):
        inst_id = _get_ls_instance_id(seeded_active_svc)
        from conftest import drove_ok
        out = drove_ok("describe", "lsinstance", seeded_active_svc,
                       inst_id, "--json")
        data = json.loads(out)
        assert isinstance(data, dict)
