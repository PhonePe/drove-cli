"""
drove-cli Integration Test Suite
=================================

## Structure

```
tests/
├── conftest.py              # Shared fixtures, helpers, cluster connectivity
├── fixtures/                # JSON spec files for test apps/services/tasks
│   ├── cli_test_app.json
│   ├── cli_test_service.json
│   └── cli_test_task.json
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
drove-cli (installed or run from project root)
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
# All tests (offline + integration)
pytest tests/ -v

# Offline only (no cluster required)
pytest tests/test_cli_basics.py tests/test_config.py -v

# Smoke tests (read-only, fast, skip lifecycle)
pytest tests/ -v -k "not Lifecycle and not Task"

# Full lifecycle tests only
pytest tests/ -v -k "Lifecycle or Task"

# Specific module
pytest tests/test_cluster.py -v

# Stop on first failure
pytest tests/ -x -v

# With a specific cluster
DROVE_CLUSTER=docker pytest tests/ -v
```

## Fixtures & Isolation

- `cluster_reachable` (session) — skips all integration tests if cluster is offline
- `executor_id` (session) — resolves first active executor ID
- `live_app` (module) — creates `CLI_TEST_APP-1`, scales to 1 healthy instance,
  destroys on teardown. Used by `test_apps.py` and `test_appinstances.py`.
- `live_service` (module) — creates `CLI_TEST_SERVICE-1`, activates it,
  destroys on teardown. Used by `test_localservices.py`.
- `app_for_tasks` (module) — creates `CLI_TEST_APP-1` in MONITORING state,
  used by `test_tasks.py`.

Pre-existing cluster apps (`TEST_APP-1`, `TEST_LOCAL_SERVICE-1`) are used only
for read-only smoke tests and are never modified.
"""
