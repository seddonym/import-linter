from typing import List
import abc


class FileFinder(abc.ABC):
    @abc.abstractmethod
    def find_any(self, filename: str) -> List[str]:
        """
        Return a list of names of any potential files that contain config.

        Args:
            filename: name of the file, e.g. 'setup.cfg'.

        Returns:
            List of absolute filenames that could be found.
        """
        raise NotImplementedError
