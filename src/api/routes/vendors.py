"""Supply Chain Optimizer - Vendor Management Routes."""

from datetime import date

from fastapi import APIRouter, HTTPException, Query
import structlog

from src.api.schemas import (
    Vendor,
    PurchaseOrder,
    PurchaseOrderRequest,
    VendorPerformance,
    OrderStatus,
)
from src.agents.vendor_agent import VendorCoordinationAgent

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/", response_model=list[Vendor])
async def list_vendors(
    product_sku: str | None = Query(default=None, description="Filter by product SKU"),
    country: str | None = Query(default=None),
) -> list[Vendor]:
    """
    List all vendors with their profiles and capabilities.
    """
    logger.info("List vendors request")
    
    try:
        agent = VendorCoordinationAgent()
        vendors = await agent.list_vendors(
            product_sku=product_sku,
            country=country,
        )
        return vendors
        
    except Exception as e:
        logger.error("Error listing vendors", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{vendor_id}", response_model=Vendor)
async def get_vendor(vendor_id: str) -> Vendor:
    """Get vendor details by ID."""
    logger.info("Get vendor", vendor_id=vendor_id)
    
    try:
        agent = VendorCoordinationAgent()
        vendor = await agent.get_vendor(vendor_id)
        
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        
        return vendor
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting vendor", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders", response_model=list[PurchaseOrder])
async def list_purchase_orders(
    status: OrderStatus | None = Query(default=None),
    vendor_id: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
) -> list[PurchaseOrder]:
    """
    List active purchase orders.
    
    Filter by status, vendor, or date range.
    """
    logger.info("List orders request", status=status, vendor_id=vendor_id)
    
    try:
        agent = VendorCoordinationAgent()
        orders = await agent.list_orders(
            status=status,
            vendor_id=vendor_id,
            from_date=from_date,
            to_date=to_date,
        )
        return orders
        
    except Exception as e:
        logger.error("Error listing orders", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders", response_model=PurchaseOrder)
async def create_purchase_order(request: PurchaseOrderRequest) -> PurchaseOrder:
    """
    Create a new purchase order.
    
    The Vendor Agent will:
    - Validate vendor and item availability
    - Calculate total cost
    - Apply negotiated pricing
    - Set expected delivery based on lead times
    """
    logger.info("Create PO request", vendor_id=request.vendor_id)
    
    try:
        agent = VendorCoordinationAgent()
        order = await agent.create_order(request)
        return order
        
    except Exception as e:
        logger.error("Error creating order", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/{po_number}", response_model=PurchaseOrder)
async def get_purchase_order(po_number: str) -> PurchaseOrder:
    """Get purchase order details."""
    logger.info("Get PO", po_number=po_number)
    
    try:
        agent = VendorCoordinationAgent()
        order = await agent.get_order(po_number)
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        return order
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting order", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/orders/{po_number}/cancel")
async def cancel_purchase_order(po_number: str, reason: str) -> dict:
    """Cancel a purchase order."""
    logger.info("Cancel PO", po_number=po_number)
    
    try:
        agent = VendorCoordinationAgent()
        result = await agent.cancel_order(po_number, reason)
        return result
        
    except Exception as e:
        logger.error("Error cancelling order", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{vendor_id}/performance", response_model=VendorPerformance)
async def get_vendor_performance(
    vendor_id: str,
    period_days: int = Query(default=90, ge=30, le=365),
) -> VendorPerformance:
    """
    Get vendor performance metrics.
    
    Tracks:
    - On-time delivery rate
    - Quality/defect rate
    - Average lead time
    - Total spend
    - Issue count
    """
    logger.info("Vendor performance request", vendor_id=vendor_id)
    
    try:
        agent = VendorCoordinationAgent()
        performance = await agent.get_vendor_performance(vendor_id, period_days)
        return performance
        
    except Exception as e:
        logger.error("Error getting performance", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rfq")
async def request_for_quote(
    product_sku: str,
    quantity: int,
    target_delivery_date: date,
    vendor_ids: list[str] | None = None,
) -> dict:
    """
    Send Request for Quote (RFQ) to vendors.
    
    The Vendor Agent will:
    - Identify eligible vendors
    - Send quote requests
    - Collect and compare responses
    - Recommend best option
    """
    logger.info("RFQ request", sku=product_sku, quantity=quantity)
    
    try:
        agent = VendorCoordinationAgent()
        result = await agent.request_quotes(
            product_sku=product_sku,
            quantity=quantity,
            target_delivery_date=target_delivery_date,
            vendor_ids=vendor_ids,
        )
        return result
        
    except Exception as e:
        logger.error("Error requesting quotes", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{vendor_id}/negotiate")
async def negotiate_pricing(
    vendor_id: str,
    product_sku: str,
    proposed_price: float,
    volume_commitment: int,
) -> dict:
    """
    Initiate automated price negotiation with vendor.
    
    The agent uses:
    - Historical pricing data
    - Market benchmarks
    - Volume leverage
    - Vendor relationship strength
    """
    logger.info("Negotiation request", vendor_id=vendor_id, sku=product_sku)
    
    try:
        agent = VendorCoordinationAgent()
        result = await agent.negotiate_pricing(
            vendor_id=vendor_id,
            product_sku=product_sku,
            proposed_price=proposed_price,
            volume_commitment=volume_commitment,
        )
        return result
        
    except Exception as e:
        logger.error("Error negotiating", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
