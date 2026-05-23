"""Supply Chain Optimizer - Inventory Management Agent."""

from datetime import datetime, date, timedelta
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from src.agents.base import BaseAgent
from src.api.schemas import (
    InventoryStatus,
    InventoryItem,
    ReorderRecommendation,
    TransferRecommendation,
)
from src.data.sample_data import get_inventory_data, get_warehouse_data, get_skus


class InventoryManagementAgent(BaseAgent):
    """
    Agent responsible for inventory monitoring and optimization.
    
    Capabilities:
    - Real-time stock level monitoring
    - Dynamic safety stock calculation
    - Reorder point (ROP) management
    - Warehouse balancing recommendations
    - Deadstock identification
    """

    def __init__(self):
        super().__init__(
            name="Inventory Management Agent",
            description=(
                "an inventory optimization specialist managing stock levels, "
                "reorder points, and warehouse balancing across the supply chain"
            ),
        )
        
        self.reorder_analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an inventory management expert.
Analyze the stock situation and provide a concise recommendation.

Consider:
1. Current stock vs reorder point
2. Lead time from suppliers
3. Demand forecast
4. Safety stock requirements
5. Cost implications

Be direct and actionable.
"""),
            ("human", """SKU: {sku} ({sku_name})
Warehouse: {warehouse_id}
Current Stock: {current_stock} units
Reorder Point: {reorder_point} units
Safety Stock: {safety_stock} units
Lead Time: {lead_time_days} days
Average Daily Demand: {avg_daily_demand} units
Days of Stock Remaining: {days_of_stock:.1f}

What is your recommendation?"""),
        ])

    async def run(self, action: str, **kwargs: Any) -> dict:
        """Execute inventory management actions."""
        if action == "status":
            return await self.get_inventory_status(**kwargs)
        elif action == "reorder":
            return await self.get_reorder_recommendations(**kwargs)
        elif action == "transfer":
            return await self.get_transfer_recommendations()
        else:
            raise ValueError(f"Unknown action: {action}")

    async def get_inventory_status(
        self,
        warehouse_id: str | None = None,
        low_stock_only: bool = False,
    ) -> InventoryStatus:
        """Get comprehensive inventory status."""
        self.logger.info("Getting inventory status", warehouse_id=warehouse_id)
        
        inventory_data = get_inventory_data()
        warehouses = get_warehouse_data()
        
        # Filter by warehouse if specified
        if warehouse_id:
            inventory_data = [i for i in inventory_data if i["warehouse_id"] == warehouse_id]
        
        # Build inventory items
        items = []
        low_stock_alerts = []
        overstock_alerts = []
        deadstock_items = []
        total_value = 0
        
        for inv in inventory_data:
            available = inv["current_stock"] - inv.get("reserved_stock", 0)
            
            item = InventoryItem(
                sku=inv["sku"],
                sku_name=self._get_sku_name(inv["sku"]),
                warehouse_id=inv["warehouse_id"],
                current_stock=inv["current_stock"],
                reserved_stock=inv.get("reserved_stock", 0),
                available_stock=available,
                reorder_point=inv["reorder_point"],
                safety_stock=inv["safety_stock"],
                lead_time_days=inv["lead_time_days"],
                unit_cost=inv["unit_cost"],
                last_updated=datetime.utcnow(),
            )
            
            # Check stock levels
            if available <= inv["safety_stock"]:
                low_stock_alerts.append({
                    "sku": inv["sku"],
                    "warehouse_id": inv["warehouse_id"],
                    "available_stock": available,
                    "safety_stock": inv["safety_stock"],
                    "severity": "critical" if available <= inv["safety_stock"] * 0.5 else "warning",
                })
            
            if available > inv["reorder_point"] * 3:
                overstock_alerts.append({
                    "sku": inv["sku"],
                    "warehouse_id": inv["warehouse_id"],
                    "available_stock": available,
                    "excess_quantity": available - inv["reorder_point"] * 2,
                })
            
            # Check for deadstock (simulated: days_since_last_sale > 90)
            if inv.get("days_since_last_sale", 0) > 90:
                deadstock_items.append(inv["sku"])
            
            total_value += inv["current_stock"] * inv["unit_cost"]
            
            if not low_stock_only or available <= inv["reorder_point"]:
                items.append(item)
        
        return InventoryStatus(
            total_skus=len(set(i["sku"] for i in inventory_data)),
            total_warehouses=len(warehouses),
            items=items,
            low_stock_alerts=low_stock_alerts,
            overstock_alerts=overstock_alerts,
            deadstock_items=deadstock_items,
            total_inventory_value=round(total_value, 2),
        )

    async def get_item_inventory(
        self,
        sku: str,
        warehouse_id: str | None = None,
    ) -> list[InventoryItem]:
        """Get inventory for a specific SKU."""
        inventory_data = get_inventory_data()
        
        items = []
        for inv in inventory_data:
            if inv["sku"] != sku:
                continue
            if warehouse_id and inv["warehouse_id"] != warehouse_id:
                continue
            
            available = inv["current_stock"] - inv.get("reserved_stock", 0)
            
            items.append(InventoryItem(
                sku=inv["sku"],
                sku_name=self._get_sku_name(inv["sku"]),
                warehouse_id=inv["warehouse_id"],
                current_stock=inv["current_stock"],
                reserved_stock=inv.get("reserved_stock", 0),
                available_stock=available,
                reorder_point=inv["reorder_point"],
                safety_stock=inv["safety_stock"],
                lead_time_days=inv["lead_time_days"],
                unit_cost=inv["unit_cost"],
                last_updated=datetime.utcnow(),
            ))
        
        return items

    async def get_reorder_recommendations(
        self,
        warehouse_id: str | None = None,
        urgency_filter: str | None = None,
    ) -> list[ReorderRecommendation]:
        """Generate reorder recommendations based on current stock and forecasts."""
        self.logger.info("Generating reorder recommendations")
        
        inventory_data = get_inventory_data()
        recommendations = []
        
        for inv in inventory_data:
            if warehouse_id and inv["warehouse_id"] != warehouse_id:
                continue
            
            available = inv["current_stock"] - inv.get("reserved_stock", 0)
            avg_daily_demand = inv.get("avg_daily_demand", 10)
            
            # Calculate days of stock remaining
            days_of_stock = available / avg_daily_demand if avg_daily_demand > 0 else 999
            
            # Determine urgency
            if days_of_stock <= inv["lead_time_days"]:
                urgency = "immediate"
            elif days_of_stock <= inv["lead_time_days"] * 1.5:
                urgency = "soon"
            elif available <= inv["reorder_point"]:
                urgency = "planned"
            else:
                continue  # No reorder needed
            
            if urgency_filter and urgency != urgency_filter:
                continue
            
            # Calculate recommended order quantity (Economic Order Quantity simplified)
            order_quantity = max(
                inv["reorder_point"] * 2 - available,
                inv["safety_stock"] * 3,
            )
            
            # Estimate stockout date
            stockout_date = None
            if days_of_stock < 30:
                stockout_date = date.today() + timedelta(days=int(days_of_stock))
            
            recommendations.append(ReorderRecommendation(
                sku=inv["sku"],
                sku_name=self._get_sku_name(inv["sku"]),
                warehouse_id=inv["warehouse_id"],
                current_stock=available,
                recommended_order_quantity=int(order_quantity),
                urgency=urgency,
                reason=self._get_reorder_reason(urgency, days_of_stock, inv["lead_time_days"]),
                estimated_stockout_date=stockout_date,
                suggested_vendor=inv.get("primary_vendor"),
                estimated_cost=round(order_quantity * inv["unit_cost"], 2),
            ))
        
        # Sort by urgency
        urgency_order = {"immediate": 0, "soon": 1, "planned": 2}
        recommendations.sort(key=lambda r: urgency_order.get(r.urgency, 3))
        
        return recommendations

    async def get_transfer_recommendations(self) -> list[TransferRecommendation]:
        """Generate stock transfer recommendations between warehouses."""
        self.logger.info("Generating transfer recommendations")
        
        inventory_data = get_inventory_data()
        recommendations = []
        
        # Group inventory by SKU
        sku_inventory: dict[str, list[dict]] = {}
        for inv in inventory_data:
            if inv["sku"] not in sku_inventory:
                sku_inventory[inv["sku"]] = []
            sku_inventory[inv["sku"]].append(inv)
        
        # Find imbalances
        for sku, inventories in sku_inventory.items():
            if len(inventories) < 2:
                continue
            
            # Find overstocked and understocked warehouses
            overstocked = []
            understocked = []
            
            for inv in inventories:
                available = inv["current_stock"] - inv.get("reserved_stock", 0)
                
                if available > inv["reorder_point"] * 2:
                    overstocked.append(inv)
                elif available < inv["safety_stock"]:
                    understocked.append(inv)
            
            # Generate transfer recommendations
            for under in understocked:
                for over in overstocked:
                    excess = over["current_stock"] - over["reorder_point"]
                    needed = under["reorder_point"] - under["current_stock"]
                    transfer_qty = min(excess, needed)
                    
                    if transfer_qty > 10:  # Minimum transfer quantity
                        recommendations.append(TransferRecommendation(
                            sku=sku,
                            from_warehouse=over["warehouse_id"],
                            to_warehouse=under["warehouse_id"],
                            quantity=int(transfer_qty),
                            reason=f"Balance stock: {over['warehouse_id']} overstocked, {under['warehouse_id']} understocked",
                            estimated_savings=round(transfer_qty * 0.5, 2),  # Simplified savings estimate
                        ))
        
        return recommendations

    async def adjust_inventory(
        self,
        sku: str,
        warehouse_id: str,
        adjustment: int,
        reason: str,
    ) -> dict:
        """Record an inventory adjustment."""
        self.logger.info(
            "Inventory adjustment",
            sku=sku,
            warehouse_id=warehouse_id,
            adjustment=adjustment,
            reason=reason,
        )
        
        # In production, would update database
        return {
            "status": "recorded",
            "sku": sku,
            "warehouse_id": warehouse_id,
            "adjustment": adjustment,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def identify_deadstock(self) -> list[dict]:
        """Identify slow-moving and dead stock items."""
        inventory_data = get_inventory_data()
        deadstock = []
        
        for inv in inventory_data:
            days_since_sale = inv.get("days_since_last_sale", 0)
            
            if days_since_sale > 60:
                deadstock.append({
                    "sku": inv["sku"],
                    "sku_name": self._get_sku_name(inv["sku"]),
                    "warehouse_id": inv["warehouse_id"],
                    "current_stock": inv["current_stock"],
                    "days_since_last_sale": days_since_sale,
                    "inventory_value": round(inv["current_stock"] * inv["unit_cost"], 2),
                    "recommendation": "liquidate" if days_since_sale > 120 else "discount",
                })
        
        return deadstock

    def _get_sku_name(self, sku: str) -> str:
        """Get human-readable SKU name."""
        for item in get_skus():
            if item["sku"] == sku:
                return item["name"]
        return sku

    def _get_reorder_reason(
        self,
        urgency: str,
        days_of_stock: float,
        lead_time: int,
    ) -> str:
        """Generate reorder reason text."""
        if urgency == "immediate":
            return f"Critical: Only {days_of_stock:.0f} days of stock, lead time is {lead_time} days"
        elif urgency == "soon":
            return f"Low stock: {days_of_stock:.0f} days remaining, approaching lead time buffer"
        else:
            return "Stock below reorder point, replenishment recommended"
