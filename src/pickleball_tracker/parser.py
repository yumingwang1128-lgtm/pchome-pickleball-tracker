import html as html_module
import json
import re

from .models import ProductSnapshot


def _product_record(html: str) -> dict:
    match = re.search(
        r'<script\s+type=["\']application/ld\+json["\']\s*>(.*?)</script>',
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if not match:
        raise ValueError("Product JSON-LD was not found")

    records = json.loads(html_module.unescape(match.group(1)))
    if not isinstance(records, list):
        records = [records]
    for record in records:
        if record.get("@type") == "Product":
            return record
    raise ValueError("Product JSON-LD record was not found")


def _original_price(html: str) -> int | None:
    match = re.search(
        r'data-regression=["\']prodPage_originalPrice["\'][^>]*>\s*\$?([\d,]+)',
        html,
        flags=re.IGNORECASE,
    )
    return int(match.group(1).replace(",", "")) if match else None


def _brand_name(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict) and isinstance(value.get("name"), str):
        return value["name"].strip() or None
    return None


def parse_product_html(html: str, product_id: str, url: str, query: str) -> ProductSnapshot:
    """Parse public Product JSON-LD plus the optional displayed original price."""
    record = _product_record(html)
    offers = record.get("offers") or {}
    rating = record.get("aggregateRating") or {}
    availability = offers.get("availability")
    if isinstance(availability, str):
        availability = availability.rsplit("/", maxsplit=1)[-1]

    return ProductSnapshot(
        product_id=product_id,
        name=record["name"].strip(),
        url=url,
        query=query,
        current_price=int(float(offers["price"])),
        original_price=_original_price(html),
        currency=offers.get("priceCurrency", "TWD"),
        availability=availability,
        brand=_brand_name(record.get("brand")),
        rating=float(rating["ratingValue"]) if rating.get("ratingValue") is not None else None,
        review_count=int(rating["reviewCount"]) if rating.get("reviewCount") is not None else None,
    )
