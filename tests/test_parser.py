import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from pickleball_tracker.parser import parse_product_html


class ProductParserTests(unittest.TestCase):
    def test_parses_required_snapshot_fields_and_keeps_missing_optional_fields_none(self):
        """A parser that drops a required price or converts absent reviews to zero is incorrect."""
        html = """
        <script type="application/ld+json">[
          {"@context":"https://schema.org","@type":"Product",
           "name":"JOOLA Astral Pickleball Paddle 16mm",
           "offers":{"price":"2331","priceCurrency":"TWD","availability":"http://schema.org/InStock"},
           "brand":null,"aggregateRating":null}
        ]</script>
        <div data-regression="prodPage_originalPrice">$2,590</div>
        """

        product = parse_product_html(
            html=html,
            product_id="DXAFFD-A900KCDBN",
            url="https://24h.pchome.com.tw/prod/DXAFFD-A900KCDBN",
            query="匹克球拍",
        )

        self.assertEqual("DXAFFD-A900KCDBN", product.product_id)
        self.assertEqual("JOOLA Astral Pickleball Paddle 16mm", product.name)
        self.assertEqual(2331, product.current_price)
        self.assertEqual(2590, product.original_price)
        self.assertEqual("TWD", product.currency)
        self.assertEqual("InStock", product.availability)
        self.assertIsNone(product.brand)
        self.assertIsNone(product.rating)
        self.assertIsNone(product.review_count)

    def test_parses_rating_and_review_count_when_the_site_provides_them(self):
        """Removing public rating data must be detected when the source supplies it."""
        html = """
        <script type="application/ld+json">[
          {"@type":"Product","name":"JOOLA PERSEUS DOUBLE VISION",
           "offers":{"price":"3591","priceCurrency":"TWD","availability":"http://schema.org/InStock"},
           "aggregateRating":{"ratingValue":"5","reviewCount":"1"}}
        ]</script>
        <div data-regression="prodPage_originalPrice">$3,990</div>
        """

        product = parse_product_html(
            html=html,
            product_id="DXAFFD-A900KCDCY",
            url="https://24h.pchome.com.tw/prod/DXAFFD-A900KCDCY",
            query="皮克球拍",
        )

        self.assertEqual(5.0, product.rating)
        self.assertEqual(1, product.review_count)
