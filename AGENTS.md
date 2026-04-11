# AGENTS.md — drove-cli Development Guidelines

This file contains instructions for AI coding agents and human contributors
working on **drove-cli**.  Read this before making changes.

---

## Project Overview

`drove-cli` is a Python command-line tool for interacting with
[Drove](https://github.com/PhonePe/drove), an open-source container
orchestrator.  The CLI is built with `argparse`, uses `requests` for HTTP
communication via `DroveClient`, and formats output with `tabulate`.

---

## Repository Layout

```
drove.py              CLI entry-point (argparse setup, plugin loading)
droveclient.py        DroveClient — all HTTP calls to the Drove API
droveutils.py         Shared utilities (log reading, printing, etc.)
plugins/              Per-command plugins (applications.py, cluster.py, …)
sample/               Canonical resource spec files shipped with the repo
  test_app.json       → creates TEST_APP-1 (SERVICE type)
  test_service.json   → creates TEST_LOCAL_SERVICE-1 (LOCAL_SERVICE type)
  test_task.json      → task spec (sourceAppName=TEST_APP, taskId=T0012)
tests/
  conftest.py         Shared pytest fixtures and helper functions
  mock_server.py      Flask-based Drove API stub (offline / CI mode)
  fixtures/           JSON spec files (mirrors sample/) for offline mock tests
  test_*.py           Live integration tests (require a cluster)
  test_offline_*.py   Offline tests (use mock server — no cluster needed)
pytest.ini            Pytest configuration
pyproject.toml        Poetry project / dependency manifest
```

---

## Running Tests

### Offline tests (no cluster required — preferred for development)

```bash
pytest -m offline
```

This starts the mock Drove API server (tests/mock_server.py) on an ephemeral
port in a background thread.  `DROVE_ENDPOINT` is automatically set so the
`drove` CLI subprocess connects to the stub.

Offline tests cover all read commands and full stateful lifecycle
(create → scale/activate → restart → suspend/deactivate → destroy) for apps,
local services, tasks, executors, and cluster commands.

**To add a new offline test:**
1. Create `tests/test_offline_<feature>.py`.
2. Add `pytestmark = pytest.mark.offline` at module level.
3. Use the `offline_env` module-scoped fixture (already sets `DROVE_ENDPOINT`
   and resets mock state).
4. If the mock server needs a new endpoint, add it to `tests/mock_server.py`
   in the `create_app()` function.

### Live integration tests (require a Drove cluster)

```bash
# Configure ~/.drove or environment variables first:
export DROVE_ENDPOINT=http://your-cluster:10000
export DROVE_USERNAME=admin
export DROVE_PASSWORD=secret

pytest -m "not offline"   # skip offline tests
pytest                    # run everything (offline + live)
```

The live test suite is **fully self-contained** — it creates all required
resources (`TEST_APP-1`, `TEST_LOCAL_SERVICE-1`, tasks) from the spec files
in `sample/` at the start of each module and destroys them on teardown.
No pre-existing cluster resources are required.

### Pytest markers

| Marker | Meaning |
|---|---|
| `smoke` | Fast read-only tests, no cluster mutation |
| `lifecycle` | Full create/scale/destroy cycles (live cluster required) |
| `offline` | Mock server only — no cluster connectivity needed |

---

## Adding a New CLI Command

1. Create `plugins/<name>.py` implementing `plugins.DrovePlugin`.
2. Register the plugin in `drove.py` (see existing plugin loading).
3. Add all new Drove API endpoints to `tests/mock_server.py`
   (in `create_app()`).
4. Add offline tests in `tests/test_offline_<name>.py`.
5. Add live integration tests in `tests/test_<name>.py` if applicable.

---

## Mock Server (tests/mock_server.py)

The mock server is a Flask application that mimics all Drove API endpoints.
It maintains an in-process mutable `DroveState` object so that lifecycle
operations (create, scale, destroy, etc.) are reflected in subsequent GET calls.

**Architecture:**
- `DroveState` — mutable dict-based registry for apps, services, tasks, executor
- `create_app(state)` — Flask app factory; routes delegate to `state` methods
- `MockDroveServer` — wraps Flask in a daemon thread, binds on port 0
- `MockDroveServer.reset()` — reinitialises state from seed data (called by
  `offline_env` fixture before each module)

**Seed data (always present after reset):**
- `TEST_APP-1` — RUNNING, 1 HEALTHY instance (`AI-test-app-inst-001`)
- `TEST_APP_DEV-1` — RUNNING
- `TEST_LOCAL_SERVICE-1` — INACTIVE
- One executor: `93b6b6f3-c7c8-3824-afc9-cb6d0b32454c`

---

## Code Style

- Python 3.10+ compatible
- Type annotations on new public functions
- `drove_ok()` / `drove()` helpers from `conftest.py` for all subprocess calls
- No `time.sleep()` in offline tests — the mock responds synchronously
- Live tests may use `wait_for_*` polling helpers for eventual-consistency waits

---

## Known Behaviours / Gotchas

- `drove` always exits **0** even on API errors; tests must check stdout for
  `"not found"` or `"error"` patterns.
- Local service healthy state is `ACTIVE` (not `RUNNING`) — do not confuse.
- `tasks list` only shows **RUNNING** tasks; completed tasks are invisible.
  Use `tasks show <source> <id>` instead.
- Local service instance IDs use `SI-` prefix (not `LSI-` or `AI-`).
- After `localservices restart --wait`, the new instance takes a few seconds
  to appear (race condition on live clusters; not an issue in mock tests).
- `DroveClient.start()` calls `GET /apis/v1/ping` on initialisation — the mock
  server must handle this endpoint (it does).

---

## Dependencies

Runtime: `requests`, `tabulate`, `urllib3`, `tenacity`, `shtab`, `certifi`

Test: `pytest`, `pytest-timeout`, `flask`

Install test deps:
```bash
poetry install --with test
# or
pip install pytest pytest-timeout flask
```
