# Drove CLI

Command-line interface for the [Drove Container Orchestrator](https://github.com/PhonePe/drove-orchestrator).

## Installation

### Using pip

```bash
pip install drove-cli
```

### Using pip (virtual environment)

```bash
python3 -m venv ~/.venvs/drove-cli
source ~/.venvs/drove-cli/bin/activate
pip install drove-cli
```

To activate in a new shell:
```bash
source ~/.venvs/drove-cli/bin/activate
```

### Using Docker

```bash
docker pull ghcr.io/phonepe/drove-cli:latest
```

Create a wrapper script for convenience:

```bash
cat > ~/bin/drove << 'EOF'
#!/bin/sh
docker run --rm -it --network host \
    -v ${HOME}/.drove:/root/.drove:ro \
    ghcr.io/phonepe/drove-cli:latest "$@"
EOF
chmod +x ~/bin/drove
```

## Upgrade

### Using pip

```bash
pip install -U drove-cli
```

### Using Docker

```bash
docker pull ghcr.io/phonepe/drove-cli:latest
```

## Configuration

Create `~/.drove` with your cluster configuration:

```ini
[DEFAULT]
stage_token = <your-stage-token>
prod_token = <your-prod-token>

[local]
endpoint = http://localhost:10000
username = admin
password = admin

[stage]
endpoint = https://drove.stage.example.com
auth_header = %(stage_token)s

[prod]
endpoint = https://drove.prod.example.com
auth_header = %(prod_token)s
```

## Quick Start

```bash
# Verify connection
drove -c prod cluster ping

# View cluster status
drove -c prod cluster summary

# List applications
drove -c prod apps list

# Get application info
drove -c prod apps info <app-name>
```

## Commands

| Command | Description                                                           |
|---------|-----------------------------------------------------------------------|
| `appinstances` | Application instance operations                                       |
| `apps` | Application lifecycle Management (list, info, deploy, scale, suspend) |
| `cluster` | Cluster operations (ping, summary, leader, maintenance)               |
| `config` | CLI configuration management                                          |
| `describe` | Show detailed information about a resource                            |
| `executor` | Executor management                                                   |
| `localservices` | Local service management                                              |
| `lsinstances` | Local service instance operations                                     |
| `tasks` | One-off task execution                                                |

Use `drove -h` or `drove <command> -h` for detailed help.

## Global Options

```
-f, --file FILE        Configuration file (default: ~/.drove)
-c, --cluster CLUSTER  Cluster name from config file
-e, --endpoint URL     Drove endpoint URL
-t, --auth-header HDR  Authorization header value
-u, --username USER    Cluster username
-p, --password PASS    Cluster password
-i, --insecure         Skip SSL verification
-d, --debug            Print error details
```

## Testing

The test suite has two distinct modes depending on whether you are working on
the **CLI itself** or verifying compatibility with a real **Drove orchestrator
cluster**.

### Install test dependencies

```bash
pip install drove-cli[test]
# or, if you are using Poetry:
poetry install --with test
```

---

### Mode 1 — Offline tests (drove-cli developers)

No Drove cluster is required.  A lightweight Flask stub starts on an ephemeral
port in a background thread and serves mock API responses that match the exact
shapes the CLI expects.

```bash
# Run the full offline suite
pytest -m offline

# Run a specific file
pytest -m offline tests/test_offline_apps.py

# Verbose output
pytest -m offline -v
```

The offline suite covers:

| Test file | What is tested |
|---|---|
| `test_offline_cluster.py` | ping, summary, leader, endpoints, describe |
| `test_offline_apps.py` | list, summary, spec, create / scale / suspend / restart / destroy |
| `test_offline_appinstances.py` | list, info |
| `test_offline_executor.py` | list, info, app- and task-instance sub-views |
| `test_offline_localservices.py` | list, summary, spec, create / activate / restart / deactivate / destroy, lsinstances list & info |
| `test_offline_tasks.py` | create / show / kill lifecycle, list |

> **Tip:** The mock server lives in `tests/mock_server.py`.  When you add a new
> endpoint to the CLI, add the corresponding stub route there and write an
> `test_offline_<feature>.py` file marked with `pytestmark = pytest.mark.offline`.

---

### Mode 2 — Live integration tests (drove orchestrator developers)

These tests run every CLI command against a real Drove cluster.  They validate
that the CLI stays compatible with a specific version of the orchestrator API.

**Prerequisites — configure the target cluster:**

```bash
# Option A: environment variables (CI-friendly)
export DROVE_ENDPOINT=http://your-cluster:10000
export DROVE_USERNAME=admin
export DROVE_PASSWORD=secret

# Option B: ~/.drove config file (see Configuration section above)
# Then pass -c <cluster-name> when running pytest via the conftest helper
```

The live test suite is **fully self-contained** — it creates all required
resources (`TEST_APP-1`, `TEST_LOCAL_SERVICE-1`, tasks) from the spec files in
`sample/` at the start of each test module and destroys them on teardown.
No pre-existing cluster resources are needed.

**Run the live tests:**

```bash
# All live tests (skips offline mock tests)
pytest -m "not offline"

# Read-only smoke tests only (safe against production clusters)
pytest -m smoke

# Full lifecycle tests (create / scale / destroy — mutates cluster state)
pytest -m lifecycle

# Everything: offline mock + live integration
pytest
```

**Pytest markers:**

| Marker | Description |
|---|---|
| `offline` | Mock server only — no cluster connectivity needed |
| `smoke` | Fast read-only tests, safe against any live cluster |
| `lifecycle` | Full create / scale / destroy cycles — requires a dedicated test cluster |

---

## Documentation

Full documentation is available at **[phonepe.github.io/drove-orchestrator](https://phonepe.github.io/drove-orchestrator/cli/)**

## License

© 2024 Santanu Sinha | Apache 2.0
