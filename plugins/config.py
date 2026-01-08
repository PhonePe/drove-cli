"""
Config plugin for drove-cli - cluster configuration management.

This plugin adds 'drove config' commands for managing clusters, largely inspired by kubectl context management.
- drove config current-cluster    : Show current default cluster
- drove config get-clusters       : List all configured clusters
- drove config use-cluster <name> : Set default cluster
- drove config view               : Show full config file
- drove config init               : Initialize a new config file
- drove config add-cluster <name> : Add a new cluster to config
- drove config delete-cluster <name> : Remove a cluster from config


Usage:
  drove config use-cluster local
"""

import argparse
import configparser
import os
import plugins

from pathlib import Path
from types import SimpleNamespace


def get_config_file_path() -> str:
    return str(Path.home()) + "/.drove"


def read_config() -> configparser.ConfigParser:
    config_file = get_config_file_path()
    config = configparser.ConfigParser()

    if os.path.isfile(config_file) and os.access(config_file, os.R_OK):
        with open(config_file) as stream:
            config.read_string(stream.read())

    return config


def write_config(config: configparser.ConfigParser) -> None:
    config_file = get_config_file_path()
    with open(config_file, 'w') as f:
        config.write(f)


def get_current_cluster() -> str:
    config = read_config()
    return config.defaults().get('current_cluster')


def set_current_cluster(cluster_name: str) -> None:
    config = read_config()
    config.set('DEFAULT', 'current_cluster', cluster_name)
    write_config(config)


def get_clusters_from_config(config: configparser.ConfigParser) -> list:
    clusters = []
    for section in config.sections():
        endpoint = config[section].get('endpoint', '')
        if endpoint:
            clusters.append({
                'name': section,
                'endpoint': endpoint,
                'has_auth': bool(config[section].get('username') or config[section].get('auth_header')),
                'insecure': config[section].get('insecure', 'false').lower() == 'true'
            })

    if config.defaults().get('endpoint'):
        clusters.insert(0, {
            'name': 'DEFAULT',
            'endpoint': config.defaults().get('endpoint'),
            'has_auth': bool(config.defaults().get('username') or config.defaults().get('auth_header')),
            'insecure': config.defaults().get('insecure', 'false').lower() == 'true'
        })

    return clusters


class Config(plugins.DrovePlugin):
    """Plugin for config/context management commands."""

    def __init__(self) -> None:
        pass

    def populate_options(self, drove_client, subparser: argparse.ArgumentParser):
        parser = subparser.add_parser("config", help="Manage drove cluster configurations")
        commands = parser.add_subparsers(help="Available config commands")

        # get-clusters: List all available clusters
        sub_parser = commands.add_parser("get-clusters", help="List all configured clusters")
        sub_parser.set_defaults(func=self.get_clusters)

        # current-cluster: Show current default
        sub_parser = commands.add_parser("current-cluster", help="Show current default cluster")
        sub_parser.set_defaults(func=self.current_cluster)

        # use-cluster: Set default cluster
        sub_parser = commands.add_parser("use-cluster", help="Set default cluster")
        sub_parser.add_argument("cluster_name", metavar="cluster-name", help="Cluster name to use as default")
        sub_parser.set_defaults(func=self.use_cluster)

        # view: Show full config
        sub_parser = commands.add_parser("view", help="Display the full configuration file")
        sub_parser.add_argument("--raw", "-r", help="Show raw config file content", action="store_true")
        sub_parser.set_defaults(func=self.view_config)

        # init: Initialize config file
        sub_parser = commands.add_parser("init", help="Initialize a new ~/.drove config file")
        sub_parser.add_argument("--endpoint", "-e", help="Drove endpoint URL", required=True)
        sub_parser.add_argument("--name", "-n", help="Cluster name", default="default")
        sub_parser.add_argument("--username", "-u", help="Username for basic auth")
        sub_parser.add_argument("--password", "-p", help="Password for basic auth")
        sub_parser.add_argument("--auth-header", "-t", dest="auth_header", help="Authorization header value")
        sub_parser.add_argument("--insecure", "-i", help="Skip SSL verification", action="store_true")
        sub_parser.set_defaults(func=self.init_config)

        # add-cluster: Add a new cluster to config
        sub_parser = commands.add_parser("add-cluster", help="Add a new cluster to config")
        sub_parser.add_argument("cluster_name", metavar="cluster-name", help="Name for this cluster")
        sub_parser.add_argument("--endpoint", "-e", help="Drove endpoint URL", required=True)
        sub_parser.add_argument("--username", "-u", help="Username for basic auth")
        sub_parser.add_argument("--password", "-p", help="Password for basic auth")
        sub_parser.add_argument("--auth-header", "-t", dest="auth_header", help="Authorization header value")
        sub_parser.add_argument("--insecure", "-i", help="Skip SSL verification", action="store_true")
        sub_parser.set_defaults(func=self.add_cluster)

        # delete-cluster: Remove a cluster from config
        sub_parser = commands.add_parser("delete-cluster", help="Remove a cluster from config")
        sub_parser.add_argument("cluster_name", metavar="cluster-name", help="Cluster name to remove")
        sub_parser.set_defaults(func=self.delete_cluster)

        super().populate_options(drove_client, parser)

    def get_clusters(self, options: SimpleNamespace):
        config = read_config()
        clusters = get_clusters_from_config(config)
        current = get_current_cluster()

        if not clusters:
            print("No clusters configured. Run 'drove config init' to set up.")
            return

        print(f"{'CURRENT':<10} {'NAME':<20} {'ENDPOINT':<50} {'AUTH':<6} {'INSECURE':<8}")
        print("-" * 95)

        for cluster in clusters:
            marker = "*" if cluster['name'] == current else ""
            auth = "yes" if cluster['has_auth'] else "no"
            insecure = "yes" if cluster['insecure'] else "no"
            print(f"{marker:<10} {cluster['name']:<20} {cluster['endpoint']:<50} {auth:<6} {insecure:<8}")

        if current:
            print(f"\nCurrent cluster: {current}")

    def current_cluster(self, options: SimpleNamespace):
        current = get_current_cluster()
        if current:
            print(current)
        else:
            print("No current cluster set. Use 'drove config use-cluster <name>' to set one.")

    def use_cluster(self, options: SimpleNamespace):
        config = read_config()
        cluster_name = options.cluster_name

        # Validate cluster exists
        valid_names = [s for s in config.sections()]
        if cluster_name == 'DEFAULT':
            if config.defaults().get('endpoint'):
                valid_names.append('DEFAULT')

        if cluster_name not in valid_names and cluster_name != 'DEFAULT':
            print(f"Error: cluster '{cluster_name}' not found in config")
            print(f"Available clusters: {', '.join(valid_names) if valid_names else 'none'}")
            return

        set_current_cluster(cluster_name)
        print(f"Switched to cluster \"{cluster_name}\".")

    def view_config(self, options: SimpleNamespace):
        config_file = get_config_file_path()

        if not os.path.isfile(config_file):
            print(f"Config file not found: {config_file}")
            print("Run 'drove config init' to create one.")
            return

        if options.raw:
            with open(config_file, 'r') as f:
                print(f.read())
        else:
            config = read_config()
            current = get_current_cluster()

            print(f"Config file: {config_file}")
            print(f"Current cluster: {current or '(not set)'}")
            print()

            for section in ['DEFAULT'] + config.sections():
                if section == 'DEFAULT':
                    items = dict(config.defaults())
                else:
                    items = dict(config[section])

                if not items.get('endpoint'):
                    continue

                marker = " (current)" if section == current else ""
                print(f"[{section}]{marker}")
                for key, value in items.items():
                    # Mask sensitive values
                    if key in ('password', 'auth_header') and value:
                        display_value = value[:4] + "****" + value[-4:] if len(value) > 8 else "****"
                    else:
                        display_value = value
                    print(f"  {key} = {display_value}")
                print()

    def init_config(self, options: SimpleNamespace):
        config_file = get_config_file_path()

        if os.path.isfile(config_file):
            print(f"Config file already exists: {config_file}")
            print("Use 'drove config add-context' to add more clusters.")
            return

        config = configparser.ConfigParser()
        section = options.name if options.name != 'default' else 'DEFAULT'

        if section != 'DEFAULT':
            config.add_section(section)
            config[section]
        else:
            config.defaults()

        if section == 'DEFAULT':
            config.set('DEFAULT', 'endpoint', options.endpoint)
            if options.username:
                config.set('DEFAULT', 'username', options.username)
            if options.password:
                config.set('DEFAULT', 'password', options.password)
            if options.auth_header:
                config.set('DEFAULT', 'auth_header', options.auth_header)
            if options.insecure:
                config.set('DEFAULT', 'insecure', 'true')
        else:
            config[section]['endpoint'] = options.endpoint
            if options.username:
                config[section]['username'] = options.username
            if options.password:
                config[section]['password'] = options.password
            if options.auth_header:
                config[section]['auth_header'] = options.auth_header
            if options.insecure:
                config[section]['insecure'] = 'true'

        with open(config_file, 'w') as f:
            config.write(f)

        set_current_cluster(section)

        print(f"Config initialized at: {config_file}")
        print(f"Current cluster set to: {section}")

    def add_cluster(self, options: SimpleNamespace):
        """Add a new cluster."""
        config = read_config()
        cluster_name = options.cluster_name

        if cluster_name in config.sections():
            print(f"Error: cluster '{cluster_name}' already exists")
            return

        config.add_section(cluster_name)
        config[cluster_name]['endpoint'] = options.endpoint
        if options.username:
            config[cluster_name]['username'] = options.username
        if options.password:
            config[cluster_name]['password'] = options.password
        if options.auth_header:
            config[cluster_name]['auth_header'] = options.auth_header
        if options.insecure:
            config[cluster_name]['insecure'] = 'true'

        config_file = get_config_file_path()
        with open(config_file, 'w') as f:
            config.write(f)

        print(f"Cluster '{cluster_name}' added to {config_file}")

    def delete_cluster(self, options: SimpleNamespace):
        config = read_config()
        cluster_name = options.cluster_name

        if cluster_name not in config.sections():
            print(f"Error: cluster '{cluster_name}' not found")
            return

        config.remove_section(cluster_name)

        config_file = get_config_file_path()
        with open(config_file, 'w') as f:
            config.write(f)

        current = get_current_cluster()
        if current == cluster_name:
            config.remove_option('DEFAULT', 'current_cluster')
            write_config(config)
            print(f"Cluster '{cluster_name}' deleted and was current cluster (now unset)")
        else:
            print(f"Cluster '{cluster_name}' deleted from {config_file}")
