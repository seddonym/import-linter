from typing import Tuple
import os

from grimp.application.ports.filesystem import AbstractFileSystem


class FileSystem(AbstractFileSystem):
    """
    Abstraction around file system calls.
    """
    def dirname(self, filename: str) -> str:
        return os.path.dirname(filename)

    def walk(self, directory_name):
        yield from os.walk(directory_name)

    def join(self, *components: str) -> str:
        return os.path.join(*components)

    def split(self, file_name: str) -> Tuple[str, str]:
        return os.path.split(file_name)

    def read(self, file_name: str) -> str:
        with open(file_name) as file:
            return file.read()

    def exists(self, file_name: str) -> bool:
        return os.path.isfile(file_name)
