import argparse
import droveclient
import droveutils
import json
import plugins

from operator import itemgetter
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

        # sub_parser = commands.add_parser("create", help="Create application")
        # sub_parser.add_argument("definition", help="JSON application definition")
        
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
        
