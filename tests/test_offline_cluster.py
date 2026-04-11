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
