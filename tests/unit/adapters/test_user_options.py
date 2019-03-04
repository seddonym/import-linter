import pytest

from importlinter.adapters.user_options import IniFileUserOptionReader
from importlinter.application.app_config import settings
from importlinter.application.user_options import UserOptions

from tests.adapters.filesystem import FakeFileSystem


@pytest.mark.parametrize(
    'contents, expected_options', (
        (
            """
            [something]
            # This file has no import-linter section.
            foo = 1
            bar = hello
            """,
            None,
        ),
        (
            """
            [something]
            foo = 1
            bar = hello
            
            [import-linter]
            foo = hello
            bar = 999
            """,
            UserOptions(
                session_options={
                    'foo': 'hello',
                    'bar': '999',
                },
                contracts_options=[],
            ),
        ),
        (
                """
                [import-linter]
                foo = hello
                
                [import-linter:contract:contract-one]
                name=Contract One
                key=value
                multiple_values=
                    one
                    two
                    three
                
                [import-linter:contract:contract-two];
                name=Contract Two
                baz=3
                """,
                UserOptions(
                    session_options={
                        'foo': 'hello',
                    },
                    contracts_options=[
                        {
                            'name': 'Contract One',
                            'key': 'value',
                            'multiple_values': ['one', 'two', 'three'],
                        },
                        {
                            'name': 'Contract Two',
                            'baz': '3',
                        }
                    ],
                ),
        ),
    )
)
def test_ini_file_reader(contents, expected_options):
    settings.configure(
        FILE_SYSTEM=FakeFileSystem(
            content_map={
                '/path/to/folder/setup.cfg': contents,
            },
            working_directory='/path/to/folder',
        )
    )

    options = IniFileUserOptionReader().read_options()

    assert expected_options == options
