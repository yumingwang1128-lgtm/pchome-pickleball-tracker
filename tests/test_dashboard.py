import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from pickleball_tracker.dashboard import (
    brand_filter_options,
    count_new_products,
    filter_snapshots,
    format_taipei_date_label,
    load_snapshots,
    localize_for_taipei_display,
    price_band_distribution,
    price_change_rankings,
    summarize_snapshots,
)
from pickleball_tracker.database import TrackerDatabase
from pickleball_tracker.models import ProductSnapshot


class DashboardDataTests(unittest.TestCase):
    def _snapshot(self, product_id: str, name: str, brand: str | None, price: int) -> ProductSnapshot:
        return ProductSnapshot(
            product_id=product_id,
            name=name,
            url=f"https://24h.pchome.com.tw/prod/{product_id}",
            query="匹克球拍",
            current_price=price,
            original_price=None,
            currency="TWD",
            availability="InStock",
            brand=brand,
            rating=None,
            review_count=None,
        )

    def test_loads_filterable_snapshots_with_product_links(self):
        """Dashboard filters must retain the product URL and parse observation timestamps."""
        with tempfile.TemporaryDirectory() as directory:
            database = TrackerDatabase(Path(directory) / "tracker.db")
            database.initialize()
            database.store_snapshot(
                self._snapshot("PADDLE-ONE", "Alpha 球拍", "Alpha", 1200),
                datetime(2026, 9, 20, tzinfo=timezone.utc),
            )
            database.store_snapshot(
                self._snapshot("PADDLE-TWO", "Beta 球拍", "Beta", 3200),
                datetime(2026, 9, 21, tzinfo=timezone.utc),
            )

            snapshots = load_snapshots(Path(directory) / "tracker.db")
            filtered = filter_snapshots(
                snapshots,
                start_date="2026-09-21",
                end_date="2026-09-21",
                brands=["Beta"],
                minimum_price=3000,
                maximum_price=4000,
            )

            self.assertEqual(["Beta 球拍"], filtered["name"].tolist())
            self.assertEqual(
                "https://24h.pchome.com.tw/prod/PADDLE-TWO",
                filtered.iloc[0]["url"],
            )

    def test_includes_missing_brands_in_brand_filter_options(self):
        """The default dashboard view must not hide products whose public brand is absent."""
        with tempfile.TemporaryDirectory() as directory:
            database = TrackerDatabase(Path(directory) / "tracker.db")
            database.initialize()
            database.store_snapshot(
                self._snapshot("PADDLE-ONE", "Alpha 球拍", "Alpha", 1000),
                datetime(2026, 9, 20, tzinfo=timezone.utc),
            )
            database.store_snapshot(
                self._snapshot("PADDLE-TWO", "未標品牌球拍", None, 2000),
                datetime(2026, 9, 20, tzinfo=timezone.utc),
            )
            snapshots = load_snapshots(Path(directory) / "tracker.db")

            self.assertEqual(["Alpha", "未提供"], brand_filter_options(snapshots))
            self.assertEqual(
                ["未標品牌球拍"],
                filter_snapshots(
                    snapshots,
                    start_date="2026-09-20",
                    end_date="2026-09-20",
                    brands=["未提供"],
                    minimum_price=0,
                    maximum_price=9999,
                )["name"].tolist(),
            )

    def test_converts_utc_observation_time_to_taipei_time_for_display(self):
        """A UTC timestamp must be shown as UTC+8 in the dashboard."""
        with tempfile.TemporaryDirectory() as directory:
            database = TrackerDatabase(Path(directory) / "tracker.db")
            database.initialize()
            database.store_snapshot(
                self._snapshot("PADDLE-ONE", "Alpha 球拍", "Alpha", 1000),
                datetime(2026, 9, 20, 16, 30, tzinfo=timezone.utc),
            )

            display_snapshots = localize_for_taipei_display(
                load_snapshots(Path(directory) / "tracker.db")
            )

            self.assertEqual(
                "2026-09-21 00:30 +0800",
                display_snapshots.iloc[0]["observed_at_taipei"].strftime("%Y-%m-%d %H:%M %z"),
            )

    def test_filters_by_taipei_calendar_date(self):
        """A snapshot shortly after midnight in Taipei belongs to that local date."""
        with tempfile.TemporaryDirectory() as directory:
            database = TrackerDatabase(Path(directory) / "tracker.db")
            database.initialize()
            database.store_snapshot(
                self._snapshot("PADDLE-ONE", "Alpha 球拍", "Alpha", 1000),
                datetime(2026, 9, 20, 16, 30, tzinfo=timezone.utc),
            )
            snapshots = load_snapshots(Path(directory) / "tracker.db")

            filtered = filter_snapshots(
                snapshots,
                start_date="2026-09-21",
                end_date="2026-09-21",
                brands=["Alpha"],
                minimum_price=0,
                maximum_price=9999,
            )

            self.assertEqual(["Alpha 球拍"], filtered["name"].tolist())

    def test_formats_taipei_dates_with_traditional_chinese_labels(self):
        """Chart date labels must not fall back to the browser's English locale."""
        timestamp = datetime(2026, 9, 20, 16, 30, tzinfo=timezone.utc)

        self.assertEqual("2026年09月21日", format_taipei_date_label(timestamp))

    def test_summarizes_latest_prices_without_counting_old_snapshots_twice(self):
        """KPI prices must use the latest snapshot per product, not every historical row."""
        with tempfile.TemporaryDirectory() as directory:
            database = TrackerDatabase(Path(directory) / "tracker.db")
            database.initialize()
            database.store_snapshot(
                self._snapshot("PADDLE-ONE", "Alpha 球拍", "Alpha", 1000),
                datetime(2026, 9, 20, tzinfo=timezone.utc),
            )
            database.store_snapshot(
                self._snapshot("PADDLE-ONE", "Alpha 球拍", "Alpha", 2000),
                datetime(2026, 9, 21, tzinfo=timezone.utc),
            )
            database.store_snapshot(
                self._snapshot("PADDLE-TWO", "Beta 球拍", "Beta", 4000),
                datetime(2026, 9, 21, tzinfo=timezone.utc),
            )

            summary = summarize_snapshots(load_snapshots(Path(directory) / "tracker.db"))

            self.assertEqual(3, summary["snapshot_count"])
            self.assertEqual(2, summary["product_count"])
            self.assertEqual(2, summary["brand_count"])
            self.assertEqual(3000, summary["latest_median_price"])
            self.assertEqual("2026-09-21", summary["latest_date"])

    def test_identifies_new_products_and_ranks_price_drops(self):
        """Dashboard must not label a historical product as new or invent a price drop."""
        with tempfile.TemporaryDirectory() as directory:
            database = TrackerDatabase(Path(directory) / "tracker.db")
            database.initialize()
            database.store_snapshot(
                self._snapshot("PADDLE-ONE", "Alpha 球拍", "Alpha", 2000),
                datetime(2026, 9, 20, tzinfo=timezone.utc),
            )
            database.store_snapshot(
                self._snapshot("PADDLE-ONE", "Alpha 球拍", "Alpha", 1500),
                datetime(2026, 9, 21, tzinfo=timezone.utc),
            )
            database.store_snapshot(
                self._snapshot("PADDLE-TWO", "Beta 球拍", "Beta", 3000),
                datetime(2026, 9, 21, tzinfo=timezone.utc),
            )
            snapshots = load_snapshots(Path(directory) / "tracker.db")

            self.assertEqual(1, count_new_products(snapshots, "2026-09-21"))
            changes = price_change_rankings(snapshots)

            self.assertEqual(["Alpha 球拍"], changes["name"].tolist())
            self.assertEqual([-500], changes["price_change"].tolist())
            self.assertEqual([-25.0], changes["price_change_percent"].tolist())

    def test_price_band_distribution_uses_plain_text_labels_for_chart_compatibility(self):
        """Altair charts cannot serialize pandas IntervalIndex labels on Streamlit Cloud."""
        with tempfile.TemporaryDirectory() as directory:
            database = TrackerDatabase(Path(directory) / "tracker.db")
            database.initialize()
            database.store_snapshot(
                self._snapshot("PADDLE-ONE", "Alpha 球拍", "Alpha", 1000),
                datetime(2026, 9, 20, tzinfo=timezone.utc),
            )
            database.store_snapshot(
                self._snapshot("PADDLE-TWO", "Beta 球拍", "Beta", 3000),
                datetime(2026, 9, 21, tzinfo=timezone.utc),
            )

            distribution = price_band_distribution(
                load_snapshots(Path(directory) / "tracker.db"), bands=2
            )

            self.assertTrue(all(isinstance(label, str) for label in distribution.index))
            self.assertEqual(2, distribution.sum())
