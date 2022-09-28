import time

from importlinter.adapters.timing import SystemClockTimer
from tests.adapters.timing import FakeTimer


class TestSystemClockTimer:
    def test_unnested(self):
        some_seconds = 2

        with SystemClockTimer() as timer:
            time.sleep(some_seconds)

        assert timer.duration_in_s >= some_seconds

    def test_nested(self):
        timer = SystemClockTimer()

        some_seconds = 1
        with timer:
            with timer:
                time.sleep(some_seconds)
                with timer:
                    time.sleep(some_seconds)
                inner_duration = timer.duration_in_s
            middle_duration = timer.duration_in_s
        outer_duration = timer.duration_in_s

        assert inner_duration >= some_seconds
        assert middle_duration >= inner_duration + some_seconds
        assert outer_duration >= middle_duration


class TestFakeTimer:
    def test_unnested(self):
        timer = FakeTimer()
        timer.setup(tick_duration=10, increment=3)

        for expected in (10, 13, 16):
            with timer:
                pass
            assert timer.duration_in_s == expected

    def test_nested(self):
        timer = FakeTimer()
        timer.setup(tick_duration=10, increment=3)
        # Note that the time ticks each time the timer exits,
        # so the duration is cumulative.

        with timer:
            with timer:
                with timer:
                    pass
                assert timer.duration_in_s == 10
            assert timer.duration_in_s == 23
        assert timer.duration_in_s == 39
