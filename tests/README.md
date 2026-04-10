"""
drove-cli Integration Test Suite
=================================

## Structure

```
tests/
├── conftest.py              # Shared fixtures, helpers, cluster connectivity
├── fixtures/                # JSON spec files (mirrors sample/) used by offline mock tests
│   ├── test_app.json
│   ├── test_service.json
│   └── test_task.json
├── mock_server.py           # Lightweight Flask stub for offline tests
├── test_cli_basics.py       # Help, completion, error handling (offline)
├── test_cluster.py          # drove cluster commands
├── test_config.py           # drove config commands (offline)
├── test_executor.py         # drove executor commands
├── test_apps.py             # drove apps (smoke + full lifecycle)
├── test_appinstances.py     # drove appinstances + describe instance
├── test_localservices.py    # drove localservices + drove lsinstances
└── test_tasks.py            # drove tasks lifecycle
```

## Requirements

```
pytest
pytest-timeout
flask
drove-cli (installed or run from project root)
```

Install via:

```bash
pip install drove-cli[test]
# or
poetry install --with test
```

## Configuration

Tests use the cluster configured in `~/.drove` (`current_cluster` by default).
Override with environment variables:

| Variable           | Description                              |
|--------------------|------------------------------------------|
| `DROVE_ENDPOINT`   | Cluster endpoint (e.g. http://host:4000) |
| `DROVE_CLUSTER`    | Cluster name from `~/.drove`             |
| `DROVE_USERNAME`   | Basic auth username                      |
| `DROVE_PASSWORD`   | Basic auth password                      |
| `DROVE_AUTH_HEADER`| Token auth header value                  |
| `DROVE_INSECURE`   | Set `1` to skip SSL verification         |

## Running

```bash
# Offline tests only (no cluster required — drove-cli developers)
pytest -m offline

# Live integration tests (requires a real Drove cluster)
pytest -m "not offline"

# Everything: offline mock + live integration
pytest

# Stop on first failure
pytest -x -v

# With a specific cluster
DROVE_CLUSTER=docker pytest -m "not offline"
```

## Fixtures & Isolation

The live test suite is **fully self-contained**.  All resources are created from
the spec files in `sample/` at the start of each module and destroyed on teardown.
No pre-existing cluster resources are required.

- `executor_id` (session) — resolves first active executor ID from the live cluster
- `live_app` (module) — creates `TEST_APP-1` from `sample/test_app.json`, scales
  to 1 healthy instance, destroys on teardown.  Used by `test_apps.py` and
  `test_appinstances.py`.
- `live_service` (module) — creates `TEST_LOCAL_SERVICE-1` from
  `sample/test_service.json`, activates it, destroys on teardown.  Used by
  `test_localservices.py`.
- `app_for_tasks` (module) — creates `TEST_APP-1` in MONITORING state from
  `sample/test_app.json`, used by `test_tasks.py`.  Tasks are submitted using
  `sample/test_task.json` (taskId=T0012, sourceAppName=TEST_APP).

## Offline mock server

The offline tests start a lightweight Flask stub (`mock_server.py`) on an
ephemeral port.  The `offline_env` fixture points `DROVE_ENDPOINT` at it so
the CLI subprocess connects to the stub transparently.

When you add a new CLI endpoint, also add the matching stub route to
`mock_server.py` and write an `test_offline_<feature>.py` file marked with
`pytestmark = pytest.mark.offline`.
"""
