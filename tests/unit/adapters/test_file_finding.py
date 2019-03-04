import pytest

from importlinter.application.app_config import settings
from importlinter.application import file_finding

from tests.adapters.filesystem import FakeFileSystem


@pytest.mark.parametrize(
    'filename, expected_result',
    (
        ('foo.txt', ['/path/to/folder/foo.txt']),
        ('bar.txt', []),
    )
)
def test_finds_file_in_current_directory(filename, expected_result):
    settings.configure(
        FILE_SYSTEM=FakeFileSystem(
            """
                /path/to/folder/
                    foo.txt
                    another/
                        foo.txt
                        bar.txt
            """,
            working_directory='/path/to/folder',
        )
    )

    result = file_finding.find_any(filename)

    assert expected_result == result
