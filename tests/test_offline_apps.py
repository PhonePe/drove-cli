"""
tests/test_offline_apps.py — offline tests for `drove apps` and `drove describe app`
commands.

All tests use the mock Drove server; no live cluster is required.
Run with:  pytest -m offline tests/test_offline_apps.py
"""
import argparse
import json
from unittest.mock import Mock

import plugins
import pytest

pytestmark = pytest.mark.offline

# App IDs seeded in mock_server.py
EXISTING_APP  = "TEST_APP-1"
CLI_APP_ID    = "TEST_APP-1"   # lifecycle tests use sample/test_app.json → TEST_APP-1


class TestOfflineAppsList:
    def test_apps_list_succeeds(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("apps", "list")
        assert len(out.strip()) > 0

    def test_apps_list_contains_known_app(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("apps", "list")
        assert "TEST_APP" in out, f"Expected TEST_APP in apps list:\n{out}"

    def test_apps_list_has_header_columns(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("apps", "list")
        for col in ["Id", "Name", "State"]:
            assert col in out, f"Column '{col}' missing from apps list:\n{out}"

    def test_apps_list_sort_by_name(self, offline_env):
        from conftest import drove
        result = drove("apps", "list", "--sort", "1", check=False)
        assert result.returncode == 0

    def test_apps_list_sort_reverse(self, offline_env):
        from conftest import drove
        result = drove("apps", "list", "--sort", "1", "--reverse", check=False)
        assert result.returncode == 0


class TestOfflineAppsSummary:
    def test_summary_existing_app(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("apps", "summary", EXISTING_APP)
        assert "TEST_APP" in out

    def test_summary_contains_state(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("apps", "summary", EXISTING_APP)
        assert "state" in out.lower()

    def test_summary_contains_instances(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("apps", "summary", EXISTING_APP)
        assert "Instance" in out or "instance" in out.lower()

    def test_summary_nonexistent_app_not_found(self, offline_env):
        from conftest import drove
        result = drove("apps", "summary", "NONEXISTENT_APP_XYZ-99", check=False)
        assert result.returncode == 0
        assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()


class TestOfflineAppsSpec:
    def test_spec_returns_json(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("apps", "spec", EXISTING_APP)
        data = json.loads(out)
        assert isinstance(data, dict)

    def test_spec_contains_name(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("apps", "spec", EXISTING_APP)
        data = json.loads(out)
        assert "name" in data

    def test_spec_contains_executable(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("apps", "spec", EXISTING_APP)
        data = json.loads(out)
        assert "executable" in data

    def test_spec_contains_resources(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("apps", "spec", EXISTING_APP)
        data = json.loads(out)
        assert "resources" in data


class TestOfflineDescribeApp:
    def test_describe_app_existing(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("describe", "app", EXISTING_APP)
        assert len(out.strip()) > 0

    def test_describe_app_json(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("describe", "app", EXISTING_APP, "--json")
        data = json.loads(out)
        assert isinstance(data, dict)

    def test_describe_app_nonexistent_not_found(self, offline_env):
        from conftest import drove
        result = drove("describe", "app", "NONEXISTENT_APP_XYZ-99", check=False)
        assert result.returncode == 0
        assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()


class TestOfflineAppsLifecycle:
    """
    Full create → scale → restart → suspend → destroy lifecycle via mock.

    Because the mock server is stateful (in-process dict), each operation is
    immediately visible to subsequent GETs — no polling delays needed.

    Uses sample/test_app.json (name=TEST_APP, version=1 → app ID TEST_APP-1).
    """

    def test_app_create(self, offline_env):
        from conftest import drove_ok, APP_SPEC
        out = drove_ok("apps", "create", APP_SPEC, timeout=10)
        # drove prints a success line or the app ID; either is fine
        assert len(out.strip()) >= 0  # just verify no crash

    def test_created_app_listed(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("apps", "list")
        assert CLI_APP_ID in out, f"{CLI_APP_ID} not in apps list:\n{out}"

    def test_app_scale_up(self, offline_env):
        from conftest import drove_ok
        drove_ok("apps", "scale", CLI_APP_ID, "2", timeout=10)
        out = drove_ok("apps", "summary", CLI_APP_ID)
        assert "RUNNING" in out

    def test_app_has_instances_after_scale(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("appinstances", "list", CLI_APP_ID)
        assert "AI-" in out, f"Expected app instance IDs:\n{out}"

    def test_app_describe_after_scale(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("describe", "app", CLI_APP_ID)
        assert CLI_APP_ID in out or "TEST_APP" in out

    def test_app_restart(self, offline_env):
        from conftest import drove_ok
        drove_ok("apps", "restart", CLI_APP_ID, timeout=10)
        out = drove_ok("apps", "summary", CLI_APP_ID)
        assert "RUNNING" in out

    def test_app_scale_down(self, offline_env):
        from conftest import drove_ok
        drove_ok("apps", "scale", CLI_APP_ID, "1", timeout=10)
        out = drove_ok("apps", "summary", CLI_APP_ID)
        assert "RUNNING" in out

    def test_app_suspend(self, offline_env):
        from conftest import drove_ok
        drove_ok("apps", "suspend", CLI_APP_ID, timeout=10)
        out = drove_ok("apps", "summary", CLI_APP_ID)
        assert "MONITORING" in out

    def test_app_destroy(self, offline_env):
        from conftest import drove
        # App is in MONITORING after suspend — destroy should succeed
        result = drove("apps", "destroy", CLI_APP_ID, check=False, timeout=10)
        assert result.returncode == 0

    def test_destroyed_app_not_listed(self, offline_env):
        from conftest import drove_ok
        out = drove_ok("apps", "list")
        assert CLI_APP_ID not in out, f"{CLI_APP_ID} still appears after destroy"


OPERATION_COMMANDS = [
    (("apps", "create"), {"type": "CREATE"}),
    (("apps", "destroy", CLI_APP_ID), {"type": "DESTROY", "appId": CLI_APP_ID}),
    (("apps", "deploy", CLI_APP_ID, "2"), {"type": "START_INSTANCES", "appId": CLI_APP_ID, "instances": 2}),
    (("apps", "scale", CLI_APP_ID, "2"), {"type": "SCALE", "appId": CLI_APP_ID, "requiredInstances": 2}),
    (("apps", "suspend", CLI_APP_ID), {"type": "SUSPEND", "appId": CLI_APP_ID}),
    (("apps", "restart", CLI_APP_ID), {"type": "REPLACE_INSTANCES", "appId": CLI_APP_ID}),
    (("appinstances", "replace", CLI_APP_ID, "AI-test-1", "AI-test-2"),
     {"type": "REPLACE_INSTANCES", "appId": CLI_APP_ID, "instanceIds": ["AI-test-1", "AI-test-2"]}),
    (("appinstances", "kill", CLI_APP_ID, "AI-test-1", "AI-test-2"),
     {"type": "STOP_INSTANCES", "appId": CLI_APP_ID, "instanceIds": ["AI-test-1", "AI-test-2"], "skipRespawn": True}),
]


class TestOfflineOperationMetadata:
    @pytest.mark.parametrize("command, expected", OPERATION_COMMANDS)
    @pytest.mark.parametrize("metadata", [None, {}, {
        "initiator": "ops", "reason": "capacity", "ticket": 123,
        "details": {"approved": True, "tags": ["manual"], "previous": None},
    }])
    def test_operation_payload(self, command, expected, metadata):
        from conftest import APP_SPEC

        client = Mock()
        client.post.return_value = {"appId": CLI_APP_ID}
        plugin = next(plugin_type() for plugin_type in plugins.DrovePlugin.plugins
                      if plugin_type().name() == command[0])
        parser = argparse.ArgumentParser()
        plugin.populate_options(client, parser.add_subparsers())
        args = list(command)
        payload = dict(expected)
        payload["opSpec"] = {"timeout": "5m", "parallelism": 1, "failureStrategy": "STOP"}
        if command[1] == "create":
            args.append(APP_SPEC)
            with open(APP_SPEC) as spec_file:
                payload["spec"] = json.load(spec_file)
        if metadata is not None:
            args += ["--metadata", json.dumps(metadata)]
            payload["operationMetadata"] = metadata

        options = parser.parse_args(args)
        options.func(options)

        client.post.assert_called_once_with("/apis/v1/applications/operations", payload)

    @pytest.mark.parametrize("command, expected", OPERATION_COMMANDS)
    @pytest.mark.parametrize("metadata", [
        "not-json", "[]", "null", '"text"', "42", "true",
        '{"value": NaN}', '{"value": Infinity}', '{"value": -Infinity}', '{"value": 1e400}',
    ])
    def test_invalid_metadata_rejected(self, command, expected, metadata, capsys):
        from conftest import APP_SPEC

        client = Mock()
        plugin = next(plugin_type() for plugin_type in plugins.DrovePlugin.plugins
                      if plugin_type().name() == command[0])
        parser = argparse.ArgumentParser()
        plugin.populate_options(client, parser.add_subparsers())
        args = list(command)
        if command[1] == "create":
            args.append(APP_SPEC)

        with pytest.raises(SystemExit) as error:
            parser.parse_args(args + ["--metadata", metadata])

        assert error.value.code == 2
        assert "metadata must be a JSON object" in capsys.readouterr().err
        client.post.assert_not_called()
