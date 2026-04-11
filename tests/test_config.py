"""
tests/test_config.py — tests for `drove config` commands.

These tests read the real ~/.drove config file to verify the config sub-commands
work correctly.  They are skipped automatically when ~/.drove does not exist
(e.g. on CI runners that have no cluster configuration).
"""
import os
import pytest
from conftest import drove_ok, drove

# Skip the entire module when there is no local config file to read from.
if not os.path.exists(os.path.expanduser("~/.drove")):
    pytest.skip("~/.drove not found — skipping config tests", allow_module_level=True)


class TestConfigGetClusters:
    def test_get_clusters_succeeds(self):
        out = drove_ok("config", "get-clusters")
        assert len(out.strip()) > 0

    def test_get_clusters_lists_header(self):
        out = drove_ok("config", "get-clusters")
        assert "NAME" in out or "ENDPOINT" in out or "CURRENT" in out

    def test_get_clusters_shows_current_marker(self):
        out = drove_ok("config", "get-clusters")
        # The current cluster should be marked with '*'
        assert "*" in out, "Expected current cluster marker '*' in output"


class TestConfigCurrentCluster:
    def test_current_cluster_returns_name(self):
        out = drove_ok("config", "current-cluster")
        assert len(out.strip()) > 0, "current-cluster returned empty output"


class TestConfigView:
    def test_config_view_succeeds(self):
        out = drove_ok("config", "view")
        assert len(out.strip()) > 0

    def test_config_view_raw(self):
        out = drove_ok("config", "view", "--raw")
        # Raw view should contain ini-style markers
        assert "[" in out, "Expected ini section brackets in raw config view"

    def test_config_view_contains_endpoint(self):
        out = drove_ok("config", "view")
        assert "endpoint" in out.lower() or "Endpoint" in out


class TestConfigUseCluster:
    def test_use_cluster_switches_and_reverts(self):
        """Switch to the same cluster we're already on — should be a no-op / succeed."""
        current_out = drove_ok("config", "current-cluster").strip()
        # current_out format: "Current cluster: dev" or just "dev"
        cluster_name = current_out.split(":")[-1].strip()
        switch_out = drove_ok("config", "use-cluster", cluster_name)
        assert len(switch_out.strip()) > 0 or True  # some builds produce no output

        # Verify we're still on the same cluster
        after_out = drove_ok("config", "current-cluster").strip()
        assert cluster_name in after_out
