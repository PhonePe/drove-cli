"""
tests/test_offline_full_help.py — offline tests for the ``--full-help`` flag.

``drove --full-help`` now prints **compact** output by default (one line per
command) for LLM/token-optimised consumption.  The verbose argparse output is
available via ``drove --full-help --verbose``.

Tests are split into two groups:

1. **TestCompactHelp** — validates the new compact default.
2. **TestVerboseHelp*** — validates the ``--verbose`` mode (original behavior).

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
EXPECTED_LINES    = 981         # total line count of verbose full-help output

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

def _run_full_help(extra_args: list | None = None, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    """Invoke ``drove --full-help`` as a subprocess and return the result."""
    cmd = [sys.executable, "drove.py", "--full-help"]
    if extra_args:
        cmd.extend(extra_args)
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


# ── compact help tests (new default) ────────────────────────────────────────

class TestCompactHelp:
    """Validate the compact one-line-per-command output (default mode)."""

    def test_compact_exit_code_zero(self, offline_env):
        result = _run_full_help()
        assert result.returncode == 0, (
            f"--full-help exited with non-zero code {result.returncode}.\n"
            f"stderr: {result.stderr}"
        )

    def test_compact_no_stderr_output(self, offline_env):
        result = _run_full_help()
        assert result.stderr.strip() == "", (
            f"Unexpected stderr from --full-help:\n{result.stderr}"
        )

    def test_compact_output_is_not_empty(self, offline_env):
        result = _run_full_help()
        assert len(result.stdout.strip()) > 0, "--full-help produced no output"

    def test_compact_output_much_smaller_than_verbose(self, offline_env):
        compact = _run_full_help()
        verbose = _run_full_help(extra_args=["--verbose"])
        compact_size = len(compact.stdout)
        verbose_size = len(verbose.stdout)
        reduction = 1.0 - (compact_size / verbose_size)
        assert reduction >= 0.80, (
            f"Compact output ({compact_size} chars) is not >=80% smaller than "
            f"verbose ({verbose_size} chars). Reduction: {reduction:.1%}"
        )

    def test_compact_no_separator_bars(self, offline_env):
        result = _run_full_help()
        sep_lines = [l for l in result.stdout.splitlines() if l == SEPARATOR]
        assert len(sep_lines) == 0, (
            f"Compact output should have no separator bars, found {len(sep_lines)}"
        )

    def test_compact_no_help_flag_noise(self, offline_env):
        result = _run_full_help()
        assert "--help" not in result.stdout, (
            "Compact output should not contain --help flag text"
        )
        assert "show this help" not in result.stdout.lower(), (
            "Compact output should not contain help descriptions"
        )

    @pytest.mark.parametrize("group", TOP_LEVEL_GROUPS)
    def test_compact_all_groups_present(self, offline_env, group):
        result = _run_full_help()
        assert group in result.stdout, (
            f"Top-level group '{group}' missing from compact --full-help output"
        )

    @pytest.mark.parametrize("group,subcommand", SUBCOMMAND_SAMPLES)
    def test_compact_all_subcommands_present(self, offline_env, group, subcommand):
        result = _run_full_help()
        expected = f"{group} {subcommand}"
        assert expected in result.stdout, (
            f"Sub-command '{group} {subcommand}' missing from compact --full-help"
        )

    def test_compact_required_flags_not_bracketed(self, offline_env):
        """Required flags must render without square brackets (e.g. -e ENDPOINT, not [-e ENDPOINT])."""
        result = _run_full_help()
        lines = result.stdout.splitlines()
        # config init has required --endpoint/-e
        init_lines = [l for l in lines if l.startswith("config init")]
        assert len(init_lines) == 1, f"Expected 1 'config init' line, found {len(init_lines)}"
        line = init_lines[0]
        assert "-e ENDPOINT" in line, f"Required -e ENDPOINT missing from: {line!r}"
        assert "[-e ENDPOINT]" not in line, (
            f"Required flag -e ENDPOINT should NOT be in brackets: {line!r}"
        )

    def test_compact_optional_flags_are_bracketed(self, offline_env):
        """Optional flags must render with square brackets."""
        result = _run_full_help()
        lines = result.stdout.splitlines()
        init_lines = [l for l in lines if l.startswith("config init")]
        assert len(init_lines) == 1
        line = init_lines[0]
        # -u USERNAME is optional in config init
        assert "[-u USERNAME]" in line, (
            f"Optional flag -u should be bracketed in: {line!r}"
        )

    def test_compact_starts_with_global_opts(self, offline_env):
        result = _run_full_help()
        first_line = result.stdout.splitlines()[0]
        assert first_line.startswith("drove "), (
            f"First line should start with 'drove ', got: {first_line!r}"
        )
        assert "[-f" in first_line, "Global opts should include [-f ...]"

    def test_compact_works_without_drove_endpoint(self, offline_env):
        clean_env = os.environ.copy()
        clean_env.pop("DROVE_ENDPOINT", None)
        clean_env.pop("DROVE_CLUSTER", None)
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


# ── verbose help tests (--verbose flag, original behavior) ───────────────────

class TestVerboseHelpExitAndBasics:
    """Basic sanity checks for --full-help --verbose: exit code, output, line count."""

    def test_exit_code_zero(self, offline_env):
        result = _run_full_help(extra_args=["--verbose"])
        assert result.returncode == 0, (
            f"--full-help --verbose exited with non-zero code {result.returncode}.\n"
            f"stderr: {result.stderr}"
        )

    def test_no_stderr_output(self, offline_env):
        result = _run_full_help(extra_args=["--verbose"])
        assert result.stderr.strip() == "", (
            f"Unexpected stderr from --full-help --verbose:\n{result.stderr}"
        )

    def test_output_is_not_empty(self, offline_env):
        result = _run_full_help(extra_args=["--verbose"])
        assert len(result.stdout.strip()) > 0, "--full-help --verbose produced no output"

    def test_output_line_count(self, offline_env):
        result = _run_full_help(extra_args=["--verbose"])
        lines = result.stdout.splitlines()
        assert len(lines) == EXPECTED_LINES, (
            f"Expected {EXPECTED_LINES} lines, got {len(lines)}"
        )

    def test_works_without_drove_endpoint(self, offline_env):
        """--full-help --verbose must not require a live cluster endpoint."""
        clean_env = os.environ.copy()
        clean_env.pop("DROVE_ENDPOINT", None)
        clean_env.pop("DROVE_CLUSTER", None)
        result = subprocess.run(
            [sys.executable, "drove.py", "--full-help", "--verbose"],
            capture_output=True,
            text=True,
            env=clean_env,
            timeout=30,
        )
        assert result.returncode == 0, (
            "--full-help --verbose should succeed even without DROVE_ENDPOINT.\n"
            f"stderr: {result.stderr}"
        )
        assert len(result.stdout.strip()) > 0


class TestVerboseHelpSeparators:
    """Validate the ``=``×72 section separators in verbose mode."""

    def test_separator_count(self, offline_env):
        result = _run_full_help(extra_args=["--verbose"])
        sep_lines = [l for l in result.stdout.splitlines() if l == SEPARATOR]
        assert len(sep_lines) == EXPECTED_SECTIONS, (
            f"Expected {EXPECTED_SECTIONS} separator lines, found {len(sep_lines)}"
        )

    def test_separator_is_72_equals(self, offline_env):
        """Each separator must be exactly 72 '=' characters."""
        result = _run_full_help(extra_args=["--verbose"])
        sep_lines = [l for l in result.stdout.splitlines() if l.startswith("=")]
        for line in sep_lines:
            assert line == SEPARATOR, (
                f"Separator line has unexpected format: {line!r} "
                f"(expected {'='*72!r})"
            )

    def test_separator_precedes_usage(self, offline_env):
        """Every ``usage:`` line must be immediately preceded by a separator."""
        lines = _run_full_help(extra_args=["--verbose"]).stdout.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("usage: drove"):
                assert i > 0 and lines[i - 1] == SEPARATOR, (
                    f"Line {i}: usage line not preceded by separator.\n"
                    f"  prev: {lines[i-1]!r}\n"
                    f"  curr: {line!r}"
                )


class TestVerboseHelpRootParser:
    """Verify the root ``drove`` parser section is present and correct in verbose mode."""

    def test_root_usage_present(self, offline_env):
        result = _run_full_help(extra_args=["--verbose"])
        assert "usage: drove " in result.stdout, (
            "Root 'usage: drove ...' line not found in --full-help --verbose output"
        )

    def test_full_help_flag_self_documented(self, offline_env):
        """The --full-help option must document itself in the root section."""
        result = _run_full_help(extra_args=["--verbose"])
        assert "--full-help" in result.stdout, (
            "--full-help flag not found in its own help output"
        )

    def test_full_help_description_present(self, offline_env):
        result = _run_full_help(extra_args=["--verbose"])
        assert "Show help for every command and sub-command" in result.stdout

    def test_root_positional_subcommands_listed(self, offline_env):
        """Root section must list available plugin groups."""
        result = _run_full_help(extra_args=["--verbose"])
        for group in ("apps", "tasks", "cluster"):
            assert group in result.stdout, (
                f"Plugin group '{group}' not mentioned in root help section"
            )


class TestVerboseHelpTopLevelGroups:
    """Every top-level plugin group must have its own usage section in verbose mode."""

    @pytest.mark.parametrize("group", TOP_LEVEL_GROUPS)
    def test_group_usage_present(self, offline_env, group):
        result = _run_full_help(extra_args=["--verbose"])
        expected = f"usage: drove {group} "
        assert expected in result.stdout, (
            f"Top-level group '{group}' usage line missing from --full-help --verbose"
        )


class TestVerboseHelpSubCommands:
    """Representative sub-commands must each have their own usage section in verbose mode."""

    @pytest.mark.parametrize("group,subcommand", SUBCOMMAND_SAMPLES)
    def test_subcommand_usage_present(self, offline_env, group, subcommand):
        result = _run_full_help(extra_args=["--verbose"])
        expected = f"usage: drove {group} {subcommand} "
        assert expected in result.stdout, (
            f"Sub-command 'drove {group} {subcommand}' usage line missing "
            f"from --full-help --verbose output"
        )


class TestVerboseHelpOrdering:
    """Sub-commands within a group must appear in alphabetical order in verbose mode."""

    def _usage_lines_for_group(self, output: str, group: str) -> list[str]:
        """Return usage lines whose second token is `group`."""
        return [
            l for l in output.splitlines()
            if l.startswith(f"usage: drove {group} ")
        ]

    def test_apps_subcommands_alphabetical(self, offline_env):
        output = _run_full_help(extra_args=["--verbose"]).stdout
        usage_lines = self._usage_lines_for_group(output, "apps")
        subcmds = [l.split()[3] for l in usage_lines if len(l.split()) >= 4]
        assert subcmds == sorted(subcmds), (
            f"apps sub-commands not alphabetically ordered: {subcmds}"
        )

    def test_appinstances_subcommands_alphabetical(self, offline_env):
        output = _run_full_help(extra_args=["--verbose"]).stdout
        usage_lines = self._usage_lines_for_group(output, "appinstances")
        subcmds = [l.split()[3] for l in usage_lines if len(l.split()) >= 4]
        assert subcmds == sorted(subcmds), (
            f"appinstances sub-commands not alphabetically ordered: {subcmds}"
        )

    def test_tasks_subcommands_alphabetical(self, offline_env):
        output = _run_full_help(extra_args=["--verbose"]).stdout
        usage_lines = self._usage_lines_for_group(output, "tasks")
        subcmds = [l.split()[3] for l in usage_lines if len(l.split()) >= 4]
        assert subcmds == sorted(subcmds), (
            f"tasks sub-commands not alphabetically ordered: {subcmds}"
        )

    def test_describe_subcommands_alphabetical(self, offline_env):
        output = _run_full_help(extra_args=["--verbose"]).stdout
        usage_lines = self._usage_lines_for_group(output, "describe")
        subcmds = [l.split()[3] for l in usage_lines if len(l.split()) >= 4]
        assert subcmds == sorted(subcmds), (
            f"describe sub-commands not alphabetically ordered: {subcmds}"
        )


class TestVerboseHelpMutualExclusion:
    """--full-help --verbose and normal commands must be mutually exclusive."""

    def test_full_help_with_subcommand_still_prints_help(self, offline_env):
        """Passing --full-help --verbose alongside a sub-command should still print help."""
        result = subprocess.run(
            [sys.executable, "drove.py", "--full-help", "--verbose", "apps", "list"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "usage: drove " in result.stdout

    def test_full_help_does_not_output_tabular_app_list(self, offline_env):
        """Full-help --verbose output must not contain an actual apps listing table."""
        result = subprocess.run(
            [sys.executable, "drove.py", "--full-help", "--verbose"],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "DROVE_ENDPOINT": offline_env.endpoint},
        )
        assert "TEST_APP" not in result.stdout, (
            "full-help --verbose output appears to contain live API data"
        )
