import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from pickleball_tracker.cli import DEFAULT_QUERIES, listing_url_for_query


class CliDefaultsTests(unittest.TestCase):
    def test_uses_the_three_configured_aliases_and_encodes_search_urls(self):
        self.assertEqual(("匹克球拍", "皮克球拍", "pickleball paddle"), DEFAULT_QUERIES)
        self.assertEqual(
            "https://24h.pchome.com.tw/search/?q=pickleball+paddle",
            listing_url_for_query("pickleball paddle"),
        )
