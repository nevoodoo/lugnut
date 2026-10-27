import time
from collections.abc import Callable

FREE_FAILURES = 5
MAX_WAIT = 900.0
MAX_TRACKED = 10_000


class LoginLimiter:
    """Exponential backoff on failed logins, per client IP, in memory."""

    # ponytail: keyed on the socket peer, so behind a reverse proxy every client shares
    # one IP and one backoff. Add a trusted-proxy header setting if that bites.

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._failures: dict[str, tuple[int, float]] = {}

    def _wait(self, failures: int) -> float:
        return min(2.0 ** (failures - FREE_FAILURES), MAX_WAIT)

    def allowed(self, ip: str) -> bool:
        failures, last = self._failures.get(ip, (0, 0.0))
        return failures < FREE_FAILURES or self._clock() - last >= self._wait(failures)

    def failed(self, ip: str) -> None:
        now = self._clock()
        if len(self._failures) >= MAX_TRACKED:
            # Drop entries whose backoff has fully expired so the table can't grow forever.
            self._failures = {k: v for k, v in self._failures.items() if now - v[1] < MAX_WAIT}
        failures, _ = self._failures.get(ip, (0, 0.0))
        self._failures[ip] = (failures + 1, now)

    def succeeded(self, ip: str) -> None:
        self._failures.pop(ip, None)
