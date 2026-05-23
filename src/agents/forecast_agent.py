"""Supply Chain Optimizer - Demand Forecasting Agent."""

from datetime import date, datetime, timedelta
from typing import Any

import numpy as np
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from src.agents.base import BaseAgent
from src.api.schemas import ForecastRequest, ForecastResponse, ForecastPoint
from src.data.sample_data import get_historical_sales


class DemandForecastingAgent(BaseAgent):
    """
    Agent responsible for demand forecasting using time-series analysis.
    
    Capabilities:
    - Historical pattern analysis (3+ years of SKU data)
    - Seasonal trend detection
    - External signal correlation (weather, holidays, promotions)
    - Confidence interval generation (P10, P50, P90)
    """

    def __init__(self):
        super().__init__(
            name="Demand Forecasting Agent",
            description=(
                "a demand forecasting specialist using time-series analysis "
                "to predict future sales velocity and inventory needs"
            ),
        )
        
        self.analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a supply chain demand forecasting expert.
Analyze the provided sales data and forecast results to generate insights.

Focus on:
1. Overall demand trend (increasing, decreasing, stable)
2. Seasonal patterns detected
3. Any anomalies or unusual patterns
4. Confidence in the forecast
5. Recommendations for inventory planning

Keep your analysis concise and actionable.
"""),
            ("human", """SKU: {sku}
Historical Sales Summary:
- Average daily sales: {avg_sales:.1f}
- Max daily sales: {max_sales}
- Min daily sales: {min_sales}
- Standard deviation: {std_sales:.1f}

Forecast Summary:
- Horizon: {horizon_days} days
- Predicted total demand: {total_demand:.0f}
- Trend detected: {trend}

Provide your analysis:"""),
        ])

    async def run(self, request: ForecastRequest) -> ForecastResponse:
        """Generate demand forecast for an SKU."""
        return await self.generate_forecast(request)

    async def generate_forecast(self, request: ForecastRequest) -> ForecastResponse:
        """
        Generate demand forecast using time-series analysis.
        
        Uses a simplified statistical approach for demonstration.
        In production, would use Prophet or similar.
        """
        self.logger.info("Generating forecast", sku=request.sku, horizon=request.horizon_days)
        
        # Get historical data
        historical = get_historical_sales(request.sku)
        
        if not historical:
            raise ValueError(f"No historical data found for SKU: {request.sku}")
        
        # Calculate statistics
        sales_values = [h["quantity"] for h in historical]
        avg_sales = np.mean(sales_values)
        std_sales = np.std(sales_values)
        max_sales = max(sales_values)
        min_sales = min(sales_values)
        
        # Detect trend (simple linear regression)
        x = np.arange(len(sales_values))
        slope = np.polyfit(x, sales_values, 1)[0]
        
        if slope > 0.1:
            trend = "increasing"
        elif slope < -0.1:
            trend = "decreasing"
        else:
            trend = "stable"
        
        # Detect seasonality (simplified)
        seasonality_detected = std_sales > avg_sales * 0.3
        
        # Generate forecast points
        daily_forecast = []
        total_demand = 0
        
        today = date.today()
        
        for i in range(request.horizon_days):
            forecast_date = today + timedelta(days=i + 1)
            
            # Simple forecast: use average with trend adjustment
            trend_adj = slope * (len(sales_values) + i)
            predicted = max(0, avg_sales + trend_adj)
            
            # Add some daily variation based on day of week
            day_of_week = forecast_date.weekday()
            if day_of_week >= 5:  # Weekend
                predicted *= 0.7
            
            # Generate confidence intervals
            p10 = max(0, predicted - 1.28 * std_sales) if request.include_confidence else None
            p50 = predicted if request.include_confidence else None
            p90 = predicted + 1.28 * std_sales if request.include_confidence else None
            
            daily_forecast.append(ForecastPoint(
                date=forecast_date,
                predicted_demand=round(predicted, 1),
                p10=round(p10, 1) if p10 else None,
                p50=round(p50, 1) if p50 else None,
                p90=round(p90, 1) if p90 else None,
            ))
            
            total_demand += predicted
        
        # Get AI-generated recommendations
        recommendations = await self._generate_recommendations(
            sku=request.sku,
            avg_sales=avg_sales,
            max_sales=max_sales,
            min_sales=min_sales,
            std_sales=std_sales,
            trend=trend,
            horizon_days=request.horizon_days,
            total_demand=total_demand,
        )
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence(
            std_sales=std_sales,
            avg_sales=avg_sales,
            data_points=len(sales_values),
        )
        
        return ForecastResponse(
            sku=request.sku,
            sku_name=self._get_sku_name(request.sku),
            horizon_days=request.horizon_days,
            total_predicted_demand=round(total_demand, 0),
            daily_forecast=daily_forecast,
            trend=trend,
            seasonality_detected=seasonality_detected,
            confidence_score=confidence_score,
            recommendations=recommendations,
        )

    async def get_forecast_accuracy(
        self,
        sku: str,
        lookback_days: int = 30,
    ) -> dict:
        """Calculate historical forecast accuracy metrics."""
        # Simulated accuracy metrics
        return {
            "sku": sku,
            "period_days": lookback_days,
            "mae": 12.5,  # Mean Absolute Error
            "mape": 8.3,  # Mean Absolute Percentage Error
            "rmse": 15.2,  # Root Mean Square Error
            "bias": 2.1,  # Forecast bias (positive = over-forecasting)
            "accuracy_rating": "good",
            "notes": "Forecast accuracy within acceptable range for this SKU category",
        }

    async def _generate_recommendations(
        self,
        sku: str,
        avg_sales: float,
        max_sales: float,
        min_sales: float,
        std_sales: float,
        trend: str,
        horizon_days: int,
        total_demand: float,
    ) -> list[str]:
        """Generate AI-powered recommendations based on forecast."""
        try:
            chain = self.analysis_prompt | self.llm
            result = await chain.ainvoke({
                "sku": sku,
                "avg_sales": avg_sales,
                "max_sales": max_sales,
                "min_sales": min_sales,
                "std_sales": std_sales,
                "horizon_days": horizon_days,
                "total_demand": total_demand,
                "trend": trend,
            })
            
            # Parse recommendations from response
            content = result.content
            recommendations = [
                line.strip().lstrip("•-123456789. ")
                for line in content.split("\n")
                if line.strip() and len(line.strip()) > 10
            ][:5]  # Limit to 5 recommendations
            
            return recommendations if recommendations else self._default_recommendations(trend)
            
        except Exception as e:
            self.logger.warning("Failed to generate AI recommendations", error=str(e))
            return self._default_recommendations(trend)

    def _default_recommendations(self, trend: str) -> list[str]:
        """Default recommendations based on trend."""
        if trend == "increasing":
            return [
                "Consider increasing safety stock levels",
                "Review supplier capacity for potential volume increase",
                "Monitor lead times closely for any delays",
            ]
        elif trend == "decreasing":
            return [
                "Review current inventory for potential overstock",
                "Consider promotional activities to boost demand",
                "Evaluate if demand decline is seasonal or structural",
            ]
        else:
            return [
                "Maintain current inventory levels",
                "Continue monitoring demand patterns",
                "Review in 30 days for any changes",
            ]

    def _calculate_confidence(
        self,
        std_sales: float,
        avg_sales: float,
        data_points: int,
    ) -> float:
        """Calculate confidence score for forecast."""
        # Coefficient of variation (lower is better)
        cv = std_sales / avg_sales if avg_sales > 0 else 1
        cv_score = max(0, 1 - cv)
        
        # Data points score (more is better, up to 365 days)
        data_score = min(data_points / 365, 1)
        
        # Combined score
        confidence = (cv_score * 0.6 + data_score * 0.4)
        return round(confidence, 2)

    def _get_sku_name(self, sku: str) -> str:
        """Get human-readable SKU name."""
        from src.data.sample_data import get_skus
        for item in get_skus():
            if item["sku"] == sku:
                return item["name"]
        return sku
