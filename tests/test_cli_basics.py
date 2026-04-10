"""
tests/test_cli_basics.py — tests for basic CLI behaviour (help, version,
completion, error handling).  No cluster connection required.
"""
import subprocess
import pytest


def run(*args, timeout=10) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["drove"] + list(args),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class TestCLIHelp:
    def test_help_flag(self):
        result = run("--help")
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "Usage" in result.stdout

    def test_help_short_flag(self):
        result = run("-h")
        assert result.returncode == 0

    def test_no_args_shows_help(self):
        result = run()
        # No args should print help (exit -1 or 0 depending on implementation)
        assert "usage" in result.stdout.lower() or "usage" in result.stderr.lower()

    def test_apps_help(self):
        result = run("apps", "--help")
        assert result.returncode == 0
        assert "list" in result.stdout or "create" in result.stdout

    def test_cluster_help(self):
        result = run("cluster", "--help")
        assert result.returncode == 0

    def test_executor_help(self):
        result = run("executor", "--help")
        assert result.returncode == 0

    def test_tasks_help(self):
        result = run("tasks", "--help")
        assert result.returncode == 0

    def test_localservices_help(self):
        result = run("localservices", "--help")
        assert result.returncode == 0

    def test_appinstances_help(self):
        result = run("appinstances", "--help")
        assert result.returncode == 0

    def test_describe_help(self):
        result = run("describe", "--help")
        assert result.returncode == 0

    def test_config_help(self):
        result = run("config", "--help")
        assert result.returncode == 0

    def test_lsinstances_help(self):
        result = run("lsinstances", "--help")
        assert result.returncode == 0


class TestCLICompletion:
    def test_bash_completion(self):
        result = run("--print-completion", "bash")
        assert result.returncode == 0
        assert len(result.stdout.strip()) > 0, "Bash completion script is empty"

    def test_zsh_completion(self):
        result = run("--print-completion", "zsh")
        assert result.returncode == 0

    def test_tcsh_completion(self):
        result = run("--print-completion", "tcsh")
        assert result.returncode == 0


class TestCLIErrorHandling:
    def test_unknown_command_fails_gracefully(self):
        result = run("nonexistent-command")
        # Should fail but not crash with a traceback
        assert result.returncode != 0
        assert "Traceback" not in result.stdout
        assert "Traceback" not in result.stderr

    def test_bad_endpoint_fails_gracefully(self):
        result = run("-e", "http://127.0.0.1:19999",
                     "-u", "admin", "-p", "admin",
                     "cluster", "ping")
        # drove reports the error in stdout but may exit 0 (known CLI behaviour).
        # We verify: no Python traceback and the error is surfaced to the user.
        assert "Traceback" not in result.stdout
        assert "Traceback" not in result.stderr
        combined = result.stdout + result.stderr
        assert "error" in combined.lower() or "connect" in combined.lower(), (
            f"Expected connection error message, got:\n{combined}"
        )

    def test_missing_app_id_fails(self):
        result = run("apps", "summary")
        assert result.returncode != 0
