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

## Documentation

Full documentation is available at **[github.com/PhonePe/drove-orchestrator](https://github.com/PhonePe/drove-orchestrator)**

## License

© 2024 Santanu Sinha | Apache 2.0
