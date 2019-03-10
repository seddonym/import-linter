from typing import Optional, Dict, Any
import configparser

from importlinter.application.user_options import UserOptions
from importlinter.application.ports import user_options as ports
from importlinter.application import file_finding
from importlinter.application.app_config import settings


class IniFileUserOptionReader(ports.UserOptionReader):
    def read_options(self) -> Optional[UserOptions]:
        config_filenames = file_finding.find_any('setup.cfg')
        if not config_filenames:
            return None
        for config_filename in config_filenames:
            config = configparser.ConfigParser()
            file_contents = settings.FILE_SYSTEM.read(config_filename)
            config.read_string(file_contents)
            if 'import-linter' in config.sections():
                return self._build_from_config(config)
        return None

    def _build_from_config(self, config: configparser.ConfigParser) -> UserOptions:
        session_options = dict(config['import-linter'])
        contract_options = []
        for section_name in config.sections():
            if section_name.startswith('import-linter:'):
                section = config[section_name]
                section_dict: Dict[str, Any] = {}
                for key, value in section.items():
                    if '\n' not in value:
                        section_dict[key] = value
                    else:
                        section_dict[key] = value.strip().split('\n')
                contract_options.append(section_dict)

        return UserOptions(
            session_options=session_options,
            contracts_options=contract_options,
        )
