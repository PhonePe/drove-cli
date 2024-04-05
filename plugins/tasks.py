import argparse
import droveclient
import droveutils
import json
import plugins

from collections import OrderedDict
from operator import itemgetter
from types import SimpleNamespace

class Tasks(plugins.DrovePlugin):
    def __init__(self) -> None:
        pass

    def populate_options(self, drove_client: droveclient.DroveClient, subparser: argparse.ArgumentParser):
        parser = subparser.add_parser("tasks", help="Drove task related commands")

        commands = parser.add_subparsers(help="Available commands for task management")

        sub_parser = commands.add_parser("create", help="Spawn a new task on cluster")
        sub_parser.add_argument("spec_file", metavar="spec-file", help="JSON spec file for the application")
        sub_parser.set_defaults(func=self.create_task)

        sub_parser = commands.add_parser("kill", help="Kill a running task")
        sub_parser.add_argument("source_app_name", metavar="source-app-name", help="Source app name as specified in spec")
        sub_parser.add_argument("task_id", metavar="task-id", help="ID of the task as specified in the spec")
        sub_parser.set_defaults(func=self.kill_task)

        sub_parser = commands.add_parser("list", help="List all active tasks")
        sub_parser.add_argument("--app", "-a", help="Show tasks only for the given source app", type=str)
        sub_parser.add_argument("--sort", "-s", help="Sort output by column", type=int, choices=range(0, 9), default = 0)
        sub_parser.add_argument("--reverse", "-r", help="Sort in reverse order", action="store_true")
        sub_parser.set_defaults(func=self.list_task)

        sub_parser = commands.add_parser("show", help="Shows details about a task")
        sub_parser.add_argument("source_app", metavar="source-app", help="Name of the Drove application that started the task")
        sub_parser.add_argument("task_id", metavar="task-id", help="Task ID")
        sub_parser.set_defaults(func=self.show_task)

        sub_parser = commands.add_parser("logs", help="Print list of logs for task")
        sub_parser.add_argument("source_app", metavar="source-app", help="Name of the Drove application that started the task")
        sub_parser.add_argument("task_id", metavar="task-id", help="Task ID")
        sub_parser.set_defaults(func=self.show_logs_list)

        sub_parser = commands.add_parser("tail", help="Tail log for task")
        sub_parser.add_argument("source_app", metavar="source-app", help="Name of the Drove application that started the task")
        sub_parser.add_argument("task_id", metavar="task-id", help="Task ID")
        sub_parser.add_argument("--file", "-f", default = "output.log", help="Log filename to tail. Default is to tail output.log")
        sub_parser.set_defaults(func=self.log_tail)

        sub_parser = commands.add_parser("download", help="Download log for task")
        sub_parser.add_argument("source_app", metavar="source-app", help="Name of the Drove application that started the task")
        sub_parser.add_argument("task_id", metavar="task-id", help="Task ID")
        sub_parser.add_argument("tasklogfile", help="Log filename to download")
        sub_parser.add_argument("--out", "-o", help="Filename to download to. Default is the same filename as provided.")
        sub_parser.set_defaults(func=self.log_download)
        
        super().populate_options(drove_client, parser)

    def create_task(self, options: SimpleNamespace):
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
            data = self.drove_client.post("/apis/v1/tasks/operations", operation)
            print("Task created. Source App Name: {sourceAppName} Task ID: {taskId}. Drove assigned task ID: {internalTaskId}"
                  .format(internalTaskId=data["taskId"], sourceAppName=spec["sourceAppName"], taskId=spec["taskId"]))
        except (OSError, IOError) as e:
            print("Error creating task. Error: " + str(e))

    def kill_task(self, options: SimpleNamespace):
        operation = {
            "type": "KILL",
            "sourceAppName" : options.source_app_name,
            "taskId" : options.task_id,
            "opSpec": {
                "timeout": "5m",
                "parallelism": 1,
                "failureStrategy": "STOP"
            }
        }
        data = self.drove_client.post("/apis/v1/tasks/operations", operation)
        print("Task kill issued")

    def list_task(self, options: SimpleNamespace):
        data = self.drove_client.get('/apis/v1/tasks')
        task_rows = []
        for task in data:
            if options.app and task["sourceAppName"] != options.app:
                continue
            row = []
            row.append(task["instanceId"])
            row.append(task["sourceAppName"])
            row.append(task["taskId"])
            row.append(task["state"])
            row.append(task.get("hostname", ""))
            cpu_list = [r for r in task.get("resources", list()) if r.get("type", "") == "CPU"]
            if len(cpu_list) > 0:
                row.append(len(cpu_list[0].get("cores", dict())))
            memory_list = [r for r in task.get("resources", list()) if r.get("type", "") == "MEMORY"]
            if len(memory_list) > 0:
                row.append(sum(memory_list[0].get("memoryInMB", dict()).values()))
            row.append(droveutils.to_date(task["created"]))
            row.append(droveutils.to_date(task["updated"]))

            task_rows.append(row)

        task_rows = sorted(task_rows, key=itemgetter(options.sort), reverse=options.reverse)

        headers = ["Id", "Source App", "Task ID", "State", "Host", "CPU", "Memory(MB)", "Created", "Updated"]
        droveutils.print_table(headers, task_rows)

    def show_task(self, options: SimpleNamespace):
        raw = self.drove_client.get("/apis/v1/tasks/{source_app}/instances/{task_id}".format(source_app = options.source_app, task_id = options.task_id))
        data = OrderedDict()
        data["Source App"] = raw["sourceAppName"]
        data["Task ID"] = raw["taskId"]
        data["Instance ID"] = raw["instanceId"]
        data["State"] = raw["state"]
        data["Executor Host"] = raw["hostname"]
        droveutils.populate_resources(raw, data)
        data["Executable"] = "{url} ({type})".format_map(raw["executable"])
        data["Volumes"] = ", ".join(["{pathOnHost} (Mounted as {pathInContainer} in {mode} mode)".format_map(v) for v in raw["volumes"]])
        data["Logging Mode"] = raw.get("logging", dict()).get("type", "")
        data["Metadata"] = ", ".join(["%s: %s" % (key,value) for (key, value) in raw.get("metadata", dict())])
        result = raw.get("taskResult", dict())
        if len(result) > 0:
            data["Result"] = "{status} (Task exit code: {exitCode})".format_map(result)
        else:
            data["Result"] = ""
        data["Error Message"] = raw.get("errorMessage", "").strip('\n')
        data["Created"] = droveutils.to_date(raw.get("created"))
        data["Last Updated"] = droveutils.to_date(raw.get("updated"))

        droveutils.print_dict(data)
        
    def show_logs_list(self, options):
        droveutils.list_logs(self.drove_client, "tasks", options.source_app, options.task_id)

    def log_tail(self, options):
        droveutils.tail_log(self.drove_client, "tasks", options.source_app, options.task_id, options.file)
        
    def log_download(self, options):
        filename = options.tasklogfile
        if options.out and len(options.out) > 0:
            filename = options.out
        droveutils.download_log(self.drove_client, "tasks", options.source_app, options.task_id, options.tasklogfile, filename)