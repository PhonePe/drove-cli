import argparse
from operator import itemgetter
import droveclient
import droveutils
import json
import plugins
import time

from types import SimpleNamespace

class Cluster(plugins.DrovePlugin):
    def __init__(self) -> None:
        pass

    def populate_options(self, drove_client: droveclient.DroveClient, subparser: argparse.ArgumentParser):
        parser = subparser.add_parser("cluster", help="Drove cluster related commands")
        
        commands = parser.add_subparsers(help="Available commands for cluster management")

        sub_parser = commands.add_parser("ping", help="Ping the cluster")
        sub_parser.set_defaults(func=self.ping)

        sub_parser = commands.add_parser("summary", help="Show cluster summary")
        sub_parser.set_defaults(func=self.show_summary)

        sub_parser = commands.add_parser("leader", help="Show leader for cluster")
        sub_parser.set_defaults(func=self.show_leader)

        sub_parser = commands.add_parser("endpoints", help="Show all exposed endpoints")
        sub_parser.add_argument("--vhost", "-v", help="Show details only for the specific vhost")

        sub_parser.set_defaults(func=self.show_endpoints)

        sub_parser = commands.add_parser("events", help="Events on the cluster")
        sub_parser.add_argument("--follow", "-f", help="Follow events (Press CTRL-C to kill)", action="store_true")
        sub_parser.add_argument("--type", "-t", help="Output events of only the matching type")
        sub_parser.add_argument("--count", "-c", help="Fetch <count> events at a time.", default=1024, type=int)
        sub_parser.add_argument("--textfmt", "-s", help="Use the format string to print message", type=str, default="{type: <25} | {id: <36} | {time: <20} | {metadata}")
        sub_parser.set_defaults(func=self.handle_events)


        # maintenance_parser = commands.add_parser("maintenance-on", help="Set cluster to maintenance mode")
        # maintenance_parser.set_defaults(func=self.set_maintenance)

        # maintenance_parser = commands.add_parser("maintenance-off", help="Removed maintenance mode on cluster")
        # maintenance_parser.set_defaults(func=self.unset_maintenance)

        # executors_command = commands.add_parser("executors", help="List executors")
        # executors_command.add_argument("--list", "-l", help="List executors", action="store_true")
        # executors_command.add_argument("--info", "-i", dest='executor_id', help="Get detailed info about executor")

        super().populate_options(drove_client, parser)

    def ping(self, options: SimpleNamespace):
        try:
            self.drove_client.get("/apis/v1/ping")
            print("Cluster ping successful")
        except droveclient.DroveException as e:
            print("Error pinging drove cluster: status: {status} message: {message} raw: {raw}"
                  .format(status = e.status_code, message = str(e), raw = e.raw))
        except Exception as e:
            print("Error pinging drove cluster: " + str(e))

    def show_summary(self, options: SimpleNamespace):
        raw = self.drove_client.get("/apis/v1/cluster")
        data = dict()
        data["State"] = raw["state"]
        data["Leader Controller"] = raw.get("leader", "")
        data["Cores"] = "Utilization: {util:.0%} (Total: {total} Used: {used} Free: {free})".format(util = float(raw["usedCores"]/raw["totalCores"]), total=raw["totalCores"], used = raw["usedCores"], free = raw["freeCores"])
        data["Memory"] = "Utilization: {util:.0%} (Total: {total:,} MB Used: {used:,} MB Free: {free:,} MB)".format(util = float(raw["usedMemory"]/raw["totalMemory"]), total = raw["totalMemory"], used = raw["usedMemory"], free = raw["freeMemory"])
        data["Number of live executors"] = raw["numExecutors"]
        data["Applications"] = "Active: {active:,} Total: {total:,}".format(total = raw["numApplications"], active =  raw["numActiveApplications"])

        droveutils.print_dict(data)

    def show_leader(self, options: SimpleNamespace):
        data = self.drove_client.get("/apis/v1/cluster")
        try:
            print("Cluster leader: " + data["leader"])
        except KeyError:
            print("Cluster has no leader")

    def show_endpoints(self, options: SimpleNamespace):
        raw = self.drove_client.get("/apis/v1/endpoints")
        data = sorted(raw, key=itemgetter('vhost', 'appId'))
        if options.vhost:
            data = [d for d in data if d['vhost'] == options.vhost]
        droveutils.print_dict({"endpoints" : data})

    def handle_events(self, options: SimpleNamespace):
        currtime = 0
        while True:
            events = self.drove_client.get("/apis/v1/cluster/events?size={size}&lastSyncTime={time}".format(size=options.count, time=currtime))
            if options.type:
                events = [e for e in events if e['type'] == options.type]
            if len(events) > 0:
                print("\n".join([self.convert_event(options.textfmt, e) for e in events]))
            if not options.follow:
                break
            currtime = droveutils.now()
            time.sleep(1)

    def set_maintenance(self, options: SimpleNamespace):
        print("Maintenance mode set")
    
    def unset_maintenance(self, options: SimpleNamespace):
        print("Maintenance mode unset")

    def convert_event(self, format: str, event: dict) -> str:
        data = dict()
        data["type"] = event["type"]
        data["id"] = event["id"]
        data["time"] = droveutils.to_date(event["time"])
        data["metadata"] = json.dumps(event["metadata"])

        return format.format_map(data)