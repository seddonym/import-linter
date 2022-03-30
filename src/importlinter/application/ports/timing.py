from __future__ import annotations

import abc
from types import TracebackType


class Timer(abc.ABC):
    """
    Context manager to allow easy timing of events.

    This is an abstraction that needs to be implemented using a subclass
    that implements the get_current_time method.

    Usage:

        with Timer() as timer:
            do_something()
        print(timer.duration_in_s)
    """

    def __enter__(self) -> Timer:
        self.start = self.get_current_time()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.end = self.get_current_time()
        self.duration_in_s = int(self.end - self.start)

    @abc.abstractmethod
    def get_current_time(self) -> float:
        """
        Return the time in seconds since the epoch as a floating point number.

        See https://docs.python.org/3/library/time.html#time.time
        """
        raise NotImplementedError
