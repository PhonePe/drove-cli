"""
tests/test_offline_full_help.py — offline tests for the ``--full-help`` flag.

``drove --full-help`` recursively prints the argparse help for the root parser
and every sub-command parser in a single pass.  It must:

* Exit with code 0.
* Require no live cluster (works without DROVE_ENDPOINT / ~/.drove).
* Print exactly 80 ``=``-separator sections (1 root + 79 command/sub-command
  parsers).
* Cover every top-level plugin group and representative sub-commands.

All tests use the mock server fixture only to inherit the offline_env
environment; ``--full-help`` itself never issues any HTTP request.

Run with:  pytest -m offline tests/test_offline_full_help.py
"""
import subprocess
import os
import sys
import pytest

pytestmark = pytest.mark.offline

# ── constants ────────────────────────────────────────────────────────────────

SEPARATOR = "=" * 72
EXPECTED_SECTIONS = 80          # 1 root + 9 plugin groups + ~70 sub-commands
EXPECTED_LINES    = 987         # total line count of full-help output

# All top-level plugin groups that must appear in the output
TOP_LEVEL_GROUPS = [
    "appinstances",
    "apps",
    "cluster",
    "config",
    "describe",
    "executor",
    "localservices",
    "lsinstances",
    "tasks",
]

# A representative sub-command from each group (group, subcommand)
SUBCOMMAND_SAMPLES = [
    ("appinstances", "list"),
    ("appinstances", "info"),
    ("appinstances", "kill"),
    ("appinstances", "replace"),
    ("appinstances", "logs"),
    ("appinstances", "tail"),
    ("appinstances", "download"),
    ("apps", "list"),
    ("apps", "create"),
    ("apps", "deploy"),
    ("apps", "destroy"),
    ("apps", "scale"),
    ("apps", "suspend"),
    ("apps", "restart"),
    ("apps", "spec"),
    ("apps", "summary"),
    ("apps", "cancelop"),
    ("cluster", "ping"),
    ("cluster", "summary"),
    ("describe", "app"),
    ("describe", "cluster"),
    ("describe", "executor"),
    ("describe", "instance"),
    ("describe", "localservice"),
    ("describe", "lsinstance"),
    ("describe", "task"),
    ("executor", "list"),
    ("localservices", "list"),
    ("lsinstances", "list"),
    ("lsinstances", "info"),
    ("lsinstances", "kill"),
    ("tasks", "list"),
    ("tasks", "create"),
    ("tasks", "kill"),
    ("tasks", "show"),
]


# ── helpers ──────────────────────────────────────────────────────────────────

def _run_full_help(extra_env: dict | None = None) -> subprocess.CompletedProcess:
    """Invoke ``drove --full-help`` as a subprocess and return the result."""
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, "drove.py", "--full-help"],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


# ── test classes ─────────────────────────────────────────────────────────────

class TestFullHelpExitAndBasics:
    """Basic sanity checks: exit code, non-empty output, line count."""

    def test_exit_code_zero(self, offline_env):
        result = _run_full_help()
        assert result.returncode == 0, (
            f"--full-help exited with non-zero code {result.returncode}.\n"
            f"stderr: {result.stderr}"
        )

    def test_no_stderr_output(self, offline_env):
        result = _run_full_help()
        assert result.stderr.strip() == "", (
            f"Unexpected stderr from --full-help:\n{result.stderr}"
        )

    def test_output_is_not_empty(self, offline_env):
        result = _run_full_help()
        assert len(result.stdout.strip()) > 0, "--full-help produced no output"

    def test_output_line_count(self, offline_env):
        result = _run_full_help()
        lines = result.stdout.splitlines()
        assert len(lines) == EXPECTED_LINES, (
            f"Expected {EXPECTED_LINES} lines, got {len(lines)}"
        )

    def test_works_without_drove_endpoint(self, offline_env):
        """--full-help must not require a live cluster endpoint."""
        env_override = {
            "DROVE_ENDPOINT": "",   # explicitly blank
        }
        # Also strip DROVE_CLUSTER so ~/.drove is not consulted
        clean_env = os.environ.copy()
        clean_env.pop("DROVE_ENDPOINT", None)
        clean_env.pop("DROVE_CLUSTER",  None)
        result = subprocess.run(
            [sys.executable, "drove.py", "--full-help"],
            capture_output=True,
            text=True,
            env=clean_env,
            timeout=30,
        )
        assert result.returncode == 0, (
            "--full-help should succeed even without DROVE_ENDPOINT.\n"
            f"stderr: {result.stderr}"
        )
        assert len(result.stdout.strip()) > 0


class TestFullHelpSeparators:
    """Validate the ``=``×72 section separators."""

    def test_separator_count(self, offline_env):
        result = _run_full_help()
        sep_lines = [l for l in result.stdout.splitlines() if l == SEPARATOR]
        assert len(sep_lines) == EXPECTED_SECTIONS, (
            f"Expected {EXPECTED_SECTIONS} separator lines, found {len(sep_lines)}"
        )

    def test_separator_is_72_equals(self, offline_env):
        """Each separator must be exactly 72 '=' characters."""
        result = _run_full_help()
        sep_lines = [l for l in result.stdout.splitlines() if l.startswith("=")]
        for line in sep_lines:
            assert line == SEPARATOR, (
                f"Separator line has unexpected format: {line!r} "
                f"(expected {'='*72!r})"
            )

    def test_separator_precedes_usage(self, offline_env):
        """Every ``usage:`` line must be immediately preceded by a separator."""
        lines = _run_full_help().stdout.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("usage: drove"):
                assert i > 0 and lines[i - 1] == SEPARATOR, (
                    f"Line {i}: usage line not preceded by separator.\n"
                    f"  prev: {lines[i-1]!r}\n"
                    f"  curr: {line!r}"
                )


class TestFullHelpRootParser:
    """Verify the root ``drove`` parser section is present and correct."""

    def test_root_usage_present(self, offline_env):
        result = _run_full_help()
        assert "usage: drove " in result.stdout, (
            "Root 'usage: drove ...' line not found in --full-help output"
        )

    def test_full_help_flag_self_documented(self, offline_env):
        """The --full-help option must document itself in the root section."""
        result = _run_full_help()
        assert "--full-help" in result.stdout, (
            "--full-help flag not found in its own help output"
        )

    def test_full_help_description_present(self, offline_env):
        result = _run_full_help()
        assert "Show help for every command and sub-command" in result.stdout

    def test_root_positional_subcommands_listed(self, offline_env):
        """Root section must list available plugin groups."""
        result = _run_full_help()
        # argparse lists subcommand choices in the root help
        for group in ("apps", "tasks", "cluster"):
            assert group in result.stdout, (
                f"Plugin group '{group}' not mentioned in root help section"
            )


class TestFullHelpTopLevelGroups:
    """Every top-level plugin group must have its own usage section."""

    @pytest.mark.parametrize("group", TOP_LEVEL_GROUPS)
    def test_group_usage_present(self, offline_env, group):
        result = _run_full_help()
        expected = f"usage: drove {group} "
        assert expected in result.stdout, (
            f"Top-level group '{group}' usage line missing from --full-help output"
        )


class TestFullHelpSubCommands:
    """Representative sub-commands must each have their own usage section."""

    @pytest.mark.parametrize("group,subcommand", SUBCOMMAND_SAMPLES)
    def test_subcommand_usage_present(self, offline_env, group, subcommand):
        result = _run_full_help()
        expected = f"usage: drove {group} {subcommand} "
        assert expected in result.stdout, (
            f"Sub-command 'drove {group} {subcommand}' usage line missing "
            f"from --full-help output"
        )


class TestFullHelpOrdering:
    """Sub-commands within a group must appear in alphabetical order."""

    def _usage_lines_for_group(self, output: str, group: str) -> list[str]:
        """Return usage lines whose second token is `group`."""
        return [
            l for l in output.splitlines()
            if l.startswith(f"usage: drove {group} ")
        ]

    def test_apps_subcommands_alphabetical(self, offline_env):
        output = _run_full_help().stdout
        usage_lines = self._usage_lines_for_group(output, "apps")
        # Extract sub-command names (4th token: "usage: drove apps <sub>")
        subcmds = [l.split()[3] for l in usage_lines if len(l.split()) >= 4]
        assert subcmds == sorted(subcmds), (
            f"apps sub-commands not alphabetically ordered: {subcmds}"
        )

    def test_appinstances_subcommands_alphabetical(self, offline_env):
        output = _run_full_help().stdout
        usage_lines = self._usage_lines_for_group(output, "appinstances")
        subcmds = [l.split()[3] for l in usage_lines if len(l.split()) >= 4]
        assert subcmds == sorted(subcmds), (
            f"appinstances sub-commands not alphabetically ordered: {subcmds}"
        )

    def test_tasks_subcommands_alphabetical(self, offline_env):
        output = _run_full_help().stdout
        usage_lines = self._usage_lines_for_group(output, "tasks")
        subcmds = [l.split()[3] for l in usage_lines if len(l.split()) >= 4]
        assert subcmds == sorted(subcmds), (
            f"tasks sub-commands not alphabetically ordered: {subcmds}"
        )

    def test_describe_subcommands_alphabetical(self, offline_env):
        output = _run_full_help().stdout
        usage_lines = self._usage_lines_for_group(output, "describe")
        subcmds = [l.split()[3] for l in usage_lines if len(l.split()) >= 4]
        assert subcmds == sorted(subcmds), (
            f"describe sub-commands not alphabetically ordered: {subcmds}"
        )


class TestFullHelpMutualExclusion:
    """--full-help and normal commands must be mutually exclusive."""

    def test_full_help_with_subcommand_still_prints_help(self, offline_env):
        """Passing --full-help alongside a sub-command should still print help
        (argparse evaluates --full-help before dispatching to sub-parsers)."""
        result = subprocess.run(
            [sys.executable, "drove.py", "--full-help", "apps", "list"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Should still succeed and output help, not execute the sub-command
        assert result.returncode == 0
        assert "usage: drove " in result.stdout

    def test_full_help_does_not_output_tabular_app_list(self, offline_env):
        """Full-help output must not contain an actual apps listing table."""
        result = subprocess.run(
            [sys.executable, "drove.py", "--full-help"],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "DROVE_ENDPOINT": offline_env.endpoint},
        )
        # The real apps list contains "TEST_APP"; help output should not
        assert "TEST_APP" not in result.stdout, (
            "full-help output appears to contain live API data"
        )
