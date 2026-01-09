"""
Describe plugin for drove-cli - detailed human-readable resource information, largely inspired by 'kubectl describe'.

This plugin adds 'drove describe' commands for viewing detailed resource info:
- drove describe executor <executor-id>  : Show detailed executor information
- drove describe app <app-id>            : Show detailed application information
- drove describe cluster                 : Show detailed cluster information
- drove describe instance <app-id> <instance-id> : Show detailed instance information
- drove describe task <source-app> <task-id>     : Show detailed task information
- drove describe localservice <service-id>       : Show detailed local service information
- drove describe lsinstance <service-id> <instance-id> : Show detailed local service instance

Usage:
  drove describe executor 93b6b6f3-c7c8-3824-afc9-cb6d0b32454c
  drove describe app MYAPP-1
  drove describe cluster
  drove describe instance MYAPP-1 AI-abc123
  drove describe task MYAPP TI-abc123
  drove describe localservice MYSERVICE-1
  drove describe lsinstance MYSERVICE-1 SI-581fa549-b78c-45f4-a098-44fcb8540c2d
"""

import argparse
import droveclient
import droveutils
import json
import plugins

from types import SimpleNamespace


class Describe(plugins.DrovePlugin):
    def __init__(self) -> None:
        pass

    def populate_options(self, drove_client: droveclient.DroveClient, subparser: argparse.ArgumentParser):
        parser = subparser.add_parser("describe", help="Show detailed information about a resource")
        commands = parser.add_subparsers(help="Available describe commands")

        # describe executor
        sub_parser = commands.add_parser("executor", help="Show detailed executor information")
        sub_parser.add_argument("executor_id", metavar="executor-id", help="Executor ID")
        sub_parser.add_argument("--json", "-j", dest="output_json", help="Output as JSON", action="store_true")
        sub_parser.set_defaults(func=self.describe_executor)

        # describe app
        sub_parser = commands.add_parser("app", help="Show detailed application information")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.add_argument("--json", "-j", dest="output_json", help="Output as JSON", action="store_true")
        sub_parser.set_defaults(func=self.describe_app)

        # describe cluster
        sub_parser = commands.add_parser("cluster", help="Show detailed cluster information")
        sub_parser.add_argument("--json", "-j", dest="output_json", help="Output as JSON", action="store_true")
        sub_parser.set_defaults(func=self.describe_cluster)

        # describe instance
        sub_parser = commands.add_parser("instance", help="Show detailed application instance information")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.add_argument("instance_id", metavar="instance-id", help="Instance ID")
        sub_parser.add_argument("--json", "-j", dest="output_json", help="Output as JSON", action="store_true")
        sub_parser.set_defaults(func=self.describe_instance)

        # describe task
        sub_parser = commands.add_parser("task", help="Show detailed task information")
        sub_parser.add_argument("source_app", metavar="source-app", help="Source Application Name")
        sub_parser.add_argument("task_id", metavar="task-id", help="Task ID")
        sub_parser.add_argument("--json", "-j", dest="output_json", help="Output as JSON", action="store_true")
        sub_parser.set_defaults(func=self.describe_task)

        # describe localservice
        sub_parser = commands.add_parser("localservice", help="Show detailed local service information")
        sub_parser.add_argument("service_id", metavar="service-id", help="Local Service ID")
        sub_parser.add_argument("--json", "-j", dest="output_json", help="Output as JSON", action="store_true")
        sub_parser.set_defaults(func=self.describe_localservice)

        # describe lsinstance
        sub_parser = commands.add_parser("lsinstance", help="Show detailed local service instance information")
        sub_parser.add_argument("service_id", metavar="service-id", help="Local Service ID")
        sub_parser.add_argument("instance_id", metavar="instance-id", help="Instance ID")
        sub_parser.add_argument("--json", "-j", dest="output_json", help="Output as JSON", action="store_true")
        sub_parser.set_defaults(func=self.describe_lsinstance)

        super().populate_options(drove_client, parser)

    def describe_executor(self, options: SimpleNamespace):
        """Show detailed executor information."""
        try:
            raw = self.drove_client.get("/apis/v1/cluster/executors/{id}".format(id=options.executor_id))
        except droveclient.DroveException as e:
            droveutils.print_drove_error(e, options.debug if hasattr(options, 'debug') else False)
            return

        if options.output_json:
            droveutils.print_json(raw)
            return

        self._print_section("Executor Details")
        print(f"  ID:              {raw['state']['executorId']}")
        print(f"  Hostname:        {raw['hostname']}")
        print(f"  Port:            {raw['port']}")
        print(f"  Transport:       {raw['transportType']}")
        print(f"  Blacklisted:     {'yes' if raw.get('blacklisted', False) else 'no'}")
        print(f"  Tags:            {', '.join(raw.get('tags', [])) or 'none'}")
        print(f"  Last Updated:    {droveutils.to_date(raw['updated'])}")

        self._print_section("CPU Resources")
        for numa_node, free_cores in raw['state']['cpus'].get('freeCores', {}).items():
            used_cores = raw['state']['cpus'].get('usedCores', {}).get(numa_node, [])
            print(f"  NUMA Node {numa_node}:")
            print(f"    Free Cores:  {', '.join(map(str, sorted(free_cores))) if free_cores else 'none'}")
            print(f"    Used Cores:  {', '.join(map(str, sorted(used_cores))) if used_cores else 'none'}")

        self._print_section("Memory Resources")
        for numa_node, free_mem in raw['state']['memory'].get('freeMemory', {}).items():
            used_mem = raw['state']['memory'].get('usedMemory', {}).get(numa_node, 0)
            print(f"  NUMA Node {numa_node}:")
            print(f"    Free Memory: {free_mem:,} MB")
            print(f"    Used Memory: {used_mem:,} MB")

        instances = raw.get('instances', [])
        tasks = raw.get('tasks', [])
        service_instances = raw.get('serviceInstances', [])

        self._print_section(f"App Instances ({len(instances)})")
        if instances:
            for inst in instances:
                state_marker = self._get_state_marker(inst['state'])
                print(f"  {state_marker} {inst['instanceId']}")
                print(f"      App: {inst['appName']} ({inst['appId']})")
                print(f"      State: {inst['state']}")
                cpu_count = self._get_resource_count(inst, 'CPU')
                mem_count = self._get_resource_sum(inst, 'MEMORY')
                print(f"      Resources: {cpu_count} CPU, {mem_count:,} MB Memory")
                if inst.get('errorMessage'):
                    print(f"      Error: {inst['errorMessage']}")
        else:
            print("  No application instances running on this executor")

        self._print_section(f"Tasks ({len(tasks)})")
        if tasks:
            for task in tasks:
                state_marker = self._get_state_marker(task['state'])
                print(f"  {state_marker} {task['taskId']}")
                print(f"      Source App: {task['sourceAppName']}")
                print(f"      State: {task['state']}")
                cpu_count = self._get_resource_count(task, 'CPU')
                mem_count = self._get_resource_sum(task, 'MEMORY')
                print(f"      Resources: {cpu_count} CPU, {mem_count:,} MB Memory")
        else:
            print("  No tasks running on this executor")

        self._print_section(f"Local Service Instances ({len(service_instances)})")
        if service_instances:
            for inst in service_instances:
                state_marker = self._get_state_marker(inst['state'])
                print(f"  {state_marker} {inst['instanceId']}")
                print(f"      Service: {inst['serviceName']} ({inst['serviceId']})")
                print(f"      State: {inst['state']}")
        else:
            print("  No local service instances running on this executor")

    def describe_app(self, options: SimpleNamespace):
        """Show detailed application information."""
        try:
            summary = self.drove_client.get("/apis/v1/applications/{app_id}".format(app_id=options.app_id))
            spec = self.drove_client.get("/apis/v1/applications/{app_id}/spec".format(app_id=options.app_id))
            instances = self.drove_client.get("/apis/v1/applications/{app_id}/instances".format(app_id=options.app_id))
        except droveclient.DroveException as e:
            droveutils.print_drove_error(e, options.debug if hasattr(options, 'debug') else False)
            return

        if options.output_json:
            droveutils.print_json({
                "summary": summary,
                "spec": spec,
                "instances": instances
            })
            return

        self._print_section("Application Details")
        print(f"  ID:                {summary.get('appId', options.app_id)}")
        print(f"  Name:              {summary.get('name', 'N/A')}")
        print(f"  State:             {summary.get('state', 'N/A')}")
        print(f"  Created:           {droveutils.to_date(summary.get('created', 0))}")
        print(f"  Updated:           {droveutils.to_date(summary.get('updated', 0))}")

        self._print_section("Instance Summary")
        print(f"  Required:          {summary.get('requiredInstances', 0)}")
        print(f"  Healthy:           {summary.get('healthyInstances', 0)}")
        print(f"  Total CPU:         {summary.get('totalCPUs', 0)}")
        print(f"  Total Memory:      {summary.get('totalMemory', 0):,} MB")

        self._print_section("Specification")
        print(f"  Executable Type:   {spec.get('executable', {}).get('type', 'N/A')}")
        if spec.get('executable', {}).get('type') == 'DOCKER':
            docker = spec.get('executable', {})
            print(f"  Docker Image:      {docker.get('url', 'N/A')}")

        resources = spec.get('resources', [])
        for res in resources:
            if res.get('type') == 'CPU':
                print(f"  CPU per Instance:  {res.get('count', 'N/A')}")
            elif res.get('type') == 'MEMORY':
                print(f"  Memory per Inst:   {res.get('sizeInMB', 'N/A')} MB")

        ports = spec.get('exposedPorts', [])
        if ports:
            self._print_section("Exposed Ports")
            for port in ports:
                print(f"  - {port.get('name', 'unnamed')}: {port.get('port', 'N/A')} ({port.get('type', 'N/A')})")

        health_checks = spec.get('healthChecks', [])
        if health_checks:
            self._print_section("Health Checks")
            for hc in health_checks:
                print(f"  - Mode: {hc.get('mode', {}).get('type', 'N/A')}")
                if hc.get('mode', {}).get('type') == 'HTTP':
                    print(f"    Path: {hc.get('mode', {}).get('path', 'N/A')}")
                    print(f"    Port: {hc.get('mode', {}).get('portName', 'N/A')}")

        placement = spec.get('placementPolicy', {})
        if placement:
            self._print_section("Placement Policy")
            print(f"  Type:              {placement.get('type', 'N/A')}")

        self._print_section(f"Instances ({len(instances) if instances else 0})")
        if instances:
            for inst in instances:
                state_marker = self._get_state_marker(inst['state'])
                host = inst.get('localInfo', {}).get('hostname', 'N/A')
                print(f"  {state_marker} {inst['instanceId']}")
                print(f"      Host: {host}")
                print(f"      State: {inst['state']}")
                print(f"      Created: {droveutils.to_date(inst.get('created', 0))}")
                if inst.get('errorMessage'):
                    print(f"      Error: {inst['errorMessage']}")
        else:
            print("  No instances running (scale up to start instances)")

    def describe_cluster(self, options: SimpleNamespace):
        """Show detailed cluster information."""
        try:
            raw = self.drove_client.get("/apis/v1/cluster")
            executors = self.drove_client.get("/apis/v1/cluster/executors")
        except droveclient.DroveException as e:
            droveutils.print_drove_error(e, options.debug if hasattr(options, 'debug') else False)
            return

        if options.output_json:
            droveutils.print_json({
                "cluster": raw,
                "executors": executors
            })
            return

        self._print_section("Cluster Overview")
        print(f"  State:             {raw.get('state', 'N/A')}")
        print(f"  Leader:            {raw.get('leader', 'N/A')}")

        self._print_section("Resource Utilization")
        total_cores = raw.get('totalCores', 0)
        used_cores = raw.get('usedCores', 0)
        free_cores = raw.get('freeCores', 0)
        core_util = (used_cores / max(total_cores, 1)) * 100

        total_mem = raw.get('totalMemory', 0)
        used_mem = raw.get('usedMemory', 0)
        free_mem = raw.get('freeMemory', 0)
        mem_util = (used_mem / max(total_mem, 1)) * 100

        print(f"  CPU:")
        print(f"    Total:           {total_cores}")
        print(f"    Used:            {used_cores}")
        print(f"    Free:            {free_cores}")
        print(f"    Utilization:     {core_util:.1f}%")
        print(f"  Memory:")
        print(f"    Total:           {total_mem:,} MB")
        print(f"    Used:            {used_mem:,} MB")
        print(f"    Free:            {free_mem:,} MB")
        print(f"    Utilization:     {mem_util:.1f}%")

        self._print_section("Workload Summary")
        print(f"  Executors:         {raw.get('numExecutors', 0)}")
        print(f"  Applications:      {raw.get('numActiveApplications', 0)} active / {raw.get('numApplications', 0)} total")

        self._print_section(f"Executors ({len(executors) if executors else 0})")
        if executors:
            for exe in executors:
                state = exe.get('state', 'UNKNOWN')
                state_marker = self._get_state_marker(state)
                print(f"  {state_marker} {exe.get('executorId', 'N/A')}")
                print(f"      Host: {exe.get('hostname', 'N/A')}:{exe.get('port', 'N/A')}")
                print(f"      CPU: {exe.get('usedCores', 0)}/{exe.get('usedCores', 0) + exe.get('freeCores', 0)} used")
                print(f"      Memory: {exe.get('usedMemory', 0):,}/{exe.get('usedMemory', 0) + exe.get('freeMemory', 0):,} MB used")
                print(f"      Tags: {', '.join(exe.get('tags', [])) or 'none'}")
        else:
            print("  No executors registered in the cluster")

    def describe_instance(self, options: SimpleNamespace):
        """Show detailed application instance information."""
        try:
            raw = self.drove_client.get(
                "/apis/v1/applications/{app_id}/instances/{instance_id}".format(
                    app_id=options.app_id,
                    instance_id=options.instance_id
                )
            )
        except droveclient.DroveException as e:
            droveutils.print_drove_error(e, options.debug if hasattr(options, 'debug') else False)
            return

        if options.output_json:
            droveutils.print_json(raw)
            return

        self._print_section("Instance Details")
        print(f"  Instance ID:       {raw.get('instanceId', 'N/A')}")
        print(f"  Application ID:    {raw.get('appId', 'N/A')}")
        print(f"  State:             {raw.get('state', 'N/A')}")
        print(f"  Created:           {droveutils.to_date(raw.get('created', 0))}")
        print(f"  Updated:           {droveutils.to_date(raw.get('updated', 0))}")

        local_info = raw.get('localInfo', {})
        if local_info:
            self._print_section("Host Information")
            print(f"  Hostname:          {local_info.get('hostname', 'N/A')}")
            print(f"  Executor ID:       {local_info.get('executorId', 'N/A')}")

            ports = local_info.get('ports', {})
            if ports:
                self._print_section("Port Mappings")
                for port_name, port_info in ports.items():
                    container_port = port_info.get('containerPort', 'N/A')
                    host_port = port_info.get('hostPort', 'N/A')
                    port_type = port_info.get('portType', 'N/A')
                    print(f"  {port_name}:")
                    print(f"    Container Port:  {container_port}")
                    print(f"    Host Port:       {host_port}")
                    print(f"    Type:            {port_type}")

        resources = raw.get('resources', [])
        if resources:
            self._print_section("Resources")
            for res in resources:
                res_type = res.get('type', 'UNKNOWN')
                if res_type == 'CPU':
                    cores = res.get('cores', {})
                    total_cores = sum(len(v) for v in cores.values())
                    print(f"  CPU Cores:         {total_cores}")
                    for numa, core_list in cores.items():
                        print(f"    NUMA {numa}:        {', '.join(map(str, sorted(core_list)))}")
                elif res_type == 'MEMORY':
                    memory = res.get('memoryInMB', {})
                    total_mem = sum(memory.values())
                    print(f"  Memory:            {total_mem:,} MB")
                    for numa, mem_mb in memory.items():
                        print(f"    NUMA {numa}:        {mem_mb:,} MB")

        metadata = raw.get('metadata', {})
        if metadata:
            self._print_section("Metadata")
            for key, value in metadata.items():
                print(f"  {key}: {value}")

        error_msg = raw.get('errorMessage', '').strip()
        if error_msg:
            self._print_section("Error")
            print(f"  {error_msg}")

    def describe_task(self, options: SimpleNamespace):
        """Show detailed task information."""
        try:
            raw = self.drove_client.get(
                "/apis/v1/tasks/{source_app}/instances/{task_id}".format(
                    source_app=options.source_app,
                    task_id=options.task_id
                )
            )
        except droveclient.DroveException as e:
            droveutils.print_drove_error(e, options.debug if hasattr(options, 'debug') else False)
            return

        if options.output_json:
            droveutils.print_json(raw)
            return

        self._print_section("Task Details")
        print(f"  Task ID:           {raw.get('taskId', 'N/A')}")
        print(f"  Source App:        {raw.get('sourceAppName', 'N/A')}")
        print(f"  State:             {raw.get('state', 'N/A')}")
        print(f"  Created:           {droveutils.to_date(raw.get('created', 0))}")
        print(f"  Updated:           {droveutils.to_date(raw.get('updated', 0))}")

        local_info = raw.get('localInfo', {})
        if local_info:
            self._print_section("Host Information")
            print(f"  Hostname:          {local_info.get('hostname', 'N/A')}")
            print(f"  Executor ID:       {local_info.get('executorId', 'N/A')}")

            ports = local_info.get('ports', {})
            if ports:
                self._print_section("Port Mappings")
                for port_name, port_info in ports.items():
                    container_port = port_info.get('containerPort', 'N/A')
                    host_port = port_info.get('hostPort', 'N/A')
                    port_type = port_info.get('portType', 'N/A')
                    print(f"  {port_name}:")
                    print(f"    Container Port:  {container_port}")
                    print(f"    Host Port:       {host_port}")
                    print(f"    Type:            {port_type}")
        else:
            self._print_section("Host Information")
            print("  Not yet assigned to an executor")

        resources = raw.get('resources', [])
        if resources:
            self._print_section("Resources")
            for res in resources:
                res_type = res.get('type', 'UNKNOWN')
                if res_type == 'CPU':
                    cores = res.get('cores', {})
                    total_cores = sum(len(v) for v in cores.values())
                    print(f"  CPU Cores:         {total_cores}")
                    for numa, core_list in cores.items():
                        print(f"    NUMA {numa}:        {', '.join(map(str, sorted(core_list)))}")
                elif res_type == 'MEMORY':
                    memory = res.get('memoryInMB', {})
                    total_mem = sum(memory.values())
                    print(f"  Memory:            {total_mem:,} MB")
                    for numa, mem_mb in memory.items():
                        print(f"    NUMA {numa}:        {mem_mb:,} MB")

        task_result = raw.get('taskResult', {})
        if task_result:
            self._print_section("Task Result")
            print(f"  Status:            {task_result.get('status', 'N/A')}")
            print(f"  Exit Code:         {task_result.get('exitCode', 'N/A')}")
            if task_result.get('message'):
                print(f"  Message:           {task_result.get('message')}")

        metadata = raw.get('metadata', {})
        if metadata:
            self._print_section("Metadata")
            for key, value in metadata.items():
                print(f"  {key}: {value}")

        error_msg = raw.get('errorMessage', '').strip()
        if error_msg:
            self._print_section("Error")
            print(f"  {error_msg}")

    def describe_localservice(self, options: SimpleNamespace):
        """Show detailed local service information."""
        try:
            summary = self.drove_client.get("/apis/v1/localservices/{service_id}".format(service_id=options.service_id))
            spec = self.drove_client.get("/apis/v1/localservices/{service_id}/spec".format(service_id=options.service_id))
            instances = self.drove_client.get("/apis/v1/localservices/{service_id}/instances".format(service_id=options.service_id))
        except droveclient.DroveException as e:
            droveutils.print_drove_error(e, options.debug if hasattr(options, 'debug') else False)
            return

        if options.output_json:
            droveutils.print_json({
                "summary": summary,
                "spec": spec,
                "instances": instances
            })
            return

        self._print_section("Local Service Details")
        print(f"  ID:                {summary.get('serviceId', options.service_id)}")
        print(f"  Name:              {summary.get('name', 'N/A')}")
        print(f"  State:             {summary.get('state', 'N/A')}")
        print(f"  Created:           {droveutils.to_date(summary.get('created', 0))}")
        print(f"  Updated:           {droveutils.to_date(summary.get('updated', 0))}")

        self._print_section("Instance Summary")
        print(f"  Required:          {summary.get('requiredInstances', 0)}")
        print(f"  Healthy:           {summary.get('healthyInstances', 0)}")
        print(f"  Total CPU:         {summary.get('totalCPUs', 0)}")
        print(f"  Total Memory:      {summary.get('totalMemory', 0):,} MB")

        self._print_section("Specification")
        print(f"  Executable Type:   {spec.get('executable', {}).get('type', 'N/A')}")
        if spec.get('executable', {}).get('type') == 'DOCKER':
            docker = spec.get('executable', {})
            print(f"  Docker Image:      {docker.get('url', 'N/A')}")

        resources = spec.get('resources', [])
        for res in resources:
            if res.get('type') == 'CPU':
                print(f"  CPU per Instance:  {res.get('count', 'N/A')}")
            elif res.get('type') == 'MEMORY':
                print(f"  Memory per Inst:   {res.get('sizeInMB', 'N/A')} MB")

        ports = spec.get('exposedPorts', [])
        if ports:
            self._print_section("Exposed Ports")
            for port in ports:
                print(f"  - {port.get('name', 'unnamed')}: {port.get('port', 'N/A')} ({port.get('type', 'N/A')})")

        placement = spec.get('placementPolicy', {})
        if placement:
            self._print_section("Placement Policy")
            print(f"  Type:              {placement.get('type', 'N/A')}")

        self._print_section(f"Instances ({len(instances) if instances else 0})")
        if instances:
            for inst in instances:
                state_marker = self._get_state_marker(inst['state'])
                host = inst.get('localInfo', {}).get('hostname', 'N/A')
                print(f"  {state_marker} {inst['instanceId']}")
                print(f"      Host: {host}")
                print(f"      State: {inst['state']}")
                print(f"      Created: {droveutils.to_date(inst.get('created', 0))}")
                if inst.get('errorMessage'):
                    print(f"      Error: {inst['errorMessage']}")
        else:
            print("  No instances running (activate to start instances)")

    def describe_lsinstance(self, options: SimpleNamespace):
        """Show detailed local service instance information."""
        try:
            raw = self.drove_client.get(
                "/apis/v1/localservices/{service_id}/instances/{instance_id}".format(
                    service_id=options.service_id,
                    instance_id=options.instance_id
                )
            )
        except droveclient.DroveException as e:
            droveutils.print_drove_error(e, options.debug if hasattr(options, 'debug') else False)
            return

        if options.output_json:
            droveutils.print_json(raw)
            return

        self._print_section("Local Service Instance Details")
        print(f"  Instance ID:       {raw.get('instanceId', 'N/A')}")
        print(f"  Service ID:        {raw.get('serviceId', 'N/A')}")
        print(f"  State:             {raw.get('state', 'N/A')}")
        print(f"  Created:           {droveutils.to_date(raw.get('created', 0))}")
        print(f"  Updated:           {droveutils.to_date(raw.get('updated', 0))}")

        local_info = raw.get('localInfo', {})
        if local_info:
            self._print_section("Host Information")
            print(f"  Hostname:          {local_info.get('hostname', 'N/A')}")
            print(f"  Executor ID:       {local_info.get('executorId', 'N/A')}")

            ports = local_info.get('ports', {})
            if ports:
                self._print_section("Port Mappings")
                for port_name, port_info in ports.items():
                    container_port = port_info.get('containerPort', 'N/A')
                    host_port = port_info.get('hostPort', 'N/A')
                    port_type = port_info.get('portType', 'N/A')
                    print(f"  {port_name}:")
                    print(f"    Container Port:  {container_port}")
                    print(f"    Host Port:       {host_port}")
                    print(f"    Type:            {port_type}")

        resources = raw.get('resources', [])
        if resources:
            self._print_section("Resources")
            for res in resources:
                res_type = res.get('type', 'UNKNOWN')
                if res_type == 'CPU':
                    cores = res.get('cores', {})
                    total_cores = sum(len(v) for v in cores.values())
                    print(f"  CPU Cores:         {total_cores}")
                    for numa, core_list in cores.items():
                        print(f"    NUMA {numa}:        {', '.join(map(str, sorted(core_list)))}")
                elif res_type == 'MEMORY':
                    memory = res.get('memoryInMB', {})
                    total_mem = sum(memory.values())
                    print(f"  Memory:            {total_mem:,} MB")
                    for numa, mem_mb in memory.items():
                        print(f"    NUMA {numa}:        {mem_mb:,} MB")

        metadata = raw.get('metadata', {})
        if metadata:
            self._print_section("Metadata")
            for key, value in metadata.items():
                print(f"  {key}: {value}")

        error_msg = raw.get('errorMessage', '').strip()
        if error_msg:
            self._print_section("Error")
            print(f"  {error_msg}")

    def _print_section(self, title: str):
        """Print a section header."""
        print()
        print(f"{title}:")
        print("-" * (len(title) + 1))

    def _get_state_marker(self, state: str) -> str:
        """Get a visual marker for resource state."""
        state_markers = {
            'HEALTHY': '[OK]',
            'RUNNING': '[OK]',
            'ACTIVE': '[OK]',
            'PENDING': '[..]',
            'STARTING': '[..]',
            'PROVISIONING': '[..]',
            'STOPPED': '[--]',
            'STOPPING': '[--]',
            'DEPROVISIONING': '[--]',
            'FAILED': '[!!]',
            'UNHEALTHY': '[!!]',
            'LOST': '[!!]',
        }
        return state_markers.get(state, '[??]')

    def _get_resource_count(self, item: dict, resource_type: str) -> int:
        resources = item.get('resources', [])
        for res in resources:
            if res.get('type') == resource_type:
                if resource_type == 'CPU':
                    cores = res.get('cores', {})
                    return sum(len(v) for v in cores.values())
        return 0

    def _get_resource_sum(self, item: dict, resource_type: str) -> int:
        resources = item.get('resources', [])
        for res in resources:
            if res.get('type') == resource_type:
                if resource_type == 'MEMORY':
                    memory = res.get('memoryInMB', {})
                    return sum(memory.values())
        return 0
