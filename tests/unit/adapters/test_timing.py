import time

from importlinter.adapters.timing import SystemClockTimer
from tests.adapters.timing import FakeTimer


class TestSystemClockTimer:
    def test_unnested(self):
        some_seconds = 2

        with SystemClockTimer() as timer:
            time.sleep(some_seconds)

        assert timer.duration_in_ms >= some_seconds * 1000

    def test_nested(self):
        timer = SystemClockTimer()

        some_seconds = 1
        with timer:
            with timer:
                time.sleep(some_seconds)
                with timer:
                    time.sleep(some_seconds)
                inner_duration = timer.duration_in_ms
            middle_duration = timer.duration_in_ms
        outer_duration = timer.duration_in_ms

        assert inner_duration >= some_seconds * 1000
        assert middle_duration >= inner_duration + some_seconds * 1000
        assert outer_duration >= middle_duration


class TestFakeTimer:
    def test_unnested(self):
        timer = FakeTimer()
        timer.setup(tick_duration=10, increment=3)

        for expected in (10, 13, 16):
            with timer:
                pass
            assert timer.duration_in_ms == expected * 1000

    def test_nested(self):
        timer = FakeTimer()
        timer.setup(tick_duration=10, increment=3)
        # Note that the time ticks each time the timer exits,
        # so the duration is cumulative.

        with timer:
            with timer:
                with timer:
                    pass
                assert timer.duration_in_ms == 10 * 1000
            assert timer.duration_in_ms == 23 * 1000
        assert timer.duration_in_ms == 39 * 1000
