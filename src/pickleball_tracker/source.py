import time
from collections.abc import Callable
from urllib.request import Request, urlopen


def _http_fetch(url: str) -> str:
    request = Request(url, headers={"User-Agent": "pickleball-price-tracker/0.1 (educational project)"})
    with urlopen(request, timeout=20) as response:  # nosec B310: caller must explicitly enable live mode
        return response.read().decode("utf-8")


class PchomeSource:
    """A deliberately opt-in public-page reader with a conservative request interval."""

    def __init__(
        self,
        fetcher: Callable[[str], str] = _http_fetch,
        live_enabled: bool = False,
        minimum_interval_seconds: float = 2.0,
    ) -> None:
        self._fetcher = fetcher
        self._live_enabled = live_enabled
        self._minimum_interval_seconds = minimum_interval_seconds
        self._last_request_at: float | None = None

    def fetch(self, url: str) -> str:
        if not self._live_enabled:
            raise PermissionError("Live fetching is disabled. Pass --live only after confirming permission.")
        if self._last_request_at is not None:
            remaining = self._minimum_interval_seconds - (time.monotonic() - self._last_request_at)
            if remaining > 0:
                time.sleep(remaining)
        response = self._fetcher(url)
        self._last_request_at = time.monotonic()
        return response
