"""Supply Chain Optimizer - Unit Tests for Agents."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, timedelta

from src.api.schemas import ForecastRequest, RouteOptimizationRequest, ShippingMode


class TestDemandForecastingAgent:
    """Tests for the Demand Forecasting Agent."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        with patch("src.agents.base.get_settings") as mock:
            settings = MagicMock()
            settings.llm_provider = "ollama"
            settings.ollama_base_url = "http://localhost:11434"
            settings.ollama_model = "llama4"
            mock.return_value = settings
            yield settings

    @pytest.fixture
    def forecast_agent(self, mock_settings):
        """Create a forecast agent with mocked LLM."""
        with patch("src.agents.base.ChatOllama") as mock_llm:
            mock_instance = MagicMock()
            mock_instance.ainvoke = AsyncMock(
                return_value=MagicMock(content="Demand is stable with seasonal patterns.")
            )
            mock_llm.return_value = mock_instance
            
            from src.agents.forecast_agent import DemandForecastingAgent
            return DemandForecastingAgent()

    @pytest.mark.asyncio
    async def test_generate_forecast(self, forecast_agent):
        """Test forecast generation."""
        request = ForecastRequest(
            sku="SKU-001",
            horizon_days=30,
            include_confidence=True,
        )
        
        forecast = await forecast_agent.generate_forecast(request)
        
        assert forecast.sku == "SKU-001"
        assert forecast.horizon_days == 30
        assert len(forecast.daily_forecast) == 30
        assert forecast.total_predicted_demand > 0
        assert forecast.trend in ["increasing", "decreasing", "stable"]

    @pytest.mark.asyncio
    async def test_forecast_confidence_score(self, forecast_agent):
        """Test that confidence score is calculated."""
        request = ForecastRequest(sku="SKU-001", horizon_days=7)
        
        forecast = await forecast_agent.generate_forecast(request)
        
        assert 0 <= forecast.confidence_score <= 1

    def test_calculate_confidence(self, forecast_agent):
        """Test confidence calculation logic."""
        # Low variability, lots of data = high confidence
        confidence = forecast_agent._calculate_confidence(
            std_sales=10,
            avg_sales=100,
            data_points=365,
        )
        assert confidence > 0.7

        # High variability = lower confidence
        confidence_low = forecast_agent._calculate_confidence(
            std_sales=80,
            avg_sales=100,
            data_points=365,
        )
        assert confidence_low < confidence


class TestInventoryManagementAgent:
    """Tests for the Inventory Management Agent."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        with patch("src.agents.base.get_settings") as mock:
            settings = MagicMock()
            settings.llm_provider = "ollama"
            settings.ollama_base_url = "http://localhost:11434"
            settings.ollama_model = "llama4"
            mock.return_value = settings
            yield settings

    @pytest.fixture
    def inventory_agent(self, mock_settings):
        """Create an inventory agent with mocked LLM."""
        with patch("src.agents.base.ChatOllama") as mock_llm:
            mock_instance = MagicMock()
            mock_llm.return_value = mock_instance
            
            from src.agents.inventory_agent import InventoryManagementAgent
            return InventoryManagementAgent()

    @pytest.mark.asyncio
    async def test_get_inventory_status(self, inventory_agent):
        """Test getting inventory status."""
        status = await inventory_agent.get_inventory_status()
        
        assert status.total_skus > 0
        assert status.total_warehouses > 0
        assert status.total_inventory_value > 0
        assert isinstance(status.items, list)

    @pytest.mark.asyncio
    async def test_get_reorder_recommendations(self, inventory_agent):
        """Test reorder recommendations."""
        recommendations = await inventory_agent.get_reorder_recommendations()
        
        assert isinstance(recommendations, list)
        # Check structure if there are recommendations
        if recommendations:
            rec = recommendations[0]
            assert hasattr(rec, "sku")
            assert hasattr(rec, "urgency")
            assert rec.urgency in ["immediate", "soon", "planned"]

    @pytest.mark.asyncio
    async def test_inventory_adjustment(self, inventory_agent):
        """Test inventory adjustment recording."""
        result = await inventory_agent.adjust_inventory(
            sku="SKU-001",
            warehouse_id="WH-US-EAST",
            adjustment=-10,
            reason="Damage write-off",
        )
        
        assert result["status"] == "recorded"
        assert result["adjustment"] == -10


class TestLogisticsRouteAgent:
    """Tests for the Logistics & Route Agent."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        with patch("src.agents.base.get_settings") as mock:
            settings = MagicMock()
            settings.llm_provider = "ollama"
            settings.ollama_base_url = "http://localhost:11434"
            settings.ollama_model = "llama4"
            mock.return_value = settings
            yield settings

    @pytest.fixture
    def logistics_agent(self, mock_settings):
        """Create a logistics agent with mocked LLM."""
        with patch("src.agents.base.ChatOllama") as mock_llm:
            mock_instance = MagicMock()
            mock_llm.return_value = mock_instance
            
            from src.agents.logistics_agent import LogisticsRouteAgent
            return LogisticsRouteAgent()

    @pytest.mark.asyncio
    async def test_optimize_route(self, logistics_agent):
        """Test route optimization."""
        request = RouteOptimizationRequest(
            origin="WH-US-EAST",
            destination="Chicago, IL",
            cargo_weight_kg=500,
            priority="normal",
        )
        
        result = await logistics_agent.optimize_route(request)
        
        assert result.recommended_route is not None
        assert result.recommended_route.estimated_cost > 0
        assert result.recommended_route.estimated_transit_days > 0

    @pytest.mark.asyncio
    async def test_optimize_route_urgent(self, logistics_agent):
        """Test urgent route optimization prefers faster options."""
        request = RouteOptimizationRequest(
            origin="WH-US-EAST",
            destination="Los Angeles, CA",
            cargo_weight_kg=100,
            priority="urgent",
        )
        
        result = await logistics_agent.optimize_route(request)
        
        # Urgent shipments should not use sea freight
        assert result.recommended_route.mode != ShippingMode.SEA

    @pytest.mark.asyncio
    async def test_track_shipment(self, logistics_agent):
        """Test shipment tracking."""
        # Existing shipment
        tracking = await logistics_agent.track_shipment("SHIP-001")
        
        assert tracking is not None
        assert tracking.shipment_id == "SHIP-001"
        assert tracking.status is not None

        # Non-existent shipment
        tracking_none = await logistics_agent.track_shipment("NONEXISTENT")
        assert tracking_none is None

    def test_calculate_emissions(self, logistics_agent):
        """Test CO2 emissions calculation."""
        # Air has highest emissions
        air_emissions = logistics_agent._calculate_emissions("air", 1000, 5000)
        sea_emissions = logistics_agent._calculate_emissions("sea", 1000, 5000)
        
        assert air_emissions > sea_emissions


class TestRiskAnalystAgent:
    """Tests for the Risk Analyst Agent."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        with patch("src.agents.base.get_settings") as mock:
            settings = MagicMock()
            settings.llm_provider = "ollama"
            settings.ollama_base_url = "http://localhost:11434"
            settings.ollama_model = "llama4"
            mock.return_value = settings
            yield settings

    @pytest.fixture
    def risk_agent(self, mock_settings):
        """Create a risk agent with mocked LLM."""
        with patch("src.agents.base.ChatOllama") as mock_llm:
            mock_instance = MagicMock()
            mock_instance.ainvoke = AsyncMock(
                return_value=MagicMock(content="Monitor the situation and prepare contingency.")
            )
            mock_llm.return_value = mock_instance
            
            from src.agents.risk_agent import RiskAnalystAgent
            return RiskAnalystAgent()

    @pytest.mark.asyncio
    async def test_analyze_risks(self, risk_agent):
        """Test risk analysis."""
        from src.api.schemas import RiskAnalysisRequest
        
        request = RiskAnalysisRequest(scope="global")
        
        analysis = await risk_agent.analyze_risks(request)
        
        assert analysis.analysis_id is not None
        assert 0 <= analysis.risk_score <= 100
        assert analysis.risk_level is not None
        assert isinstance(analysis.active_risks, list)

    @pytest.mark.asyncio
    async def test_get_active_alerts(self, risk_agent):
        """Test getting active alerts."""
        alerts = await risk_agent.get_active_alerts()
        
        assert isinstance(alerts, list)
        # Should have some high-severity alerts from sample data
        if alerts:
            assert alerts[0].severity is not None

    @pytest.mark.asyncio
    async def test_scenario_analysis(self, risk_agent):
        """Test scenario planning."""
        result = await risk_agent.run_scenario(
            scenario_type="port_closure",
            parameters={"port": "Los Angeles", "duration_days": 7},
        )
        
        assert result["scenario_id"] is not None
        assert "impact_assessment" in result
        assert "recommended_preparations" in result
