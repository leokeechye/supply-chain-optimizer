"""Supply Chain Optimizer - Data accessors.

For the five entities backed by SQLite (skus, warehouses, inventory,
sales_history, vendors), the accessors here delegate to src/data/db.py.
Uploading a CSV via POST /api/v1/data/upload/{entity} writes through to
the database, so changes survive restarts (with a mounted volume on Railway).

For the remaining entities that aren't user-supplied (carriers, shipments,
orders, risks) the hardcoded sample data below is returned as-is.

The `SAMPLE_SKUS` constant is preserved as a static snapshot for any code
that imported it directly; prefer `get_skus()` to see the live DB state.
"""

from datetime import date, datetime, timedelta
import random

from src.data import db

# ============================================================================
# SKU Data
# ============================================================================

SAMPLE_SKUS = [
    {"sku": "SKU-001", "name": "Industrial Pump Motor", "category": "motors"},
    {"sku": "SKU-002", "name": "Hydraulic Valve Assembly", "category": "valves"},
    {"sku": "SKU-003", "name": "Control Panel Unit", "category": "electronics"},
    {"sku": "SKU-004", "name": "Pressure Sensor Module", "category": "sensors"},
    {"sku": "SKU-005", "name": "Steel Bearing Set", "category": "bearings"},
    {"sku": "SKU-006", "name": "Conveyor Belt Section", "category": "conveyors"},
    {"sku": "SKU-007", "name": "Power Supply Unit", "category": "electronics"},
    {"sku": "SKU-008", "name": "Pneumatic Cylinder", "category": "pneumatics"},
    {"sku": "SKU-009", "name": "Industrial Cable 100m", "category": "cables"},
    {"sku": "SKU-010", "name": "Gearbox Assembly", "category": "motors"},
]


def get_skus() -> list[dict]:
    """SKU catalog from SQLite (seeded from src/data/csv/skus.csv on first boot)."""
    return db.list_skus()


# ============================================================================
# Warehouse Data
# ============================================================================

def get_warehouse_data() -> list[dict]:
    """Warehouses from SQLite."""
    return db.list_warehouses()


# ============================================================================
# Inventory Data
# ============================================================================

def get_inventory_data() -> list[dict]:
    """Current inventory from SQLite. Stable across calls (unlike the old random version)."""
    return db.list_inventory()


# ============================================================================
# Historical Sales Data
# ============================================================================

def get_historical_sales(sku: str, days: int = 365) -> list[dict]:
    """Historical sales for an SKU from SQLite (deterministic seed at first boot)."""
    return db.list_sales_for_sku(sku)


# ============================================================================
# Carrier Data
# ============================================================================

def get_carrier_data() -> list[dict]:
    """Get carrier information for logistics."""
    return [
        {
            "id": "CARRIER-001",
            "name": "GlobalFreight Air",
            "mode": "air",
            "base_rate_per_kg": 8.50,
            "avg_transit_days": 3,
            "reliability_score": 0.92,
            "hazmat_certified": True,
            "reefer_available": True,
            "typical_distance_km": 8000,
            "cost_rating": "premium",
            "capabilities": ["express", "hazmat", "temperature_controlled"],
        },
        {
            "id": "CARRIER-002",
            "name": "Pacific Shipping Lines",
            "mode": "sea",
            "base_rate_per_kg": 0.85,
            "avg_transit_days": 21,
            "reliability_score": 0.88,
            "hazmat_certified": True,
            "reefer_available": True,
            "typical_distance_km": 15000,
            "cost_rating": "economy",
            "capabilities": ["bulk", "containers", "hazmat"],
            "waypoints": ["Shanghai", "Singapore", "Los Angeles"],
        },
        {
            "id": "CARRIER-003",
            "name": "Continental Trucking",
            "mode": "road",
            "base_rate_per_kg": 1.20,
            "avg_transit_days": 5,
            "reliability_score": 0.95,
            "hazmat_certified": True,
            "reefer_available": True,
            "typical_distance_km": 2500,
            "cost_rating": "standard",
            "capabilities": ["ltl", "ftl", "last_mile"],
        },
        {
            "id": "CARRIER-004",
            "name": "EuroRail Freight",
            "mode": "rail",
            "base_rate_per_kg": 0.60,
            "avg_transit_days": 8,
            "reliability_score": 0.90,
            "hazmat_certified": False,
            "reefer_available": False,
            "typical_distance_km": 3000,
            "cost_rating": "economy",
            "capabilities": ["bulk", "intermodal"],
        },
        {
            "id": "CARRIER-005",
            "name": "Express Air Cargo",
            "mode": "air",
            "base_rate_per_kg": 12.00,
            "avg_transit_days": 2,
            "reliability_score": 0.96,
            "hazmat_certified": False,
            "reefer_available": True,
            "typical_distance_km": 10000,
            "cost_rating": "premium",
            "capabilities": ["express", "next_day", "temperature_controlled"],
        },
    ]


# ============================================================================
# Shipment Data
# ============================================================================

def get_shipment_data() -> list[dict]:
    """Get current shipment tracking data."""
    return [
        {
            "id": "SHIP-001",
            "carrier": "Pacific Shipping Lines",
            "tracking_number": "PSL-2024-78542",
            "status": "in_transit",
            "origin": "Shanghai, China",
            "destination": "Los Angeles, CA, USA",
            "current_location": "Pacific Ocean, 2500km from destination",
            "eta": (date.today() + timedelta(days=5)).isoformat(),
            "events": [
                {"date": (date.today() - timedelta(days=10)).isoformat(), "event": "Departed Shanghai"},
                {"date": (date.today() - timedelta(days=5)).isoformat(), "event": "Passed Singapore"},
                {"date": (date.today() - timedelta(days=1)).isoformat(), "event": "Mid-Pacific checkpoint"},
            ],
        },
        {
            "id": "SHIP-002",
            "carrier": "Continental Trucking",
            "tracking_number": "CT-2024-45821",
            "status": "in_transit",
            "origin": "Newark, NJ, USA",
            "destination": "Chicago, IL, USA",
            "current_location": "Cleveland, OH",
            "eta": (date.today() + timedelta(days=1)).isoformat(),
            "events": [
                {"date": date.today().isoformat(), "event": "Departed Newark"},
                {"date": date.today().isoformat(), "event": "Arrived Cleveland checkpoint"},
            ],
        },
        {
            "id": "SHIP-003",
            "carrier": "GlobalFreight Air",
            "tracking_number": "GFA-2024-98754",
            "status": "delivered",
            "origin": "Frankfurt, Germany",
            "destination": "Singapore",
            "current_location": "Singapore",
            "eta": (date.today() - timedelta(days=1)).isoformat(),
            "events": [
                {"date": (date.today() - timedelta(days=2)).isoformat(), "event": "Departed Frankfurt"},
                {"date": (date.today() - timedelta(days=1)).isoformat(), "event": "Arrived Singapore"},
                {"date": (date.today() - timedelta(days=1)).isoformat(), "event": "Delivered to recipient"},
            ],
        },
    ]


# ============================================================================
# Vendor Data
# ============================================================================

def get_vendor_data() -> list[dict]:
    """Vendors from SQLite."""
    return db.list_vendors()


def _legacy_vendor_data() -> list[dict]:
    """Hardcoded vendor list kept only for reference / fallback diagnostics."""
    return [
        {
            "id": "VENDOR-001",
            "name": "TechParts Manufacturing",
            "country": "China",
            "lead_time_days": 14,
            "reliability_score": 0.88,
            "price_competitiveness": 0.85,
            "products": ["SKU-001", "SKU-003", "SKU-007"],
            "payment_terms": "Net 30",
            "contact_email": "sales@techparts.example.com",
        },
        {
            "id": "VENDOR-002",
            "name": "Euro Industrial Supplies",
            "country": "Germany",
            "lead_time_days": 10,
            "reliability_score": 0.95,
            "price_competitiveness": 0.70,
            "products": ["SKU-002", "SKU-005", "SKU-010"],
            "payment_terms": "Net 45",
            "contact_email": "orders@euroindustrial.example.com",
        },
        {
            "id": "VENDOR-003",
            "name": "American Components Inc",
            "country": "USA",
            "lead_time_days": 7,
            "reliability_score": 0.92,
            "price_competitiveness": 0.65,
            "products": ["SKU-004", "SKU-008", "SKU-009"],
            "payment_terms": "Net 30",
            "contact_email": "supply@amcomp.example.com",
        },
        {
            "id": "VENDOR-004",
            "name": "Asia Pacific Trading",
            "country": "Singapore",
            "lead_time_days": 12,
            "reliability_score": 0.85,
            "price_competitiveness": 0.90,
            "products": ["SKU-001", "SKU-006", "SKU-007"],
            "payment_terms": "Net 60",
            "contact_email": "orders@aptrade.example.com",
        },
        {
            "id": "VENDOR-005",
            "name": "Precision Parts Ltd",
            "country": "Japan",
            "lead_time_days": 15,
            "reliability_score": 0.97,
            "price_competitiveness": 0.60,
            "products": ["SKU-002", "SKU-004", "SKU-005"],
            "payment_terms": "Net 30",
            "contact_email": "sales@precisionparts.example.com",
        },
    ]


# ============================================================================
# Purchase Order Data
# ============================================================================

def get_order_data() -> list[dict]:
    """Get purchase order data."""
    return [
        {
            "po_number": "PO-2024-001",
            "vendor_id": "VENDOR-001",
            "vendor_name": "TechParts Manufacturing",
            "status": "in_transit",
            "items": [
                {"sku": "SKU-001", "quantity": 100, "unit_price": 45.00},
                {"sku": "SKU-003", "quantity": 50, "unit_price": 120.00},
            ],
            "total_amount": 10500.00,
            "currency": "USD",
            "created_at": (datetime.utcnow() - timedelta(days=10)).isoformat(),
            "expected_delivery": (date.today() + timedelta(days=4)).isoformat(),
        },
        {
            "po_number": "PO-2024-002",
            "vendor_id": "VENDOR-002",
            "vendor_name": "Euro Industrial Supplies",
            "status": "confirmed",
            "items": [
                {"sku": "SKU-002", "quantity": 200, "unit_price": 35.00},
            ],
            "total_amount": 7000.00,
            "currency": "USD",
            "created_at": (datetime.utcnow() - timedelta(days=3)).isoformat(),
            "expected_delivery": (date.today() + timedelta(days=7)).isoformat(),
        },
        {
            "po_number": "PO-2024-003",
            "vendor_id": "VENDOR-003",
            "vendor_name": "American Components Inc",
            "status": "delivered",
            "items": [
                {"sku": "SKU-004", "quantity": 150, "unit_price": 22.00},
                {"sku": "SKU-009", "quantity": 80, "unit_price": 18.00},
            ],
            "total_amount": 4740.00,
            "currency": "USD",
            "created_at": (datetime.utcnow() - timedelta(days=14)).isoformat(),
            "expected_delivery": (date.today() - timedelta(days=7)).isoformat(),
            "actual_delivery": (date.today() - timedelta(days=6)).isoformat(),
        },
    ]


# ============================================================================
# Risk Data
# ============================================================================

def get_risk_data() -> list[dict]:
    """Get current risk factors."""
    return [
        {
            "id": "RISK-001",
            "category": "geopolitical",
            "title": "Red Sea Shipping Disruption",
            "description": "Increased transit times and costs due to Red Sea route diversions",
            "severity": "high",
            "probability": 0.85,
            "affected_regions": ["Europe", "Asia"],
            "affected_routes": ["Asia-Europe", "Middle East-Europe"],
            "potential_impact": "14-21 day delays, 15-20% cost increase",
            "mitigation_actions": [
                "Use Cape of Good Hope route",
                "Consider air freight for urgent shipments",
                "Increase safety stock for affected SKUs",
            ],
            "auto_mitigate": False,
            "source": "Logistics Intelligence Feed",
        },
        {
            "id": "RISK-002",
            "category": "weather",
            "title": "Hurricane Season - Gulf Coast",
            "description": "Potential tropical storm activity affecting Gulf ports",
            "severity": "medium",
            "probability": 0.45,
            "affected_regions": ["US-Gulf", "US-Southeast"],
            "potential_impact": "3-7 day port closures possible",
            "mitigation_actions": [
                "Pre-position inventory at inland warehouses",
                "Identify backup ports",
            ],
            "source": "NOAA Weather Service",
        },
        {
            "id": "RISK-003",
            "category": "supplier",
            "title": "Key Supplier Capacity Constraint",
            "description": "VENDOR-001 operating at 95% capacity, lead times increasing",
            "severity": "medium",
            "probability": 0.70,
            "affected_skus": ["SKU-001", "SKU-003", "SKU-007"],
            "potential_impact": "5-7 day additional lead time",
            "mitigation_actions": [
                "Qualify alternative supplier",
                "Increase order quantities to build buffer",
            ],
            "source": "Supplier Portal",
        },
        {
            "id": "RISK-004",
            "category": "transport",
            "title": "Driver Shortage - US Trucking",
            "description": "Industry-wide driver shortage affecting domestic trucking",
            "severity": "low",
            "probability": 0.60,
            "affected_regions": ["US-Midwest", "US-West"],
            "potential_impact": "1-2 day delays on ground shipments",
            "mitigation_actions": [
                "Book capacity early",
                "Use rail for non-urgent shipments",
            ],
            "source": "Industry Report",
        },
    ]
