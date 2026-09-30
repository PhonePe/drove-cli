"""
tests/test_offline_cluster.py — offline tests for `drove cluster` commands.

All tests use the mock Drove server; no live cluster is required.
Run with:  pytest -m offline tests/test_offline_cluster.py
"""
import json
import pytest

pytestmark = pytest.mark.offline


class TestOfflineClusterPing:
    def test_ping_succeeds(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("cluster", "ping")
        assert "ping successful" in out.lower(), f"Unexpected output: {out}"

    def test_ping_exit_code(self, offline_env):
        from conftest import drove
        result = drove("cluster", "ping", check=False)
        assert result.returncode == 0


class TestOfflineClusterSummary:
    def test_summary_contains_state(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("cluster", "summary")
        assert "State" in out

    def test_summary_contains_leader(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("cluster", "summary")
        assert "Leader" in out

    def test_summary_contains_cores(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("cluster", "summary")
        assert "Cores" in out or "CPU" in out

    def test_summary_contains_memory(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("cluster", "summary")
        assert "Memory" in out

    def test_summary_contains_executors(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("cluster", "summary")
        assert "executor" in out.lower()

    def test_summary_contains_applications(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("cluster", "summary")
        assert "Application" in out


class TestOfflineClusterLeader:
    def test_leader_returns_output(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("cluster", "leader")
        assert len(out.strip()) > 0, "Leader command returned empty output"


class TestOfflineClusterEndpoints:
    def test_endpoints_succeeds(self, offline_env):
        from conftest import drove
        result = drove("cluster", "endpoints", check=False)
        assert result.returncode == 0

    def test_endpoints_with_vhost_filter(self, offline_env):
        from conftest import drove
        result = drove("cluster", "endpoints", "--vhost", "nonexistent.local", check=False)
        assert result.returncode == 0

    def test_endpoints_shows_exposed_app(self, offline_env):
        """The seed TEST_APP-1 exposes testapp.local — should appear."""
        from conftest import drove_ok
        out = drove_ok("cluster", "endpoints")
        assert "testapp.local" in out


class TestOfflineDescribeCluster:
    def test_describe_cluster_contains_overview(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("describe", "cluster")
        assert "Cluster" in out or "State" in out

    def test_describe_cluster_json(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("describe", "cluster", "--json")
        data = json.loads(out)
        assert isinstance(data, dict)

    def test_describe_cluster_contains_executors(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("describe", "cluster")
        assert "Executor" in out or "exec" in out.lower()


class TestOfflineClusterSimulatePlacement:
    """Offline tests for `drove cluster simulate-placement`."""

    SIM_SPEC = {
        "type": "COMPUTATION",
        "sourceAppName": "TEST_APP",
        "taskId": "SIM001",
        "executable": {
            "type": "DOCKER",
            "url": "ghcr.io/appform-io/test-task",
            "dockerPullTimeout": "100 seconds",
        },
        "resources": [
            {"type": "CPU", "count": 1},
            {"type": "MEMORY", "sizeInMB": 512},
        ],
        "placementPolicy": {"type": "ANY"},
    }

    @pytest.fixture()
    def sim_spec_file(self, tmp_path):
        spec_file = tmp_path / "sim_task.json"
        spec_file.write_text(json.dumps(self.SIM_SPEC))
        return str(spec_file)

    def test_simulate_placement_succeeds(self, offline_env, sim_spec_file):
        from conftest import drove_ok
        out = drove_ok("cluster", "simulate-placement", sim_spec_file,
                       "--num-instances", "2")
        assert "Requested instances: 2" in out, f"Unexpected output: {out}"
        assert "Placed instances:    2" in out, f"Unexpected output: {out}"
        assert "Errors:              0" in out, f"Unexpected output: {out}"

    def test_simulate_placement_default_one_instance(self, offline_env, sim_spec_file):
        from conftest import drove_ok
        out = drove_ok("cluster", "simulate-placement", sim_spec_file)
        assert "Requested instances: 1" in out, f"Unexpected output: {out}"

    def test_simulate_placement_detail_shows_placements(self, offline_env, sim_spec_file):
        from conftest import drove_ok
        out = drove_ok("cluster", "simulate-placement", sim_spec_file,
                      "--num-instances", "2", "--detail")
        assert "Executor Id" in out, f"Expected placement table in output: {out}"
        assert "exec-host-1" in out, f"Expected seed executor in placements: {out}"

    def test_simulate_placement_json_output(self, offline_env, sim_spec_file):
        from conftest import drove_ok
        out = drove_ok("cluster", "simulate-placement", sim_spec_file,
                       "--num-instances", "2", "--json")
        data = json.loads(out)
        assert data["requested"] == 2
        assert data["placed"] == 2
        assert data["errors"] == []
        assert data["placements"] == []

    def test_simulate_placement_json_detail_has_placements(self, offline_env, sim_spec_file):
        from conftest import drove_ok
        out = drove_ok("cluster", "simulate-placement", sim_spec_file,
                       "--num-instances", "2", "--detail", "--json")
        data = json.loads(out)
        assert len(data["placements"]) == 2
        placement = data["placements"][0]
        assert placement["hostname"] == "exec-host-1"
        assert placement["executorState"] == "ACTIVE"

    def test_simulate_placement_over_capacity_reports_shortfall(self, offline_env, sim_spec_file):
        """Seed executor: 8 free cores, 2048 MB. One instance needs 1 core,
        512 MB — so at most 4 instances can be placed."""
        from conftest import drove_ok
        out = drove_ok("cluster", "simulate-placement", sim_spec_file,
                       "--num-instances", "100")
        assert "Placed instances:    4" in out, f"Unexpected output: {out}"
        assert "Cluster can place only 4 of 100" in out, f"Unexpected output: {out}"

    def test_simulate_placement_spec_without_type_fails(self, offline_env, tmp_path):
        from conftest import drove_ok
        bad_spec = {k: v for k, v in self.SIM_SPEC.items() if k != "type"}
        bad_spec_file = tmp_path / "bad_sim_spec.json"
        bad_spec_file.write_text(json.dumps(bad_spec))
        out = drove_ok("cluster", "simulate-placement", str(bad_spec_file))
        assert "Placement simulation failed" in out, f"Unexpected output: {out}"

    def test_simulate_placement_missing_file_fails(self, offline_env, tmp_path):
        from conftest import drove_ok
        missing_file = tmp_path / "no_such_spec.json"
        out = drove_ok("cluster", "simulate-placement", str(missing_file))
        assert "Error reading simulation input" in out, f"Unexpected output: {out}"
