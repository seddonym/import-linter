import abc


class FileSystem(abc.ABC):
    """
    Abstraction around file system calls.
    """

    @abc.abstractmethod
    def join(self, *components: str) -> str:
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

    @abc.abstractmethod
    def getcwd(self) -> str:
        """
        Return the current working directory.
        """
        raise NotImplementedError
