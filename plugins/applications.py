import argparse
import droveclient
import droveutils
import json
import plugins
import tenacity

from operator import itemgetter
from tenacity import retry
from types import SimpleNamespace

class Applications(plugins.DrovePlugin):
    def __init__(self) -> None:
        pass

    def populate_options(self, drove_client: droveclient.DroveClient, subparser: argparse.ArgumentParser):
        parser = subparser.add_parser("apps", help="Drove application related commands")

        commands = parser.add_subparsers(help="Available commands for application management")

        sub_parser = commands.add_parser("list", help="List all applications")
        sub_parser.add_argument("--sort", "-s", help="Sort output by column", type=int, choices=range(0, 9), default = 0)
        sub_parser.add_argument("--reverse", "-r", help="Sort in reverse order", action="store_true")
        sub_parser.set_defaults(func=self.list_apps)

        sub_parser = commands.add_parser("summary", help="Show a summary for an application")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.set_defaults(func=self.show_summary)

        sub_parser = commands.add_parser("spec", help="Print the raw json spec for an application")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.set_defaults(func=self.show_spec)

        sub_parser = commands.add_parser("create", help="Create application on cluster")
        sub_parser.add_argument("spec_file", metavar="spec-file", help="JSON spec file for the application")
        sub_parser.set_defaults(func=self.create_app)
        
        sub_parser = commands.add_parser("destroy", help="Destroy an app with zero instances")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.set_defaults(func=self.destroy_app)

        sub_parser = commands.add_parser("deploy", help="Deploy new app instances.")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.add_argument("instances", metavar="instances", type=int, help="Number of new instances to be created")
        sub_parser.add_argument("--parallelism", "-p", help="Number of parallel threads to be used to execute operation", type=int, default = 1)
        sub_parser.add_argument("--timeout", "-t", help="Timeout for the operation on the cluster", type=str, default = "5m")
        sub_parser.add_argument("--wait", "-w", help="Wait to ensure instance count is reached", default=False, action="store_true")
        sub_parser.set_defaults(func=self.deploy_app)


        sub_parser = commands.add_parser("scale", help="Scale app to required instances. Will increase or decrease instances on the cluster to match this number")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.add_argument("instances", metavar="instances", type=int, help="Number of instances. Setting this to 0 will suspend the app")
        sub_parser.add_argument("--parallelism", "-p", help="Number of parallel threads to be used to execute operation", type=int, default = 1)
        sub_parser.add_argument("--timeout", "-t", help="Timeout for the operation on the cluster", type=str, default = "5m")
        sub_parser.add_argument("--wait", "-w", help="Wait to ensure instance count is reached", default=False, action="store_true")
        sub_parser.set_defaults(func=self.scale_app)

        sub_parser = commands.add_parser("suspend", help="Suspend the app")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.add_argument("--parallelism", "-p", help="Number of parallel threads to be used to execute operation", type=int, default = 1)
        sub_parser.add_argument("--timeout", "-t", help="Timeout for the operation on the cluster", type=str, default = "5m")
        sub_parser.add_argument("--wait", "-w", help="Wait to ensure all instances are suspended", default=False, action="store_true")
        sub_parser.set_defaults(func=self.suspend_app)

        sub_parser = commands.add_parser("restart", help="Restart am existing app instances.")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.add_argument("--parallelism", "-p", help="Number of parallel threads to be used to execute operation", type=int, default = 1)
        sub_parser.add_argument("--timeout", "-t", help="Timeout for the operation on the cluster", type=str, default = "5m")
        sub_parser.add_argument("--wait", "-w", help="Wait to ensure all instances are replaced", default=False, action="store_true")
        sub_parser.set_defaults(func=self.restart_app)

        sub_parser = commands.add_parser("cancelop", help="Cancel current operation")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.set_defaults(func=self.cancel_app_operation)

        super().populate_options(drove_client, parser)


    def list_apps(self, options: SimpleNamespace):
        data = self.drove_client.get('/apis/v1/applications')
        app_rows = []
        for app_id, app_data in data.items():
            row = []
            row.append(app_id)
            row.append(app_data["name"])
            row.append(app_data["state"])
            row.append(app_data["totalCPUs"])
            row.append(app_data["totalMemory"])
            row.append(app_data["requiredInstances"])
            row.append(app_data["healthyInstances"])
            row.append(droveutils.to_date(app_data["created"]))
            row.append(droveutils.to_date(app_data["updated"]))

            app_rows.append(row)

        app_rows = sorted(app_rows, key=itemgetter(options.sort), reverse=options.reverse)

        headers = ["Id", "Name", "State", "Total CPU", "Total Memory(MB)", "Required Instances", "Healthy Instances", "Created", "Updated"]
        droveutils.print_table(headers, app_rows)

    def show_summary(self, options: SimpleNamespace):
        data = self.drove_client.get("/apis/v1/applications/{app_id}".format(app_id = options.app_id))
        droveutils.print_dict(data)

    def show_spec(self, options: SimpleNamespace):
        data = self.drove_client.get("/apis/v1/applications/{app_id}/spec".format(app_id = options.app_id))
        droveutils.print_json(data)

    def create_app(self, options: SimpleNamespace):
        try:
            with open(options.spec_file, 'r') as fp:
                spec = json.load(fp)
            operation = {
                "type": "CREATE",
                "spec": spec,
                "opSpec": {
                   "timeout": "5m",
                    "parallelism": 1,
                    "failureStrategy": "STOP"
                }
            }
            data = self.drove_client.post("/apis/v1/applications/operations", operation)
            print("Application created with app id: {appid}".format(appid=data["appId"]))
        except (OSError, IOError) as e:
            print("Error creating application. Error: " + str(e))

    def destroy_app(self, options: SimpleNamespace):
        operation = {
            "type": "DESTROY",
            "appId": options.app_id,
            "opSpec": {
                "timeout": "5m",
                "parallelism": 1,
                "failureStrategy": "STOP"
            }
        }
        data = self.drove_client.post("/apis/v1/applications/operations", operation)
        print("Application destroyed")

    def scale_app(self, options: SimpleNamespace):
        operation = {
            "type": "SCALE",
            "appId": options.app_id,
            "requiredInstances": options.instances,
            "opSpec": {
                "timeout": options.timeout,
                "parallelism": options.parallelism,
                "failureStrategy": "STOP"
            }
        }
        data = self.drove_client.post("/apis/v1/applications/operations", operation)
        if options.wait:
            print("Waiting till required scale is reached")
            self.ensure_count(options.app_id, options.instances)
            print("Required number of instances reached")
        else:
            print("Application scaling command accepted. Please use appinstances comand or the UI to check status of deployment")

    def suspend_app(self, options: SimpleNamespace):
        operation = {
            "type": "SUSPEND",
            "appId": options.app_id,
            "opSpec": {
                "timeout": options.timeout,
                "parallelism": options.parallelism,
                "failureStrategy": "STOP"
            }
        }
        data = self.drove_client.post("/apis/v1/applications/operations", operation)
        if options.wait:
            print("Waiting till all instances shut down")
            self.ensure_count(options.app_id, 0)
            print("All instances suspended")
        else:
            print("Application suspend command accepted.")

    def deploy_app(self, options: SimpleNamespace):
        operation = {
            "type": "START_INSTANCES",
            "appId": options.app_id,
            "instances": options.instances,
            "opSpec": {
                "timeout": options.timeout,
                "parallelism": options.parallelism,
                "failureStrategy": "STOP"
            }
        }
        existing_count = 0 if options.wait == False else len(self.drove_client.app_instances(options.app_id))
        data = self.drove_client.post("/apis/v1/applications/operations", operation)
        if options.wait:
            print("Waiting till required scale is reached")
            self.ensure_count(options.app_id, existing_count + options.instances)
            print("Required number of instances reached")
        else:
            print("Application deployment command accepted. Please use appinstances comand or the UI to check status of deployment")

    def restart_app(self, options: SimpleNamespace):
        operation = {
            "type": "REPLACE_INSTANCES",
            "appId": options.app_id,
            "opSpec": {
                "timeout": options.timeout,
                "parallelism": options.parallelism,
                "failureStrategy": "STOP"
            }
        }
        existing = [] if options.wait == False else self.drove_client.app_instances(options.app_id)
        data = self.drove_client.post("/apis/v1/applications/operations", operation)
        if options.wait:
            self.ensure_replaced(options.app_id, set(existing))
            print("All instances replaced")
        else:
            print("Application restart command accepted.")

    def cancel_app_operation(self, options: SimpleNamespace):
        data = self.drove_client.post("/apis/v1/operations/{appId}/cancel".format(appId=options.app_id), None, False)
        print("Operation cancellation request registered :" + data["message"])

    @retry(wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
           retry=tenacity.retry_if_result(lambda x: x == False))
    def ensure_count(self, app_id: str, instances: int) -> bool:
        healthy = len(self.drove_client.app_instances(app_id))
        print("Healthy instances count: {count}".format(count=healthy))
        return healthy == instances

    @retry(wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
           retry=tenacity.retry_if_result(lambda x: x == False))
    def ensure_replaced(self, app_id: str, existing: set) -> bool:
        healthy = self.drove_client.app_instances(app_id)
        overlap = len(existing.intersection(healthy))
        print("Remaining old instance count: {overlap}".format(overlap = overlap))
        return overlap == 0
