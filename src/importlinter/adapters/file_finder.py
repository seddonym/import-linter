from typing import List
import os

from importlinter.application.ports import file_finder as ports


class FileFinder(ports.FileFinder):
    def find_any(self, filename: str) -> List[str]:
        return [
            os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', filename))
        ]
