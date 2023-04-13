import argparse
import droveclient
import os
import traceback

from importlib import util
from types import SimpleNamespace


class DrovePlugin:
    plugins = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.plugins.append(cls)

    def __init__(self) -> None:
        self.drove_client: droveclient.DroveClient = None
        self.parser: argparse.ArgumentParser = None
        
    def populate_options(self, drove_client: droveclient.DroveClient, subparser: argparse.ArgumentParser):
        self.drove_client = drove_client
        subparser.set_defaults(func=self.process)
        self.parser = subparser

    def process(self, options: SimpleNamespace):
        self.parser.print_help()
        exit(-1)

def load_module(path):
    name = os.path.split(path)[-1]
    spec = util.spec_from_file_location(name, path)
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

path = os.path.abspath(__file__)
dirpath = os.path.dirname(path)

for fname in os.listdir(dirpath):
    # Load only "real modules"
    if not fname.startswith('.') and \
       not fname.startswith('__') and fname.endswith('.py'):
        try:
            load_module(os.path.join(dirpath, fname))
        except Exception:
            traceback.print_exc()