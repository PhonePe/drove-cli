"""
conftest.py — shared fixtures and utilities for drove-cli integration tests.

The tests run against a live Drove cluster. Configure the cluster via ~/.drove
or environment variables (see README in tests/).

Environment Variables (override ~/.drove):
  DROVE_ENDPOINT    e.g. http://localhost:10000
  DROVE_USERNAME    basic auth username
  DROVE_PASSWORD    basic auth password
  DROVE_AUTH_HEADER bearer / token header value
  DROVE_CLUSTER     cluster name from ~/.drove  (default: uses current_cluster)
  DROVE_INSECURE    set to '1' to skip SSL verification
"""
import json
import os
import subprocess
import time
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
TESTS_DIR = Path(__file__).parent
FIXTURES_DIR = TESTS_DIR / "fixtures"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_cmd() -> list[str]:
    """Build the base `drove` command with optional env overrides."""
    cmd = ["drove"]
    endpoint = os.environ.get("DROVE_ENDPOINT")
    cluster  = os.environ.get("DROVE_CLUSTER")
    username = os.environ.get("DROVE_USERNAME")
    password = os.environ.get("DROVE_PASSWORD")
    auth_hdr = os.environ.get("DROVE_AUTH_HEADER")
    insecure = os.environ.get("DROVE_INSECURE", "").strip() in ("1", "true", "yes")

    if endpoint:
        cmd += ["-e", endpoint]
    elif cluster:
        cmd += ["-c", cluster]
    if username:
        cmd += ["-u", username]
    if password:
        cmd += ["-p", password]
    if auth_hdr:
        cmd += ["-t", auth_hdr]
    if insecure:
        cmd += ["-i"]
    return cmd


def drove(*args, check: bool = True, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run the drove CLI with the given arguments and return the result."""
    cmd = _base_cmd() + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"drove {' '.join(args)} failed (rc={result.returncode}):\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def drove_ok(*args, timeout: int = 30) -> str:
    """Run drove, assert success, return stdout."""
    return drove(*args, check=True, timeout=timeout).stdout


def drove_json(*args, timeout: int = 30) -> dict:
    """Run drove with --json flag (where supported), parse and return JSON."""
    return json.loads(drove_ok(*args, "--json", timeout=timeout))


def wait_for_app_state(app_id: str, desired_state: str, retries: int = 30, delay: float = 3.0):
    """Poll apps summary until the app reaches the desired state."""
    for i in range(retries):
        out = drove("apps", "summary", app_id, check=False).stdout
        if desired_state in out:
            return True
        time.sleep(delay)
    raise TimeoutError(
        f"App {app_id!r} did not reach state {desired_state!r} within "
        f"{retries * delay:.0f}s"
    )


def wait_for_healthy_instances(app_id: str, count: int, retries: int = 60, delay: float = 5.0):
    """Poll until the expected number of healthy instances are reported."""
    for i in range(retries):
        out = drove("apps", "summary", app_id, check=False).stdout
        for line in out.splitlines():
            if "healthyInstances" in line:
                try:
                    actual = int(line.split()[-1])
                    if actual >= count:
                        return True
                except ValueError:
                    pass
        time.sleep(delay)
    raise TimeoutError(
        f"App {app_id!r} did not reach {count} healthy instance(s) within "
        f"{retries * delay:.0f}s"
    )


def wait_for_ls_state(svc_id: str, desired_state: str, retries: int = 30, delay: float = 3.0):
    """Poll localservices summary until the service reaches the desired state."""
    for i in range(retries):
        out = drove("localservices", "summary", svc_id, check=False).stdout
        if desired_state in out:
            return True
        time.sleep(delay)
    raise TimeoutError(
        f"Local service {svc_id!r} did not reach state {desired_state!r} within "
        f"{retries * delay:.0f}s"
    )


# ---------------------------------------------------------------------------
# Pytest session-level fixtures
# ---------------------------------------------------------------------------

def _destroy_app_safe(app_id: str, max_retries: int = 10, delay: float = 3.0):
    """
    Destroy an app reliably, retrying if the cluster is in a transitional state.

    After suspend, Drove may briefly enter SCALING_REQUESTED before returning to
    MONITORING.  In that window, destroy returns a 400 validation error (but
    exits 0).  We retry until the destroy succeeds or we give up.
    """
    for attempt in range(max_retries):
        result = drove("apps", "destroy", app_id, check=False, timeout=30)
        # Successful destroy prints "Application destroyed"
        if "destroyed" in result.stdout.lower():
            return
        # App may no longer exist (already destroyed)
        if "not found" in result.stdout.lower() or "not found" in result.stderr.lower():
            return
        # Transitional state — wait and retry
        time.sleep(delay)
    # Last attempt — ignore errors
    drove("apps", "destroy", app_id, check=False, timeout=30)



def cluster_reachable():
    """Assert the cluster is online before any test runs."""
    result = drove("cluster", "ping", check=False, timeout=10)
    if result.returncode != 0:
        pytest.skip(
            f"Drove cluster not reachable — skipping all integration tests.\n"
            f"Configure ~/.drove or set DROVE_ENDPOINT.\n"
            f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )


@pytest.fixture(scope="session")
def executor_id() -> str:
    """Return the first active executor ID from the cluster."""
    out = drove_ok("executor", "list")
    for line in out.splitlines():
        # Lines starting with a UUID
        parts = line.split()
        if parts and len(parts[0]) == 36 and parts[0].count("-") == 4:
            return parts[0]
    pytest.skip("No active executor found in cluster.")


# ---------------------------------------------------------------------------
# App lifecycle fixture — creates CLI_TEST_APP-1, yields its ID, destroys it
# ---------------------------------------------------------------------------

APP_SPEC   = str(FIXTURES_DIR / "cli_test_app.json")
APP_ID     = "CLI_TEST_APP-1"

SVC_SPEC   = str(FIXTURES_DIR / "cli_test_service.json")
SVC_ID     = "CLI_TEST_SERVICE-1"

TASK_SPEC  = str(FIXTURES_DIR / "cli_test_task.json")
TASK_SOURCE = "CLI_TEST_APP"
TASK_ID    = "CLI_TEST_TASK_001"


@pytest.fixture(scope="module")
def live_app():
    """
    Create CLI_TEST_APP-1, deploy 1 instance, wait for HEALTHY, yield app_id.
    Suspends and destroys the app on teardown.
    """
    # Clean up any leftover from a previous run
    drove("apps", "suspend", APP_ID, "--wait", check=False, timeout=120)
    # Wait for app to settle to MONITORING (post-suspend transitional state)
    try:
        wait_for_app_state(APP_ID, "MONITORING", retries=10, delay=2)
    except (TimeoutError, Exception):
        pass
    _destroy_app_safe(APP_ID)

    drove_ok("apps", "create", APP_SPEC, timeout=30)
    drove_ok("apps", "scale", APP_ID, "1", "--wait", timeout=300)
    wait_for_healthy_instances(APP_ID, 1, retries=60, delay=5)

    yield APP_ID

    # Teardown
    drove("apps", "suspend", APP_ID, "--wait", check=False, timeout=120)
    # Wait for app to settle before destroying (avoid SCALING_REQUESTED race)
    try:
        wait_for_app_state(APP_ID, "MONITORING", retries=10, delay=2)
    except (TimeoutError, Exception):
        pass
    _destroy_app_safe(APP_ID)


def _destroy_ls_safe(svc_id: str, max_retries: int = 15, delay: float = 3.0):
    """
    Deactivate and destroy a local service reliably.

    After activation or restart, Drove may transition through ADJUSTING_INSTANCES
    before settling to INACTIVE.  We wait for INACTIVE before calling destroy,
    retrying if the service is still in a transitional state.
    """
    # Deactivate first (ignore errors — may already be inactive or not exist)
    drove("localservices", "deactivate", svc_id, check=False, timeout=60)
    # Wait for INACTIVE (transitional state: ADJUSTING_INSTANCES)
    try:
        wait_for_ls_state(svc_id, "INACTIVE", retries=20, delay=3)
    except (TimeoutError, Exception):
        pass
    # Now destroy with retries
    for attempt in range(max_retries):
        result = drove("localservices", "destroy", svc_id, check=False, timeout=30)
        if "destroyed" in result.stdout.lower():
            return
        if "not found" in result.stdout.lower() or "not found" in result.stderr.lower():
            return
        # Service may be in transitional state — wait and retry
        time.sleep(delay)
    # Last attempt — ignore errors
    drove("localservices", "destroy", svc_id, check=False, timeout=30)


@pytest.fixture(scope="module")
def live_service():
    """
    Create CLI_TEST_SERVICE-1, activate it, wait for ACTIVE, yield svc_id.
    Deactivates and destroys on teardown.

    NOTE: Drove local services use state="ACTIVE" (not "RUNNING") once healthy.
    Intermediate states on activation: may briefly show PROVISIONING before ACTIVE.
    On warm start (image cached): ACTIVE within ~5s.
    On cold start (docker image pull): may take up to 120s.
    """
    # Clean up any leftover from a previous run
    _destroy_ls_safe(SVC_ID)

    drove_ok("localservices", "create", SVC_SPEC, timeout=30)
    drove_ok("localservices", "activate", SVC_ID, timeout=30)
    # Wait for ACTIVE state — local services use ACTIVE (not RUNNING)
    wait_for_ls_state(SVC_ID, "ACTIVE", retries=30, delay=5)

    yield SVC_ID

    # Teardown: deactivate → wait for INACTIVE → destroy
    _destroy_ls_safe(SVC_ID)

