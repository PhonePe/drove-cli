import argparse
import droveclient
from plugins import DrovePlugin
from types import SimpleNamespace



class DroveCli:
    def __init__(self, parser: argparse.ArgumentParser):
        self.parser = parser
        self.drove_client = droveclient.DroveClient()
        self.plugins: list = []
        self.debug = False
        subparsers = parser.add_subparsers(help="Available plugins")
        for plugin_class in DrovePlugin.plugins:
            plugin = plugin_class()
            # print("Loading plugin: " + str(plugin))
            plugin.populate_options(drove_client=self.drove_client, subparser=subparsers)
            self.plugins.append(plugin)
        parser.set_defaults(func=self.show_help)
        
        
    def run(self):
        args = self.parser.parse_args()
        self.debug = args.debug
        drove_client = droveclient.build_drove_client(self.drove_client, args=args)
        if drove_client is None:
            return None
        self.drove_client = drove_client

        # Load plugins
        
        args.func(args)
    
    def show_help(self, options: SimpleNamespace) -> None:
        self.parser.print_help()
        exit(-1)
