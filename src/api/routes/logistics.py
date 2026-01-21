"""Supply Chain Optimizer - Logistics & Routing Routes."""

from fastapi import APIRouter, HTTPException
import structlog

from src.api.schemas import (
    RouteOptimizationRequest,
    RouteOptimizationResponse,
    ShipmentTracking,
    ShippingMode,
)
from src.agents.logistics_agent import LogisticsRouteAgent

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("/optimize", response_model=RouteOptimizationResponse)
async def optimize_route(request: RouteOptimizationRequest) -> RouteOptimizationResponse:
    """
    Run route optimization for a shipment.
    
    The Logistics Agent considers:
    - Multi-modal options (Air, Sea, Road, Rail)
    - Cost vs speed trade-offs
    - Current traffic and weather conditions
    - Carrier reliability scores
    - CO2 emissions (sustainability)
    
    Returns recommended and alternative routes with full cost breakdown.
    """
    logger.info(
        "Route optimization request",
        origin=request.origin,
        destination=request.destination,
        priority=request.priority,
    )
    
    try:
        agent = LogisticsRouteAgent()
        result = await agent.optimize_route(request)
        return result
        
    except Exception as e:
        logger.error("Error optimizing route", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/carriers")
async def list_carriers(
    mode: ShippingMode | None = None,
    origin_country: str | None = None,
    destination_country: str | None = None,
) -> list[dict]:
    """
    List available carriers with performance metrics.
    
    Shows:
    - Carrier name and supported modes
    - Average transit times
    - Reliability scores
    - Cost competitiveness
    """
    logger.info("List carriers request")
    
    try:
        agent = LogisticsRouteAgent()
        carriers = await agent.list_carriers(
            mode=mode,
            origin_country=origin_country,
            destination_country=destination_country,
        )
        return carriers
        
    except Exception as e:
        logger.error("Error listing carriers", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/track/{shipment_id}", response_model=ShipmentTracking)
async def track_shipment(shipment_id: str) -> ShipmentTracking:
    """
    Get real-time tracking for a shipment.
    
    Returns:
    - Current location and status
    - Full event history
    - Updated ETA
    """
    logger.info("Track shipment", shipment_id=shipment_id)
    
    try:
        agent = LogisticsRouteAgent()
        tracking = await agent.track_shipment(shipment_id)
        
        if not tracking:
            raise HTTPException(status_code=404, detail="Shipment not found")
        
        return tracking
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error tracking shipment", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/consolidate")
async def consolidate_shipments(
    shipment_ids: list[str],
) -> dict:
    """
    Analyze shipment consolidation opportunities.
    
    Groups small shipments to:
    - Maximize container utilization
    - Reduce per-unit shipping costs
    - Minimize environmental impact
    """
    logger.info("Consolidation request", shipment_count=len(shipment_ids))
    
    try:
        agent = LogisticsRouteAgent()
        result = await agent.consolidate_shipments(shipment_ids)
        return result
        
    except Exception as e:
        logger.error("Error consolidating shipments", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/capacity")
async def get_warehouse_capacity() -> list[dict]:
    """
    Get current warehouse capacity utilization.
    
    Shows:
    - Available space by warehouse
    - Inbound/outbound volume trends
    - Capacity bottlenecks
    """
    logger.info("Warehouse capacity request")
    
    try:
        agent = LogisticsRouteAgent()
        capacity = await agent.get_warehouse_capacity()
        return capacity
        
    except Exception as e:
        logger.error("Error getting capacity", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reroute/{shipment_id}")
async def reroute_shipment(
    shipment_id: str,
    reason: str,
    new_destination: str | None = None,
) -> dict:
    """
    Request shipment rerouting due to disruption or change.
    
    The agent will:
    - Analyze current shipment position
    - Calculate new optimal route
    - Coordinate with carrier for rerouting
    """
    logger.info("Reroute request", shipment_id=shipment_id, reason=reason)
    
    try:
        agent = LogisticsRouteAgent()
        result = await agent.reroute_shipment(
            shipment_id=shipment_id,
            reason=reason,
            new_destination=new_destination,
        )
        return result
        
    except Exception as e:
        logger.error("Error rerouting shipment", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
