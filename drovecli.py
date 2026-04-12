import argparse
import os
import droveclient
import droveutils
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

    @staticmethod
    def _print_full_help(parser: argparse.ArgumentParser) -> None:
        """Recursively print help for a parser and all its subcommands."""
        separator = "=" * 72
        print(separator)
        print(parser.format_help())

        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                for _name, subparser in sorted(action.choices.items()):
                    DroveCli._print_full_help(subparser)
                break

    @staticmethod
    def _print_compact_help(parser: argparse.ArgumentParser) -> None:
        """Print a compact one-line-per-command reference for LLM consumption."""
        # Print global options from the root parser
        global_opts = DroveCli._format_opts(parser, skip={"full_help", "compact", "verbose", "print_completion"})
        print(f"drove {global_opts}")

        # Walk the parser tree and collect leaf commands grouped by top-level plugin
        lines_by_group: dict[str, list[str]] = {}
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                for group_name, group_parser in sorted(action.choices.items()):
                    lines_by_group[group_name] = []
                    DroveCli._collect_compact_lines(group_name, group_parser, lines_by_group[group_name])
                break

        for group_name, lines in lines_by_group.items():
            print()
            for line in lines:
                print(line)

    @staticmethod
    def _collect_compact_lines(path: str, parser: argparse.ArgumentParser, lines: list[str]) -> None:
        """Recursively collect compact lines for a parser into the lines list."""
        # Check if this parser has sub-parsers (i.e., it's a group, not a leaf)
        sub_action = None
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                sub_action = action
                break

        if sub_action is not None:
            # This is a group — recurse into its sub-commands
            for name, subparser in sorted(sub_action.choices.items()):
                DroveCli._collect_compact_lines(f"{path} {name}", subparser, lines)
        else:
            # This is a leaf command — build one compact line
            positionals = DroveCli._format_positionals(parser)
            opts = DroveCli._format_opts(parser)
            parts = [path]
            if positionals:
                parts.append(positionals)
            if opts:
                parts.append(opts)
            lines.append(" ".join(parts))

    @staticmethod
    def _format_positionals(parser: argparse.ArgumentParser) -> str:
        """Format positional arguments as <metavar> or <metavar...>."""
        parts = []
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                continue
            if action.option_strings:
                continue  # skip optionals
            if isinstance(action, argparse._HelpAction):
                continue
            metavar = action.metavar or action.dest
            if action.nargs in ("+", "*"):
                parts.append(f"<{metavar}...>")
            else:
                parts.append(f"<{metavar}>")
        return " ".join(parts)

    @staticmethod
    def _format_opts(parser: argparse.ArgumentParser, skip: set = None) -> str:
        """Format optional arguments as [-short VAL] compact notation."""
        skip = skip or set()
        parts = []
        for action in parser._actions:
            if isinstance(action, argparse._HelpAction):
                continue
            if not action.option_strings:
                continue  # skip positionals
            if action.dest in skip:
                continue

            # Pick the shortest flag (prefer -f over --file)
            flags = sorted(action.option_strings, key=len)
            flag = flags[0]

            if isinstance(action, (argparse._StoreTrueAction, argparse._StoreFalseAction, argparse._CountAction)):
                parts.append(f"[{flag}]")
            else:
                metavar = action.metavar or action.dest.upper()
                if isinstance(metavar, tuple):
                    metavar = " ".join(metavar)
                if action.required:
                    parts.append(f"{flag} {metavar}")
                else:
                    parts.append(f"[{flag} {metavar}]")
        return " ".join(parts)

    def run(self):
        args = self.parser.parse_args()
        self.debug = args.debug

        if args.print_completion:
            print(shtab.complete(self.parser, shell=args.print_completion))
            exit(0)

        if args.full_help:
            if args.verbose:
                self._print_full_help(self.parser)
            else:
                self._print_compact_help(self.parser)
            exit(0)

        # Set compact mode for data output
        compact = args.compact or os.environ.get("DROVE_COMPACT", "") == "1"
        droveutils.set_compact(compact)

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
