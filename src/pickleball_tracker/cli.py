import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlencode
from uuid import uuid4

from .database import TrackerDatabase
from .pipeline import CollectionResult, collect_products, select_distinct_product_links
from .source import PchomeSource

DEFAULT_QUERIES = ("匹克球拍", "皮克球拍", "pickleball paddle")


def listing_url_for_query(query: str) -> str:
    return f"https://24h.pchome.com.tw/search/?{urlencode({'q': query})}"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def run_collection(
    *,
    database: TrackerDatabase,
    queries: tuple[str, ...],
    fetch_listing: Callable[[str], str],
    fetch_product: Callable[[str], str],
    maximum_products: int,
    clock: Callable[[], datetime] = utc_now,
    run_id: str | None = None,
) -> CollectionResult:
    """Collect one scheduled batch and persist its diagnostic summary."""
    run_id = run_id or uuid4().hex
    started_at = clock()
    database.start_crawl_run(run_id, started_at)
    selected_count = 0
    totals = CollectionResult(0, 0, 0)
    try:
        selected = select_distinct_product_links(queries, fetch_listing, maximum_products)
        selected_count = len(selected)
        for query, product_id, url in selected:
            result = collect_products(
                database=database,
                product_links=[(product_id, url)],
                query=query,
                fetch_html=fetch_product,
                observed_at=started_at,
            )
            totals = CollectionResult(
                totals.stored_count + result.stored_count,
                totals.invalid_count + result.invalid_count,
                totals.fetch_error_count + result.fetch_error_count,
            )
    except Exception:
        database.finish_crawl_run(
            run_id,
            clock(),
            selected_count=selected_count,
            stored_count=totals.stored_count,
            invalid_count=totals.invalid_count,
            fetch_error_count=totals.fetch_error_count,
            status="failed",
        )
        raise

    status = "completed" if totals.fetch_error_count == 0 else "completed_with_errors"
    database.finish_crawl_run(
        run_id,
        clock(),
        selected_count=selected_count,
        stored_count=totals.stored_count,
        invalid_count=totals.invalid_count,
        fetch_error_count=totals.fetch_error_count,
        status=status,
    )
    return totals


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

    totals = run_collection(
        database=database,
        queries=queries,
        fetch_listing=fetch_listing,
        fetch_product=source.fetch,
        maximum_products=args.max_products,
    )
    latest_run = database.latest_crawl_run()
    selected_count = latest_run["selected_count"] if latest_run is not None else 0
    print(
        f"stored={totals.stored_count} invalid={totals.invalid_count} "
        f"fetch_errors={totals.fetch_error_count} selected={selected_count}"
    )
    return 0 if totals.fetch_error_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
