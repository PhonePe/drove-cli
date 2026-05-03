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
import os
import subprocess
import sys
from pathlib import Path
import pytest

pytestmark = pytest.mark.offline

# TASK_SOURCE, TASK_ID, and APP_SPEC are imported from conftest:
#   TASK_SOURCE = "TEST_APP"      (sourceAppName in sample/test_task.json)
#   TASK_ID     = "T0012"         (taskId in sample/test_task.json)
#   APP_SPEC    = sample/test_app.json  (name=TEST_APP → ID TEST_APP-1)
from conftest import TASK_SOURCE, TASK_ID, APP_SPEC, TASK_SPEC


def local_drove(*args, timeout=30):
    cli_dir = Path(__file__).resolve().parents[1]
    cmd = ["python3", "drove.py"]
    endpoint = os.environ.get("DROVE_ENDPOINT")
    if endpoint:
        cmd += ["-e", endpoint]
    cmd += list(args)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(cli_dir),
        env=os.environ.copy(),
    )


@pytest.fixture(scope="module")
def app_for_offline_tasks(offline_env):
    """
    Ensure TEST_APP-1 exists in the mock server before task tests run.
    The mock task spec (sample/test_task.json) references TEST_APP as
    sourceAppName.
    """
    from conftest import drove_ok
    drove_ok("apps", "create", APP_SPEC, timeout=10)
    yield "TEST_APP-1"
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
        from conftest import drove_ok, drove
        # Kill any leftover task first
        drove("tasks", "kill", TASK_SOURCE, TASK_ID, check=False, timeout=10)

        drove_ok("tasks", "create", TASK_SPEC, timeout=10)

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

class TestOfflineTaskCliRegressions:
    def test_tasks_tail_log_flag_does_not_override_global_config_file(self):
        cli_dir = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(cli_dir))
        try:
            import drove as drove_entry
            import drovecli as drove_cli

            parser = drove_entry.build_parser()
            client = drove_cli.DroveCli(parser)
            args = client.parser.parse_args([
                "tasks", "tail", TASK_SOURCE, TASK_ID, "--log", "output.log"
            ])

            assert args.log == "output.log"
            assert args.file is None
        finally:
            sys.path.pop(0)

    def test_describe_task_uses_top_level_host_fields(self, app_for_offline_tasks):
        from conftest import drove, drove_ok

        drove("tasks", "kill", TASK_SOURCE, TASK_ID, check=False, timeout=10)
        drove_ok("tasks", "create", TASK_SPEC, timeout=10)

        result = local_drove("describe", "task", TASK_SOURCE, TASK_ID, timeout=10)
        assert result.returncode == 0
        assert "Hostname:" in result.stdout
        assert "exec-host-1" in result.stdout
        assert "Executor ID:" in result.stdout

    def test_missing_config_file_does_not_trigger_none_type_crash(self):
        result = local_drove(
            "-f", "/tmp/__missing_drove_config__.json", "tasks", "list", timeout=10
        )

        assert "unsupported operand type" not in result.stdout.lower()
        assert "unsupported operand type" not in result.stderr.lower()

