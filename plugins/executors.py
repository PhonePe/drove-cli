import argparse
from operator import itemgetter
import droveclient
import droveutils
import json
import plugins
import time

from types import SimpleNamespace

class Executors(plugins.DrovePlugin):
    def __init__(self) -> None:
        pass

    def populate_options(self, drove_client: droveclient.DroveClient, subparser: argparse.ArgumentParser):
        parser = subparser.add_parser("executor", help="Drove cluster executor related commands")
        
        commands = parser.add_subparsers(help="Available commands for cluster executor management")

        sub_parser = commands.add_parser("list", help="List all executors")
        sub_parser.set_defaults(func=self.list)

        sub_parser = commands.add_parser("info", help="Show details about executor")
        sub_parser.add_argument("executor_id", metavar="executor-id", help="Executor id for which info is to be shown")
        sub_parser.set_defaults(func=self.show_info)

        sub_parser = commands.add_parser("appinstances", help="Show app instances running on this executor")
        sub_parser.add_argument("executor_id", metavar="executor-id", help="Executor id for which info is to be shown")
        sub_parser.add_argument("--sort", "-s", help="Sort output by column", type=int, choices=range(0, 6), default = 1)
        sub_parser.add_argument("--reverse", "-r", help="Sort in reverse order", action="store_true")
        sub_parser.set_defaults(func=self.show_appinstances)


        sub_parser = commands.add_parser("tasks", help="Show tasks running on this executor")
        sub_parser.add_argument("executor_id", metavar="executor-id", help="Executor id for which info is to be shown")
        sub_parser.add_argument("--sort", "-s", help="Sort output by column", type=int, choices=range(0, 6), default = 1)
        sub_parser.add_argument("--reverse", "-r", help="Sort in reverse order", action="store_true")
        sub_parser.set_defaults(func=self.show_tasks)

        super().populate_options(drove_client, parser)

    def list(self, options: SimpleNamespace):
        raw = self.drove_client.get("/apis/v1/cluster/executors")
        droveutils.print_dict_table(raw, headers={"executorId" : "Executor ID",
                                                "hostname" : "Host",
                                                "port" : "Port",
                                                "transportType" : "Transport",
                                                "freeCores" : "Free Cores",
                                                "usedCores" : "Used Cores",
                                                "freeMemory" : "Free Memory (MB)",
                                                "usedMemory" : "Used Memory (MB)",
                                                "tags" : "Tags",
                                                "state" : "State"})

    def show_info(self, options: SimpleNamespace):
        raw = self.drove_client.get("/apis/v1/cluster/executors/{id}".format(id=options.executor_id))
        # droveutils.print_dict(raw)
        data = dict()
        data["ID"] = raw["state"]["executorId"]
        data["Host"] = raw["hostname"]
        data["Port"] = raw["port"]
        data["Transport"] = raw["transportType"]
        cpu_nodes = dict()
        for key, value in raw["state"]["cpus"]["freeCores"].items():
            cpu_nodes["NUMA node " + str(key)] = "Free cores: " + ",".join(map(str, sorted(value)))
        for key, value in raw["state"]["cpus"]["usedCores"].items():
            cpu_nodes["NUMA node " + str(key)] = cpu_nodes.get("NUMA node " + str(key), "") + " Used cores: " + ",".join(map(str, sorted(value)))
        memory_nodes = dict()
        for key, value in raw["state"]["memory"]["freeMemory"].items():
            memory_nodes["NUMA node " + str(key)] = "Free : {0: ,} MB".format(value)
        for key, value in raw["state"]["memory"]["usedMemory"].items():
            memory_nodes["NUMA node " + str(key)] = memory_nodes.get("NUMA node " + str(key), "") + " Used: {0: ,} MB".format(value)

        data["Resources"] = { "CPU" : cpu_nodes, "Memory" : memory_nodes }
        data["Blacklisted"] = raw["blacklisted"]
        data["Tags"] = ",".join(raw["tags"])
        data["Last Updated"] = droveutils.to_date(raw["updated"])

        droveutils.print_dict(data)

    def show_appinstances(self, options: SimpleNamespace):
        raw = self.drove_client.get("/apis/v1/cluster/executors/{id}".format(id=options.executor_id))
        headers = ["Instance ID", "App name", "App ID", "CPU", "Memory (MB)", "State", "Error Message", "Created", "Last Updated"]
        rows = []
        for instance in raw.get("instances", list()):
            row = []
            row.append(instance["instanceId"])
            row.append(instance["appName"])
            row.append(instance["appId"])
            cpu_list = [r for r in instance.get("resources", list()) if r.get("type", "") == "CPU"]
            if len(cpu_list) > 0:
                row.append(len(cpu_list[0].get("cores", dict())))
            memory_list = [r for r in instance.get("resources", list()) if r.get("type", "") == "MEMORY"]
            if len(memory_list) > 0:
                row.append("{0: ,}".format(sum(memory_list[0].get("memoryInMB", dict()).values())))
            row.append(instance["state"])
            row.append(instance["errorMessage"])
            row.append(droveutils.to_date(instance["created"]))
            row.append(droveutils.to_date(instance["updated"]))

            rows.append(row)
        rows = sorted(rows, key=itemgetter(options.sort), reverse=options.reverse)
        droveutils.print_table(headers, rows)

    def show_tasks(self, options: SimpleNamespace):
        raw = self.drove_client.get("/apis/v1/cluster/executors/{id}".format(id=options.executor_id))
        task_rows = []
        for task in raw.get("tasks", list()):
            if options.app and task["sourceAppName"] != options.app:
                continue
            row = []
            row.append(task["instanceId"])
            row.append(task["sourceAppName"])
            row.append(task["taskId"])
            row.append(task["state"])
            cpu_list = [r for r in task.get("resources", list()) if r.get("type", "") == "CPU"]
            if len(cpu_list) > 0:
                row.append(len(cpu_list[0].get("cores", dict())))
            memory_list = [r for r in task.get("resources", list()) if r.get("type", "") == "MEMORY"]
            if len(memory_list) > 0:
                row.append("{0: ,}".format(sum(memory_list[0].get("memoryInMB", dict()).values())))
            row.append(droveutils.to_date(task["created"]))
            row.append(droveutils.to_date(task["updated"]))

            task_rows.append(row)

        task_rows = sorted(task_rows, key=itemgetter(options.sort), reverse=options.reverse)
        headers = ["Id", "Source App", "Task ID", "State", "CPU", "Memory(MB)", "Created", "Updated"]
        droveutils.print_table(headers, task_rows)