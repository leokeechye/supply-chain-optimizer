"""Supply Chain Optimizer - Data ingest routes.

Lets callers replace the in-memory sample data with their own CSVs:

    POST   /api/v1/data/upload/{entity}     multipart file=<csv>
    GET    /api/v1/data/template/{entity}   downloadable CSV template
    GET    /api/v1/data/status              what's been overridden
    POST   /api/v1/data/reset               clear all overrides
    POST   /api/v1/data/reset/{entity}      clear one entity

Entities: skus, warehouses, inventory, sales, vendors.

State is in-memory only — see src/data/store.py for the persistence caveat.
"""

import csv
import io
from collections import defaultdict
from typing import Any, Callable

import structlog
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse

from src.data import store

router = APIRouter()
logger = structlog.get_logger(__name__)


# --- Per-entity schemas ----------------------------------------------------

def _as_int(v: str, field: str, row: int) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        raise ValueError(f"Row {row}: column '{field}' must be an integer, got {v!r}")


def _as_float(v: str, field: str, row: int) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        raise ValueError(f"Row {row}: column '{field}' must be a number, got {v!r}")


def _as_str(v: str, field: str, row: int) -> str:
    if v is None or str(v).strip() == "":
        raise ValueError(f"Row {row}: column '{field}' is empty")
    return str(v).strip()


def _row_skus(row: dict, row_num: int) -> dict:
    return {
        "sku":      _as_str(row.get("sku"),      "sku",      row_num),
        "name":     _as_str(row.get("name"),     "name",     row_num),
        "category": _as_str(row.get("category"), "category", row_num),
    }


def _row_warehouses(row: dict, row_num: int) -> dict:
    return {
        "id":           _as_str  (row.get("id"),           "id",           row_num),
        "name":         _as_str  (row.get("name"),         "name",         row_num),
        "location":     _as_str  (row.get("location"),     "location",     row_num),
        "capacity_sqm": _as_int  (row.get("capacity_sqm"), "capacity_sqm", row_num),
        "used_sqm":     _as_int  (row.get("used_sqm"),     "used_sqm",     row_num),
        "region":       _as_str  (row.get("region"),       "region",       row_num),
    }


def _row_inventory(row: dict, row_num: int) -> dict:
    return {
        "sku":                  _as_str  (row.get("sku"),                  "sku",                  row_num),
        "warehouse_id":         _as_str  (row.get("warehouse_id"),         "warehouse_id",         row_num),
        "current_stock":        _as_int  (row.get("current_stock"),        "current_stock",        row_num),
        "reserved_stock":       _as_int  (row.get("reserved_stock", 0),    "reserved_stock",       row_num),
        "reorder_point":        _as_int  (row.get("reorder_point"),        "reorder_point",        row_num),
        "safety_stock":         _as_int  (row.get("safety_stock"),         "safety_stock",         row_num),
        "lead_time_days":       _as_int  (row.get("lead_time_days"),       "lead_time_days",       row_num),
        "unit_cost":            _as_float(row.get("unit_cost"),            "unit_cost",            row_num),
        "avg_daily_demand":     _as_int  (row.get("avg_daily_demand", 0),  "avg_daily_demand",     row_num),
        "days_since_last_sale": _as_int  (row.get("days_since_last_sale", 0), "days_since_last_sale", row_num),
        "primary_vendor":       _as_str  (row.get("primary_vendor", "-"),  "primary_vendor",       row_num),
    }


def _row_sales(row: dict, row_num: int) -> dict:
    return {
        "date":     _as_str(row.get("date"),     "date",     row_num),
        "sku":      _as_str(row.get("sku"),      "sku",      row_num),
        "quantity": _as_int(row.get("quantity"), "quantity", row_num),
    }


def _row_vendors(row: dict, row_num: int) -> dict:
    products_raw = (row.get("products") or "").strip()
    products = [p.strip() for p in products_raw.split(";") if p.strip()] if products_raw else []
    return {
        "id":                     _as_str  (row.get("id"),                     "id",                     row_num),
        "name":                   _as_str  (row.get("name"),                   "name",                   row_num),
        "country":                _as_str  (row.get("country"),                "country",                row_num),
        "lead_time_days":         _as_int  (row.get("lead_time_days"),         "lead_time_days",         row_num),
        "reliability_score":      _as_float(row.get("reliability_score"),      "reliability_score",      row_num),
        "price_competitiveness":  _as_float(row.get("price_competitiveness"),  "price_competitiveness",  row_num),
        "products":               products,
        "payment_terms":          row.get("payment_terms") or "Net 30",
        "contact_email":          row.get("contact_email") or "",
    }


_SCHEMAS: dict[str, dict[str, Any]] = {
    "skus": {
        "columns": ["sku", "name", "category"],
        "parser":  _row_skus,
        "example": [{"sku": "SKU-001", "name": "Industrial Pump Motor", "category": "motors"}],
    },
    "warehouses": {
        "columns": ["id", "name", "location", "capacity_sqm", "used_sqm", "region"],
        "parser":  _row_warehouses,
        "example": [{"id": "WH-US-EAST", "name": "East Coast DC", "location": "Newark, NJ", "capacity_sqm": "50000", "used_sqm": "42000", "region": "us-east"}],
    },
    "inventory": {
        "columns": ["sku", "warehouse_id", "current_stock", "reserved_stock", "reorder_point", "safety_stock", "lead_time_days", "unit_cost", "avg_daily_demand", "days_since_last_sale", "primary_vendor"],
        "parser":  _row_inventory,
        "example": [{"sku": "SKU-001", "warehouse_id": "WH-US-EAST", "current_stock": "480", "reserved_stock": "52", "reorder_point": "180", "safety_stock": "90", "lead_time_days": "9", "unit_cost": "128.29", "avg_daily_demand": "12", "days_since_last_sale": "1", "primary_vendor": "VENDOR-001"}],
    },
    "sales": {
        "columns": ["date", "sku", "quantity"],
        "parser":  _row_sales,
        "example": [{"date": "2026-05-01", "sku": "SKU-001", "quantity": "85"}],
    },
    "vendors": {
        "columns": ["id", "name", "country", "lead_time_days", "reliability_score", "price_competitiveness", "products", "payment_terms", "contact_email"],
        "parser":  _row_vendors,
        "example": [{"id": "VENDOR-001", "name": "TechParts Manufacturing", "country": "China", "lead_time_days": "14", "reliability_score": "0.88", "price_competitiveness": "0.85", "products": "SKU-001;SKU-003;SKU-007", "payment_terms": "Net 30", "contact_email": "sales@techparts.example.com"}],
    },
}


# --- Helpers ---------------------------------------------------------------

def _parse_csv(content: bytes, entity: str) -> list[dict]:
    schema = _SCHEMAS[entity]
    parser: Callable[[dict, int], dict] = schema["parser"]
    required = set(schema["columns"])

    try:
        text = content.decode("utf-8-sig")  # strip BOM if Excel
    except UnicodeDecodeError as e:
        raise HTTPException(status_code=400, detail=f"File is not UTF-8: {e}")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV has no header row")

    headers = {h.strip() for h in reader.fieldnames if h}
    missing = required - headers
    # Allow extra columns; only required ones must be present. Sales doesn't
    # care about optional columns either. Inventory has a few optional ones
    # (reserved_stock, avg_daily_demand, etc) with defaults — they're listed
    # in `columns` but the parser tolerates missing values.
    if entity in ("skus", "warehouses", "sales", "vendors"):
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing required columns: {sorted(missing)}")
    else:
        # Inventory: only the truly required subset.
        inv_required = {"sku", "warehouse_id", "current_stock", "reorder_point", "safety_stock", "lead_time_days", "unit_cost"}
        if (m := inv_required - headers):
            raise HTTPException(status_code=400, detail=f"Missing required columns: {sorted(m)}")

    rows: list[dict] = []
    try:
        for i, raw in enumerate(reader, start=2):  # start=2 (header is row 1)
            rows.append(parser(raw, i))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not rows:
        raise HTTPException(status_code=400, detail="CSV has no data rows")
    return rows


# --- Endpoints -------------------------------------------------------------

@router.post("/upload/{entity}")
async def upload_entity(entity: str, file: UploadFile = File(...)) -> dict:
    """Upload a CSV for one entity. Replaces any previous override."""
    if entity not in _SCHEMAS:
        raise HTTPException(status_code=404, detail=f"Unknown entity '{entity}'. Allowed: {list(_SCHEMAS)}")

    content = await file.read()
    rows = _parse_csv(content, entity)
    logger.info("Data upload", entity=entity, row_count=len(rows), filename=file.filename)

    if entity == "sales":
        grouped: dict[str, list[dict]] = defaultdict(list)
        for r in rows:
            grouped[r["sku"]].append(r)
        store.set_sales_override(dict(grouped))
        return {"entity": "sales", "rows_loaded": len(rows), "skus_with_history": list(grouped.keys())}

    store.set_override(entity, rows)
    return {"entity": entity, "rows_loaded": len(rows)}


@router.get("/template/{entity}", response_class=PlainTextResponse)
async def download_template(entity: str) -> PlainTextResponse:
    """Download a starter CSV with the expected header + one example row."""
    if entity not in _SCHEMAS:
        raise HTTPException(status_code=404, detail=f"Unknown entity '{entity}'. Allowed: {list(_SCHEMAS)}")

    schema = _SCHEMAS[entity]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=schema["columns"])
    writer.writeheader()
    for ex in schema["example"]:
        writer.writerow(ex)
    return PlainTextResponse(
        buf.getvalue(),
        headers={"Content-Disposition": f'attachment; filename="{entity}_template.csv"'},
        media_type="text/csv",
    )


@router.get("/status")
async def get_status() -> dict:
    """Show which entities have been overridden by uploads."""
    return store.status()


@router.post("/reset")
async def reset_all() -> dict:
    """Drop every override and fall back to sample data for all entities."""
    store.reset_all()
    return {"reset": "all", "status": store.status()}


@router.post("/reset/{entity}")
async def reset_one(entity: str) -> dict:
    """Drop the override for one entity."""
    try:
        store.reset_entity(entity)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown entity '{entity}'")
    return {"reset": entity, "status": store.status()}
