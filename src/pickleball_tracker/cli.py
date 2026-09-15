import argparse
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

from .database import TrackerDatabase
from .pipeline import CollectionResult, collect_products, select_distinct_product_links
from .source import PchomeSource

DEFAULT_QUERIES = ("匹克球拍", "皮克球拍", "pickleball paddle")


def listing_url_for_query(query: str) -> str:
    return f"https://24h.pchome.com.tw/search/?{urlencode({'q': query})}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect public PChome pickleball-paddle price snapshots.")
    parser.add_argument("--live", action="store_true", help="Permit controlled live HTTP requests.")
    parser.add_argument("--database", type=Path, default=Path("data/tracker.db"))
    parser.add_argument("--query", action="append", help="Limit collection to a query; may be repeated.")
    parser.add_argument("--listing-url", help="Use a custom listing page with exactly one --query.")
    parser.add_argument("--max-products", type=int, default=10)
    args = parser.parse_args()
    if not args.live:
        parser.error("Refusing network access without --live.")

    source = PchomeSource(live_enabled=True)
    database = TrackerDatabase(args.database)
    args.database.parent.mkdir(parents=True, exist_ok=True)
    database.initialize()
    queries = tuple(args.query) if args.query else DEFAULT_QUERIES
    if args.listing_url and len(queries) != 1:
        parser.error("--listing-url requires exactly one --query.")

    def fetch_listing(query: str) -> str:
        return source.fetch(args.listing_url or listing_url_for_query(query))

    selected = select_distinct_product_links(queries, fetch_listing, args.max_products)
    totals = CollectionResult(0, 0, 0)
    observed_at = datetime.now(timezone.utc)
    for query, product_id, url in selected:
        result = collect_products(
            database=database,
            product_links=[(product_id, url)],
            query=query,
            fetch_html=source.fetch,
            observed_at=observed_at,
        )
        totals = CollectionResult(
            totals.stored_count + result.stored_count,
            totals.invalid_count + result.invalid_count,
            totals.fetch_error_count + result.fetch_error_count,
        )
    print(
        f"stored={totals.stored_count} invalid={totals.invalid_count} "
        f"fetch_errors={totals.fetch_error_count} selected={len(selected)}"
    )
    return 0 if totals.fetch_error_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
