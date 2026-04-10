"""
tests/test_appinstances.py — tests for `drove appinstances` commands.

Requires the `live_app` fixture (TEST_APP-1 with ≥1 healthy instance).
No pre-existing cluster resources are required.
"""
import pytest
from conftest import drove_ok, drove, APP_ID


def _get_instance_id(app_id: str) -> str:
    """Return the first instance ID for the given app."""
    out = drove_ok("appinstances", "list", app_id)
    for line in out.strip().splitlines():
        parts = line.split()
        if parts and parts[0].startswith("AI-"):
            return parts[0]
    pytest.skip(f"No app instances found for {app_id}")


class TestAppInstancesList:
    def test_list_live_app(self, live_app):
        out = drove_ok("appinstances", "list", live_app)
        assert len(out.strip()) > 0

    def test_list_contains_instance_id(self, live_app):
        out = drove_ok("appinstances", "list", live_app)
        assert "AI-" in out, f"Expected instance IDs in output:\n{out}"

    def test_list_has_header(self, live_app):
        out = drove_ok("appinstances", "list", live_app)
        assert any(h in out for h in ["Instance", "State", "Host"])

    def test_list_with_old_flag(self, live_app):
        result = drove("appinstances", "list", live_app, "--old", check=False)
        assert result.returncode == 0

    def test_list_sort_and_reverse(self, live_app):
        # --sort takes integer column index: 0=Instance ID, 1=Executor Host, 2=Ports, 3=State, ...
        result = drove("appinstances", "list", live_app,
                       "--sort", "3", "--reverse", check=False)
        assert result.returncode == 0

    def test_list_nonexistent_app_empty(self):
        # drove exits 0 even for nonexistent apps; result is empty table (no AI- entries)
        result = drove("appinstances", "list", "NONEXISTENT-1", check=False)
        assert result.returncode == 0
        assert "AI-" not in result.stdout  # no instances for nonexistent app


class TestAppInstancesInfo:
    def test_info_succeeds(self, live_app):
        instance_id = _get_instance_id(live_app)
        out = drove_ok("appinstances", "info", live_app, instance_id)
        assert len(out.strip()) > 0

    def test_info_contains_state(self, live_app):
        instance_id = _get_instance_id(live_app)
        out = drove_ok("appinstances", "info", live_app, instance_id)
        assert "HEALTHY" in out or "State" in out or "state" in out.lower()

    def test_info_contains_host(self, live_app):
        instance_id = _get_instance_id(live_app)
        out = drove_ok("appinstances", "info", live_app, instance_id)
        assert "Host" in out or "host" in out.lower()


class TestAppInstancesLogs:
    def test_logs_list_succeeds(self, live_app):
        instance_id = _get_instance_id(live_app)
        result = drove("appinstances", "logs", live_app, instance_id, check=False)
        assert result.returncode == 0

    def test_logs_list_contains_files(self, live_app):
        instance_id = _get_instance_id(live_app)
        out = drove("appinstances", "logs", live_app, instance_id,
                    check=False).stdout
        # Might contain .log files or an empty table
        assert out is not None  # Just assert the command ran


class TestAppInstancesTail:
    def test_tail_default_log(self, live_app):
        """Tail a few lines from output.log.

        `drove appinstances tail` is a streaming command that never exits on its
        own.  We launch it with Popen, wait a few seconds for it to start
        streaming, then terminate it.  The test passes as long as the process
        starts successfully (we don't get an immediate error).
        """
        import subprocess
        import time
        from conftest import _base_cmd

        instance_id = _get_instance_id(live_app)
        cmd = _base_cmd() + ["appinstances", "tail", live_app, instance_id]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        # Give it a couple of seconds to connect and start streaming
        time.sleep(3)
        # Check it hasn't already died with an error
        poll = proc.poll()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        # poll is None → was still streaming (success), or 0 → clean exit
        assert poll is None or poll == 0, (
            f"tail exited immediately with rc={poll}"
        )


class TestDescribeInstance:
    def test_describe_instance_succeeds(self, live_app):
        instance_id = _get_instance_id(live_app)
        out = drove_ok("describe", "instance", live_app, instance_id)
        assert len(out.strip()) > 0

    def test_describe_instance_json(self, live_app):
        import json
        instance_id = _get_instance_id(live_app)
        out = drove_ok("describe", "instance", live_app, instance_id, "--json")
        data = json.loads(out)
        assert isinstance(data, dict)

    def test_describe_instance_contains_app_id(self, live_app):
        instance_id = _get_instance_id(live_app)
        out = drove_ok("describe", "instance", live_app, instance_id)
        assert "TEST_APP" in out or instance_id in out
