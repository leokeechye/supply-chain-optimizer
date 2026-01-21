"""Supply Chain Optimizer - Logistics & Route Optimization Agent."""

from datetime import datetime, date, timedelta
from typing import Any
import uuid

from langchain_core.prompts import ChatPromptTemplate

from src.agents.base import BaseAgent
from src.api.schemas import (
    RouteOptimizationRequest,
    RouteOptimizationResponse,
    RouteOption,
    ShipmentTracking,
    ShippingMode,
)
from src.data.sample_data import get_carrier_data, get_shipment_data


class LogisticsRouteAgent(BaseAgent):
    """
    Agent responsible for logistics and route optimization.
    
    Capabilities:
    - Multi-modal optimization (Air, Sea, Road, Rail)
    - Dynamic routing based on cost, speed, and reliability
    - Last-mile efficiency planning
    - Load consolidation for container utilization
    - Real-time shipment tracking
    """

    def __init__(self):
        super().__init__(
            name="Logistics & Route Agent",
            description=(
                "a logistics optimization specialist managing route planning, "
                "carrier selection, and shipment coordination"
            ),
        )
        
        self.route_analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a logistics and route optimization expert.
Analyze the shipping requirements and provide a recommendation.

Consider:
1. Cost vs speed trade-offs
2. Reliability of shipping modes
3. Environmental impact (CO2 emissions)
4. Risk factors (weather, congestion, geopolitical)
5. Cargo requirements (hazardous, temperature-controlled)

Be concise and provide clear reasoning.
"""),
            ("human", """Shipment Requirements:
- Origin: {origin}
- Destination: {destination}
- Cargo Weight: {weight} kg
- Required Delivery: {delivery_date}
- Priority: {priority}
- Hazardous: {hazardous}
- Temperature Controlled: {temp_controlled}

Available Options:
{options}

Which option do you recommend and why?"""),
        ])

    async def run(self, request: RouteOptimizationRequest) -> RouteOptimizationResponse:
        """Run route optimization."""
        return await self.optimize_route(request)

    async def optimize_route(
        self,
        request: RouteOptimizationRequest,
    ) -> RouteOptimizationResponse:
        """
        Optimize shipping route considering multiple factors.
        """
        self.logger.info(
            "Optimizing route",
            origin=request.origin,
            destination=request.destination,
            priority=request.priority,
        )
        
        # Get available carriers
        carriers = get_carrier_data()
        
        # Filter by allowed modes
        if request.allowed_modes:
            carriers = [
                c for c in carriers
                if c["mode"] in [m.value for m in request.allowed_modes]
            ]
        
        # Generate route options
        options = []
        
        for carrier in carriers:
            # Calculate estimated cost and transit time
            base_cost = carrier["base_rate_per_kg"] * request.cargo_weight_kg
            
            # Adjust for priority
            if request.priority == "urgent":
                if carrier["mode"] == "sea":
                    continue  # Sea not suitable for urgent
                base_cost *= 1.5
            elif request.priority == "economy":
                if carrier["mode"] == "air":
                    base_cost *= 0.8  # No expedited handling
            
            # Adjust for special requirements
            if request.hazardous:
                base_cost *= 1.3
                if not carrier.get("hazmat_certified", False):
                    continue
            
            if request.temperature_controlled:
                base_cost *= 1.2
                if not carrier.get("reefer_available", False):
                    continue
            
            transit_days = carrier["avg_transit_days"]
            if request.priority == "urgent":
                transit_days = max(1, transit_days - 2)
            
            arrival_date = date.today() + timedelta(days=transit_days)
            
            # Check if meets delivery requirement
            if request.required_delivery_date:
                if arrival_date > request.required_delivery_date:
                    if request.priority == "urgent":
                        continue  # Must meet date for urgent
            
            # Calculate CO2 emissions
            co2_emissions = self._calculate_emissions(
                mode=carrier["mode"],
                weight_kg=request.cargo_weight_kg,
                distance_km=carrier.get("typical_distance_km", 5000),
            )
            
            options.append(RouteOption(
                route_id=f"RT-{uuid.uuid4().hex[:8].upper()}",
                mode=ShippingMode(carrier["mode"]),
                carrier=carrier["name"],
                estimated_cost=round(base_cost, 2),
                estimated_transit_days=transit_days,
                estimated_arrival=arrival_date,
                co2_emissions_kg=co2_emissions,
                reliability_score=carrier["reliability_score"],
                waypoints=carrier.get("waypoints", []),
                notes=carrier.get("notes"),
            ))
        
        if not options:
            raise ValueError("No suitable shipping options found for requirements")
        
        # Score and rank options
        options = self._score_options(options, request)
        
        # Best option is first after scoring
        recommended = options[0]
        alternatives = options[1:5]  # Top 4 alternatives
        
        return RouteOptimizationResponse(
            request_id=f"REQ-{uuid.uuid4().hex[:8].upper()}",
            origin=request.origin,
            destination=request.destination,
            recommended_route=recommended,
            alternative_routes=alternatives,
            optimization_factors={
                "cost_weight": 0.35,
                "speed_weight": 0.30,
                "reliability_weight": 0.25,
                "sustainability_weight": 0.10,
            },
        )

    async def list_carriers(
        self,
        mode: ShippingMode | None = None,
        origin_country: str | None = None,
        destination_country: str | None = None,
    ) -> list[dict]:
        """List available carriers with performance metrics."""
        carriers = get_carrier_data()
        
        if mode:
            carriers = [c for c in carriers if c["mode"] == mode.value]
        
        return [
            {
                "carrier_id": c["id"],
                "name": c["name"],
                "mode": c["mode"],
                "reliability_score": c["reliability_score"],
                "avg_transit_days": c["avg_transit_days"],
                "cost_rating": c.get("cost_rating", "medium"),
                "capabilities": c.get("capabilities", []),
            }
            for c in carriers
        ]

    async def track_shipment(self, shipment_id: str) -> ShipmentTracking | None:
        """Get real-time tracking for a shipment."""
        shipments = get_shipment_data()
        
        for shipment in shipments:
            if shipment["id"] == shipment_id:
                return ShipmentTracking(
                    shipment_id=shipment["id"],
                    carrier=shipment["carrier"],
                    tracking_number=shipment["tracking_number"],
                    status=shipment["status"],
                    current_location=shipment.get("current_location"),
                    origin=shipment["origin"],
                    destination=shipment["destination"],
                    estimated_arrival=shipment.get("eta"),
                    events=shipment.get("events", []),
                )
        
        return None

    async def consolidate_shipments(self, shipment_ids: list[str]) -> dict:
        """Analyze shipment consolidation opportunities."""
        self.logger.info("Analyzing consolidation", shipment_count=len(shipment_ids))
        
        # Simplified consolidation analysis
        return {
            "consolidation_possible": True,
            "original_shipments": len(shipment_ids),
            "consolidated_containers": max(1, len(shipment_ids) // 3),
            "estimated_savings": round(len(shipment_ids) * 150, 2),
            "savings_percentage": 15,
            "recommendation": "Consolidate shipments to same destination region into shared containers",
        }

    async def get_warehouse_capacity(self) -> list[dict]:
        """Get warehouse capacity utilization."""
        from src.data.sample_data import get_warehouse_data
        
        warehouses = get_warehouse_data()
        
        return [
            {
                "warehouse_id": w["id"],
                "name": w["name"],
                "location": w["location"],
                "total_capacity_sqm": w["capacity_sqm"],
                "used_capacity_sqm": w["used_sqm"],
                "utilization_pct": round(w["used_sqm"] / w["capacity_sqm"] * 100, 1),
                "status": "high" if w["used_sqm"] / w["capacity_sqm"] > 0.9 else "normal",
            }
            for w in warehouses
        ]

    async def reroute_shipment(
        self,
        shipment_id: str,
        reason: str,
        new_destination: str | None = None,
    ) -> dict:
        """Request shipment rerouting."""
        self.logger.info("Rerouting shipment", shipment_id=shipment_id, reason=reason)
        
        return {
            "status": "reroute_requested",
            "shipment_id": shipment_id,
            "reason": reason,
            "new_destination": new_destination,
            "estimated_delay_days": 2,
            "additional_cost": 250.00,
            "approval_required": True,
        }

    def _score_options(
        self,
        options: list[RouteOption],
        request: RouteOptimizationRequest,
    ) -> list[RouteOption]:
        """Score and rank route options."""
        scored = []
        
        # Get ranges for normalization
        costs = [o.estimated_cost for o in options]
        min_cost, max_cost = min(costs), max(costs)
        
        for option in options:
            # Normalize cost (lower is better)
            if max_cost > min_cost:
                cost_score = 1 - (option.estimated_cost - min_cost) / (max_cost - min_cost)
            else:
                cost_score = 1
            
            # Speed score (fewer days is better)
            speed_score = 1 / (option.estimated_transit_days + 1)
            
            # Reliability from carrier data
            reliability_score = option.reliability_score
            
            # Sustainability (lower emissions is better)
            if option.co2_emissions_kg:
                max_emissions = max(o.co2_emissions_kg or 0 for o in options)
                sustainability_score = 1 - (option.co2_emissions_kg / max_emissions) if max_emissions > 0 else 1
            else:
                sustainability_score = 0.5
            
            # Weighted total
            weights = {
                "cost": 0.35 if request.priority == "economy" else 0.25,
                "speed": 0.40 if request.priority == "urgent" else 0.25,
                "reliability": 0.25,
                "sustainability": 0.10,
            }
            
            total_score = (
                weights["cost"] * cost_score +
                weights["speed"] * speed_score +
                weights["reliability"] * reliability_score +
                weights["sustainability"] * sustainability_score
            )
            
            scored.append((total_score, option))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return [option for _, option in scored]

    def _calculate_emissions(
        self,
        mode: str,
        weight_kg: float,
        distance_km: float,
    ) -> float:
        """Calculate CO2 emissions for shipment."""
        # Emission factors (kg CO2 per ton-km)
        emission_factors = {
            "air": 0.602,
            "sea": 0.016,
            "road": 0.096,
            "rail": 0.028,
        }
        
        factor = emission_factors.get(mode, 0.1)
        weight_tons = weight_kg / 1000
        
        emissions = weight_tons * distance_km * factor
        return round(emissions, 2)
