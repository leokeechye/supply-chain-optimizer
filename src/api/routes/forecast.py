"""Supply Chain Optimizer - Demand Forecasting Routes."""

from fastapi import APIRouter, HTTPException, Query
import structlog

from src.api.schemas import ForecastRequest, ForecastResponse
from src.agents.forecast_agent import DemandForecastingAgent

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/{sku}", response_model=ForecastResponse)
async def get_demand_forecast(
    sku: str,
    horizon_days: int = Query(default=30, ge=1, le=365),
    include_confidence: bool = Query(default=True),
    include_components: bool = Query(default=False),
) -> ForecastResponse:
    """
    Get demand forecast for a specific SKU.
    
    Uses time-series analysis with Prophet to predict future demand based on:
    - Historical sales data
    - Seasonal patterns
    - External signals (weather, holidays, promotions)
    
    Returns:
    - Daily forecast for the specified horizon
    - Confidence intervals (P10, P50, P90)
    - Trend analysis and recommendations
    """
    logger.info(
        "Forecast request",
        sku=sku,
        horizon_days=horizon_days,
    )
    
    try:
        agent = DemandForecastingAgent()
        
        request = ForecastRequest(
            sku=sku,
            horizon_days=horizon_days,
            include_confidence=include_confidence,
            include_components=include_components,
        )
        
        forecast = await agent.generate_forecast(request)
        return forecast
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Error generating forecast", sku=sku, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def get_batch_forecast(
    skus: list[str],
    horizon_days: int = Query(default=30, ge=1, le=365),
) -> dict:
    """
    Get demand forecasts for multiple SKUs.
    
    Useful for planning across product categories.
    """
    logger.info("Batch forecast request", sku_count=len(skus))
    
    try:
        agent = DemandForecastingAgent()
        
        forecasts = []
        errors = []
        
        for sku in skus:
            try:
                request = ForecastRequest(sku=sku, horizon_days=horizon_days)
                forecast = await agent.generate_forecast(request)
                forecasts.append(forecast)
            except Exception as e:
                errors.append({"sku": sku, "error": str(e)})
        
        return {
            "forecasts": forecasts,
            "errors": errors,
            "success_count": len(forecasts),
            "error_count": len(errors),
        }
        
    except Exception as e:
        logger.error("Error in batch forecast", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{sku}/accuracy")
async def get_forecast_accuracy(
    sku: str,
    lookback_days: int = Query(default=30, ge=7, le=90),
) -> dict:
    """
    Get historical accuracy metrics for SKU forecasts.
    
    Compares past predictions against actual sales to measure:
    - Mean Absolute Error (MAE)
    - Mean Absolute Percentage Error (MAPE)
    - Forecast bias
    """
    logger.info("Forecast accuracy request", sku=sku)
    
    try:
        agent = DemandForecastingAgent()
        accuracy = await agent.get_forecast_accuracy(sku, lookback_days)
        return accuracy
        
    except Exception as e:
        logger.error("Error getting accuracy", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
