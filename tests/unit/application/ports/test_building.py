from importlinter.application.ports.building import SourceSyntaxError


class TestSourceSyntaxError:
    def test_str(self):
        assert "Syntax error in path/to/somefile.py, line 3: something wrong" == str(
            SourceSyntaxError(filename="path/to/somefile.py", lineno=3, text="something wrong",)
        )

    def test_same_values_are_equal(self):
        assert SourceSyntaxError(
            filename="path/to/somefile.py", lineno=3, text="something wrong",
        ) == SourceSyntaxError(filename="path/to/somefile.py", lineno=3, text="something wrong",)

    def test_different_filenames_are_not_equal(self):
        assert SourceSyntaxError(
            filename="path/to/somefile.py", lineno=3, text="something wrong",
        ) != SourceSyntaxError(
            filename="path/to/anotherfile.py", lineno=3, text="something wrong",
        )

    def test_different_linenos_are_not_equal(self):
        assert SourceSyntaxError(
            filename="path/to/somefile.py", lineno=3, text="something wrong",
        ) != SourceSyntaxError(filename="path/to/somefile.py", lineno=4, text="something wrong",)

    def test_different_texts_are_not_equal(self):
        assert SourceSyntaxError(
            filename="path/to/somefile.py", lineno=3, text="something wrong",
        ) != SourceSyntaxError(
            filename="path/to/somefile.py", lineno=3, text="something else wrong",
        )
