import argparse
import droveclient
from plugins import DrovePlugin
from types import SimpleNamespace
import shtab


class DroveCli:
    def __init__(self, parser: argparse.ArgumentParser):
        self.parser = parser
        self.plugins: dict[str, DrovePlugin] = {}
        self.debug = False
        subparsers = parser.add_subparsers(help="Available plugins", dest="plugin")
        drove_client = droveclient.DroveClient()
        for plugin_class in DrovePlugin.plugins:
            plugin = plugin_class()
            # print("Loading plugin: " + str(plugin))
            plugin.populate_options(drove_client=drove_client, subparser=subparsers)
            self.plugins[plugin.name()] = plugin
        parser.set_defaults(func=self.show_help)
        
        
    def run(self):
        args = self.parser.parse_args()
        self.debug = args.debug

        if args.print_completion:
            print(shtab.complete(self.parser, shell=args.print_completion))
            exit(0)

        # Load plugins
        if args.debug:
            print("Selected plugin: " + args.plugin)

        if args.plugin:
            plugin = self.plugins.get(args.plugin)
            if plugin and plugin.needs_client():
                droveclient.build_drove_client(plugin.drove_client, args)
        args.func(args)
    
    def show_help(self, options: SimpleNamespace) -> None:
        self.parser.print_help()
        exit(-1)
