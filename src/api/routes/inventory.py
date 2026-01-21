"""Supply Chain Optimizer - Inventory Management Routes."""

from fastapi import APIRouter, HTTPException, Query
import structlog

from src.api.schemas import (
    InventoryStatus,
    InventoryItem,
    ReorderRecommendation,
    TransferRecommendation,
)
from src.agents.inventory_agent import InventoryManagementAgent

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/status", response_model=InventoryStatus)
async def get_inventory_status(
    warehouse_id: str | None = Query(default=None, description="Filter by warehouse"),
    low_stock_only: bool = Query(default=False),
) -> InventoryStatus:
    """
    Get global inventory status across all warehouses.
    
    Returns:
    - Current stock levels by SKU and warehouse
    - Low stock and overstock alerts
    - Deadstock identification
    - Total inventory value
    """
    logger.info("Inventory status request", warehouse_id=warehouse_id)
    
    try:
        agent = InventoryManagementAgent()
        status = await agent.get_inventory_status(
            warehouse_id=warehouse_id,
            low_stock_only=low_stock_only,
        )
        return status
        
    except Exception as e:
        logger.error("Error getting inventory status", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/item/{sku}")
async def get_inventory_item(
    sku: str,
    warehouse_id: str | None = Query(default=None),
) -> list[InventoryItem]:
    """Get inventory details for a specific SKU."""
    logger.info("Inventory item request", sku=sku)
    
    try:
        agent = InventoryManagementAgent()
        items = await agent.get_item_inventory(sku, warehouse_id)
        return items
        
    except Exception as e:
        logger.error("Error getting inventory item", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reorder-recommendations", response_model=list[ReorderRecommendation])
async def get_reorder_recommendations(
    warehouse_id: str | None = Query(default=None),
    urgency: str | None = Query(default=None, description="'immediate', 'soon', or 'planned'"),
) -> list[ReorderRecommendation]:
    """
    Get recommended reorders based on current stock and demand forecasts.
    
    The Inventory Agent analyzes:
    - Current stock levels vs reorder points
    - Lead times from vendors
    - Demand forecasts
    - Safety stock requirements
    """
    logger.info("Reorder recommendations request")
    
    try:
        agent = InventoryManagementAgent()
        recommendations = await agent.get_reorder_recommendations(
            warehouse_id=warehouse_id,
            urgency_filter=urgency,
        )
        return recommendations
        
    except Exception as e:
        logger.error("Error getting reorder recommendations", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transfer-recommendations", response_model=list[TransferRecommendation])
async def get_transfer_recommendations() -> list[TransferRecommendation]:
    """
    Get recommended stock transfers between warehouses.
    
    Identifies opportunities to:
    - Balance inventory across locations
    - Reduce stockouts at high-demand locations
    - Minimize holding costs at overstocked locations
    """
    logger.info("Transfer recommendations request")
    
    try:
        agent = InventoryManagementAgent()
        recommendations = await agent.get_transfer_recommendations()
        return recommendations
        
    except Exception as e:
        logger.error("Error getting transfer recommendations", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/adjust")
async def adjust_inventory(
    sku: str,
    warehouse_id: str,
    adjustment: int,
    reason: str,
) -> dict:
    """
    Manually adjust inventory for a SKU.
    
    Used for:
    - Physical count reconciliation
    - Damage/loss write-offs
    - Returns processing
    """
    logger.info(
        "Inventory adjustment",
        sku=sku,
        warehouse_id=warehouse_id,
        adjustment=adjustment,
    )
    
    try:
        agent = InventoryManagementAgent()
        result = await agent.adjust_inventory(
            sku=sku,
            warehouse_id=warehouse_id,
            adjustment=adjustment,
            reason=reason,
        )
        return result
        
    except Exception as e:
        logger.error("Error adjusting inventory", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deadstock")
async def get_deadstock() -> list[dict]:
    """
    Identify slow-moving and dead stock items.
    
    Returns items with:
    - No sales in 90+ days
    - Excess inventory relative to demand
    - Liquidation recommendations
    """
    logger.info("Deadstock analysis request")
    
    try:
        agent = InventoryManagementAgent()
        deadstock = await agent.identify_deadstock()
        return deadstock
        
    except Exception as e:
        logger.error("Error getting deadstock", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
