"""
tests/test_cluster.py — tests for `drove cluster` commands.

Covers: ping, summary, leader, endpoints, describe cluster
All tests are smoke/read-only (no mutation).
"""
import pytest
from conftest import drove_ok, drove


# ---------------------------------------------------------------------------
# drove cluster ping
# ---------------------------------------------------------------------------

class TestClusterPing:
    def test_ping_succeeds(self):
        out = drove_ok("cluster", "ping")
        assert "ping successful" in out.lower(), f"Unexpected output: {out}"

    def test_ping_exit_code(self):
        result = drove("cluster", "ping", check=False)
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# drove cluster summary
# ---------------------------------------------------------------------------

class TestClusterSummary:
    def test_summary_contains_state(self):
        out = drove_ok("cluster", "summary")
        assert "State" in out

    def test_summary_contains_leader(self):
        out = drove_ok("cluster", "summary")
        assert "Leader" in out

    def test_summary_contains_cores(self):
        out = drove_ok("cluster", "summary")
        assert "Cores" in out or "CPU" in out

    def test_summary_contains_memory(self):
        out = drove_ok("cluster", "summary")
        assert "Memory" in out

    def test_summary_contains_executors(self):
        out = drove_ok("cluster", "summary")
        assert "executor" in out.lower()

    def test_summary_contains_applications(self):
        out = drove_ok("cluster", "summary")
        assert "Application" in out


# ---------------------------------------------------------------------------
# drove cluster leader
# ---------------------------------------------------------------------------

class TestClusterLeader:
    def test_leader_returns_output(self):
        out = drove_ok("cluster", "leader")
        assert len(out.strip()) > 0, "Leader command returned empty output"


# ---------------------------------------------------------------------------
# drove cluster endpoints
# ---------------------------------------------------------------------------

class TestClusterEndpoints:
    def test_endpoints_succeeds(self):
        # May return empty table if no apps are exposed, but should not fail
        result = drove("cluster", "endpoints", check=False)
        assert result.returncode == 0

    def test_endpoints_with_vhost_filter(self):
        result = drove("cluster", "endpoints", "--vhost", "nonexistent.local", check=False)
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# drove describe cluster
# ---------------------------------------------------------------------------

class TestDescribeCluster:
    def test_describe_cluster_contains_overview(self):
        out = drove_ok("describe", "cluster")
        assert "Cluster" in out or "State" in out

    def test_describe_cluster_json(self):
        import json
        out = drove_ok("describe", "cluster", "--json")
        data = json.loads(out)
        assert isinstance(data, dict), "Expected JSON object"

    def test_describe_cluster_contains_executors(self):
        out = drove_ok("describe", "cluster")
        assert "Executor" in out or "exec" in out.lower()
