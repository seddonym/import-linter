import os

from importlinter.application.ports import filesystem as ports


class FileSystem(ports.FileSystem):
    """
    File system adapter that delegates to built in file system functions.
    """

    def join(self, *components: str) -> str:
        return os.path.join(*components)

    def read(self, file_name: str) -> str:
        """
        Return all non "\n" lines as a string while preserving formatting.
        """
        cleaned_file_str = ""
        with open(file_name) as file:
            for line in file.readlines():
                if line == '\n':
                    continue
                else:
                    cleaned_file_str += line
            return cleaned_file_str

    def exists(self, file_name: str) -> bool:
        return os.path.isfile(file_name)

    def getcwd(self) -> str:
        return os.getcwd()
