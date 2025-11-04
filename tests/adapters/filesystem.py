import yaml

from importlinter.application.ports import filesystem as ports


class FakeFileSystem(ports.FileSystem):
    def __init__(
        self,
        contents: str | None = None,
        content_map: dict[str, str] | None = None,
        working_directory: str | None = None,
    ) -> None:
        """
        Files can be declared as existing in the file system in two different ways, either
        in a contents string (which is a quick way of defining a lot of files), or in content_map
        (which specifies the actual contents of a file in the file system). For a file to be
        treated as existing, it needs to be declared in at least one of these. If it isn't
        declared in content_map, the file will behave as an empty file.

        Args:
            contents: a string in the following format:

                /path/to/mypackage/
                    __init__.py
                    foo/
                        __init__.py
                        one.py
                        two/
                            __init__.py
                            green.py
                            blue.py

            content_map: A dictionary keyed with filenames, with values that are the contents.
                         If present in content_map, .read(filename) will return the string.
                {
                    '/path/to/foo/__init__.py': "from . import one",
                }

            working_directory: The path to be treated as the current working directory, e.g.
                               '/path/to/directory'.
        """
        self.contents = self._parse_contents(contents)
        self.content_map = content_map if content_map else {}
        self.working_directory = working_directory

    def join(self, *components: str) -> str:
        return "/".join(components)

    def _parse_contents(self, raw_contents: str | None):
        """
        Returns the raw contents parsed in the form:
            {
                '/path/to/mypackage': {
                    '__init__.py': None,
                    'foo': {
                        '__init__.py': None,
                        'one.py': None,
                        'two': {
                            '__init__.py': None,
                            'blue.py': None,
                            'green.py': None,
                        }
                    }
                }
            }
        """
        if raw_contents is None:
            return {}

        # Convert to yaml for ease of parsing.
        yamlified_lines = []
        raw_lines = [line for line in raw_contents.split("\n") if line.strip()]

        dedented_lines = self._dedent(raw_lines)

        for line in dedented_lines:
            trimmed_line = line.rstrip().rstrip("/")
            yamlified_line = trimmed_line + ":"
            yamlified_lines.append(yamlified_line)

        yamlified_string = "\n".join(yamlified_lines)

        return yaml.safe_load(yamlified_string)

    def _dedent(self, lines: list[str]) -> list[str]:
        """
        Dedent all lines by the same amount.
        """
        first_line = lines[0]
        first_line_indent = len(first_line) - len(first_line.lstrip())

        def dedented(line):
            return line[first_line_indent:]

        return list(map(dedented, lines))

    def read(self, file_name: str, encoding: str | None = None) -> str:
        if not self.exists(file_name):
            raise FileNotFoundError  # pragma: nocover
        try:
            file_contents = self.content_map[file_name]
        except KeyError:
            return ""
        raw_lines = [line for line in file_contents.split("\n") if line.strip()]
        dedented_lines = self._dedent(raw_lines)
        return "\n".join(dedented_lines)

    def exists(self, file_name: str) -> bool:
        # The file should exist if it's either declared in contents or in content_map.
        if file_name in self.content_map.keys():
            return True

        found_directory = None
        for directory in self.contents.keys():
            if file_name.startswith(directory):
                found_directory = directory
        if not found_directory:
            return False

        relative_file_name = file_name[len(found_directory) + 1 :]
        file_components = relative_file_name.split("/")

        contents = self.contents[found_directory]
        for component in file_components:
            try:
                contents = contents[component]
            except KeyError:
                return False
        return True

    def getcwd(self) -> str:
        if self.working_directory:
            return self.working_directory
        raise RuntimeError("No working directory specified.")  # pragma: nocover
