from .adapters.building import GraphBuilder
from .adapters.filesystem import FileSystem
from .adapters.printing import ClickPrinter
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
        PRINTER=ClickPrinter(),
        FILE_SYSTEM=FileSystem(),
        TIMER=SystemClockTimer(),
    )
