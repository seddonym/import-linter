from __future__ import annotations

from types import TracebackType

from importlinter.application.ports.timing import Timer


class FakeTimer(Timer):
    ARBITRARY_SECONDS_SINCE_EPOCH = 1_000_000

    def __init__(self) -> None:
        self._current_time = float(self.ARBITRARY_SECONDS_SINCE_EPOCH)
        self._tick_duration = 1
        self._increment = 0

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._tick()
        super().__exit__(exc_type, exc_val, exc_tb)

    def get_current_time(self) -> float:
        return self._current_time

    def setup(self, tick_duration: int, increment: int) -> None:
        self._tick_duration = tick_duration
        self._increment = increment

    def _tick(self) -> None:
        self._current_time += self._tick_duration
        self._tick_duration += self._increment
