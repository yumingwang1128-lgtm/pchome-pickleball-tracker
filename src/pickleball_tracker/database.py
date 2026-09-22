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
                CREATE TABLE IF NOT EXISTS crawl_runs (
                    run_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    selected_count INTEGER NOT NULL DEFAULT 0,
                    stored_count INTEGER NOT NULL DEFAULT 0,
                    invalid_count INTEGER NOT NULL DEFAULT 0,
                    fetch_error_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL CHECK(status IN (
                        'running', 'completed', 'completed_with_errors', 'failed'
                    ))
                );
                CREATE INDEX IF NOT EXISTS idx_crawl_runs_started_at
                    ON crawl_runs(started_at);
                """
            )

    def start_crawl_run(self, run_id: str, started_at: datetime) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO crawl_runs(run_id, started_at, status)
                VALUES (?, ?, 'running')
                """,
                (run_id, started_at.isoformat()),
            )

    def finish_crawl_run(
        self,
        run_id: str,
        finished_at: datetime,
        *,
        selected_count: int,
        stored_count: int,
        invalid_count: int,
        fetch_error_count: int,
        status: str,
    ) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                UPDATE crawl_runs
                SET finished_at = ?, selected_count = ?, stored_count = ?, invalid_count = ?,
                    fetch_error_count = ?, status = ?
                WHERE run_id = ?
                """,
                (
                    finished_at.isoformat(),
                    selected_count,
                    stored_count,
                    invalid_count,
                    fetch_error_count,
                    status,
                    run_id,
                ),
            )

    def latest_crawl_run(self) -> dict[str, str | int | None] | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT run_id, started_at, finished_at, selected_count, stored_count,
                       invalid_count, fetch_error_count, status
                FROM crawl_runs
                ORDER BY started_at DESC
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            return None
        columns = (
            "run_id",
            "started_at",
            "finished_at",
            "selected_count",
            "stored_count",
            "invalid_count",
            "fetch_error_count",
            "status",
        )
        return dict(zip(columns, row))

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
