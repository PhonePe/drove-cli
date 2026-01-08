import argparse
import droveclient
import droveutils
import json
import plugins
import tenacity

from operator import itemgetter
from tenacity import retry
from types import SimpleNamespace

class LocalServices(plugins.DrovePlugin):
    def __init__(self) -> None:
        super().__init__()

    def populate_options(self, drove_client: droveclient.DroveClient, subparser: argparse.ArgumentParser):
        parser = subparser.add_parser("localservices", help="Drove local service related commands")

        commands = parser.add_subparsers(help="Available commands for local services management")

        sub_parser = commands.add_parser("list", help="List all local services")
        sub_parser.add_argument("--sort", "-s", help="Sort output by column", type=int, choices=range(0, 9), default = 0)
        sub_parser.add_argument("--reverse", "-r", help="Sort in reverse order", action="store_true")
        sub_parser.set_defaults(func=self.list_services)

        sub_parser = commands.add_parser("summary", help="Show summary for a local service")
        sub_parser.add_argument("service_id", metavar="service-id", help="local services ID")
        sub_parser.set_defaults(func=self.show_summary)

        sub_parser = commands.add_parser("spec", help="Print the raw json spec for an local services")
        sub_parser.add_argument("service_id", metavar="service-id", help="local services ID")
        sub_parser.set_defaults(func=self.show_spec)

        sub_parser = commands.add_parser("create", help="Create a local service on cluster")
        sub_parser.add_argument("spec_file", metavar="spec-file", help="JSON spec file for the local service")
        sub_parser.set_defaults(func=self.create_service)
        sub_parser.add_argument("--instances", "-i", metavar="instances", help="Number instances to run per executor. Default: 1", type=int, default = 1)
        
        sub_parser = commands.add_parser("destroy", help="Destroy an inactive local service")
        sub_parser.add_argument("service_id", metavar="service-id", help="Local service ID")
        sub_parser.set_defaults(func=self.destroy_service)
        
        sub_parser = commands.add_parser("activate", help="Activate a local service")
        sub_parser.add_argument("service_id", metavar="service-id", help="Local service ID")
        sub_parser.set_defaults(func=self.activate_service)


        sub_parser = commands.add_parser("conftest", help="Spin up one instance of service on any machine to ensure it is running")
        sub_parser.add_argument("service_id", metavar="service-id", help="Local service ID")
        sub_parser.set_defaults(func=self.conftest_service)

        
        sub_parser = commands.add_parser("deactivate", help="Deactivate a local service")
        sub_parser.add_argument("service_id", metavar="service-id", help="Local service ID")
        sub_parser.set_defaults(func=self.deactivate_service)

        sub_parser = commands.add_parser("update", help="Update instances count per host for a local service")
        sub_parser.add_argument("service_id", metavar="service-id", help="Local service ID")
        sub_parser.add_argument("count", metavar="count", help="Instance count per executor node", type=int, choices=range(1, 256))
        sub_parser.set_defaults(func=self.update_count)

        sub_parser = commands.add_parser("restart", help="Restart a local service.")
        sub_parser.add_argument("service_id", metavar="service-id", help="Local service ID")
        sub_parser.add_argument("--stop", "-s", action='store_true', help="Stop current instance before spinning up new ones", default = False)
        sub_parser.add_argument("--parallelism", "-p", help="Number of parallel threads to be used to execute operation", type=int, default = 1)
        sub_parser.add_argument("--timeout", "-t", help="Timeout for the operation on the cluster", type=str, default = "5m")
        sub_parser.add_argument("--wait", "-w", help="Wait to ensure all instances are replaced", default=False, action="store_true")
        sub_parser.set_defaults(func=self.restart_service)

        sub_parser = commands.add_parser("cancelop", help="Cancel current operation")
        sub_parser.add_argument("service_id", metavar="service-id", help="Local service ID")
        sub_parser.set_defaults(func=self.cancel_service_operation)

        super().populate_options(drove_client, parser)


    def list_services(self, options: SimpleNamespace):
        data = self.drove_client.get('/apis/v1/localservices')
        service_rows = []
        for service_id, service_data in data.items():
            row = []
            row.append(service_id)
            row.append(service_data["name"])
            row.append(service_data["state"])
            row.append(service_data["activationState"])
            row.append(service_data["totalCPUs"])
            row.append(service_data["totalMemory"])
            row.append(service_data["instancesPerHost"])
            row.append(service_data["healthyInstances"])
            row.append(droveutils.to_date(service_data["created"]))
            row.append(droveutils.to_date(service_data["updated"]))

            service_rows.append(row)

        service_rows = sorted(service_rows, key=itemgetter(options.sort), reverse=options.reverse)

        headers = ["Id", "Name", "State", "Activation State", "Total CPU", "Total Memory(MB)", "Instances Per Host", "Healthy Instances", "Created", "Updated"]
        droveutils.print_table(headers, service_rows)

    def show_summary(self, options: SimpleNamespace):
        data = self.drove_client.get("/apis/v1/localservices/{service_id}".format(service_id = options.service_id))
        droveutils.print_dict(data)

    def show_spec(self, options: SimpleNamespace):
        data = self.drove_client.get("/apis/v1/localservices/{service_id}/spec".format(service_id = options.service_id))
        droveutils.print_json(data)

    def create_service(self, options: SimpleNamespace):
        try:
            with open(options.spec_file, 'r') as fp:
                spec = json.load(fp)
            operation = {
                "type": "CREATE",
                "spec": spec,
                "instancesPerHost": options.instances
            }
            data = self.drove_client.post("/apis/v1/localservices/operations", operation)
            print("Local service created with service id: {serviceId}".format(serviceId=data["serviceId"]))
        except (OSError, IOError) as e:
            print("Error creating local services. Error: " + str(e))

    def destroy_service(self, options: SimpleNamespace):
        operation = {
            "type": "DESTROY",
            "serviceId": options.service_id
        }
        data = self.drove_client.post("/apis/v1/localservices/operations", operation)
        print("Local service destroyed")

    def activate_service(self, options: SimpleNamespace):
        operation = {
            "type": "ACTIVATE",
            "serviceId": options.service_id
        }
        data = self.drove_client.post("/apis/v1/localservices/operations", operation)
        print("Local service activated")

    def conftest_service(self, options: SimpleNamespace):
        operation = {
            "type": "DEPLOY_TEST_INSTANCE",
            "serviceId": options.service_id
        }
        data = self.drove_client.post("/apis/v1/localservices/operations", operation)
        print("Local service activated")

    def deactivate_service(self, options: SimpleNamespace):
        operation = {
            "type": "DEACTIVATE",
            "serviceId": options.service_id
        }
        data = self.drove_client.post("/apis/v1/localservices/operations", operation)
        print("Local service deactivated")

    def update_count(self, options: SimpleNamespace):
        operation = {
            "type": "UPDATE_INSTANCE_COUNT",
            "serviceId": options.service_id,
            "instancesPerHost": options.count
        }
        data = self.drove_client.post("/apis/v1/localservices/operations", operation)
        print("Local service instance count updated")
    
    def restart_service(self, options: SimpleNamespace):
        operation = {
            "type": "RESTART",
            "serviceId": options.service_id,
            "stopFirst": options.stop,
            "opSpec": {
                "timeout": options.timeout,
                "parallelism": options.parallelism,
                "failureStrategy": "STOP"
            }
        }
        existing = [] if options.wait == False else self.drove_client.service_instances(options.service_id)
        data = self.drove_client.post("/apis/v1/localservices/operations", operation)
        if options.wait:
            self.ensure_replaced(options.service_id, set(existing))
            print("All instances replaced")
        else:
            print("Local service restart command accepted.")

    def cancel_service_operation(self, options: SimpleNamespace):
        data = self.drove_client.post("/apis/v1/localservices/operations/{serviceId}/cancel".format(serviceId=options.service_id), None, False)
        print("Operation cancellation request registered :" + data["message"])

    @retry(wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
           retry=tenacity.retry_if_result(lambda x: x == False))
    def ensure_replaced(self, service_id: str, existing: set) -> bool:
        healthy = self.drove_client.service_instances(service_id)
        overlap = len(existing.intersection(healthy))
        print("Remaining old instance count: {overlap}".format(overlap = overlap))
        return overlap == 0
