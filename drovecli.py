import argparse
from types import SimpleNamespace

import droveclient
from plugins import DrovePlugin


class DroveCli:
    def __init__(self, parser: argparse.ArgumentParser):
        self.parser = parser
        self.plugins: list = []
        self.debug = False
        self.drove_client = droveclient.DroveClient()
        subparsers = parser.add_subparsers(help="Available plugins")
        for plugin_class in DrovePlugin.plugins:
            plugin = plugin_class()
            plugin.populate_options(
                drove_client=self.drove_client, subparser=subparsers
            )
            self.plugins.append(plugin)
        parser.set_defaults(func=self.show_help)

    def run(self):
        args = self.parser.parse_args()
        self.debug = args.debug

        # Initialize the drove client if not already done
        if self.drove_client.endpoint is None:
            droveclient.build_drove_client(self.drove_client, args)

        args.func(args)

    def show_help(self, options: SimpleNamespace) -> None:
        self.parser.print_help()
        exit(-1)
