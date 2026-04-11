"""
tests/test_executor.py — tests for `drove executor` commands.

All tests are read-only (no blacklisting in automated tests to avoid
impacting the cluster).
"""
import pytest
from conftest import drove_ok, drove


class TestExecutorList:
    def test_executor_list_succeeds(self):
        out = drove_ok("executor", "list")
        assert len(out.strip()) > 0

    def test_executor_list_has_header(self):
        out = drove_ok("executor", "list")
        header_keywords = ["Executor", "Host", "Port", "Cores", "Memory", "State"]
        assert any(kw in out for kw in header_keywords), (
            f"None of {header_keywords} found in output:\n{out}"
        )

    def test_executor_list_has_at_least_one_executor(self):
        out = drove_ok("executor", "list")
        lines = [l for l in out.strip().splitlines() if l.strip()]
        # Should have at least a header + one data row
        assert len(lines) >= 2, "Expected at least one executor in list"


class TestExecutorInfo:
    def test_executor_info_succeeds(self, executor_id):
        out = drove_ok("executor", "info", executor_id)
        assert len(out.strip()) > 0

    def test_executor_info_contains_host(self, executor_id):
        out = drove_ok("executor", "info", executor_id)
        assert "Host" in out or "host" in out.lower()

    def test_executor_info_contains_resources(self, executor_id):
        out = drove_ok("executor", "info", executor_id)
        assert "CPU" in out or "Memory" in out or "core" in out.lower()


class TestExecutorAppInstances:
    def test_executor_appinstances_succeeds(self, executor_id):
        result = drove("executor", "appinstances", executor_id, check=False)
        assert result.returncode == 0, (
            f"executor appinstances failed:\n{result.stdout}\n{result.stderr}"
        )

    def test_executor_tasks_succeeds(self, executor_id):
        result = drove("executor", "tasks", executor_id, check=False)
        assert result.returncode == 0

    def test_executor_lsinstances_succeeds(self, executor_id):
        result = drove("executor", "lsinstances", executor_id, check=False)
        assert result.returncode == 0


class TestDescribeExecutor:
    def test_describe_executor_succeeds(self, executor_id):
        out = drove_ok("describe", "executor", executor_id)
        assert len(out.strip()) > 0

    def test_describe_executor_json(self, executor_id):
        import json
        out = drove_ok("describe", "executor", executor_id, "--json")
        data = json.loads(out)
        assert isinstance(data, dict)
