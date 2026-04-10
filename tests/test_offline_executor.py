"""
tests/test_offline_executor.py — offline tests for `drove executor` commands.

All tests use the mock Drove server; no live cluster is required.
Run with:  pytest -m offline tests/test_offline_executor.py
"""
import json
import pytest

pytestmark = pytest.mark.offline


class TestOfflineExecutorList:
    def test_executor_list_succeeds(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("executor", "list")
        assert len(out.strip()) > 0

    def test_executor_list_has_header(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("executor", "list")
        header_keywords = ["Executor", "Host", "Port", "Cores", "Memory", "State"]
        assert any(kw in out for kw in header_keywords), (
            f"None of {header_keywords} found in output:\n{out}"
        )

    def test_executor_list_has_at_least_one_executor(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("executor", "list")
        lines = [l for l in out.strip().splitlines() if l.strip()]
        assert len(lines) >= 2, "Expected at least header + one executor row"


class TestOfflineExecutorInfo:
    def test_executor_info_succeeds(self, offline_executor_id):
        from conftest import drove_ok
        out = drove_ok("executor", "info", offline_executor_id)
        assert len(out.strip()) > 0

    def test_executor_info_contains_host(self, offline_executor_id):
        from conftest import drove_ok
        out = drove_ok("executor", "info", offline_executor_id)
        assert "Host" in out or "host" in out.lower()

    def test_executor_info_contains_resources(self, offline_executor_id):
        from conftest import drove_ok
        out = drove_ok("executor", "info", offline_executor_id)
        assert "CPU" in out or "Memory" in out or "core" in out.lower()


class TestOfflineExecutorAppInstances:
    def test_executor_appinstances_succeeds(self, offline_executor_id):
        from conftest import drove
        result = drove("executor", "appinstances", offline_executor_id, check=False)
        assert result.returncode == 0

    def test_executor_tasks_succeeds(self, offline_executor_id):
        from conftest import drove
        result = drove("executor", "tasks", offline_executor_id, check=False)
        assert result.returncode == 0

    def test_executor_lsinstances_succeeds(self, offline_executor_id):
        from conftest import drove
        result = drove("executor", "lsinstances", offline_executor_id, check=False)
        assert result.returncode == 0


class TestOfflineDescribeExecutor:
    def test_describe_executor_succeeds(self, offline_executor_id):
        from conftest import drove_ok
        out = drove_ok("describe", "executor", offline_executor_id)
        assert len(out.strip()) > 0

    def test_describe_executor_json(self, offline_executor_id):
        from conftest import drove_ok
        out = drove_ok("describe", "executor", offline_executor_id, "--json")
        data = json.loads(out)
        assert isinstance(data, dict)
