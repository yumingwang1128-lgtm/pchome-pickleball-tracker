import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from pickleball_tracker.cli import DEFAULT_QUERIES, listing_url_for_query, run_collection
from pickleball_tracker.database import TrackerDatabase


class CliDefaultsTests(unittest.TestCase):
    def test_uses_the_three_configured_aliases_and_encodes_search_urls(self):
        self.assertEqual(("匹克球拍", "皮克球拍", "pickleball paddle"), DEFAULT_QUERIES)
        self.assertEqual(
            "https://24h.pchome.com.tw/search/?q=pickleball+paddle",
            listing_url_for_query("pickleball paddle"),
        )

    def test_collection_records_one_completed_run_with_its_statistics(self):
        """The scheduler must leave a run record that explains its snapshot writes."""
        product_url = "https://24h.pchome.com.tw/prod/DXAFFD-A900KCDCY"
        pages = {
            "listing": '<a href="/prod/DXAFFD-A900KCDCY">JOOLA 匹克球拍</a>',
            product_url: '''
                <script type="application/ld+json">[{"@type":"Product","name":"JOOLA 匹克球拍",
                "offers":{"price":"1200","priceCurrency":"TWD"}}]</script>
            ''',
        }
        with tempfile.TemporaryDirectory() as directory:
            database = TrackerDatabase(Path(directory) / "tracker.db")
            database.initialize()

            result = run_collection(
                database=database,
                queries=("匹克球拍",),
                fetch_listing=lambda _query: pages["listing"],
                fetch_product=pages.__getitem__,
                maximum_products=10,
                clock=lambda: datetime(2026, 9, 15, tzinfo=timezone.utc),
                run_id="run-test",
            )

            self.assertEqual(1, result.stored_count)
            self.assertEqual(
                {
                    "run_id": "run-test",
                    "started_at": "2026-09-15T00:00:00+00:00",
                    "finished_at": "2026-09-15T00:00:00+00:00",
                    "selected_count": 1,
                    "stored_count": 1,
                    "invalid_count": 0,
                    "fetch_error_count": 0,
                    "status": "completed",
                },
                database.latest_crawl_run(),
            )

    def test_listing_failure_is_recorded_as_a_failed_crawl_run(self):
        """An unavailable search page must be diagnosable after the command exits nonzero."""
        with tempfile.TemporaryDirectory() as directory:
            database = TrackerDatabase(Path(directory) / "tracker.db")
            database.initialize()

            with self.assertRaisesRegex(RuntimeError, "listing unavailable"):
                run_collection(
                    database=database,
                    queries=("匹克球拍",),
                    fetch_listing=lambda _query: (_ for _ in ()).throw(RuntimeError("listing unavailable")),
                    fetch_product=lambda _url: "",
                    maximum_products=10,
                    clock=lambda: datetime(2026, 9, 15, tzinfo=timezone.utc),
                    run_id="run-failed",
                )

            self.assertEqual("failed", database.latest_crawl_run()["status"])
