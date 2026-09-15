import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from pickleball_tracker.database import TrackerDatabase
from pickleball_tracker.pipeline import collect_products


class PipelineTests(unittest.TestCase):
    def test_stores_valid_products_and_reports_invalid_product_pages(self):
        """A reversed price must not reach SQLite even when another page is valid."""
        valid_url = "https://24h.pchome.com.tw/prod/DXAFFD-A900GOOD1"
        invalid_url = "https://24h.pchome.com.tw/prod/DXAFFD-A900BAD01"
        pages = {
            valid_url: """
                <script type="application/ld+json">[{"@type":"Product","name":"Good 匹克球拍",
                "offers":{"price":"1200","priceCurrency":"TWD"}}]</script>
                <div data-regression="prodPage_originalPrice">$1,500</div>
            """,
            invalid_url: """
                <script type="application/ld+json">[{"@type":"Product","name":"Bad 匹克球拍",
                "offers":{"price":"1200","priceCurrency":"TWD"}}]</script>
                <div data-regression="prodPage_originalPrice">$1,000</div>
            """,
        }
        with tempfile.TemporaryDirectory() as directory:
            database = TrackerDatabase(Path(directory) / "tracker.db")
            database.initialize()

            result = collect_products(
                database=database,
                product_links=[
                    ("DXAFFD-A900GOOD1", valid_url),
                    ("DXAFFD-A900BAD01", invalid_url),
                ],
                query="匹克球拍",
                fetch_html=pages.__getitem__,
                observed_at=datetime(2026, 9, 10, tzinfo=timezone.utc),
            )

            self.assertEqual(1, result.stored_count)
            self.assertEqual(1, result.invalid_count)
            self.assertEqual(1, database.snapshot_count())
