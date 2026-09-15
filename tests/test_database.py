import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from pickleball_tracker.database import TrackerDatabase
from pickleball_tracker.models import ProductSnapshot


class TrackerDatabaseTests(unittest.TestCase):
    def test_upsert_keeps_one_product_and_records_snapshots_from_two_days(self):
        """Replacing historical snapshots instead of appending them would destroy the price trend."""
        with tempfile.TemporaryDirectory() as directory:
            database = TrackerDatabase(Path(directory) / "tracker.db")
            database.initialize()
            product = ProductSnapshot(
                product_id="DXAFFD-A900KCDBN",
                name="JOOLA Astral Pickleball Paddle 16mm",
                url="https://24h.pchome.com.tw/prod/DXAFFD-A900KCDBN",
                query="匹克球拍",
                current_price=2331,
                original_price=2590,
                currency="TWD",
                availability="InStock",
                brand=None,
                rating=None,
                review_count=None,
            )

            database.store_snapshot(product, datetime(2026, 9, 8, tzinfo=timezone.utc))
            database.store_snapshot(product, datetime(2026, 9, 9, tzinfo=timezone.utc))

            self.assertEqual(1, database.product_count())
            self.assertEqual(2, database.snapshot_count())
