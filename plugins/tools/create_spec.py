import argparse
import json
import re
import droveclient
from plugins import tools
from typing import Dict, Any, Callable

class CreateSpecTool(tools.DroveTool):
    """Interactive application specification creator"""
    
    _name = "create-spec"
    
    def __init__(self):
        super().__init__()
        self.spec_structure = {
            "name": {"prompt": "Application name", "type": str, "required": True},
            "version": {"prompt": "Version", "type": str, "default": "1.0.0"},
            "type": {
                "prompt": "Type (SERVICE/JOB)", 
                "type": str,
                "choices": ["SERVICE", "JOB"],
                "required": True
            },
            "dependencies": {
                "prompt": "Dependencies (comma separated)",
                "type": list,
                "default": []
            }
        }

    def populate_options(self, drove_client: droveclient.DroveClient, subparser: argparse.ArgumentParser):
        spec_parser = subparser.add_parser(self._name, 
            help="Interactive application spec creation")
        spec_parser.add_argument("--name", help="Application name")
        spec_parser.add_argument("--version", help="Version string")
        spec_parser.add_argument("--type", help="Type (SERVICE/JOB)")
        spec_parser.add_argument("--output", "-o", 
            help="Output file path", default="appspec.json")
        super().populate_options(drove_client, spec_parser)
        

    def process(self, options):
        spec = {}
        for field, config in self.spec_structure.items():
            value = None
            while True:
                # Get input from user or CLI args
                if getattr(options, field, None):
                    value = getattr(options, field)
                else:
                    default = config.get('default', '')
                    choices = f' ({"/".join(config["choices"])})' if 'choices' in config else ''
                    prompt = f"{config['prompt']}{choices} [{'required' if config.get('required') else 'optional'}]: "
                    value = input(prompt) or default

                # Validate input
                if value or not config.get('required'):
                    if self._validate_input(value, config):
                        break
                    self.drove_client.log(f"Invalid value for {field}")
                else:
                    self.drove_client.log(f"{field} is required")

                # Clear invalid value
                setattr(options, field, None)

            # Convert and store validated value
            if config['type'] == list:
                spec[field] = [item.strip() for item in value.split(',')] if value else []
            else:
                spec[field] = config['type'](value) if value else None
        
        with open(options.output, 'w') as f:
            json.dump(spec, f, indent=2)
            
        print(f"Spec file created at {options.output}")

    def _validate_input(self, value: str, field_config: Dict[str, Any]) -> bool:
        if not value and field_config.get('required'):
            return False
            
        if 'choices' in field_config and value not in field_config['choices']:
            return False
            
        try:
            if field_config['type'] == list:
                return isinstance(value.split(','), list)
            return isinstance(field_config['type'](value), field_config['type'])
        except (ValueError, TypeError):
            return False
