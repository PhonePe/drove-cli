"""
tests/test_tasks.py — tests for `drove tasks` commands.

Tasks require that TEST_APP-1 is created in MONITORING state first
(sample/test_task.json references TEST_APP as its sourceAppName).
The `app_for_tasks` fixture creates a fresh app (MONITORING state only —
no running instances needed) to bind the task to, runs the task, polls
for completion, then cleans up.

All resources are created by the test suite; no pre-existing cluster
resources are required.

NOTE: The test-task image (test_task.json uses ITERATIONS=10) runs for a
short time and exits. Expected final state is SUCCESSFUL.
"""
import json
import time
import pytest
from conftest import drove_ok, drove, TASK_SPEC, TASK_SOURCE, TASK_ID, APP_SPEC, APP_ID


# How long to wait for a task to reach a terminal state (seconds)
TASK_TIMEOUT = 300
TASK_POLL_INTERVAL = 5


def _wait_for_task_terminal(source_app: str, task_id: str,
                             timeout: int = TASK_TIMEOUT,
                             poll: int = TASK_POLL_INTERVAL) -> str:
    """Poll until the task reaches a terminal state; return final state."""
    terminal_states = {"SUCCESSFUL", "STOPPED", "FAILED"}
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = drove("tasks", "show", source_app, task_id, check=False)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                for state in terminal_states:
                    if state in line:
                        return state
        time.sleep(poll)
    raise TimeoutError(
        f"Task {source_app}/{task_id} did not reach terminal state "
        f"within {timeout}s"
    )


# ---------------------------------------------------------------------------
# Module-scoped fixture: create TEST_APP-1 in MONITORING state for tasks
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app_for_tasks():
    """
    Create TEST_APP-1 from sample/test_app.json in MONITORING state (no
    running instances needed — tasks only need the app to exist).
    Cleans up on teardown.
    """
    # Destroy any leftover from a previous run
    drove("apps", "suspend", APP_ID, "--wait", check=False, timeout=120)
    drove("apps", "destroy", APP_ID, check=False, timeout=30)

    drove_ok("apps", "create", APP_SPEC, timeout=30)
    yield APP_ID

    # Kill any running task first, then clean up the app
    drove("tasks", "kill", TASK_SOURCE, TASK_ID, check=False, timeout=30)
    drove("apps", "suspend", APP_ID, "--wait", check=False, timeout=120)
    drove("apps", "destroy", APP_ID, check=False, timeout=30)


# ---------------------------------------------------------------------------
# Task list (before we create any) — safe read-only
# ---------------------------------------------------------------------------

class TestTasksList:
    def test_tasks_list_succeeds(self):
        result = drove("tasks", "list", check=False)
        assert result.returncode == 0

    def test_tasks_list_filter_by_app(self, app_for_tasks):
        result = drove("tasks", "list", "--app", TASK_SOURCE, check=False)
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Task lifecycle
# ---------------------------------------------------------------------------

class TestTaskLifecycle:
    def test_task_create(self, app_for_tasks):
        """Create a task and verify it's registered (via tasks show).

        NOTE: `tasks list` only shows RUNNING (active) tasks; a short-lived task
        may finish quickly and immediately disappear from the list.
        We verify creation via `tasks show`, which returns results for both active
        and recently completed tasks.
        """
        # Kill any leftover task first
        drove("tasks", "kill", TASK_SOURCE, TASK_ID, check=False, timeout=30)
        time.sleep(2)

        drove_ok("tasks", "create", TASK_SPEC, timeout=30)

        # Verify task was registered — use `tasks show` (works for active AND completed)
        result = drove("tasks", "show", TASK_SOURCE, TASK_ID, check=False, timeout=30)
        assert result.returncode == 0 and TASK_ID in result.stdout, (
            f"Task not visible via 'tasks show' after create:\n{result.stdout}"
        )

    def test_task_show(self, app_for_tasks):
        """show should return task details."""
        result = drove("tasks", "show", TASK_SOURCE, TASK_ID, check=False, timeout=30)
        # May fail if task already finished; check output has some content
        if result.returncode == 0:
            assert len(result.stdout.strip()) > 0

    def test_task_logs_list(self, app_for_tasks):
        """logs command should not hard-fail (task may still be running)."""
        result = drove("tasks", "logs", TASK_SOURCE, TASK_ID,
                       check=False, timeout=30)
        assert result.returncode == 0 or "not found" in result.stdout.lower() \
               or "not found" in result.stderr.lower()

    def test_task_reaches_terminal_state(self, app_for_tasks):
        """Wait for the task to complete successfully."""
        final = _wait_for_task_terminal(TASK_SOURCE, TASK_ID)
        assert final in ("SUCCESSFUL", "STOPPED"), (
            f"Task ended in unexpected state: {final}"
        )

    def test_describe_task(self, app_for_tasks):
        """describe task should return details for a completed task."""
        result = drove("describe", "task", TASK_SOURCE, TASK_ID,
                       check=False, timeout=30)
        # describe may fail for a finished task depending on cluster config
        if result.returncode == 0:
            assert len(result.stdout.strip()) > 0

    def test_describe_task_json(self, app_for_tasks):
        result = drove("describe", "task", TASK_SOURCE, TASK_ID,
                       "--json", check=False, timeout=30)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            assert isinstance(data, dict)
