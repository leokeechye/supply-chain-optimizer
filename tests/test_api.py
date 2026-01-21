"""Supply Chain Optimizer - API Integration Tests."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import date, timedelta


@pytest.fixture
def mock_settings():
    """Mock settings for all tests."""
    with patch("src.config.get_settings") as mock:
        settings = MagicMock()
        settings.app_name = "supply-chain-optimizer"
        settings.app_env = "development"
        settings.debug = True
        settings.host = "0.0.0.0"
        settings.port = 8000
        settings.llm_provider = "ollama"
        settings.ollama_base_url = "http://localhost:11434"
        settings.ollama_model = "llama4"
        settings.chroma_persist_directory = "./test_data/chroma"
        mock.return_value = settings
        yield settings


@pytest.fixture
def client(mock_settings):
    """Create test client with mocked dependencies."""
    with patch("src.agents.base.ChatOllama") as mock_llm:
        mock_instance = MagicMock()
        mock_instance.ainvoke = AsyncMock(
            return_value=MagicMock(content="Test response")
        )
        mock_llm.return_value = mock_instance
        
        from src.main import app
        with TestClient(app) as test_client:
            yield test_client


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health endpoint returns healthy status."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "app" in data


class TestForecastEndpoints:
    """Tests for demand forecasting endpoints."""

    def test_get_forecast(self, client):
        """Test getting forecast for a SKU."""
        response = client.get("/api/v1/forecast/SKU-001")
        
        assert response.status_code == 200
        data = response.json()
        assert data["sku"] == "SKU-001"
        assert "daily_forecast" in data
        assert "total_predicted_demand" in data

    def test_get_forecast_with_horizon(self, client):
        """Test forecast with custom horizon."""
        response = client.get("/api/v1/forecast/SKU-001?horizon_days=7")
        
        assert response.status_code == 200
        data = response.json()
        assert data["horizon_days"] == 7
        assert len(data["daily_forecast"]) == 7

    def test_batch_forecast(self, client):
        """Test batch forecasting."""
        response = client.post(
            "/api/v1/forecast/batch",
            params={"skus": ["SKU-001", "SKU-002"], "horizon_days": 14}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "forecasts" in data


class TestInventoryEndpoints:
    """Tests for inventory management endpoints."""

    def test_get_inventory_status(self, client):
        """Test getting global inventory status."""
        response = client.get("/api/v1/inventory/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_skus" in data
        assert "total_warehouses" in data
        assert "items" in data

    def test_get_inventory_by_warehouse(self, client):
        """Test filtering inventory by warehouse."""
        response = client.get(
            "/api/v1/inventory/status",
            params={"warehouse_id": "WH-US-EAST"}
        )
        
        assert response.status_code == 200

    def test_get_reorder_recommendations(self, client):
        """Test reorder recommendations."""
        response = client.get("/api/v1/inventory/reorder-recommendations")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_transfer_recommendations(self, client):
        """Test transfer recommendations."""
        response = client.get("/api/v1/inventory/transfer-recommendations")
        
        assert response.status_code == 200


class TestLogisticsEndpoints:
    """Tests for logistics and routing endpoints."""

    def test_optimize_route(self, client):
        """Test route optimization."""
        response = client.post(
            "/api/v1/logistics/optimize",
            json={
                "origin": "WH-US-EAST",
                "destination": "Chicago, IL",
                "cargo_weight_kg": 500,
                "priority": "normal",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "recommended_route" in data
        assert "alternative_routes" in data

    def test_optimize_urgent_route(self, client):
        """Test urgent route optimization."""
        response = client.post(
            "/api/v1/logistics/optimize",
            json={
                "origin": "WH-EU-CENTRAL",
                "destination": "New York, NY",
                "cargo_weight_kg": 100,
                "priority": "urgent",
            }
        )
        
        assert response.status_code == 200

    def test_list_carriers(self, client):
        """Test listing carriers."""
        response = client.get("/api/v1/logistics/carriers")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:
            assert "name" in data[0]
            assert "mode" in data[0]

    def test_track_shipment(self, client):
        """Test shipment tracking."""
        response = client.get("/api/v1/logistics/track/SHIP-001")
        
        assert response.status_code == 200
        data = response.json()
        assert data["shipment_id"] == "SHIP-001"

    def test_track_nonexistent_shipment(self, client):
        """Test tracking non-existent shipment."""
        response = client.get("/api/v1/logistics/track/NONEXISTENT")
        
        assert response.status_code == 404


class TestRiskEndpoints:
    """Tests for risk analysis endpoints."""

    def test_analyze_risks(self, client):
        """Test risk analysis."""
        response = client.post(
            "/api/v1/risk/analyze",
            json={"scope": "global"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "risk_score" in data
        assert "risk_level" in data
        assert "active_risks" in data

    def test_get_alerts(self, client):
        """Test getting active alerts."""
        response = client.get("/api/v1/risk/alerts")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_weather_risks(self, client):
        """Test weather risk analysis."""
        response = client.get("/api/v1/risk/weather/US-Gulf")
        
        assert response.status_code == 200
        data = response.json()
        assert "region" in data


class TestVendorEndpoints:
    """Tests for vendor management endpoints."""

    def test_list_vendors(self, client):
        """Test listing vendors."""
        response = client.get("/api/v1/vendors/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:
            assert "vendor_id" in data[0]
            assert "name" in data[0]

    def test_get_vendor(self, client):
        """Test getting vendor by ID."""
        response = client.get("/api/v1/vendors/VENDOR-001")
        
        assert response.status_code == 200
        data = response.json()
        assert data["vendor_id"] == "VENDOR-001"

    def test_get_nonexistent_vendor(self, client):
        """Test getting non-existent vendor."""
        response = client.get("/api/v1/vendors/NONEXISTENT")
        
        assert response.status_code == 404

    def test_list_orders(self, client):
        """Test listing purchase orders."""
        response = client.get("/api/v1/vendors/orders")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_create_order(self, client):
        """Test creating a purchase order."""
        response = client.post(
            "/api/v1/vendors/orders",
            json={
                "vendor_id": "VENDOR-001",
                "items": [
                    {"sku": "SKU-001", "quantity": 100, "unit_price": 45.00}
                ],
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "po_number" in data
        assert data["vendor_id"] == "VENDOR-001"

    def test_get_vendor_performance(self, client):
        """Test getting vendor performance metrics."""
        response = client.get("/api/v1/vendors/VENDOR-001/performance")
        
        assert response.status_code == 200
        data = response.json()
        assert "on_time_delivery_rate" in data
        assert "overall_score" in data
