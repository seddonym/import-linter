from __future__ import annotations

import abc
from types import TracebackType


class Timer(abc.ABC):
    """
    Context manager to allow easy timing of events.

    This is an abstraction that needs to be implemented using a subclass
    that implements the get_current_time_ms method.

    Usage:

        with Timer() as timer:
            do_something()
        print(timer.duration_in_ms)
    """

    def __init__(self) -> None:
        # We use a stack so context managers can be nested.
        self._start_stack_ms: list[int] = []

    def __enter__(self) -> Timer:
        self._start_stack_ms.append(self.get_current_time_ms())
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        end_ms = self.get_current_time_ms()
        start_ms = self._start_stack_ms.pop()
        delta_ms = int(end_ms - start_ms)
        self.duration_in_ms = delta_ms

    @abc.abstractmethod
    def get_current_time_ms(self) -> int:
        """
        Return the current time as integer milliseconds."""
        raise NotImplementedError

    def get_current_time(self) -> float:  # pragma: no cover - legacy API
        """
        Return the time in seconds since the epoch as a floating point number.

        See https://docs.python.org/3/library/time.html#time.time
        """
        return self.get_current_time_ms() / 1000.0
