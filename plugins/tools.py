import argparse
from types import SimpleNamespace
import droveclient
import droveutils
import plugins
from plugins.tools import DroveTool

class Tools(plugins.DrovePlugin):

    def __init__(self) -> None:
        self.registered_tools = {tool for tool in DroveTool.tools}

    def populate_options(self, drove_client: droveclient.DroveClient, subparser: argparse.ArgumentParser):
        parser = subparser.add_parser("tools", help="Tools and Utilities")

        commands = parser.add_subparsers(help="Available tools")
        
        # Register all discovered tools
        for tool_cls in self.registered_tools:
            tool = tool_cls()
            tool.populate_options(drove_client, commands)

    def process(self, options: SimpleNamespace):
        """Handle tools command execution"""
        if hasattr(options, 'func'):
            return options.func(options)
        super().process(options)

    def list_tools(self, options: SimpleNamespace):
        """List registered tools"""
        print("Available tools:")
        for tool_cls in self.__class__.plugins:
            print(f"- {tool_cls.get_plugin_name()}")


    def execute(self, options):
        if hasattr(options, 'tool_instance'):
            return options.tool_instance.execute(options)
        raise ValueError("No tool selected - use one of the available subcommands")
