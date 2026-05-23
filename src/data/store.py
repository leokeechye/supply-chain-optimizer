"""Supply Chain Optimizer - In-memory data override store.

When a CSV is uploaded via POST /api/v1/data/upload/{entity}, the parsed rows
land here. Accessor functions in sample_data.py check this store first and
fall back to the hardcoded defaults when an entity hasn't been overridden.

State is process-local: it does NOT survive a restart, a redeploy, or a
Railway sleep. Re-upload after any of those. If you need persistence, swap
this module for the SQLite path declared in src/config.py.
"""

from threading import RLock
from typing import Any

_lock = RLock()

# Entity → overriding payload. None means "not overridden; use default".
# Sales is keyed by SKU because the consumer asks for one SKU at a time.
_overrides: dict[str, Any] = {
    "skus": None,
    "warehouses": None,
    "inventory": None,
    "sales": {},  # {sku: list[dict]}
    "vendors": None,
}


def get_override(entity: str) -> Any:
    with _lock:
        return _overrides.get(entity)


def set_override(entity: str, value: Any) -> None:
    if entity not in _overrides:
        raise KeyError(f"Unknown entity: {entity}")
    with _lock:
        _overrides[entity] = value


def get_sales_override(sku: str) -> list[dict] | None:
    with _lock:
        sales = _overrides.get("sales") or {}
        return sales.get(sku)


def set_sales_override(sales_by_sku: dict[str, list[dict]]) -> None:
    with _lock:
        _overrides["sales"] = sales_by_sku


def reset_entity(entity: str) -> None:
    if entity not in _overrides:
        raise KeyError(f"Unknown entity: {entity}")
    with _lock:
        _overrides[entity] = {} if entity == "sales" else None


def reset_all() -> None:
    with _lock:
        for k in list(_overrides.keys()):
            _overrides[k] = {} if k == "sales" else None


def status() -> dict[str, Any]:
    with _lock:
        return {
            "skus":       {"overridden": _overrides["skus"]       is not None, "count": len(_overrides["skus"]      or [])},
            "warehouses": {"overridden": _overrides["warehouses"] is not None, "count": len(_overrides["warehouses"] or [])},
            "inventory":  {"overridden": _overrides["inventory"]  is not None, "count": len(_overrides["inventory"]  or [])},
            "vendors":    {"overridden": _overrides["vendors"]    is not None, "count": len(_overrides["vendors"]    or [])},
            "sales":      {"overridden": bool(_overrides["sales"]),            "skus_with_history": list((_overrides["sales"] or {}).keys())},
        }
