"""
tests/mock_server.py — Lightweight Flask stub that mimics the Drove API.

Used by the `mock_drove_server` pytest fixture (session-scoped) so that all
offline tests can run without a real Drove cluster.  The stub is started on an
ephemeral port in a daemon thread; DROVE_ENDPOINT is set to point the CLI at it.

All responses follow the canonical Drove envelope:
    {"status": "SUCCESS", "data": <payload>}

Stateful mutation routes (create/scale/destroy/etc.) update an in-process
registry so subsequent GET calls reflect the change, enabling lifecycle tests.

Response shapes match the exact field names the drove CLI plugins expect
(verified against plugins/applications.py, plugins/executors.py, etc.).

Endpoints implemented
─────────────────────
GET  /apis/v1/ping
GET  /apis/v1/cluster
GET  /apis/v1/cluster/executors
GET  /apis/v1/cluster/executors/<exec_id>
GET  /apis/v1/cluster/events
GET  /apis/v1/endpoints
POST /apis/v1/cluster/maintenance/set
POST /apis/v1/cluster/maintenance/unset
POST /apis/v1/cluster/executors/blacklist
POST /apis/v1/cluster/executors/unblacklist

GET  /apis/v1/applications
GET  /apis/v1/applications/<app_id>
GET  /apis/v1/applications/<app_id>/spec
GET  /apis/v1/applications/<app_id>/instances
GET  /apis/v1/applications/<app_id>/instances/old
GET  /apis/v1/applications/<app_id>/instances/<inst_id>
POST /apis/v1/applications/operations
POST /apis/v1/applications/operations/<app_id>/cancel

GET  /apis/v1/localservices
GET  /apis/v1/localservices/<svc_id>
GET  /apis/v1/localservices/<svc_id>/spec
GET  /apis/v1/localservices/<svc_id>/instances
GET  /apis/v1/localservices/<svc_id>/instances/old
GET  /apis/v1/localservices/<svc_id>/instances/<inst_id>
POST /apis/v1/localservices/operations
POST /apis/v1/localservices/operations/<svc_id>/cancel

GET  /apis/v1/tasks
GET  /apis/v1/tasks/<source_app>/instances/<task_id>
POST /apis/v1/tasks/operations

GET  /apis/v1/logfiles/<prefix>/<domain>/<obj_id>/list
GET  /apis/v1/logfiles/<prefix>/<domain>/<obj_id>/read/<name>
GET  /apis/v1/logfiles/<prefix>/<domain>/<obj_id>/download/<name>
"""

from __future__ import annotations

import copy
import json
import threading
import time
from typing import Any

from flask import Flask, jsonify, request

# ---------------------------------------------------------------------------
# Seed data — these mirror what the live tests expect to find pre-existing
# ---------------------------------------------------------------------------

EXECUTOR_ID = "93b6b6f3-c7c8-3824-afc9-cb6d0b32454c"

# ---------------------------------------------------------------------------
# Executor seed data
#
# Two separate structures:
#   _EXECUTOR_LIST_SEED  — returned by GET /apis/v1/cluster/executors (list view)
#   _EXECUTOR_INFO_SEED  — returned by GET /apis/v1/cluster/executors/<id> (detail view)
#
# plugins/executors.py:
#   list()      uses: executorId, hostname, port, transportType,
#                     freeCores, usedCores, freeMemory, usedMemory, tags, state
#   show_info() uses: state.executorId, hostname, port, transportType,
#                     state.cpus.freeCores, state.cpus.usedCores,
#                     state.memory.freeMemory, state.memory.usedMemory,
#                     executorState, tags (list), updated
# plugins/describe.py describe_executor() uses same show_info() fields plus:
#   instances, tasks, serviceInstances
# ---------------------------------------------------------------------------

_EXECUTOR_LIST_ENTRY = {
    "executorId": EXECUTOR_ID,
    "hostname": "exec-host-1",
    "port": 12000,
    "transportType": "HTTP",
    "state": "ACTIVE",
    "tags": [],
    "freeCores": 8,
    "usedCores": 2,
    "freeMemory": 2048,
    "usedMemory": 512,
}

_EXECUTOR_INFO_SEED = {
    "hostname": "exec-host-1",
    "port": 12000,
    "transportType": "HTTP",
    "executorState": "ACTIVE",
    "blacklisted": False,
    "tags": [],
    "updated": 1700000010000,
    # Nested state with CPU/memory NUMA topology
    "state": {
        "executorId": EXECUTOR_ID,
        "cpus": {
            "freeCores": {"0": [2, 3, 4, 5, 6, 7, 8, 9]},
            "usedCores": {"0": [0, 1]},
        },
        "memory": {
            "freeMemory": {"0": 2048},
            "usedMemory": {"0": 512},
        },
    },
    # Running instances (empty by default; populated during test lifecycle)
    "instances": [],
    "tasks": [],
    "serviceInstances": [],
}

# ---------------------------------------------------------------------------
# Application seed data
#
# GET /apis/v1/applications returns a DICT keyed by app_id.
# Each value is a flat dict:
#   name, state, totalCPUs, totalMemory, requiredInstances, healthyInstances,
#   created, updated
# (from plugins/applications.py list_apps())
#
# GET /apis/v1/applications/<app_id> returns the flat summary dict directly.
#
# GET /apis/v1/applications/<app_id>/instances returns a list of instance dicts:
#   instanceId, localInfo.{hostname, ports.{portName: {hostPort, containerPort, portType}}},
#   state, errorMessage, created, updated
# (from plugins/appinstances.py list_instances() and show_instance())
# ---------------------------------------------------------------------------

_APP_INSTANCE_SEED = {
    "instanceId": "AI-test-app-inst-001",
    "appId": "TEST_APP-1",
    "appName": "TEST_APP",
    "executorId": EXECUTOR_ID,
    "localInfo": {
        "hostname": "exec-host-1",
        "ports": {
            "main": {
                "hostPort": 32000,
                "containerPort": 8080,
                "portType": "TCP",
            }
        },
    },
    "state": "HEALTHY",
    "errorMessage": "",
    "resources": [
        {"type": "CPU", "cores": {"0": [0]}},
        {"type": "MEMORY", "memoryInMB": {"0": 128}},
    ],
    "metadata": {},
    "created": 1700000000000,
    "updated": 1700000001000,
}

_APP_SEED: dict[str, dict] = {
    "TEST_APP-1": {
        # Flat summary (returned by /applications and /applications/<id>)
        "summary": {
            "id": "TEST_APP-1",
            "name": "TEST_APP",
            "version": "1",
            "state": "RUNNING",
            "totalCPUs": 1,
            "totalMemory": 128,
            "requiredInstances": 1,
            "healthyInstances": 1,
            "created": 1700000000000,
            "updated": 1700000001000,
        },
        "spec": {
            "name": "TEST_APP",
            "version": "1",
            "type": "SERVICE",
            "executable": {
                "type": "DOCKER",
                "url": "ghcr.io/appform-io/perf-test-server-httplib",
            },
            "resources": [
                {"type": "CPU", "count": 1},
                {"type": "MEMORY", "sizeInMB": 128},
            ],
            "exposureSpec": {
                "vhost": "testapp.local",
                "portName": "main",
                "mode": "ALL",
            },
        },
        "instances": [copy.deepcopy(_APP_INSTANCE_SEED)],
    },
    "TEST_APP_DEV-1": {
        "summary": {
            "id": "TEST_APP_DEV-1",
            "name": "TEST_APP_DEV",
            "version": "1",
            "state": "RUNNING",
            "totalCPUs": 1,
            "totalMemory": 128,
            "requiredInstances": 1,
            "healthyInstances": 1,
            "created": 1700000000000,
            "updated": 1700000001000,
        },
        "spec": {
            "name": "TEST_APP_DEV",
            "version": "1",
            "type": "SERVICE",
            "executable": {
                "type": "DOCKER",
                "url": "ghcr.io/appform-io/perf-test-server-httplib",
            },
            "resources": [
                {"type": "CPU", "count": 1},
                {"type": "MEMORY", "sizeInMB": 128},
            ],
        },
        "instances": [],
    },
}

# ---------------------------------------------------------------------------
# Local service seed data
#
# GET /apis/v1/localservices returns a DICT keyed by svc_id.
# Each value needs flat fields:
#   name, state, activationState, totalCPUs, totalMemory,
#   instancesPerHost, healthyInstances, created, updated
# (from plugins/localservices.py list_services())
#
# Instances need same shape as app instances but with serviceId instead of appId.
# (from plugins/localserviceinstances.py list_instances() / show_instance())
# ---------------------------------------------------------------------------

_LS_SEED: dict[str, dict] = {
    "TEST_LOCAL_SERVICE-1": {
        "summary": {
            "id": "TEST_LOCAL_SERVICE-1",
            "name": "TEST_LOCAL_SERVICE",
            "version": "1",
            "state": "INACTIVE",
            "activationState": "INACTIVE",
            "totalCPUs": 0,
            "totalMemory": 0,
            "instancesPerHost": 1,
            "requiredInstances": 0,
            "healthyInstances": 0,
            "totalInstances": 0,
            "created": 1700000000000,
            "updated": 1700000001000,
        },
        "spec": {
            "name": "TEST_LOCAL_SERVICE",
            "version": "1",
            "type": "LOCAL_SERVICE",
            "executable": {
                "type": "DOCKER",
                "url": "ghcr.io/appform-io/perf-test-server-httplib",
            },
            "resources": [
                {"type": "CPU", "count": 1},
                {"type": "MEMORY", "sizeInMB": 128},
            ],
        },
        "instances": [],
    },
}

_TASK_SEED: dict[str, dict] = {}  # populated on task create


# ---------------------------------------------------------------------------
# Mutable state (deep-copied from seeds so each server instance is isolated)
# ---------------------------------------------------------------------------

class DroveState:
    """Mutable in-memory state for the mock server."""

    def __init__(self):
        self.apps: dict[str, dict] = copy.deepcopy(_APP_SEED)
        self.local_services: dict[str, dict] = copy.deepcopy(_LS_SEED)
        self.tasks: dict[str, dict] = copy.deepcopy(_TASK_SEED)  # key: f"{src}/{tid}"
        self.executor_list_entry: dict = copy.deepcopy(_EXECUTOR_LIST_ENTRY)
        self.executor_info: dict = copy.deepcopy(_EXECUTOR_INFO_SEED)
        self.maintenance: bool = False

    # ------------------------------------------------------------------
    # App helpers
    # ------------------------------------------------------------------

    def get_app(self, app_id: str) -> dict | None:
        return self.apps.get(app_id)

    def create_app(self, spec: dict) -> str:
        name = spec.get("name", "UNKNOWN")
        version = spec.get("version", "1")
        app_id = f"{name}-{version}"
        now = int(time.time() * 1000)
        self.apps[app_id] = {
            "summary": {
                "id": app_id,
                "name": name,
                "version": version,
                "state": "MONITORING",
                "totalCPUs": 0,
                "totalMemory": 0,
                "requiredInstances": 0,
                "healthyInstances": 0,
                "created": now,
                "updated": now,
            },
            "spec": spec,
            "instances": [],
        }
        return app_id

    def scale_app(self, app_id: str, count: int):
        if app_id not in self.apps:
            return
        app = self.apps[app_id]
        now = int(time.time() * 1000)
        app["summary"]["requiredInstances"] = count
        app["summary"]["state"] = "RUNNING" if count > 0 else "MONITORING"
        app["summary"]["updated"] = now
        # Simulate instances
        current = len(app["instances"])
        if count > current:
            for i in range(current, count):
                app["instances"].append({
                    "instanceId": f"AI-{app_id.lower()}-inst-{i:03d}",
                    "appId": app_id,
                    "appName": app["summary"]["name"],
                    "executorId": self.executor_info["state"]["executorId"],
                    "localInfo": {
                        "hostname": "exec-host-1",
                        "ports": {
                            "main": {
                                "hostPort": 32000 + i,
                                "containerPort": 8080,
                                "portType": "TCP",
                            }
                        },
                    },
                    "state": "HEALTHY",
                    "errorMessage": "",
                    "resources": [
                        {"type": "CPU", "cores": {"0": [i % 10]}},
                        {"type": "MEMORY", "memoryInMB": {"0": 128}},
                    ],
                    "metadata": {},
                    "created": now,
                    "updated": now,
                })
        elif count < current:
            app["instances"] = app["instances"][:count]
        app["summary"]["healthyInstances"] = len(app["instances"])
        app["summary"]["totalCPUs"] = len(app["instances"])
        app["summary"]["totalMemory"] = len(app["instances"]) * 128

    def suspend_app(self, app_id: str):
        if app_id not in self.apps:
            return
        now = int(time.time() * 1000)
        self.apps[app_id]["summary"]["state"] = "MONITORING"
        self.apps[app_id]["summary"]["requiredInstances"] = 0
        self.apps[app_id]["summary"]["healthyInstances"] = 0
        self.apps[app_id]["summary"]["totalCPUs"] = 0
        self.apps[app_id]["summary"]["totalMemory"] = 0
        self.apps[app_id]["summary"]["updated"] = now
        self.apps[app_id]["instances"] = []

    def destroy_app(self, app_id: str):
        self.apps.pop(app_id, None)

    def restart_app(self, app_id: str):
        """Simulate rolling restart — state stays RUNNING."""
        pass  # no-op for mock

    # ------------------------------------------------------------------
    # Local service helpers
    # ------------------------------------------------------------------

    def get_ls(self, svc_id: str) -> dict | None:
        return self.local_services.get(svc_id)

    def create_ls(self, spec: dict) -> str:
        name = spec.get("name", "UNKNOWN")
        version = spec.get("version", "1")
        svc_id = f"{name}-{version}"
        now = int(time.time() * 1000)
        self.local_services[svc_id] = {
            "summary": {
                "id": svc_id,
                "name": name,
                "version": version,
                "state": "INACTIVE",
                "activationState": "INACTIVE",
                "totalCPUs": 0,
                "totalMemory": 0,
                "instancesPerHost": 1,
                "requiredInstances": 0,
                "healthyInstances": 0,
                "totalInstances": 0,
                "created": now,
                "updated": now,
            },
            "spec": spec,
            "instances": [],
        }
        return svc_id

    def activate_ls(self, svc_id: str):
        if svc_id not in self.local_services:
            return
        svc = self.local_services[svc_id]
        now = int(time.time() * 1000)
        svc["summary"]["state"] = "ACTIVE"
        svc["summary"]["activationState"] = "ACTIVE"
        svc["summary"]["requiredInstances"] = 1
        svc["summary"]["updated"] = now
        if not svc["instances"]:
            svc["instances"].append({
                "instanceId": f"SI-{svc_id.lower()}-inst-000",
                "serviceId": svc_id,
                "serviceName": svc["summary"]["name"],
                "executorId": self.executor_info["state"]["executorId"],
                "localInfo": {
                    "hostname": "exec-host-1",
                    "ports": {
                        "main": {
                            "hostPort": 33000,
                            "containerPort": 8080,
                            "portType": "TCP",
                        }
                    },
                },
                "state": "HEALTHY",
                "errorMessage": "",
                "resources": [
                    {"type": "CPU", "cores": {"0": [0]}},
                    {"type": "MEMORY", "memoryInMB": {"0": 128}},
                ],
                "metadata": {},
                "created": now,
                "updated": now,
            })
        svc["summary"]["healthyInstances"] = len(svc["instances"])
        svc["summary"]["totalInstances"] = len(svc["instances"])
        svc["summary"]["totalCPUs"] = len(svc["instances"])
        svc["summary"]["totalMemory"] = len(svc["instances"]) * 128

    def deactivate_ls(self, svc_id: str):
        if svc_id not in self.local_services:
            return
        svc = self.local_services[svc_id]
        now = int(time.time() * 1000)
        svc["summary"]["state"] = "INACTIVE"
        svc["summary"]["activationState"] = "INACTIVE"
        svc["summary"]["requiredInstances"] = 0
        svc["summary"]["healthyInstances"] = 0
        svc["summary"]["totalInstances"] = 0
        svc["summary"]["totalCPUs"] = 0
        svc["summary"]["totalMemory"] = 0
        svc["summary"]["updated"] = now
        svc["instances"] = []

    def destroy_ls(self, svc_id: str):
        self.local_services.pop(svc_id, None)

    def restart_ls(self, svc_id: str):
        """Simulate restart: deactivate + re-activate with new instance ID."""
        if svc_id not in self.local_services:
            return
        self.deactivate_ls(svc_id)
        self.activate_ls(svc_id)
        # Use a fresh instance ID to simulate a real restart
        svc = self.local_services[svc_id]
        svc["instances"][0]["instanceId"] = (
            f"SI-{svc_id.lower()}-inst-{int(time.time()) % 10000:04d}"
        )

    # ------------------------------------------------------------------
    # Task helpers
    # ------------------------------------------------------------------

    def _task_key(self, source_app: str, task_id: str) -> str:
        return f"{source_app}/{task_id}"

    def get_task(self, source_app: str, task_id: str) -> dict | None:
        return self.tasks.get(self._task_key(source_app, task_id))

    def create_task(self, spec: dict) -> str:
        source = spec.get("sourceAppName", "UNKNOWN")
        task_id = spec.get("taskId", f"T-{int(time.time())}")
        key = self._task_key(source, task_id)
        now = int(time.time() * 1000)
        self.tasks[key] = {
            "taskId": task_id,
            "sourceAppName": source,
            "instanceId": f"TI-{task_id.lower()}-000",
            "executorId": self.executor_info["state"]["executorId"],
            "hostname": "exec-host-1",
            "state": "RUNNING",
            # Fields required by tasks.py show_task()
            "resources": [
                {"type": "CPU", "cores": {"0": [0]}},
                {"type": "MEMORY", "memoryInMB": {"0": 128}},
            ],
            "executable": {
                "type": "DOCKER",
                "url": spec.get("executable", {}).get("url", "docker://mock-task"),
            },
            "volumes": [],
            "logging": {"type": "LOCAL"},
            "metadata": {},
            "taskResult": {},
            "errorMessage": "",
            "created": now,
            "updated": now,
            "spec": spec,
        }
        return task_id

    def kill_task(self, source_app: str, task_id: str):
        key = self._task_key(source_app, task_id)
        if key in self.tasks:
            self.tasks[key]["state"] = "STOPPED"


# ---------------------------------------------------------------------------
# Flask application factory
# ---------------------------------------------------------------------------

def create_app(state: DroveState | None = None) -> Flask:
    """Build and return a configured Flask app using the given DroveState."""
    if state is None:
        state = DroveState()

    app = Flask(__name__)
    app.config["TESTING"] = True

    # Silence Flask request logs during tests (set to WARNING)
    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.WARNING)

    def ok(data: Any = None):
        payload: dict = {"status": "SUCCESS"}
        if data is not None:
            payload["data"] = data
        return jsonify(payload)

    def err(message: str, code: int = 400):
        return jsonify({"status": "ERROR", "message": message}), code

    # ------------------------------------------------------------------ ping
    @app.route("/apis/v1/ping")
    def ping():
        return ok("pong")

    # ------------------------------------------------------------------ cluster
    @app.route("/apis/v1/cluster")
    def cluster_summary():
        num_active = sum(
            1 for a in state.apps.values()
            if a["summary"].get("state") == "RUNNING"
        )
        data = {
            "state": "NORMAL" if not state.maintenance else "MAINTENANCE",
            # leader must be a plain string (show_leader does: print("Cluster leader: " + data["leader"]))
            "leader": "controller-1:10000",
            "freeCores": 8,
            "usedCores": 2,
            "freeMemory": 2048,
            "usedMemory": 512,
            "totalCores": 10,
            "totalMemory": 2560,
            "numExecutors": 1,
            # show_summary uses both numActiveApplications and numApplications
            "numApplications": len(state.apps),
            "numActiveApplications": num_active,
            "numLocalServices": len(state.local_services),
        }
        return ok(data)

    @app.route("/apis/v1/cluster/executors")
    def executor_list():
        # Returns a list; each entry has executorId at top level (not "id")
        return ok([state.executor_list_entry])

    @app.route("/apis/v1/cluster/executors/<exec_id>")
    def executor_info(exec_id: str):
        if exec_id != state.executor_info["state"]["executorId"]:
            return err(f"Executor {exec_id} not found", 404)
        return ok(state.executor_info)

    @app.route("/apis/v1/cluster/events")
    def cluster_events():
        return ok([])

    @app.route("/apis/v1/endpoints")
    def endpoints():
        vhost_filter = request.args.get("vhost")
        result = []
        for app_data in state.apps.values():
            spec = app_data.get("spec", {})
            exposure = spec.get("exposureSpec")
            if exposure:
                vhost = exposure.get("vhost", "")
                if not vhost_filter or vhost_filter in vhost:
                    result.append({
                        "vhost": vhost,
                        "portName": exposure.get("portName", "main"),
                        "appId": spec.get("name", ""),
                    })
        return ok(result)

    @app.route("/apis/v1/cluster/maintenance/set", methods=["POST"])
    def maintenance_set():
        state.maintenance = True
        return ok({"state": "MAINTENANCE"})

    @app.route("/apis/v1/cluster/maintenance/unset", methods=["POST"])
    def maintenance_unset():
        state.maintenance = False
        return ok({"state": "NORMAL"})

    @app.route("/apis/v1/cluster/executors/blacklist", methods=["POST"])
    def executor_blacklist():
        return ok({"successful": [], "failed": []})

    @app.route("/apis/v1/cluster/executors/unblacklist", methods=["POST"])
    def executor_unblacklist():
        return ok({"successful": [], "failed": []})

    # ------------------------------------------------------------------ apps
    @app.route("/apis/v1/applications")
    def apps_list():
        # CLI does: for app_id, app_data in data.items(): ...
        # So return a DICT keyed by app_id, each value is the flat summary dict.
        result = {app_id: app_data["summary"] for app_id, app_data in state.apps.items()}
        return ok(result)

    @app.route("/apis/v1/applications/<app_id>")
    def app_summary(app_id: str):
        app = state.get_app(app_id)
        if app is None:
            return err(f"App {app_id} not found", 404)
        # Return the flat summary dict directly
        return ok(app["summary"])

    @app.route("/apis/v1/applications/<app_id>/spec")
    def app_spec(app_id: str):
        app = state.get_app(app_id)
        if app is None:
            return err(f"App {app_id} not found", 404)
        return ok(app["spec"])

    @app.route("/apis/v1/applications/<app_id>/instances")
    def app_instances(app_id: str):
        app = state.get_app(app_id)
        if app is None:
            return ok([])
        return ok(app["instances"])

    @app.route("/apis/v1/applications/<app_id>/instances/old")
    def app_instances_old(app_id: str):
        return ok([])

    @app.route("/apis/v1/applications/<app_id>/instances/<inst_id>")
    def app_instance_info(app_id: str, inst_id: str):
        app = state.get_app(app_id)
        if app is None:
            return err(f"App {app_id} not found", 404)
        for inst in app["instances"]:
            if inst["instanceId"] == inst_id:
                return ok(inst)
        return err(f"Instance {inst_id} not found", 404)

    @app.route("/apis/v1/applications/operations", methods=["POST"])
    def app_operations():
        body = request.get_json(force=True, silent=True) or {}
        op_type = body.get("type", "")

        if op_type == "CREATE":
            spec = body.get("spec", {})
            app_id = state.create_app(spec)
            return ok({"appId": app_id})

        elif op_type in ("SCALE",):
            app_id = body.get("appId", "")
            instances = body.get("requiredInstances", 0)
            if app_id not in state.apps:
                return err(f"App {app_id} not found", 404)
            state.scale_app(app_id, instances)
            return ok({"appId": app_id})

        elif op_type == "START_INSTANCES":
            app_id = body.get("appId", "")
            additional = body.get("instances", 0)
            if app_id not in state.apps:
                return err(f"App {app_id} not found", 404)
            current = len(state.apps[app_id]["instances"])
            state.scale_app(app_id, current + additional)
            return ok({"appId": app_id})

        elif op_type == "SUSPEND":
            app_id = body.get("appId", "")
            if app_id not in state.apps:
                return err(f"App {app_id} not found", 404)
            state.suspend_app(app_id)
            return ok({"appId": app_id})

        elif op_type == "DESTROY":
            app_id = body.get("appId", "")
            if app_id not in state.apps:
                return err(f"App {app_id} not found", 404)
            state.destroy_app(app_id)
            return ok({"appId": app_id})

        elif op_type in ("ROLLING_RESTART", "RESTART", "REPLACE_INSTANCES"):
            app_id = body.get("appId", "")
            if app_id not in state.apps:
                return err(f"App {app_id} not found", 404)
            state.restart_app(app_id)
            return ok({"appId": app_id})

        elif op_type == "STOP_INSTANCES":
            app_id = body.get("appId", "")
            instance_ids = body.get("instanceIds", [])
            if app_id not in state.apps:
                return err(f"App {app_id} not found", 404)
            app = state.apps[app_id]
            app["instances"] = [
                i for i in app["instances"] if i["instanceId"] not in instance_ids
            ]
            app["summary"]["healthyInstances"] = len(app["instances"])
            return ok({"appId": app_id})

        else:
            return err(f"Unknown operation type: {op_type}", 400)

    @app.route("/apis/v1/applications/operations/<app_id>/cancel", methods=["POST"])
    def app_operation_cancel(app_id: str):
        return ok({"appId": app_id, "message": "Operation cancelled"})

    # ------------------------------------------------------------------ local services
    @app.route("/apis/v1/localservices")
    def ls_list():
        # CLI does: for service_id, service_data in data.items(): ...
        # Return DICT keyed by svc_id, each value is the flat summary dict.
        result = {svc_id: svc_data["summary"] for svc_id, svc_data in state.local_services.items()}
        return ok(result)

    @app.route("/apis/v1/localservices/<svc_id>")
    def ls_summary(svc_id: str):
        svc = state.get_ls(svc_id)
        if svc is None:
            return err(f"Local service {svc_id} not found", 404)
        return ok(svc["summary"])

    @app.route("/apis/v1/localservices/<svc_id>/spec")
    def ls_spec(svc_id: str):
        svc = state.get_ls(svc_id)
        if svc is None:
            return err(f"Local service {svc_id} not found", 404)
        return ok(svc["spec"])

    @app.route("/apis/v1/localservices/<svc_id>/instances")
    def ls_instances(svc_id: str):
        svc = state.get_ls(svc_id)
        if svc is None:
            return ok([])
        return ok(svc["instances"])

    @app.route("/apis/v1/localservices/<svc_id>/instances/old")
    def ls_instances_old(svc_id: str):
        return ok([])

    @app.route("/apis/v1/localservices/<svc_id>/instances/<inst_id>")
    def ls_instance_info(svc_id: str, inst_id: str):
        svc = state.get_ls(svc_id)
        if svc is None:
            return err(f"Local service {svc_id} not found", 404)
        for inst in svc["instances"]:
            if inst["instanceId"] == inst_id:
                return ok(inst)
        return err(f"Instance {inst_id} not found", 404)

    @app.route("/apis/v1/localservices/operations", methods=["POST"])
    def ls_operations():
        body = request.get_json(force=True, silent=True) or {}
        op_type = body.get("type", "")

        if op_type == "CREATE":
            spec = body.get("spec", {})
            svc_id = state.create_ls(spec)
            return ok({"serviceId": svc_id})

        elif op_type == "ACTIVATE":
            svc_id = body.get("serviceId", "")
            if svc_id not in state.local_services:
                return err(f"Local service {svc_id} not found", 404)
            state.activate_ls(svc_id)
            return ok({"serviceId": svc_id})

        elif op_type == "DEACTIVATE":
            svc_id = body.get("serviceId", "")
            if svc_id not in state.local_services:
                return err(f"Local service {svc_id} not found", 404)
            state.deactivate_ls(svc_id)
            return ok({"serviceId": svc_id})

        elif op_type == "DESTROY":
            svc_id = body.get("serviceId", "")
            if svc_id not in state.local_services:
                return err(f"Local service {svc_id} not found", 404)
            state.destroy_ls(svc_id)
            return ok({"serviceId": svc_id})

        elif op_type in ("RESTART", "ROLLING_RESTART"):
            svc_id = body.get("serviceId", "")
            if svc_id not in state.local_services:
                return err(f"Local service {svc_id} not found", 404)
            state.restart_ls(svc_id)
            return ok({"serviceId": svc_id})

        elif op_type == "UPDATE_INSTANCE_COUNT":
            svc_id = body.get("serviceId", "")
            if svc_id not in state.local_services:
                return err(f"Local service {svc_id} not found", 404)
            count = body.get("instancesPerHost", 1)
            state.local_services[svc_id]["summary"]["instancesPerHost"] = count
            return ok({"serviceId": svc_id})

        elif op_type == "DEPLOY_TEST_INSTANCE":
            svc_id = body.get("serviceId", "")
            if svc_id not in state.local_services:
                return err(f"Local service {svc_id} not found", 404)
            # Just activate for mock purposes
            state.activate_ls(svc_id)
            return ok({"serviceId": svc_id})

        else:
            return err(f"Unknown operation type: {op_type}", 400)

    @app.route("/apis/v1/localservices/operations/<svc_id>/cancel", methods=["POST"])
    def ls_operation_cancel(svc_id: str):
        return ok({"serviceId": svc_id, "message": "Operation cancelled"})

    # ------------------------------------------------------------------ tasks
    @app.route("/apis/v1/tasks")
    def tasks_list():
        app_filter = request.args.get("app")
        result = []
        for task in state.tasks.values():
            if task.get("state") == "RUNNING":
                if not app_filter or task.get("sourceAppName") == app_filter:
                    result.append(task)
        return ok(result)

    @app.route("/apis/v1/tasks/<source_app>/instances/<task_id>")
    def task_show(source_app: str, task_id: str):
        task = state.get_task(source_app, task_id)
        if task is None:
            return err(f"Task {source_app}/{task_id} not found", 404)
        return ok(task)

    @app.route("/apis/v1/tasks/operations", methods=["POST"])
    def task_operations():
        body = request.get_json(force=True, silent=True) or {}
        op_type = body.get("type", "")

        if op_type == "CREATE":
            spec = body.get("spec", {})
            task_id = state.create_task(spec)
            return ok({"taskId": task_id})

        elif op_type == "KILL":
            source = body.get("sourceAppName", "")
            task_id = body.get("taskId", "")
            state.kill_task(source, task_id)
            return ok({"taskId": task_id})

        else:
            return err(f"Unknown task operation: {op_type}", 400)

    # ------------------------------------------------------------------ logfiles
    @app.route("/apis/v1/logfiles/<prefix>/<domain>/<obj_id>/list")
    def logfiles_list(prefix: str, domain: str, obj_id: str):
        return jsonify({"files": ["output.log", "errors.log"], "path": f"/logs/{prefix}/{domain}/{obj_id}"})

    @app.route("/apis/v1/logfiles/<prefix>/<domain>/<obj_id>/read/<name>")
    def logfiles_read(prefix: str, domain: str, obj_id: str, name: str):
        offset = request.args.get("offset", 0)
        return jsonify({
            "data": f"[mock log] {name} offset={offset}\n",
            "offset": int(offset) + 30,
            "length": 30,
        })

    @app.route("/apis/v1/logfiles/<prefix>/<domain>/<obj_id>/download/<name>")
    def logfiles_download(prefix: str, domain: str, obj_id: str, name: str):
        from flask import Response
        content = f"[mock log download] {name}\nLine 1\nLine 2\n"
        return Response(content, mimetype="text/plain")

    return app


# ---------------------------------------------------------------------------
# Server runner (used by the pytest fixture)
# ---------------------------------------------------------------------------

class MockDroveServer:
    """Wraps a Flask app running in a background daemon thread."""

    def __init__(self):
        self.state = DroveState()
        self._app = create_app(self.state)
        self._server = None
        self._thread = None
        self.host = "127.0.0.1"
        self.port: int = 0

    def start(self):
        import socket
        from werkzeug.serving import make_server

        # Find a free ephemeral port: bind to port 0, record the assigned port,
        # then close the socket so Werkzeug can bind to it by port number.
        # (Passing fd= to make_server is unreliable — it fails silently when the
        #  socket is closed before the fd is consumed.)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, 0))
        self.port = sock.getsockname()[1]
        sock.close()  # release the port so make_server can re-bind to it

        self._server = make_server(self.host, self.port, self._app)

        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="MockDroveServer",
            daemon=True,
        )
        self._thread.start()
        time.sleep(0.2)  # give the server a moment to start accepting connections

    def stop(self):
        if self._server:
            self._server.shutdown()
        if self._thread:
            self._thread.join(timeout=5)

    @property
    def endpoint(self) -> str:
        return f"http://{self.host}:{self.port}"

    def reset(self):
        """Reset state to seed data — call between test modules if needed."""
        self.state.__init__()
