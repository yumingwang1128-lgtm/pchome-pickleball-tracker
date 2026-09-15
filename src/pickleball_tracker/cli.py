import argparse
from datetime import datetime, timezone
from pathlib import Path

from .database import TrackerDatabase
from .listing import parse_product_links
from .pipeline import collect_products
from .source import PchomeSource

DEFAULT_LISTING_URL = "https://24h.pchome.com.tw/store/DXAFFK"


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect public PChome pickleball-paddle price snapshots.")
    parser.add_argument("--live", action="store_true", help="Permit controlled live HTTP requests.")
    parser.add_argument("--database", type=Path, default=Path("data/tracker.db"))
    parser.add_argument("--query", default="匹克球拍")
    parser.add_argument("--listing-url", default=DEFAULT_LISTING_URL)
    parser.add_argument("--max-products", type=int, default=10)
    args = parser.parse_args()
    if not args.live:
        parser.error("Refusing network access without --live.")

    source = PchomeSource(live_enabled=True)
    database = TrackerDatabase(args.database)
    args.database.parent.mkdir(parents=True, exist_ok=True)
    database.initialize()
    links = parse_product_links(source.fetch(args.listing_url), args.query)[: args.max_products]
    result = collect_products(
        database=database,
        product_links=links,
        query=args.query,
        fetch_html=source.fetch,
        observed_at=datetime.now(timezone.utc),
    )
    print(f"stored={result.stored_count} invalid={result.invalid_count} fetch_errors={result.fetch_error_count}")
    return 0 if result.fetch_error_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
