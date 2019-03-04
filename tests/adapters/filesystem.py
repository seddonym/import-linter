from typing import List, Tuple, Any, Dict, Optional, Generator

import yaml

from grimp.application.ports.filesystem import AbstractFileSystem


class FakeFileSystem(AbstractFileSystem):
    def __init__(self, contents: str = None, content_map: Dict[str, str] = None) -> None:
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
        """
        self.contents = self._parse_contents(contents)
        self.content_map = content_map if content_map else {}

    def dirname(self, filename: str) -> str:
        """
        Return the full path to the directory name of the supplied filename.

        E.g. '/path/to/filename.py' will return '/path/to'.
        """
        return self.split(filename)[0]

    def walk(self, directory_name):
        """
        Given a directory, walk the file system recursively.

        For each directory in the tree rooted at directory top (including top itself),
        it yields a 3-tuple (dirpath, dirnames, filenames).
        """
        try:
            directory_contents = self.contents[directory_name]
        except KeyError:
            return []

        yield from self._walk_contents(directory_contents, containing_directory=directory_name)

    def _walk_contents(
        self, directory_contents: Dict[str, Any], containing_directory: str
    ) -> Generator[Tuple[str, List[str], List[str]], None, None]:

        directories = []
        files = []
        for key, value in directory_contents.items():
            if value is None:
                files.append(key)
            else:
                directories.append(key)

        yield (containing_directory, directories, files)

        if directories:
            for directory in directories:
                yield from self._walk_contents(
                    directory_contents=directory_contents[directory],
                    containing_directory=self.join(containing_directory, directory),
                )

    def join(self, *components: str) -> str:
        return '/'.join(components)

    def split(self, file_name: str) -> Tuple[str, str]:
        components = file_name.split('/')
        return ('/'.join(components[:-1]), components[-1])

    def _parse_contents(self, raw_contents: Optional[str]):
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
        raw_lines = [line for line in raw_contents.split('\n') if line.strip()]

        dedented_lines = self._dedent(raw_lines)

        for line in dedented_lines:
            trimmed_line = line.rstrip().rstrip('/')
            yamlified_line = trimmed_line + ':'
            yamlified_lines.append(yamlified_line)

        yamlified_string = '\n'.join(yamlified_lines)

        return yaml.load(yamlified_string)

    def _dedent(self, lines: List[str]) -> List[str]:
        """
        Dedent all lines by the same amount.
        """
        first_line = lines[0]
        first_line_indent = len(first_line) - len(first_line.lstrip())
        dedented = lambda line: line[first_line_indent:]
        return list(map(dedented, lines))

    def read(self, file_name: str) -> str:
        if not self.exists(file_name):
            raise FileNotFoundError
        try:
            file_contents = self.content_map[file_name]
        except KeyError:
            return ''
        raw_lines = [line for line in file_contents.split('\n') if line.strip()]
        dedented_lines = self._dedent(raw_lines)
        return '\n'.join(dedented_lines)

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

        relative_file_name = file_name[len(found_directory) + 1:]
        file_components = relative_file_name.split('/')

        contents = self.contents[found_directory]
        for component in file_components:
            try:
                contents = contents[component]
            except KeyError:
                return False
        return True
