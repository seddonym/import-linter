from collections.abc import Iterable

from importlinter.application.app_config import settings


def find_any(*filenames: Iterable[str]) -> list[str]:
    """
    Return a list of names of any potential files that contain config.

    Args:
        *filenames: list of filenames, e.g. ('setup.cfg', '.importlinter').

    Returns:
        List of absolute filenames that could be found.
    """
    found_files: list[str] = []

    filesystem = settings.FILE_SYSTEM
    current_working_directory = filesystem.getcwd()

    for filename in filenames:
        candidate_filename = filesystem.join(current_working_directory, filename)

        if filesystem.exists(candidate_filename):
            found_files.append(candidate_filename)

    return found_files
