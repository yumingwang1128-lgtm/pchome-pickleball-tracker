import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from pickleball_tracker.pipeline import select_distinct_product_links


class BatchCollectionTests(unittest.TestCase):
    def test_keeps_the_first_query_source_deduplicates_ids_and_applies_total_limit(self):
        pages = {
            "匹克球拍": '<a href="/prod/DXAFFK-A900ONE01">甲 匹克球拍</a>',
            "皮克球拍": (
                '<a href="/prod/DXAFFK-A900ONE01">甲 皮克球拍</a>'
                '<a href="/prod/DXAFFK-A900TWO02">乙 皮克球拍</a>'
            ),
            "pickleball paddle": '<a href="/prod/DXAFFK-A900THR03">Gamma pickleball paddle</a>',
        }

        links = select_distinct_product_links(
            queries=["匹克球拍", "皮克球拍", "pickleball paddle"],
            fetch_listing=pages.__getitem__,
            maximum_products=2,
        )

        self.assertEqual(
            [
                ("匹克球拍", "DXAFFK-A900ONE01", "https://24h.pchome.com.tw/prod/DXAFFK-A900ONE01"),
                ("皮克球拍", "DXAFFK-A900TWO02", "https://24h.pchome.com.tw/prod/DXAFFK-A900TWO02"),
            ],
            links,
        )

    def test_keeps_a_standardized_title_found_via_an_english_alias_search(self):
        links = select_distinct_product_links(
            queries=["pickleball paddle"],
            fetch_listing=lambda _: '<a href="/prod/DXAFFK-A900ENG001">甲 匹克球拍</a>',
            maximum_products=1,
            product_terms=("匹克球拍", "皮克球拍", "pickleball paddle"),
        )

        self.assertEqual(
            [("pickleball paddle", "DXAFFK-A900ENG001", "https://24h.pchome.com.tw/prod/DXAFFK-A900ENG001")],
            links,
        )

    def test_reads_every_alias_listing_even_when_the_first_one_reaches_the_limit(self):
        fetched_queries: list[str] = []

        def fetch_listing(query: str) -> str:
            fetched_queries.append(query)
            return '<a href="/prod/DXAFFK-A900FIRST1">甲 匹克球拍</a>'

        select_distinct_product_links(
            queries=["匹克球拍", "皮克球拍", "pickleball paddle"],
            fetch_listing=fetch_listing,
            maximum_products=1,
        )

        self.assertEqual(["匹克球拍", "皮克球拍", "pickleball paddle"], fetched_queries)
