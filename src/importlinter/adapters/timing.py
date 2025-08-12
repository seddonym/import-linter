import time

from importlinter.application.ports.timing import Timer


class SystemClockTimer(Timer):
    def get_current_time_ms(self) -> int:
        # Use high-resolution monotonic clock and convert to integer milliseconds (rounded).
        return (time.perf_counter_ns() + 500_000) // 1_000_000
