import time

from importlinter.application.ports.timing import Timer


class SystemClockTimer(Timer):
    def get_current_time(self) -> float:
        return time.time()
