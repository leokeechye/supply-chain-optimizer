"""Supply Chain Optimizer - Risk Analysis Routes."""

from fastapi import APIRouter, HTTPException, Query
import structlog

from src.api.schemas import (
    RiskAnalysisRequest,
    RiskAnalysisResponse,
    DisruptionAlert,
    RiskSeverity,
)
from src.agents.risk_agent import RiskAnalystAgent

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("/analyze", response_model=RiskAnalysisResponse)
async def analyze_risks(request: RiskAnalysisRequest) -> RiskAnalysisResponse:
    """
    Analyze external threats to the supply chain.
    
    The Risk Analyst Agent monitors:
    - Geopolitical events (port strikes, trade restrictions)
    - Weather disruptions (hurricanes, floods)
    - Supplier issues (financial health, capacity constraints)
    - Transport disruptions (route closures, carrier issues)
    
    Returns risk score, active threats, and mitigation recommendations.
    """
    logger.info("Risk analysis request", scope=request.scope)
    
    try:
        agent = RiskAnalystAgent()
        result = await agent.analyze_risks(request)
        return result
        
    except Exception as e:
        logger.error("Error analyzing risks", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts", response_model=list[DisruptionAlert])
async def get_active_alerts(
    severity: RiskSeverity | None = Query(default=None),
    category: str | None = Query(default=None),
) -> list[DisruptionAlert]:
    """
    Get active disruption alerts.
    
    Returns real-time alerts for:
    - Port congestion
    - Weather events
    - Strike actions
    - Supplier issues
    """
    logger.info("Get alerts request", severity=severity)
    
    try:
        agent = RiskAnalystAgent()
        alerts = await agent.get_active_alerts(
            severity_filter=severity,
            category_filter=category,
        )
        return alerts
        
    except Exception as e:
        logger.error("Error getting alerts", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str) -> dict:
    """Acknowledge a disruption alert."""
    logger.info("Acknowledge alert", alert_id=alert_id)
    
    try:
        agent = RiskAnalystAgent()
        result = await agent.acknowledge_alert(alert_id)
        return result
        
    except Exception as e:
        logger.error("Error acknowledging alert", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mitigate/{risk_id}")
async def mitigate_risk(
    risk_id: str,
    action: str,
    auto_execute: bool = False,
) -> dict:
    """
    Execute risk mitigation action.
    
    Available actions depend on risk type:
    - Alternative routing
    - Supplier diversification
    - Inventory buffer increase
    - Expedited shipping
    """
    logger.info("Mitigate risk", risk_id=risk_id, action=action)
    
    try:
        agent = RiskAnalystAgent()
        result = await agent.mitigate_risk(
            risk_id=risk_id,
            action=action,
            auto_execute=auto_execute,
        )
        return result
        
    except Exception as e:
        logger.error("Error mitigating risk", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weather/{region}")
async def get_weather_risks(region: str) -> dict:
    """
    Get weather-related risks for a region.
    
    Uses weather APIs to identify:
    - Upcoming severe weather
    - Impact on logistics routes
    - Warehouse vulnerability
    """
    logger.info("Weather risk request", region=region)
    
    try:
        agent = RiskAnalystAgent()
        risks = await agent.get_weather_risks(region)
        return risks
        
    except Exception as e:
        logger.error("Error getting weather risks", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/supplier/{vendor_id}")
async def get_supplier_risks(vendor_id: str) -> dict:
    """
    Analyze supplier-specific risks.
    
    Evaluates:
    - Financial health indicators
    - Delivery performance trends
    - Geographic concentration risk
    - Alternative supplier availability
    """
    logger.info("Supplier risk request", vendor_id=vendor_id)
    
    try:
        agent = RiskAnalystAgent()
        risks = await agent.get_supplier_risks(vendor_id)
        return risks
        
    except Exception as e:
        logger.error("Error getting supplier risks", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scenario")
async def run_scenario_analysis(
    scenario_type: str = Query(..., description="'port_closure', 'supplier_failure', 'demand_spike'"),
    parameters: dict | None = None,
) -> dict:
    """
    Run what-if scenario analysis.
    
    Simulates supply chain impact of various disruption scenarios
    and recommends preventive measures.
    """
    logger.info("Scenario analysis", scenario_type=scenario_type)
    
    try:
        agent = RiskAnalystAgent()
        result = await agent.run_scenario(
            scenario_type=scenario_type,
            parameters=parameters or {},
        )
        return result
        
    except Exception as e:
        logger.error("Error running scenario", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
