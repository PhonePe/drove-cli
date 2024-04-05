import argparse
import droveclient
import droveutils
import plugins
import tenacity

from operator import itemgetter
from tenacity import retry
from types import SimpleNamespace

class Applications(plugins.DrovePlugin):
    def __init__(self) -> None:
        pass

    def populate_options(self, drove_client: droveclient.DroveClient, subparser: argparse.ArgumentParser):
        parser = subparser.add_parser("appinstances", help="Drove application instance related commands")

        commands = parser.add_subparsers(help="Available commands for application management")

        sub_parser = commands.add_parser("list", help="List all application instances")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.add_argument("--old", "-o", help="Show old instances", action="store_true")
        sub_parser.add_argument("--sort", "-s", help="Sort output by column", type=int, choices=range(0, 6), default = 0)
        sub_parser.add_argument("--reverse", "-r", help="Sort in reverse order", action="store_true")
        sub_parser.set_defaults(func=self.list_instances)

        sub_parser = commands.add_parser("info", help="Print details for an application instance")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.add_argument("instance_id", metavar="instance-id", help="Application Instance ID")
        sub_parser.set_defaults(func=self.show_instance)

        sub_parser = commands.add_parser("logs", help="Print list of logs for application instance")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.add_argument("instance_id", metavar="instance-id", help="Application Instance ID")
        sub_parser.set_defaults(func=self.show_logs_list)

        sub_parser = commands.add_parser("tail", help="Tail log for application instance")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.add_argument("instance_id", metavar="instance-id", help="Application Instance ID")
        sub_parser.add_argument("--log", "-l", default = "output.log", help="Log filename to tail. Default is to tail output.log")
        sub_parser.set_defaults(func=self.log_tail)

        sub_parser = commands.add_parser("download", help="Download log for application instance")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.add_argument("instance_id", metavar="instance-id", help="Application Instance ID")
        sub_parser.add_argument("applogfile", help="Log filename to download")
        sub_parser.add_argument("--out", "-o", help="Filename to download to. Default is the same filename as provided.")
        sub_parser.set_defaults(func=self.log_download)


        sub_parser = commands.add_parser("replace", help="Replace specific app instances with fresh instances")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.add_argument("instance_ids", nargs="+", metavar="instance-id", help="Application Instance IDs")
        sub_parser.add_argument("--parallelism", "-p", help="Number of parallel threads to be used to execute operation", type=int, default = 1)
        sub_parser.add_argument("--timeout", "-t", help="Timeout for the operation on the cluster", type=str, default = "5m")
        sub_parser.add_argument("--wait", "-w", help="Wait to ensure all instances are replaced", default=False, action="store_true")
        sub_parser.set_defaults(func=self.replace)

        sub_parser = commands.add_parser("kill", help="Kill specific app instances")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.add_argument("instance_ids", nargs="+", metavar="instance-id", help="Application Instance IDs")
        sub_parser.add_argument("--parallelism", "-p", help="Number of parallel threads to be used to execute operation", type=int, default = 1)
        sub_parser.add_argument("--timeout", "-t", help="Timeout for the operation on the cluster", type=str, default = "5m")
        sub_parser.add_argument("--wait", "-w", help="Wait to ensure all instances are killed", default=False, action="store_true")
        sub_parser.set_defaults(func=self.kill)

        # sub_parser = commands.add_parser("create", help="Create application")
        # sub_parser.add_argument("definition", help="JSON application definition")
        
        super().populate_options(drove_client, parser)


    def list_instances(self, options: SimpleNamespace):
        api = "/apis/v1/applications/{app_id}/instances"
        if options.old:
            api = "/apis/v1/applications/{app_id}/instances/old"
        data = self.drove_client.get(api.format(app_id = options.app_id))
        #headers = ["Instance ID", "Executor", "CPU", "Memory(MB)", "State", "Error Message", "Created", "Last Updated"]
        headers = ["Instance ID", "Executor Host", "State", "Error Message", "Created", "Last Updated"]
        rows = []
        for instance in data:
            instance_row = []
            instance_row.append(instance["instanceId"])
            try:
                instance_row.append(instance["localInfo"]["hostname"])
            except KeyError:
                instance_row.append("")
            instance_row.append(instance["state"])
            instance_row.append(instance["errorMessage"])
            instance_row.append(droveutils.to_date(instance["created"]))
            instance_row.append(droveutils.to_date(instance["updated"]))

            rows.append(instance_row)
        rows = sorted(rows, key=itemgetter(options.sort), reverse=options.reverse)
        droveutils.print_table(headers, rows)

    def show_instance(self, options):
        raw = self.drove_client.get("/apis/v1/applications/{app_id}/instances/{instance_id}".format(app_id = options.app_id, instance_id=options.instance_id))
        data = dict()
        data["Instance ID"] = raw["instanceId"]
        data["App ID"] = raw["appId"]
        data["State"] = raw["state"]
        data["Host"] = raw.get("localInfo", dict()).get("hostname", "")
        droveutils.populate_resources(raw, data)
        ports = raw.get("localInfo", dict()).get("ports", dict())
        data["Ports"] = ", ".join(["%s: %s" % (key, "{containerPort}->{hostPort} ({portType})".format_map(value)) for (key, value) in ports.items()])
        data["Metadata"] = ", ".join(["%s: %s" % (key,value) for (key, value) in raw.get("metadata", dict())])
        data["Error Message"] = raw.get("errorMessage", "").strip('\n')
        data["Created"] = droveutils.to_date(raw.get("created"))
        data["Last Updated"] = droveutils.to_date(raw.get("updated"))

        droveutils.print_dict(data)

    def show_logs_list(self, options):
        droveutils.list_logs(self.drove_client, "applications", options.app_id, options.instance_id)

    def log_tail(self, options):
        droveutils.tail_log(self.drove_client, "applications", options.app_id, options.instance_id, options.log)
        
    def log_download(self, options):
        filename = options.applogfile
        if options.out and len(options.out) > 0:
            filename = options.out
        droveutils.download_log(self.drove_client, "applications", options.app_id, options.instance_id, options.applogfile, filename)

    def replace(self, options):
        operation = {
            "type": "REPLACE_INSTANCES",
            "appId": options.app_id,
            "instanceIds": options.instance_ids,
            "opSpec": {
                "timeout": options.timeout,
                "parallelism": options.parallelism,
                "failureStrategy": "STOP"
            }
        }
        data = self.drove_client.post("/apis/v1/applications/operations", operation)
        if options.wait:
            self.ensure_replaced(options.app_id, set(options.instance_ids))
            print("All instances replaced")
        else:
            print("Instance(s) replace command accepted.")

    def kill(self, options):
        operation = {
            "type": "STOP_INSTANCES",
            "appId": options.app_id,
            "instanceIds": options.instance_ids,
            "skipRespawn": True,
            "opSpec": {
                "timeout": options.timeout,
                "parallelism": options.parallelism,
                "failureStrategy": "STOP"
            }
        }
        data = self.drove_client.post("/apis/v1/applications/operations", operation)
        if options.wait:
            self.ensure_replaced(options.app_id, set(options.instance_ids))
            print("All instances replaced")
        else:
            print("Instance(s) kill command accepted.")

    @retry(wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
           retry=tenacity.retry_if_result(lambda x: x == False))
    def ensure_replaced(self, app_id: str, existing: set) -> bool:
        healthy = self.drove_client.app_instances(app_id, False)
        overlap = len(existing.intersection(healthy))
        print("Remaining old instance count: {overlap}".format(overlap = overlap))
        return overlap == 0
