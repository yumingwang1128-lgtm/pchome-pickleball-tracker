import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from pickleball_tracker.models import ProductSnapshot
from pickleball_tracker.quality import validate_snapshot


class SnapshotQualityTests(unittest.TestCase):
    def test_rejects_an_original_price_lower_than_the_current_price(self):
        """A reversed price pair would create a false discount in the dashboard."""
        snapshot = ProductSnapshot(
            product_id="DXAFFD-A900KCDBN",
            name="JOOLA Astral Pickleball Paddle 16mm",
            url="https://24h.pchome.com.tw/prod/DXAFFD-A900KCDBN",
            query="匹克球拍",
            current_price=2331,
            original_price=2000,
            currency="TWD",
            availability="InStock",
            brand=None,
            rating=None,
            review_count=None,
        )

        result = validate_snapshot(snapshot)

        self.assertFalse(result.is_valid)
        self.assertIn("original_price must be greater than or equal to current_price", result.errors)
