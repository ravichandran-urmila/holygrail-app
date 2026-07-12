import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path("/data/screener.db") if Path("/data").exists() else Path("screener.db")

def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS screener_cache (
                universe TEXT PRIMARY KEY,
                results TEXT,
                updated_at REAL,
                total_tickers INTEGER,
                done_tickers INTEGER,
                state TEXT
            )
        """)
        conn.commit()

def save_cache(universe: str, results: list, state: str, total: int, done: int):
    with _get_conn() as conn:
        conn.execute("""
            INSERT INTO screener_cache (universe, results, updated_at, total_tickers, done_tickers, state)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(universe) DO UPDATE SET
                results=excluded.results,
                updated_at=excluded.updated_at,
                total_tickers=excluded.total_tickers,
                done_tickers=excluded.done_tickers,
                state=excluded.state
        """, (universe, json.dumps(results), time.time(), total, done, state))
        conn.commit()

def load_cache(universe: str) -> dict | None:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM screener_cache WHERE universe = ?", (universe,)).fetchone()
        if not row:
            return None
        return {
            "universe": row["universe"],
            "results": json.loads(row["results"]),
            "updated_at": row["updated_at"],
            "total_tickers": row["total_tickers"],
            "done_tickers": row["done_tickers"],
            "state": row["state"],
        }
