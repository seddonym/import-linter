import pytest

from importlinter.application import rendering


@pytest.mark.parametrize(
    "milliseconds, expected",
    [
        (0, "0.000s"),
        (1, "0.001s"),
        (532, "0.532s"),
        (999, "0.999s"),
        (1000, "1.0s"),
        (1234, "1.2s"),
        (9950, "9.9s"),
        (9999, "10.0s"),  # a bit ugly but not really worth fixing
        (10000, "10s"),
        (12400, "12s"),
    ],
)
def test_format_duration(milliseconds, expected):
    assert rendering.format_duration(milliseconds) == expected
