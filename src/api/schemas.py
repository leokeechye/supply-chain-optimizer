"""Supply Chain Optimizer - Pydantic Schemas for API."""

from datetime import datetime, date
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================


class ForecastConfidenceLevel(str, Enum):
    """Forecast confidence levels."""
    P10 = "p10"  # 10th percentile (optimistic)
    P50 = "p50"  # 50th percentile (median)
    P90 = "p90"  # 90th percentile (conservative)


class ShippingMode(str, Enum):
    """Shipping modes."""
    AIR = "air"
    SEA = "sea"
    ROAD = "road"
    RAIL = "rail"
    MULTIMODAL = "multimodal"


class RiskSeverity(str, Enum):
    """Risk severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OrderStatus(str, Enum):
    """Purchase order status."""
    DRAFT = "draft"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class InventoryAction(str, Enum):
    """Inventory recommended actions."""
    REORDER = "reorder"
    TRANSFER = "transfer"
    HOLD = "hold"
    LIQUIDATE = "liquidate"
    EXPEDITE = "expedite"


# ============================================================================
# Forecast Schemas
# ============================================================================


class ForecastRequest(BaseModel):
    """Request for demand forecast."""
    sku: str = Field(..., description="Stock Keeping Unit identifier")
    horizon_days: int = Field(default=30, ge=1, le=365, description="Forecast horizon in days")
    include_confidence: bool = Field(default=True, description="Include confidence intervals")
    include_components: bool = Field(default=False, description="Include trend/seasonal components")


class ForecastPoint(BaseModel):
    """Single forecast data point."""
    date: date
    predicted_demand: float
    p10: float | None = None  # 10th percentile
    p50: float | None = None  # Median
    p90: float | None = None  # 90th percentile


class ForecastResponse(BaseModel):
    """Response for demand forecast."""
    sku: str
    sku_name: str | None = None
    forecast_generated_at: datetime = Field(default_factory=datetime.utcnow)
    horizon_days: int
    total_predicted_demand: float
    daily_forecast: list[ForecastPoint]
    trend: str | None = Field(default=None, description="'increasing', 'decreasing', or 'stable'")
    seasonality_detected: bool = False
    confidence_score: float = Field(default=0.0, ge=0, le=1)
    recommendations: list[str] = Field(default_factory=list)


# ============================================================================
# Inventory Schemas
# ============================================================================


class InventoryItem(BaseModel):
    """Single inventory item."""
    sku: str
    sku_name: str
    warehouse_id: str
    current_stock: int
    reserved_stock: int = 0
    available_stock: int
    reorder_point: int
    safety_stock: int
    lead_time_days: int
    unit_cost: float
    last_updated: datetime


class InventoryStatus(BaseModel):
    """Global inventory status response."""
    total_skus: int
    total_warehouses: int
    items: list[InventoryItem]
    low_stock_alerts: list[dict] = Field(default_factory=list)
    overstock_alerts: list[dict] = Field(default_factory=list)
    deadstock_items: list[str] = Field(default_factory=list)
    total_inventory_value: float
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ReorderRecommendation(BaseModel):
    """Reorder recommendation for an SKU."""
    sku: str
    sku_name: str
    warehouse_id: str
    current_stock: int
    recommended_order_quantity: int
    urgency: str  # immediate, soon, planned
    reason: str
    estimated_stockout_date: date | None = None
    suggested_vendor: str | None = None
    estimated_cost: float | None = None


class TransferRecommendation(BaseModel):
    """Stock transfer recommendation."""
    sku: str
    from_warehouse: str
    to_warehouse: str
    quantity: int
    reason: str
    estimated_savings: float | None = None


# ============================================================================
# Logistics Schemas
# ============================================================================


class RouteOptimizationRequest(BaseModel):
    """Request for route optimization."""
    origin: str = Field(..., description="Origin location (warehouse ID or address)")
    destination: str = Field(..., description="Destination address or location")
    cargo_weight_kg: float = Field(..., ge=0)
    cargo_volume_cbm: float | None = Field(default=None, description="Volume in cubic meters")
    required_delivery_date: date | None = None
    priority: str = Field(default="normal", description="'urgent', 'normal', or 'economy'")
    allowed_modes: list[ShippingMode] | None = None
    hazardous: bool = False
    temperature_controlled: bool = False


class RouteOption(BaseModel):
    """Single route option."""
    route_id: str
    mode: ShippingMode
    carrier: str
    estimated_cost: float
    estimated_transit_days: int
    estimated_arrival: date
    co2_emissions_kg: float | None = None
    reliability_score: float = Field(default=0.0, ge=0, le=1)
    waypoints: list[str] = Field(default_factory=list)
    notes: str | None = None


class RouteOptimizationResponse(BaseModel):
    """Response for route optimization."""
    request_id: str
    origin: str
    destination: str
    recommended_route: RouteOption
    alternative_routes: list[RouteOption]
    optimization_factors: dict[str, float] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ShipmentTracking(BaseModel):
    """Shipment tracking information."""
    shipment_id: str
    carrier: str
    tracking_number: str
    status: str
    current_location: str | None = None
    origin: str
    destination: str
    estimated_arrival: date | None = None
    events: list[dict] = Field(default_factory=list)


# ============================================================================
# Risk Schemas
# ============================================================================


class RiskAnalysisRequest(BaseModel):
    """Request for risk analysis."""
    scope: str = Field(default="global", description="'global', 'region', or specific route")
    categories: list[str] | None = Field(
        default=None,
        description="Risk categories: 'weather', 'geopolitical', 'supplier', 'transport'"
    )
    time_horizon_days: int = Field(default=30, ge=1, le=90)


class RiskFactor(BaseModel):
    """Single risk factor."""
    risk_id: str
    category: str
    title: str
    description: str
    severity: RiskSeverity
    probability: float = Field(ge=0, le=1)
    affected_regions: list[str] = Field(default_factory=list)
    affected_skus: list[str] = Field(default_factory=list)
    potential_impact: str
    mitigation_actions: list[str] = Field(default_factory=list)
    source: str | None = None
    detected_at: datetime = Field(default_factory=datetime.utcnow)


class RiskAnalysisResponse(BaseModel):
    """Response for risk analysis."""
    analysis_id: str
    scope: str
    risk_score: float = Field(ge=0, le=100, description="Overall risk score")
    risk_level: RiskSeverity
    active_risks: list[RiskFactor]
    recommendations: list[str]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class DisruptionAlert(BaseModel):
    """Supply chain disruption alert."""
    alert_id: str
    type: str  # port_congestion, weather, strike, supplier_issue
    severity: RiskSeverity
    title: str
    description: str
    affected_routes: list[str]
    affected_orders: list[str]
    recommended_actions: list[str]
    auto_mitigation_available: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Vendor Schemas
# ============================================================================


class Vendor(BaseModel):
    """Vendor information."""
    vendor_id: str
    name: str
    country: str
    lead_time_days: int
    reliability_score: float = Field(ge=0, le=1)
    price_competitiveness: float = Field(ge=0, le=1)
    products: list[str] = Field(default_factory=list)
    payment_terms: str | None = None
    contact_email: str | None = None


class PurchaseOrder(BaseModel):
    """Purchase order."""
    po_number: str
    vendor_id: str
    vendor_name: str
    status: OrderStatus
    items: list[dict]
    total_amount: float
    currency: str = "USD"
    created_at: datetime
    expected_delivery: date | None = None
    actual_delivery: date | None = None
    notes: str | None = None


class PurchaseOrderRequest(BaseModel):
    """Request to create a purchase order."""
    vendor_id: str
    items: list[dict]  # [{"sku": "SKU001", "quantity": 100, "unit_price": 10.50}]
    requested_delivery_date: date | None = None
    notes: str | None = None


class VendorPerformance(BaseModel):
    """Vendor performance metrics."""
    vendor_id: str
    vendor_name: str
    period_start: date
    period_end: date
    total_orders: int
    on_time_delivery_rate: float
    quality_rate: float
    average_lead_time_days: float
    total_spend: float
    issues_count: int
    overall_score: float = Field(ge=0, le=100)


# ============================================================================
# Orchestrator / Workflow Schemas
# ============================================================================


class OptimizationTask(BaseModel):
    """Task for the orchestrator."""
    task_id: str
    task_type: str  # forecast, reorder, route, risk_mitigation
    priority: int = Field(default=5, ge=1, le=10)
    payload: dict
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    result: dict | None = None


class WorkflowStatus(BaseModel):
    """Status of the optimization workflow."""
    workflow_id: str
    status: str  # running, completed, failed
    current_step: str | None = None
    steps_completed: list[str] = Field(default_factory=list)
    agents_involved: list[str] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime | None = None
    final_decision: str | None = None
