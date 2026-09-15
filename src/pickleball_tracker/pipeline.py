from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from .database import TrackerDatabase
from .listing import parse_product_links
from .parser import parse_product_html
from .quality import validate_snapshot


@dataclass(frozen=True)
class CollectionResult:
    stored_count: int
    invalid_count: int
    fetch_error_count: int


def select_distinct_product_links(
    queries: list[str],
    fetch_listing: Callable[[str], str],
    maximum_products: int,
    product_terms: tuple[str, ...] | None = None,
) -> list[tuple[str, str, str]]:
    """Return query-tagged product links, preserving query priority and a global cap."""
    selected: list[tuple[str, str, str]] = []
    seen_product_ids: set[str] = set()
    title_terms = product_terms or tuple(queries)
    listings = [(query, parse_product_links(fetch_listing(query), title_terms)) for query in queries]
    for query, product_links in listings:
        for product_id, url in product_links:
            if product_id in seen_product_ids:
                continue
            selected.append((query, product_id, url))
            seen_product_ids.add(product_id)
            if len(selected) >= maximum_products:
                return selected
    return selected


def collect_products(
    database: TrackerDatabase,
    product_links: list[tuple[str, str]],
    query: str,
    fetch_html: Callable[[str], str],
    observed_at: datetime,
) -> CollectionResult:
    stored_count = 0
    invalid_count = 0
    fetch_error_count = 0
    for product_id, url in product_links:
        try:
            snapshot = parse_product_html(fetch_html(url), product_id, url, query)
        except (KeyError, TypeError, ValueError):
            fetch_error_count += 1
            continue
        validation = validate_snapshot(snapshot)
        if not validation.is_valid:
            invalid_count += 1
            continue
        database.store_snapshot(snapshot, observed_at)
        stored_count += 1
    return CollectionResult(stored_count, invalid_count, fetch_error_count)
