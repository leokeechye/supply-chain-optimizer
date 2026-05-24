"""Supply Chain Optimizer - SQLite persistence layer.

One-stop module for the durable data: schema, seed-from-CSV, and the
typed accessors the agents call. Uses stdlib sqlite3 (no new deps), WAL
mode for safe concurrent reads, and a connection-per-thread pattern.

The DB file lives at {repo}/data/supply_chain.db by default — on Railway
mount a Volume at /app/data so the file survives redeploys (see DEPLOY.md).
If the DB is empty on startup, seed_from_csv() loads src/data/csv/*.csv
and generates one year of sales history deterministically (seeded random).
"""

import csv
import logging
import random
import sqlite3
import threading
from datetime import date, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Path to the SQLite file. Override via env if needed; the volume mount
# point on Railway should be /app/data.
_DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "supply_chain.db"
_CSV_DIR = Path(__file__).parent / "csv"

_local = threading.local()


# --- Connection management -------------------------------------------------

def _db_path() -> Path:
    """Resolve the SQLite path. Env var SQLITE_PATH overrides the default."""
    import os
    return Path(os.environ.get("SQLITE_PATH", str(_DEFAULT_DB_PATH)))


def _conn() -> sqlite3.Connection:
    """One connection per thread; rows come back as dicts."""
    c = getattr(_local, "conn", None)
    if c is None:
        path = _db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        c = sqlite3.connect(str(path), isolation_level=None, check_same_thread=False)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        _local.conn = c
    return c


# --- Schema ----------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS skus (
    sku       TEXT PRIMARY KEY,
    name      TEXT NOT NULL,
    category  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS warehouses (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    location      TEXT NOT NULL,
    capacity_sqm  INTEGER NOT NULL,
    used_sqm      INTEGER NOT NULL,
    region        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory (
    sku                  TEXT NOT NULL,
    warehouse_id         TEXT NOT NULL,
    current_stock        INTEGER NOT NULL,
    reserved_stock       INTEGER DEFAULT 0,
    reorder_point        INTEGER NOT NULL,
    safety_stock         INTEGER NOT NULL,
    lead_time_days       INTEGER NOT NULL,
    unit_cost            REAL NOT NULL,
    avg_daily_demand     INTEGER DEFAULT 0,
    days_since_last_sale INTEGER DEFAULT 0,
    primary_vendor       TEXT,
    PRIMARY KEY (sku, warehouse_id)
);

CREATE TABLE IF NOT EXISTS sales_history (
    date      TEXT NOT NULL,
    sku       TEXT NOT NULL,
    quantity  INTEGER NOT NULL,
    PRIMARY KEY (date, sku)
);
CREATE INDEX IF NOT EXISTS idx_sales_sku ON sales_history(sku);

CREATE TABLE IF NOT EXISTS vendors (
    id                    TEXT PRIMARY KEY,
    name                  TEXT NOT NULL,
    country               TEXT NOT NULL,
    lead_time_days        INTEGER NOT NULL,
    reliability_score     REAL NOT NULL,
    price_competitiveness REAL NOT NULL,
    products              TEXT,           -- semicolon-separated SKUs
    payment_terms         TEXT,
    contact_email         TEXT
);
"""


def init_db() -> None:
    """Create tables (idempotent) and seed from CSV if empty.

    Called once on FastAPI startup via the lifespan hook in src/main.py.
    """
    c = _conn()
    c.executescript(_SCHEMA)
    seed_from_csv_if_empty()


# --- Seeding ---------------------------------------------------------------

def _load_csv(name: str) -> list[dict]:
    path = _CSV_DIR / name
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _table_empty(table: str) -> bool:
    return _conn().execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone() is None


def seed_from_csv_if_empty() -> None:
    """Seed any empty table from its CSV. Generates sales_history on the fly."""
    c = _conn()

    if _table_empty("skus"):
        rows = _load_csv("skus.csv")
        c.executemany(
            "INSERT INTO skus(sku,name,category) VALUES(:sku,:name,:category)",
            rows,
        )
        logger.info("seeded skus: %d rows", len(rows))

    if _table_empty("warehouses"):
        rows = _load_csv("warehouses.csv")
        c.executemany(
            "INSERT INTO warehouses(id,name,location,capacity_sqm,used_sqm,region) "
            "VALUES(:id,:name,:location,:capacity_sqm,:used_sqm,:region)",
            [{**r, "capacity_sqm": int(r["capacity_sqm"]), "used_sqm": int(r["used_sqm"])} for r in rows],
        )
        logger.info("seeded warehouses: %d rows", len(rows))

    if _table_empty("vendors"):
        rows = _load_csv("vendors.csv")
        c.executemany(
            "INSERT INTO vendors(id,name,country,lead_time_days,reliability_score,"
            "price_competitiveness,products,payment_terms,contact_email) "
            "VALUES(:id,:name,:country,:lead_time_days,:reliability_score,"
            ":price_competitiveness,:products,:payment_terms,:contact_email)",
            [{**r,
              "lead_time_days": int(r["lead_time_days"]),
              "reliability_score": float(r["reliability_score"]),
              "price_competitiveness": float(r["price_competitiveness"])}
             for r in rows],
        )
        logger.info("seeded vendors: %d rows", len(rows))

    if _table_empty("inventory"):
        rows = _load_csv("inventory.csv")
        int_fields = ("current_stock", "reserved_stock", "reorder_point", "safety_stock",
                      "lead_time_days", "avg_daily_demand", "days_since_last_sale")
        c.executemany(
            "INSERT INTO inventory(sku,warehouse_id,current_stock,reserved_stock,reorder_point,"
            "safety_stock,lead_time_days,unit_cost,avg_daily_demand,days_since_last_sale,primary_vendor) "
            "VALUES(:sku,:warehouse_id,:current_stock,:reserved_stock,:reorder_point,"
            ":safety_stock,:lead_time_days,:unit_cost,:avg_daily_demand,:days_since_last_sale,:primary_vendor)",
            [{**r,
              **{k: int(r[k]) for k in int_fields},
              "unit_cost": float(r["unit_cost"])}
             for r in rows],
        )
        logger.info("seeded inventory: %d rows", len(rows))

    if _table_empty("sales_history"):
        skus = [r["sku"] for r in _conn().execute("SELECT sku FROM skus")]
        rows = _generate_sales_history(skus, days=365, seed=42)
        c.executemany(
            "INSERT INTO sales_history(date,sku,quantity) VALUES(?,?,?)",
            rows,
        )
        logger.info("seeded sales_history: %d rows (%d SKUs × ~365 days)", len(rows), len(skus))


def _generate_sales_history(skus: list[str], days: int, seed: int) -> list[tuple]:
    """Deterministic synthetic sales history with seasonality + weekly cycle + slow growth."""
    rng = random.Random(seed)
    today = date.today()
    base_date = today - timedelta(days=days)
    out: list[tuple] = []
    for sku in skus:
        # Each SKU gets its own base demand level so they're not identical.
        base = rng.randint(60, 140)
        for i in range(days):
            d = base_date + timedelta(days=i)
            month = d.month
            seasonal = 1.3 if month in (10, 11, 12) else 0.8 if month in (1, 2) else 1.0
            dow = 0.6 if d.weekday() >= 5 else 1.0
            trend = 1 + (i / days) * 0.10
            qty = int(max(0, base * seasonal * dow * trend + rng.gauss(0, base * 0.2)))
            out.append((d.isoformat(), sku, qty))
    return out


# --- Read accessors --------------------------------------------------------

def list_skus() -> list[dict]:
    return [dict(r) for r in _conn().execute("SELECT sku,name,category FROM skus ORDER BY sku")]


def list_warehouses() -> list[dict]:
    return [dict(r) for r in _conn().execute(
        "SELECT id,name,location,capacity_sqm,used_sqm,region FROM warehouses ORDER BY id"
    )]


def list_inventory() -> list[dict]:
    return [dict(r) for r in _conn().execute("SELECT * FROM inventory ORDER BY sku, warehouse_id")]


def list_vendors() -> list[dict]:
    out: list[dict] = []
    for r in _conn().execute("SELECT * FROM vendors ORDER BY id"):
        row = dict(r)
        row["products"] = [p for p in (row["products"] or "").split(";") if p]
        out.append(row)
    return out


def list_sales_for_sku(sku: str) -> list[dict]:
    return [dict(r) for r in _conn().execute(
        "SELECT date,sku,quantity FROM sales_history WHERE sku=? ORDER BY date", (sku,)
    )]


# --- Write paths (called by /api/v1/data/upload) ---------------------------

def replace_skus(rows: list[dict]) -> int:
    c = _conn()
    with c:
        c.execute("DELETE FROM skus")
        c.executemany("INSERT INTO skus(sku,name,category) VALUES(:sku,:name,:category)", rows)
    return len(rows)


def replace_warehouses(rows: list[dict]) -> int:
    c = _conn()
    with c:
        c.execute("DELETE FROM warehouses")
        c.executemany(
            "INSERT INTO warehouses(id,name,location,capacity_sqm,used_sqm,region) "
            "VALUES(:id,:name,:location,:capacity_sqm,:used_sqm,:region)", rows)
    return len(rows)


def replace_inventory(rows: list[dict]) -> int:
    c = _conn()
    with c:
        c.execute("DELETE FROM inventory")
        c.executemany(
            "INSERT INTO inventory(sku,warehouse_id,current_stock,reserved_stock,reorder_point,"
            "safety_stock,lead_time_days,unit_cost,avg_daily_demand,days_since_last_sale,primary_vendor) "
            "VALUES(:sku,:warehouse_id,:current_stock,:reserved_stock,:reorder_point,"
            ":safety_stock,:lead_time_days,:unit_cost,:avg_daily_demand,:days_since_last_sale,:primary_vendor)",
            rows)
    return len(rows)


def replace_vendors(rows: list[dict]) -> int:
    c = _conn()
    serialized = [
        {**r, "products": ";".join(r["products"]) if isinstance(r.get("products"), list) else (r.get("products") or "")}
        for r in rows
    ]
    with c:
        c.execute("DELETE FROM vendors")
        c.executemany(
            "INSERT INTO vendors(id,name,country,lead_time_days,reliability_score,"
            "price_competitiveness,products,payment_terms,contact_email) "
            "VALUES(:id,:name,:country,:lead_time_days,:reliability_score,"
            ":price_competitiveness,:products,:payment_terms,:contact_email)",
            serialized)
    return len(rows)


def replace_sales(rows: list[dict]) -> int:
    """Replace ALL sales history with the provided rows."""
    c = _conn()
    with c:
        c.execute("DELETE FROM sales_history")
        c.executemany(
            "INSERT INTO sales_history(date,sku,quantity) VALUES(:date,:sku,:quantity)",
            rows)
    return len(rows)


def reset_to_seeds() -> None:
    """Drop everything and re-seed from the bundled CSVs."""
    c = _conn()
    with c:
        for t in ("skus", "warehouses", "inventory", "vendors", "sales_history"):
            c.execute(f"DELETE FROM {t}")
    seed_from_csv_if_empty()


def status() -> dict[str, int]:
    c = _conn()
    return {
        "skus":          c.execute("SELECT COUNT(*) FROM skus").fetchone()[0],
        "warehouses":    c.execute("SELECT COUNT(*) FROM warehouses").fetchone()[0],
        "inventory":     c.execute("SELECT COUNT(*) FROM inventory").fetchone()[0],
        "vendors":       c.execute("SELECT COUNT(*) FROM vendors").fetchone()[0],
        "sales_history": c.execute("SELECT COUNT(*) FROM sales_history").fetchone()[0],
    }
