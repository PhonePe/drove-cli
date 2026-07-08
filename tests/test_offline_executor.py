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


class TestOfflineExecutorTasks:
    """Tests for `drove executor tasks` — verifies the --app filter works.

    The mock executor seed data includes a task with sourceAppName='TEST_APP'.
    Before the fix, running `drove executor tasks <id>` with any tasks present
    would crash with ``AttributeError: 'Namespace' object has no attribute 'app'``
    because the ``--app`` argument was missing from the subparser definition.
    """

    def test_executor_tasks_shows_task_data(self, offline_executor_id):
        """Tasks output should contain the seeded task information."""
        from conftest import drove_ok
        out = drove_ok("executor", "tasks", offline_executor_id)
        assert "TEST_APP" in out, (
            f"Expected 'TEST_APP' in tasks output but got:\n{out}"
        )

    def test_executor_tasks_app_filter_shows_match(self, offline_executor_id):
        """The --app flag should show tasks matching the given source app."""
        from conftest import drove_ok
        out = drove_ok("executor", "tasks", offline_executor_id, "--app", "TEST_APP")
        assert "TEST_APP" in out, (
            f"Expected 'TEST_APP' in filtered output but got:\n{out}"
        )

    def test_executor_tasks_app_filter_excludes_nonmatch(self, offline_executor_id):
        """The --app flag should exclude tasks from other apps."""
        from conftest import drove_ok
        out = drove_ok("executor", "tasks", offline_executor_id, "--app", "NONEXISTENT_APP")
        assert "TEST_APP" not in out, (
            f"Expected 'TEST_APP' to be filtered out but got:\n{out}"
        )
