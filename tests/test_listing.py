import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from pickleball_tracker.listing import parse_product_links


class ListingParserTests(unittest.TestCase):
    def test_keeps_only_product_links_with_the_target_term(self):
        """Including balls and court accessories would corrupt the paddle-only price trend."""
        html = """
        <a href="/prod/DXAFFD-A900KCDCY">JOOLA PERSEUS 匹克球拍</a>
        <a href="/prod/DXAFFD-A900OTHER">40孔匹克球</a>
        <a href="/prod/DXAFFD-A900KCDBN">JOOLA 匹克球拍 16mm</a>
        """

        links = parse_product_links(html, "匹克球拍")

        self.assertEqual(
            [
                ("DXAFFD-A900KCDCY", "https://24h.pchome.com.tw/prod/DXAFFD-A900KCDCY"),
                ("DXAFFD-A900KCDBN", "https://24h.pchome.com.tw/prod/DXAFFD-A900KCDBN"),
            ],
            links,
        )

    def test_parses_product_link_embedded_in_the_current_nextjs_payload(self):
        """A Next.js payload must not silently yield an empty collection run."""
        html = r'''{"name":"相關推薦","originProductName":"Luzz 碳纖維匹克球拍","link":"/prod/DXAFFK-A900JNMV1","price":1490}'''

        links = parse_product_links(html, "匹克球拍")

        self.assertEqual(
            [("DXAFFK-A900JNMV1", "https://24h.pchome.com.tw/prod/DXAFFK-A900JNMV1")],
            links,
        )

    def test_excludes_paddle_accessories_that_only_mention_a_paddle(self):
        """A paddle-protection strip is an accessory, not a paddle price observation."""
        html = '<a href="/prod/DXAFFK-A900K0TQN">匹克球拍保護條</a>'

        links = parse_product_links(html, "匹克球拍")

        self.assertEqual([], links)

    def test_accepts_any_configured_product_term_for_an_alias_search_result(self):
        html = '<a href="/prod/DXAFFK-A900TERM01">甲 匹克球拍</a>'

        links = parse_product_links(html, ("匹克球拍", "皮克球拍", "pickleball paddle"))

        self.assertEqual(
            [("DXAFFK-A900TERM01", "https://24h.pchome.com.tw/prod/DXAFFK-A900TERM01")],
            links,
        )
