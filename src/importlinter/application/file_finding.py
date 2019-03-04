from typing import List

from importlinter.application.app_config import settings


def find_any(filename: str) -> List[str]:
    """
    Return a list of names of any potential files that contain config.

    Args:
        filename: name of the file, e.g. 'setup.cfg'.

    Returns:
        List of absolute filenames that could be found.
    """
    filesystem = settings.FILE_SYSTEM
    current_working_directory = filesystem.getcwd()
    candidate_filename = filesystem.join(current_working_directory, filename)

    if filesystem.exists(candidate_filename):
        return [candidate_filename]
    else:
        return []
