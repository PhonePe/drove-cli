import argparse
import re
import traceback
from typing import Dict
from typing import List

import pybars
from mako.template import Template

import droveclient
from plugins import tools


class Reader:

    def __init__(self, provided: dict = None, interactive: bool = True):
        self.provided = provided if provided is not None else dict()
        self.interactive = interactive

    def read_str(self, name: str, description: str, required: bool = True, default: any = None,
                 max_length: int = None, pattern: str = None) -> str:
        return self.__read_value(name, description, required, default,
                                 lambda x: Reader.__validate_str(x, max_length=max_length, pattern=pattern))

    def read_choice(self, name: str, description: str, choices: List[str], required: bool = True,
                    default: any = None) -> str:
        return self.__read_value(name, description + f" (Allowed: {choices}) ", required, default,
                                 lambda x: [] if x in choices else [f"Invalid choice. Valid choices are {choices}"])

    def read_int(self, name: str, description: str, required: bool = True, default: any = None,
                 min_value: int = None, max_value: int = None) -> str:
        return self.__read_value(name, description, required, default,
                                 lambda x: Reader.__validate_int(x, min_value=min_value, max_value=max_value))

    def read_list(self, name: str, description: str, reader: callable, default: list = None,
                  required: bool = True) -> list:
        values: list = self.provided.get(name, list())
        while len(values) == 0:
            i = 0
            while True:
                value = reader(name, f"{description} - id {i} (Press ENTER to complete list)", False)
                i += 1
                if value == "":
                    break
                values.append(value)
            if len(values) == 0 and not required:
                break
        return values

    def read_strs(self, name: str, description: str, required: bool = True,
                  max_length: int = None, pattern: str = None) -> List[str]:
        return self.read_list(name=name,
                              description=description,
                              required=required,
                              reader=lambda _name, _description, _required: self.read_str(name=_name,
                                                                                          description=_description,
                                                                                          required=_required,
                                                                                          max_length=max_length,
                                                                                          pattern=pattern))

    def read_kvs(self, name: str, description: str, key_reader: callable, value_reader: callable,
                 required: bool = True) -> dict():
        values: Dict[str, str] = self.provided.get(name, dict())
        while len(values) == 0:
            i = 0
            while True:
                key = key_reader(name, f"{description} - id {i} (Press ENTER to complete list)", False)
                if key == "":
                    break
                value = value_reader(name, f"Value for key {key}", True)
                values[key] = value
                i = i + 1
            if len(values) == 0 and not required:
                break
        return values

    def read_str_kvs(self, name: str, description: str, required: bool = True,
                     max_key_length: int = None, max_value_length: int = None,
                     key_pattern: str = None, value_pattern: str = None) -> Dict[str, str]:
        return self.read_kvs(
            name=name,
            description=description,
            required=required,
            key_reader=lambda _name, _description, _required: self.read_str(
                name=_name,
                description=_description,
                required=_required,
                max_length=max_key_length,
                pattern=key_pattern
            ),
            value_reader=lambda _name, _description, _required: self.read_str(
                name=_name,
                description=_description,
                required=_required,
                max_length=max_value_length,
                pattern=value_pattern
            )
        )

    @staticmethod
    def __validate_str(value: object, max_length: int, pattern: str) -> List[str]:
        str_value = str(value)
        errors = list()
        if pattern is not None and not bool(re.fullmatch(pattern, str_value)):
            errors.append(f"Provided value does not match provided pattern: {pattern}")
        if max_length is not None and 0 < max_length < len(str_value):
            errors.append(f"Provided input is longer than max allowed length: {max_length}")
        return errors

    @staticmethod
    def __validate_int(value: object, min_value: int, max_value: int) -> List[str]:
        try:
            errors = list()
            int_value = int(str(value))
            if min_value is not None and int_value < min_value:
                errors.append(f"Value is less than allowed min: {min_value}")
            if max_value is not None and int_value > max_value:
                errors.append(f"Value is more than allowed max: {max_value}")
            return errors
        except ValueError:
            return ["Value is not an integer"]

    def __read_value(self, name: str, description: str, required: bool = True, default: any = None,
                     validator: callable(str) = None) -> str:
        # If value is passed via argument use that first
        value = self.__ensure_value_for_quiet_mode(default, name, self.provided.get(name, None))
        while True:
            # If required ask for value
            value = self.__read_value_from_user(description, default, required) if value is None else value
            if value is not None:
                errors = validator(value) if validator is not None else []
                if len(errors) > 0:
                    print(f"Errors: {errors}")
                else:
                    return str(value)
            elif not required:
                return u""
            value = None

    def __ensure_value_for_quiet_mode(self, default, name, value):
        if not self.interactive and value is None:
            value = default
            if value is None:
                raise ValueError(f'Value for parameter {name} is not available')
        return value

    @staticmethod
    def __read_value_from_user(description: str, default: any, required: bool):
        prompt = description + (" " if default is None else f"[{default}]") + ": "
        value = input(prompt)
        if value != "":
            return value
        elif required:
            return default
        return None


class CreateSpecTool(tools.DroveTool):
    """Interactive application specification creator"""

    _name = "create-spec"

    def __init__(self):
        super().__init__()
        self.compiler = pybars.Compiler()

    # Rest of the file remains unchanged below this point
    def populate_options(self, drove_client: droveclient.DroveClient, subparser: argparse.ArgumentParser):
        spec_parser = subparser.add_parser(self._name, help="Interactive application spec creation")
        spec_parser.add_argument("template", help="Template path")
        spec_parser.add_argument("--output", "-o", help="Output file path", default="spec.json")
        spec_parser.add_argument("--values", "-v", help="Use values provided in the specified file", type=str)

        super().populate_options(drove_client, spec_parser)

    def process(self, options):
        try:
            template = Template(filename=options.template)
            reader = Reader(provided=dict(), interactive=True)
            print(template.render(reader=reader))
        except Exception as e:
            print("Template parsing error: " + str(e))
            traceback.print_exc()
            return
