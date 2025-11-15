from .adapters.building import GraphBuilder
from .adapters.filesystem import FileSystem
from .application.output import RichPrinter
from .adapters.timing import SystemClockTimer
from .adapters.user_options import IniFileUserOptionReader, TomlFileUserOptionReader
from .application.app_config import settings


def configure():
    settings.configure(
        USER_OPTION_READERS={
            "ini": IniFileUserOptionReader(),
            "toml": TomlFileUserOptionReader(),
        },
        GRAPH_BUILDER=GraphBuilder(),
        PRINTER=RichPrinter(),
        FILE_SYSTEM=FileSystem(),
        TIMER=SystemClockTimer(),
        DEFAULT_CACHE_DIR=".import_linter_cache",
    )
