from pathlib import Path
import sqlite3
from contextlib import closing

import pandas as pd


def load_snapshots(database_path: Path) -> pd.DataFrame:
    """Load dashboard fields from the tracker database in chronological order."""
    with closing(sqlite3.connect(database_path)) as connection:
        snapshots = pd.read_sql_query(
            """
            SELECT s.product_id, p.name, p.brand, p.url, s.observed_at,
                   s.current_price, s.original_price, s.rating, s.review_count,
                   s.availability
            FROM price_snapshots AS s
            JOIN products AS p USING(product_id)
            ORDER BY s.observed_at
            """,
            connection,
            parse_dates=["observed_at"],
        )
    return snapshots


def filter_snapshots(
    snapshots: pd.DataFrame,
    *,
    start_date: str,
    end_date: str,
    brands: list[str],
    minimum_price: int,
    maximum_price: int,
) -> pd.DataFrame:
    """Apply inclusive dashboard filters without changing the original dataset."""
    start = pd.Timestamp(start_date, tz="UTC")
    end_exclusive = pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(days=1)
    filtered = snapshots[
        (snapshots["observed_at"] >= start)
        & (snapshots["observed_at"] < end_exclusive)
        & (snapshots["current_price"] >= minimum_price)
        & (snapshots["current_price"] <= maximum_price)
    ]
    if brands:
        filtered = filtered[filtered["brand"].isin(brands)]
    return filtered.copy()


def summarize_snapshots(snapshots: pd.DataFrame) -> dict[str, int | str | None]:
    """Return sample-size and latest-price KPIs for the active dashboard filters."""
    if snapshots.empty:
        return {
            "snapshot_count": 0,
            "product_count": 0,
            "brand_count": 0,
            "latest_median_price": None,
            "latest_date": None,
        }
    latest_per_product = (
        snapshots.sort_values("observed_at")
        .groupby("product_id", as_index=False)
        .tail(1)
    )
    latest_at = snapshots["observed_at"].max()
    return {
        "snapshot_count": len(snapshots),
        "product_count": snapshots["product_id"].nunique(),
        "brand_count": snapshots["brand"].nunique(),
        "latest_median_price": int(latest_per_product["current_price"].median()),
        "latest_date": latest_at.date().isoformat(),
    }


def count_new_products(snapshots: pd.DataFrame, start_date: str) -> int:
    """Count products whose first observation is on or after the selected period."""
    start = pd.Timestamp(start_date, tz="UTC")
    first_seen = snapshots.groupby("product_id")["observed_at"].min()
    return int((first_seen >= start).sum())


def price_change_rankings(snapshots: pd.DataFrame) -> pd.DataFrame:
    """Return products whose price fell within the active filter period."""
    if snapshots.empty:
        return pd.DataFrame(
            columns=("product_id", "name", "brand", "first_price", "latest_price", "price_change", "price_change_percent")
        )
    ordered = snapshots.sort_values("observed_at")
    first = ordered.groupby("product_id", as_index=False).first()
    latest = ordered.groupby("product_id", as_index=False).tail(1)
    changes = first[["product_id", "current_price"]].merge(
        latest[["product_id", "name", "brand", "current_price"]],
        on="product_id",
        suffixes=("_first", "_latest"),
    )
    changes = changes.rename(
        columns={"current_price_first": "first_price", "current_price_latest": "latest_price"}
    )
    changes["price_change"] = changes["latest_price"] - changes["first_price"]
    changes["price_change_percent"] = (
        changes["price_change"] / changes["first_price"] * 100
    ).round(1)
    return changes[changes["price_change"] < 0].sort_values("price_change").reset_index(drop=True)


def price_band_distribution(snapshots: pd.DataFrame, bands: int = 6) -> pd.Series:
    """Return chart-safe, human-readable price-band counts."""
    distribution = pd.cut(snapshots["current_price"], bins=bands).value_counts().sort_index()
    distribution.index = distribution.index.map(str)
    return distribution
