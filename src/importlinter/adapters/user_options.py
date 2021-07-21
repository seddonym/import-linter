import configparser
from typing import Any, Dict, Optional

try:
    import toml

    _HAS_TOML = True
except ImportError:
    _HAS_TOML = False

from importlinter.application import file_finding
from importlinter.application.app_config import settings
from importlinter.application.ports import user_options as ports
from importlinter.application.user_options import UserOptions


class IniFileUserOptionReader(ports.UserOptionReader):
    """
    Reader that looks for and parses the contents of INI files.
    """

    potential_config_filenames = ("setup.cfg", ".importlinter")
    section_name = "importlinter"

    def read_options(self, config_filename: Optional[str] = None) -> Optional[UserOptions]:
        if config_filename:
            config_filenames = file_finding.find_any(config_filename)
            if not config_filenames:
                # If we specify a filename, raise an exception.
                raise FileNotFoundError(f"Could not find {config_filename}.")
        else:
            config_filenames = file_finding.find_any(*self.potential_config_filenames)
            if not config_filenames:
                return None

        for config_filename in config_filenames:
            config = configparser.ConfigParser()
            file_contents = settings.FILE_SYSTEM.read(config_filename)
            try:
                config.read_string(file_contents)
            except configparser.Error:
                return None
            if self.section_name in config.sections():
                return self._build_from_config(config)
        return None

    def _build_from_config(self, config: configparser.ConfigParser) -> UserOptions:
        session_options = self._clean_section_config(dict(config[self.section_name]))
        contract_options = []
        for section_name in config.sections():
            if section_name.startswith(f"{self.section_name}:"):
                contract_options.append(self._clean_section_config(dict(config[section_name])))
        return UserOptions(session_options=session_options, contracts_options=contract_options)

    @staticmethod
    def _clean_section_config(section_config: Dict[str, Any]) -> Dict[str, Any]:
        section_dict: Dict[str, Any] = {}
        for key, value in section_config.items():
            if "\n" not in value:
                section_dict[key] = value
            else:
                section_dict[key] = value.strip().split("\n")
        return section_dict


class TomlUserOptionReader(ports.UserOptionReader):
    """
    Reader that looks for and parses the contents of TOML files.
    """

    section_name = "importlinter"

    def read_options(self, config_filename: Optional[str] = None) -> Optional[UserOptions]:
        if not _HAS_TOML:
            return None

        if config_filename:
            config_filenames = file_finding.find_any(config_filename)
            if not config_filenames:
                raise FileNotFoundError(f"Could not find {config_filename}.")
        else:
            config_filenames = file_finding.find_any("pyproject.toml")
            if not config_filenames:
                return None

        file_contents = settings.FILE_SYSTEM.read(config_filenames[0])
        try:
            data = toml.loads(file_contents)
        except toml.TomlDecodeError:
            return None

        tool_data = data.get("tool", {})
        session_options = tool_data.get("importlinter", {})
        if not session_options:
            return None

        contracts = session_options.pop("contracts", [])
        return UserOptions(session_options=session_options, contracts_options=contracts)
