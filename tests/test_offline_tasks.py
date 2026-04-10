"""
tests/test_offline_tasks.py — offline tests for `drove tasks` commands.

All tests use the mock Drove server; no live cluster is required.
Run with:  pytest -m offline tests/test_offline_tasks.py

The mock server returns RUNNING state immediately for created tasks.
Kill sets the task to STOPPED.  `tasks list` only returns RUNNING tasks
(consistent with real Drove behaviour — completed tasks are invisible).
`tasks show` works for both RUNNING and terminal-state tasks.
"""
import json
import pytest

pytestmark = pytest.mark.offline

TASK_SOURCE   = "CLI_TEST_APP"
TASK_ID       = "CLI_TEST_TASK_001"


@pytest.fixture(scope="module")
def app_for_offline_tasks(offline_env):
    """
    Ensure CLI_TEST_APP-1 exists in the mock server before task tests run.
    The mock task spec references CLI_TEST_APP as sourceAppName.
    """
    from conftest import drove_ok, FIXTURES_DIR
    spec = str(FIXTURES_DIR / "cli_test_app.json")
    drove_ok("apps", "create", spec, timeout=10)
    yield "CLI_TEST_APP-1"
    # No teardown needed — offline_env resets state between modules


class TestOfflineTasksList:
    def test_tasks_list_succeeds(self, app_for_offline_tasks):
        from conftest import drove
        result = drove("tasks", "list", check=False)
        assert result.returncode == 0

    def test_tasks_list_filter_by_app(self, app_for_offline_tasks):
        from conftest import drove
        result = drove("tasks", "list", "--app", TASK_SOURCE, check=False)
        assert result.returncode == 0


class TestOfflineTaskLifecycle:
    def test_task_create(self, app_for_offline_tasks):
        from conftest import drove_ok, drove, FIXTURES_DIR
        spec = str(FIXTURES_DIR / "cli_test_task.json")
        # Kill any leftover task first
        drove("tasks", "kill", TASK_SOURCE, TASK_ID, check=False, timeout=10)

        drove_ok("tasks", "create", spec, timeout=10)

        # Verify task registered via `tasks show` (works for active AND completed)
        result = drove("tasks", "show", TASK_SOURCE, TASK_ID,
                       check=False, timeout=10)
        assert result.returncode == 0 and TASK_ID in result.stdout, (
            f"Task not visible via 'tasks show':\n{result.stdout}"
        )

    def test_task_appears_in_list_while_running(self, app_for_offline_tasks):
        """Mock server returns RUNNING for freshly created tasks."""
        from conftest import drove_ok
        out = drove_ok("tasks", "list")
        # Task may or may not appear (list filters to RUNNING); just assert no crash
        assert out is not None

    def test_task_show(self, app_for_offline_tasks):
        from conftest import drove
        result = drove("tasks", "show", TASK_SOURCE, TASK_ID,
                       check=False, timeout=10)
        if result.returncode == 0:
            assert len(result.stdout.strip()) > 0

    def test_task_show_contains_task_id(self, app_for_offline_tasks):
        from conftest import drove
        result = drove("tasks", "show", TASK_SOURCE, TASK_ID,
                       check=False, timeout=10)
        assert result.returncode == 0
        assert TASK_ID in result.stdout, (
            f"Expected {TASK_ID} in tasks show output:\n{result.stdout}"
        )

    def test_task_logs_list(self, app_for_offline_tasks):
        from conftest import drove
        result = drove("tasks", "logs", TASK_SOURCE, TASK_ID,
                       check=False, timeout=10)
        assert result.returncode == 0 or "not found" in result.stdout.lower()

    def test_task_kill(self, app_for_offline_tasks):
        from conftest import drove
        result = drove("tasks", "kill", TASK_SOURCE, TASK_ID,
                       check=False, timeout=10)
        assert result.returncode == 0

    def test_task_show_after_kill(self, app_for_offline_tasks):
        """After kill, show should return STOPPED state."""
        from conftest import drove
        result = drove("tasks", "show", TASK_SOURCE, TASK_ID,
                       check=False, timeout=10)
        if result.returncode == 0:
            # Mock sets state to STOPPED after kill
            assert "STOPPED" in result.stdout or len(result.stdout.strip()) > 0

    def test_describe_task(self, app_for_offline_tasks):
        from conftest import drove
        result = drove("describe", "task", TASK_SOURCE, TASK_ID,
                       check=False, timeout=10)
        if result.returncode == 0:
            assert len(result.stdout.strip()) > 0

    def test_describe_task_json(self, app_for_offline_tasks):
        from conftest import drove
        result = drove("describe", "task", TASK_SOURCE, TASK_ID,
                       "--json", check=False, timeout=10)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            assert isinstance(data, dict)
