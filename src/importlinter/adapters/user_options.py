from typing import Optional
import os
import configparser

from importlinter.application.user_options import UserOptions
from importlinter.application.ports import user_options as ports


class HardcodedUserOptionReader(ports.UserOptionReader):
    def read_options(self) -> Optional[UserOptions]:
        return UserOptions(
            session_options = {
                'root_package_name': 'grimp',
            },
            contracts_options=[
                {
                    'name': 'Layer contract',
                    'class': 'importlinter.contracts.layers.LayersContract',
                    'containers': [
                       'grimp',
                    ],
                    'layers': [
                        'adaptors',
                        'main',
                        'application',
                        'domain',
                    ],
                },
                {
                    'name': 'Independence contract',
                    'class': 'importlinter.contracts.independence.IndependenceContract',
                    'containers': [
                        'grimp',
                    ],
                    'modules': [
                        'grimp.main',
                        'grimp.domain',
                    ],
                },
            ],
        )


class IniFileUserOptionReader(ports.UserOptionReader):
    def read_options(self) -> Optional[UserOptions]:
        config_filenames = self._discover_filenames()
        if not config_filenames:
            return None
        for config_filename in config_filenames:
            config = configparser.ConfigParser()
            config.read(config_filename)
            if 'import-linter' in config.sections():
                return self._build_from_config(config)

    def _discover_filenames(self):
        return [
            os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'setup.cfg'))
        ]

    def _build_from_config(self, config: configparser.ConfigParser) -> UserOptions:
        session_options = config['import-linter']
        contract_options = []
        for section_name in config.sections():
            if section_name.startswith('import-linter:'):
                section = config[section_name]
                contract_name = 'TODO'
                section_dict = {}
                for key, value in section.items():
                    if '\n' not in value:
                        section_dict[key] = value
                    else:
                        section_dict[key] = value.split()
                contract_options.append(section_dict)

        return UserOptions(
            session_options=session_options,
            contracts_options=contract_options,
        )