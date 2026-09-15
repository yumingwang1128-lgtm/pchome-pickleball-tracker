import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from pickleball_tracker.source import PchomeSource


class PchomeSourceTests(unittest.TestCase):
    def test_refuses_live_requests_until_explicitly_enabled(self):
        """Accidentally running the CLI must not start automatic web requests."""
        source = PchomeSource(fetcher=lambda _: "unused")

        with self.assertRaisesRegex(PermissionError, "Live fetching is disabled"):
            source.fetch("https://24h.pchome.com.tw/prod/DXAFFD-A900KCDBN")

    def test_uses_the_injected_fetcher_after_live_fetching_is_enabled(self):
        """The source should make one controlled request only after opt-in."""
        source = PchomeSource(fetcher=lambda url: f"page:{url}", live_enabled=True)

        result = source.fetch("https://24h.pchome.com.tw/prod/DXAFFD-A900KCDBN")

        self.assertEqual("page:https://24h.pchome.com.tw/prod/DXAFFD-A900KCDBN", result)
