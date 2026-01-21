"""Supply Chain Optimizer - Vendor Coordination Agent."""

from datetime import datetime, date, timedelta
from typing import Any
import uuid

from langchain_core.prompts import ChatPromptTemplate

from src.agents.base import BaseAgent
from src.api.schemas import (
    Vendor,
    PurchaseOrder,
    PurchaseOrderRequest,
    VendorPerformance,
    OrderStatus,
)
from src.data.sample_data import get_vendor_data, get_order_data


class VendorCoordinationAgent(BaseAgent):
    """
    Agent responsible for vendor relationship management.
    
    Capabilities:
    - Purchase Order generation and tracking
    - Vendor performance monitoring
    - RFQ (Request for Quote) management
    - Automated price negotiation
    - Supplier diversification recommendations
    """

    def __init__(self):
        super().__init__(
            name="Vendor Coordination Agent",
            description=(
                "a procurement specialist managing vendor relationships, "
                "purchase orders, and supplier negotiations"
            ),
        )
        
        self.negotiation_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a procurement negotiation expert.
Analyze the pricing scenario and suggest a negotiation strategy.

Consider:
1. Current market prices
2. Order volume leverage
3. Vendor relationship history
4. Alternative supplier availability
5. Quality and reliability factors

Provide a concise negotiation recommendation.
"""),
            ("human", """Negotiation Context:
- Vendor: {vendor_name}
- Product: {product_sku}
- Current Price: ${current_price:.2f}
- Proposed Price: ${proposed_price:.2f}
- Volume Commitment: {volume} units
- Vendor Reliability Score: {reliability:.0%}

What is your negotiation strategy?"""),
        ])

    async def run(self, action: str, **kwargs: Any) -> dict:
        """Execute vendor management actions."""
        if action == "list":
            return await self.list_vendors(**kwargs)
        elif action == "create_order":
            return await self.create_order(**kwargs)
        elif action == "performance":
            return await self.get_vendor_performance(**kwargs)
        else:
            raise ValueError(f"Unknown action: {action}")

    async def list_vendors(
        self,
        product_sku: str | None = None,
        country: str | None = None,
    ) -> list[Vendor]:
        """List vendors with optional filtering."""
        vendors = get_vendor_data()
        
        if product_sku:
            vendors = [v for v in vendors if product_sku in v.get("products", [])]
        
        if country:
            vendors = [v for v in vendors if v["country"].lower() == country.lower()]
        
        return [
            Vendor(
                vendor_id=v["id"],
                name=v["name"],
                country=v["country"],
                lead_time_days=v["lead_time_days"],
                reliability_score=v["reliability_score"],
                price_competitiveness=v.get("price_competitiveness", 0.7),
                products=v.get("products", []),
                payment_terms=v.get("payment_terms"),
                contact_email=v.get("contact_email"),
            )
            for v in vendors
        ]

    async def get_vendor(self, vendor_id: str) -> Vendor | None:
        """Get vendor by ID."""
        vendors = get_vendor_data()
        
        for v in vendors:
            if v["id"] == vendor_id:
                return Vendor(
                    vendor_id=v["id"],
                    name=v["name"],
                    country=v["country"],
                    lead_time_days=v["lead_time_days"],
                    reliability_score=v["reliability_score"],
                    price_competitiveness=v.get("price_competitiveness", 0.7),
                    products=v.get("products", []),
                    payment_terms=v.get("payment_terms"),
                    contact_email=v.get("contact_email"),
                )
        
        return None

    async def list_orders(
        self,
        status: OrderStatus | None = None,
        vendor_id: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[PurchaseOrder]:
        """List purchase orders with filtering."""
        orders = get_order_data()
        
        if status:
            orders = [o for o in orders if o["status"] == status.value]
        
        if vendor_id:
            orders = [o for o in orders if o["vendor_id"] == vendor_id]
        
        return [
            PurchaseOrder(
                po_number=o["po_number"],
                vendor_id=o["vendor_id"],
                vendor_name=o["vendor_name"],
                status=OrderStatus(o["status"]),
                items=o["items"],
                total_amount=o["total_amount"],
                currency=o.get("currency", "USD"),
                created_at=datetime.fromisoformat(o["created_at"]),
                expected_delivery=date.fromisoformat(o["expected_delivery"]) if o.get("expected_delivery") else None,
                actual_delivery=date.fromisoformat(o["actual_delivery"]) if o.get("actual_delivery") else None,
                notes=o.get("notes"),
            )
            for o in orders
        ]

    async def create_order(self, request: PurchaseOrderRequest) -> PurchaseOrder:
        """Create a new purchase order."""
        self.logger.info("Creating purchase order", vendor_id=request.vendor_id)
        
        # Get vendor details
        vendor = await self.get_vendor(request.vendor_id)
        if not vendor:
            raise ValueError(f"Vendor not found: {request.vendor_id}")
        
        # Calculate total
        total = sum(
            item.get("quantity", 0) * item.get("unit_price", 0)
            for item in request.items
        )
        
        # Calculate expected delivery
        expected_delivery = date.today() + timedelta(days=vendor.lead_time_days)
        if request.requested_delivery_date:
            expected_delivery = max(expected_delivery, request.requested_delivery_date)
        
        po_number = f"PO-{uuid.uuid4().hex[:8].upper()}"
        
        return PurchaseOrder(
            po_number=po_number,
            vendor_id=request.vendor_id,
            vendor_name=vendor.name,
            status=OrderStatus.PENDING,
            items=request.items,
            total_amount=round(total, 2),
            currency="USD",
            created_at=datetime.utcnow(),
            expected_delivery=expected_delivery,
            notes=request.notes,
        )

    async def get_order(self, po_number: str) -> PurchaseOrder | None:
        """Get order by PO number."""
        orders = get_order_data()
        
        for o in orders:
            if o["po_number"] == po_number:
                return PurchaseOrder(
                    po_number=o["po_number"],
                    vendor_id=o["vendor_id"],
                    vendor_name=o["vendor_name"],
                    status=OrderStatus(o["status"]),
                    items=o["items"],
                    total_amount=o["total_amount"],
                    currency=o.get("currency", "USD"),
                    created_at=datetime.fromisoformat(o["created_at"]),
                    expected_delivery=date.fromisoformat(o["expected_delivery"]) if o.get("expected_delivery") else None,
                    actual_delivery=date.fromisoformat(o["actual_delivery"]) if o.get("actual_delivery") else None,
                    notes=o.get("notes"),
                )
        
        return None

    async def cancel_order(self, po_number: str, reason: str) -> dict:
        """Cancel a purchase order."""
        self.logger.info("Cancelling order", po_number=po_number, reason=reason)
        
        return {
            "status": "cancelled",
            "po_number": po_number,
            "reason": reason,
            "cancelled_at": datetime.utcnow().isoformat(),
        }

    async def get_vendor_performance(
        self,
        vendor_id: str,
        period_days: int = 90,
    ) -> VendorPerformance:
        """Get vendor performance metrics."""
        vendor = await self.get_vendor(vendor_id)
        if not vendor:
            raise ValueError(f"Vendor not found: {vendor_id}")
        
        # Simulated performance data
        end_date = date.today()
        start_date = end_date - timedelta(days=period_days)
        
        return VendorPerformance(
            vendor_id=vendor_id,
            vendor_name=vendor.name,
            period_start=start_date,
            period_end=end_date,
            total_orders=24,
            on_time_delivery_rate=vendor.reliability_score,
            quality_rate=0.97,
            average_lead_time_days=vendor.lead_time_days,
            total_spend=125000.00,
            issues_count=2,
            overall_score=round(vendor.reliability_score * 100, 1),
        )

    async def request_quotes(
        self,
        product_sku: str,
        quantity: int,
        target_delivery_date: date,
        vendor_ids: list[str] | None = None,
    ) -> dict:
        """Send RFQ to vendors and collect quotes."""
        self.logger.info(
            "Requesting quotes",
            sku=product_sku,
            quantity=quantity,
            vendors=vendor_ids,
        )
        
        # Get eligible vendors
        if vendor_ids:
            vendors = [await self.get_vendor(vid) for vid in vendor_ids]
            vendors = [v for v in vendors if v]
        else:
            all_vendors = await self.list_vendors(product_sku=product_sku)
            vendors = all_vendors[:5]  # Top 5 vendors
        
        # Simulated quotes
        quotes = []
        for vendor in vendors:
            base_price = 10.0  # Base price per unit
            competitive_price = base_price * (2 - vendor.price_competitiveness)
            
            # Volume discount
            if quantity > 1000:
                competitive_price *= 0.9
            elif quantity > 500:
                competitive_price *= 0.95
            
            quotes.append({
                "vendor_id": vendor.vendor_id,
                "vendor_name": vendor.name,
                "unit_price": round(competitive_price, 2),
                "total_price": round(competitive_price * quantity, 2),
                "lead_time_days": vendor.lead_time_days,
                "can_meet_date": (date.today() + timedelta(days=vendor.lead_time_days)) <= target_delivery_date,
            })
        
        # Sort by total price
        quotes.sort(key=lambda q: q["total_price"])
        
        return {
            "rfq_id": f"RFQ-{uuid.uuid4().hex[:8].upper()}",
            "product_sku": product_sku,
            "quantity": quantity,
            "target_delivery": target_delivery_date.isoformat(),
            "quotes_received": len(quotes),
            "quotes": quotes,
            "recommendation": quotes[0] if quotes else None,
        }

    async def negotiate_pricing(
        self,
        vendor_id: str,
        product_sku: str,
        proposed_price: float,
        volume_commitment: int,
    ) -> dict:
        """Initiate automated price negotiation."""
        self.logger.info(
            "Negotiating pricing",
            vendor_id=vendor_id,
            sku=product_sku,
            proposed=proposed_price,
        )
        
        vendor = await self.get_vendor(vendor_id)
        if not vendor:
            raise ValueError(f"Vendor not found: {vendor_id}")
        
        # Current price (simulated)
        current_price = 12.50
        
        # Get AI negotiation strategy
        try:
            chain = self.negotiation_prompt | self.llm
            strategy_result = await chain.ainvoke({
                "vendor_name": vendor.name,
                "product_sku": product_sku,
                "current_price": current_price,
                "proposed_price": proposed_price,
                "volume": volume_commitment,
                "reliability": vendor.reliability_score,
            })
            strategy = strategy_result.content
        except Exception as e:
            self.logger.warning("AI strategy generation failed", error=str(e))
            strategy = "Standard volume-based negotiation recommended"
        
        # Calculate likely outcome
        discount_potential = min(0.15, volume_commitment / 10000)  # Max 15% discount
        realistic_price = current_price * (1 - discount_potential)
        
        return {
            "vendor_id": vendor_id,
            "vendor_name": vendor.name,
            "product_sku": product_sku,
            "current_price": current_price,
            "proposed_price": proposed_price,
            "volume_commitment": volume_commitment,
            "realistic_price": round(realistic_price, 2),
            "potential_savings": round((current_price - realistic_price) * volume_commitment, 2),
            "negotiation_strategy": strategy,
            "confidence": "high" if vendor.reliability_score > 0.8 else "medium",
        }
