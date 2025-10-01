import pytest

from importlinter.application import file_finding
from importlinter.application.app_config import settings
from tests.adapters.filesystem import FakeFileSystem


@pytest.mark.parametrize(
    "filenames, expected_result",
    (
        (["foo.txt"], ["/path/to/folder/foo.txt"]),
        (
            ["foo.txt", ".another"],
            ["/path/to/folder/foo.txt", "/path/to/folder/.another"],
        ),
        (["bar.txt"], []),
    ),
)
def test_finds_file_in_current_directory(filenames, expected_result):
    settings.configure(
        FILE_SYSTEM=FakeFileSystem(
            """
                /path/to/folder/
                    foo.txt
                    .another
                    another/
                        foo.txt
                        bar.txt
            """,
            working_directory="/path/to/folder",
        )
    )

    result = file_finding.find_any(*filenames)

    assert expected_result == result
