"""Supply Chain Optimizer - API Router Assembly.

Extracted from src/api/__init__.py so that importing src.api.schemas does not
trigger eager loading of every route (and through them, every agent), which
caused a circular import when src.agents.orchestrator was imported directly.
"""

from fastapi import APIRouter

from src.api.routes import (
    forecast,
    inventory,
    logistics,
    orchestrate,
    risk,
    vendors,
)

router = APIRouter()

router.include_router(forecast.router, prefix="/forecast", tags=["Demand Forecasting"])
router.include_router(inventory.router, prefix="/inventory", tags=["Inventory Management"])
router.include_router(logistics.router, prefix="/logistics", tags=["Logistics & Routing"])
router.include_router(risk.router, prefix="/risk", tags=["Risk Analysis"])
router.include_router(vendors.router, prefix="/vendors", tags=["Vendor Management"])
router.include_router(orchestrate.router, prefix="/orchestrate", tags=["Multi-Agent Orchestrator"])
