"""Supply Chain Optimizer - API Routes."""

from fastapi import APIRouter

from src.api.routes import (
    forecast,
    inventory,
    logistics,
    risk,
    vendors,
)

router = APIRouter()

# Include all route modules
router.include_router(forecast.router, prefix="/forecast", tags=["Demand Forecasting"])
router.include_router(inventory.router, prefix="/inventory", tags=["Inventory Management"])
router.include_router(logistics.router, prefix="/logistics", tags=["Logistics & Routing"])
router.include_router(risk.router, prefix="/risk", tags=["Risk Analysis"])
router.include_router(vendors.router, prefix="/vendors", tags=["Vendor Management"])
