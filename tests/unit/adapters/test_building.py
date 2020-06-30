from unittest.mock import patch

import grimp
import pytest
from grimp import exceptions as grimp_exceptions
from importlinter.adapters.building import GraphBuilder
from importlinter.application.ports.building import SourceSyntaxError


@patch.object(grimp, "build_graph")
def test_grimp_syntax_error_is_reraised_as_importlinter_syntax_error(mock_build_graph):
    builder = GraphBuilder()
    grimp_exception = grimp_exceptions.SourceSyntaxError(
        filename="/path/to/file.py", lineno=10, text="fromd import wrong\n",
    )
    mock_build_graph.side_effect = grimp_exception

    with pytest.raises(SourceSyntaxError) as excinfo:
        builder.build(root_package_names=["foo", "bar"])
    #
    # expected_exception = SourceSyntaxError(
    #     filename=grimp_exception.filename,
    #     lineno=grimp_exception.lineno,
    #     text=grimp_exception.text,
    # )
    # assert expected_exception == excinfo.value
