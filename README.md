# Drove CLI

Command-line interface for [Drove Container Orchestrator](https://github.com/PhonePe/drove).

## Installation

```bash
pip install drove-cli
```

Or via Docker:
```bash
docker pull ghcr.io/phonepe/drove-cli:latest
```

## Quick Start

1. Create configuration at `~/.drove`:
```ini
[DEFAULT]
current_cluster = prod

[prod]
endpoint = https://drove.example.com
auth_header = Bearer <token>
```

2. Verify connection:
```bash
drove cluster ping
drove cluster summary
```

## Commands

```
drove appinstances   Instance operations
drove apps           Application lifecycle
drove cluster        Cluster operations
drove config         CLI configuration
drove describe       Detailed resource views
drove executor       Node management
drove localservices  Per-node services
drove lsinstances    Local service instances
drove tasks          One-off task execution
```

Use `drove -h` or `drove <command> -h` for help.

## Documentation

For comprehensive documentation including architecture, configuration options, and detailed command reference:

**[phonepe.github.io/drove-orchestrator](https://phonepe.github.io/drove-orchestrator/)**

- [CLI Reference](https://phonepe.github.io/drove-orchestrator/extra/cli.html) — Full command documentation
- [Configuration](https://phonepe.github.io/drove-orchestrator/extra/cli/configuration.html) — Multi-cluster setup, authentication
- [Application Specs](https://phonepe.github.io/drove-orchestrator/applications/specification.html) — Service specification format
- [Task Specs](https://phonepe.github.io/drove-orchestrator/tasks/specification.html) — Ephemeral task format

## License

© 2024 Santanu Sinha | Apache 2.0
