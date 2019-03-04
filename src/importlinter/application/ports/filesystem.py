from typing import Tuple
import abc


class AbstractFileSystem(abc.ABC):
    """
    Abstraction around file system calls.
    """
    @abc.abstractmethod
    def dirname(self, filename: str) -> str:
        """
        Return the full path to the directory name of the supplied filename.

        E.g. '/path/to/filename.py' will return '/path/to'.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def walk(self, directory_name):
        """
        Given a directory, walk the file system recursively.

        For each directory in the tree rooted at directory top (including top itself),
        it yields a 3-tuple (dirpath, dirnames, filenames).
        """
        raise NotImplementedError

    @abc.abstractmethod
    def join(self, *components: str) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def split(self, file_name: str) -> Tuple[str, str]:
        """
        Split the pathname path into a pair, (head, tail) where tail is the last pathname component
        and head is everything leading up to that. The tail part will never contain a slash;
        if path ends in a slash, tail will be empty. If there is no slash in path, head will be
        empty. If path is empty, both head and tail are empty. Trailing slashes are stripped from
        head unless it is the root (one or more slashes only). In all cases, join(head, tail)
        returns a path to the same location as path (but the strings may differ).
        """
        raise NotImplementedError

    @abc.abstractmethod
    def read(self, file_name: str) -> str:
        """
        Given a file name, return the contents of the file.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def exists(self, file_name: str) -> bool:
        """
        Return whether a file exists.
        """
        raise NotImplementedError
