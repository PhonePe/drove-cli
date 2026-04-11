---
name: drove-cli
description: >
  Operate, inspect, and manage Drove container-orchestrator deployables
  (applications, local services, tasks, app instances, executors, and cluster)
  using the `drove` CLI tool. Use this skill whenever the user asks to deploy,
  scale, restart, suspend, destroy, list, inspect, or tail logs for anything
  on a Drove cluster — or to manage Drove CLI configuration (endpoints,
  credentials). Activate when you see words like: drove, app deploy, scale app,
  local service, localservice, lsinstance, drove task, container orchestrator,
  drove cluster, drove endpoint, drove executor, drove config. Even if the user
  just pastes an app-id or says "check on my app", use this skill.
---

# drove-cli Skill

You are an expert operator of **Drove**, an open-source container orchestrator,
using the `drove` CLI.

---

## Step 0 — Check and Install drove-cli

Before running any `drove` command, verify the CLI is available:

```bash
which drove 2>/dev/null || python3 -c "import drovecli" 2>/dev/null
```

If missing, install it:

```bash
pip install drove-cli
```

After installation verify:

```bash
drove --version
```

If `drove` is still not on PATH after pip install, try `python3 -m drove` as a
fallback invocation prefix.

---

## Step 1 — Load the Full Command Reference

Run this once to bring every command and sub-command into context:

```bash
drove --full-help
```

This prints the complete, always-up-to-date help for every command and
sub-command in one shot. Use it to look up flags, argument names, and
available options — no need to memorise them.

> **Full documentation:** https://phonepe.github.io/drove-orchestrator/cli/
> Refer to this whenever the built-in help isn't enough or something is unclear.

---

## Step 2 — Configure Cluster Connection

drove reads connection details from `~/.drove` or from env vars / CLI flags.

### Option A – CLI flags (one-off)
```bash
drove -e http://my-cluster:10000 -u admin -p secret cluster ping
```

### Option B – Environment variables (CI / scripts)
```bash
export DROVE_ENDPOINT=http://my-cluster:10000
export DROVE_USERNAME=admin
export DROVE_PASSWORD=secret
```

### Option C – Config file `~/.drove`
```bash
drove config init --endpoint http://my-cluster:10000 --name prod \
                  --username admin --password secret
drove config use-cluster prod      # switch active cluster
drove config get-clusters          # list saved clusters
```

Always verify connectivity before running other commands:
```bash
drove cluster ping     # → "Ping successful"
```

---

## Step 3 — Resource Types

| Resource | Plugin | Description |
|---|---|---|
| Application | `apps` | Long-running containerised services |
| App Instance | `appinstances` | Individual running containers of an app |
| Local Service | `localservices` | Services pinned to specific executor nodes |
| LS Instance | `lsinstances` | Individual containers of a local service |
| Task | `tasks` | Short-lived one-shot jobs |
| Executor | `executor` | Worker nodes in the cluster |
| Cluster | `cluster` | Cluster-level health and meta-commands |
| Describe | `describe` | Deep-dive JSON view of any resource |

---

## Step 4 — Common Workflows

### Deploy a new app
```bash
drove apps create my_app.json
drove apps scale  MY_APP-1 3 --wait
drove apps summary MY_APP-1
```

### Rolling restart
```bash
drove apps restart MY_APP-1 --parallelism 1 --timeout 10m --wait
```

### Tear down an app
```bash
# App must be suspended before it can be destroyed
drove apps suspend MY_APP-1 --wait
drove apps destroy MY_APP-1
```

### Tail logs from a running instance
```bash
drove appinstances list MY_APP-1          # find instance IDs
drove appinstances tail MY_APP-1 AI-abc123
```

### Run a one-shot task and monitor it
```bash
drove tasks create my_task.json
drove tasks show  MY_APP T0042
drove tasks tail  MY_APP T0042
```

### Activate a local service
```bash
drove localservices create   my_service.json
drove localservices conftest MY_SVC-1      # validate with one instance first
drove localservices activate MY_SVC-1
drove localservices summary  MY_SVC-1
```

---

## Gotchas

- `drove` **always exits 0**, even on API errors — check stdout for `"not found"`
  or `"error"` rather than relying on the return code in scripts
- `tasks list` shows only **running** tasks — use `tasks show <source> <id>` for
  completed or stopped tasks
- Local service healthy state is **`ACTIVE`** (not `RUNNING`)
- An app must be in `MONITORING` state (i.e. suspended) before it can be
  destroyed — suspend it first
- For SSL-terminated clusters with a self-signed cert, pass `--insecure` / `-i`
