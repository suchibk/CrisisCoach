"""Injectable elapsed-time source; timers never depend on wall-clock changes."""
import time
from typing import Protocol

class Clock(Protocol):
    def now(self) -> float: ...

class MonotonicClock:
    def now(self) -> float:
        return time.monotonic()
