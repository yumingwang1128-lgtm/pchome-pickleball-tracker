import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from .models import ProductSnapshot


class TrackerDatabase:
    def __init__(self, path: Path):
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS products (
                    product_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    brand TEXT
                );
                CREATE TABLE IF NOT EXISTS price_snapshots (
                    product_id TEXT NOT NULL REFERENCES products(product_id),
                    observed_at TEXT NOT NULL,
                    query TEXT NOT NULL,
                    current_price INTEGER NOT NULL,
                    original_price INTEGER,
                    currency TEXT NOT NULL,
                    availability TEXT,
                    rating REAL,
                    review_count INTEGER,
                    PRIMARY KEY (product_id, observed_at, query)
                );
                CREATE INDEX IF NOT EXISTS idx_snapshots_observed_at
                    ON price_snapshots(observed_at);
                """
            )

    def store_snapshot(self, snapshot: ProductSnapshot, observed_at: datetime) -> None:
        timestamp = observed_at.isoformat()
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO products(product_id, name, url, brand)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(product_id) DO UPDATE SET
                    name = excluded.name,
                    url = excluded.url,
                    brand = COALESCE(excluded.brand, products.brand)
                """,
                (snapshot.product_id, snapshot.name, snapshot.url, snapshot.brand),
            )
            connection.execute(
                """
                INSERT OR REPLACE INTO price_snapshots(
                    product_id, observed_at, query, current_price, original_price,
                    currency, availability, rating, review_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.product_id,
                    timestamp,
                    snapshot.query,
                    snapshot.current_price,
                    snapshot.original_price,
                    snapshot.currency,
                    snapshot.availability,
                    snapshot.rating,
                    snapshot.review_count,
                ),
            )

    def product_count(self) -> int:
        with closing(self._connect()) as connection:
            return connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]

    def snapshot_count(self) -> int:
        with closing(self._connect()) as connection:
            return connection.execute("SELECT COUNT(*) FROM price_snapshots").fetchone()[0]
