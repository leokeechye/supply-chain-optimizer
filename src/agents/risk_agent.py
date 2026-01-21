"""Supply Chain Optimizer - Risk Analyst Agent."""

from datetime import datetime, date, timedelta
from typing import Any
import uuid

from langchain_core.prompts import ChatPromptTemplate

from src.agents.base import BaseAgent
from src.api.schemas import (
    RiskAnalysisRequest,
    RiskAnalysisResponse,
    RiskFactor,
    DisruptionAlert,
    RiskSeverity,
)
from src.data.sample_data import get_risk_data


class RiskAnalystAgent(BaseAgent):
    """
    Agent responsible for supply chain risk analysis and mitigation.
    
    Capabilities:
    - Geopolitical event monitoring (port strikes, trade restrictions)
    - Weather disruption analysis
    - Supplier risk assessment
    - Transport disruption detection
    - Scenario planning and mitigation recommendations
    """

    def __init__(self):
        super().__init__(
            name="Risk Analyst Agent",
            description=(
                "a supply chain risk specialist monitoring external threats "
                "and providing mitigation strategies for disruptions"
            ),
        )
        
        self.risk_analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a supply chain risk analyst.
Analyze the current risk landscape and provide actionable recommendations.

Focus on:
1. Severity and probability of each risk
2. Potential impact on operations
3. Immediate mitigation actions
4. Long-term preventive measures
5. Monitoring indicators

Be specific and prioritize by urgency.
"""),
            ("human", """Current Risk Factors:
{risk_factors}

Overall Risk Score: {risk_score}/100
Scope: {scope}

Provide your risk assessment and recommendations:"""),
        ])

        self.scenario_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a supply chain scenario planner.
Analyze the hypothetical disruption scenario and provide impact assessment.

Consider:
1. Immediate operational impact
2. Financial implications
3. Customer service effects
4. Recovery timeline
5. Preventive measures

Provide a structured analysis.
"""),
            ("human", """Scenario: {scenario_type}
Parameters: {parameters}

Analyze this scenario and its potential impact:"""),
        ])

    async def run(self, request: RiskAnalysisRequest) -> RiskAnalysisResponse:
        """Run risk analysis."""
        return await self.analyze_risks(request)

    async def analyze_risks(
        self,
        request: RiskAnalysisRequest,
    ) -> RiskAnalysisResponse:
        """Analyze external threats to the supply chain."""
        self.logger.info("Analyzing risks", scope=request.scope)
        
        # Get current risk data
        risks = get_risk_data()
        
        # Filter by categories if specified
        if request.categories:
            risks = [r for r in risks if r["category"] in request.categories]
        
        # Convert to RiskFactor objects
        risk_factors = [
            RiskFactor(
                risk_id=r["id"],
                category=r["category"],
                title=r["title"],
                description=r["description"],
                severity=RiskSeverity(r["severity"]),
                probability=r["probability"],
                affected_regions=r.get("affected_regions", []),
                affected_skus=r.get("affected_skus", []),
                potential_impact=r["potential_impact"],
                mitigation_actions=r.get("mitigation_actions", []),
                source=r.get("source"),
            )
            for r in risks
        ]
        
        # Calculate overall risk score
        risk_score = self._calculate_risk_score(risk_factors)
        
        # Determine risk level
        if risk_score >= 75:
            risk_level = RiskSeverity.CRITICAL
        elif risk_score >= 50:
            risk_level = RiskSeverity.HIGH
        elif risk_score >= 25:
            risk_level = RiskSeverity.MEDIUM
        else:
            risk_level = RiskSeverity.LOW
        
        # Get AI-generated recommendations
        recommendations = await self._generate_recommendations(
            risk_factors=risk_factors,
            risk_score=risk_score,
            scope=request.scope,
        )
        
        return RiskAnalysisResponse(
            analysis_id=f"RA-{uuid.uuid4().hex[:8].upper()}",
            scope=request.scope,
            risk_score=risk_score,
            risk_level=risk_level,
            active_risks=risk_factors,
            recommendations=recommendations,
        )

    async def get_active_alerts(
        self,
        severity_filter: RiskSeverity | None = None,
        category_filter: str | None = None,
    ) -> list[DisruptionAlert]:
        """Get active disruption alerts."""
        risks = get_risk_data()
        
        if severity_filter:
            risks = [r for r in risks if r["severity"] == severity_filter.value]
        
        if category_filter:
            risks = [r for r in risks if r["category"] == category_filter]
        
        # Convert high-severity risks to alerts
        alerts = []
        for r in risks:
            if r["severity"] in ["high", "critical"]:
                alerts.append(DisruptionAlert(
                    alert_id=f"ALT-{r['id']}",
                    type=r["category"],
                    severity=RiskSeverity(r["severity"]),
                    title=r["title"],
                    description=r["description"],
                    affected_routes=r.get("affected_routes", []),
                    affected_orders=r.get("affected_orders", []),
                    recommended_actions=r.get("mitigation_actions", []),
                    auto_mitigation_available=r.get("auto_mitigate", False),
                ))
        
        return alerts

    async def acknowledge_alert(self, alert_id: str) -> dict:
        """Acknowledge a disruption alert."""
        self.logger.info("Acknowledging alert", alert_id=alert_id)
        
        return {
            "status": "acknowledged",
            "alert_id": alert_id,
            "acknowledged_at": datetime.utcnow().isoformat(),
            "acknowledged_by": "system",
        }

    async def mitigate_risk(
        self,
        risk_id: str,
        action: str,
        auto_execute: bool = False,
    ) -> dict:
        """Execute risk mitigation action."""
        self.logger.info(
            "Mitigating risk",
            risk_id=risk_id,
            action=action,
            auto_execute=auto_execute,
        )
        
        # Simulated mitigation execution
        if auto_execute:
            status = "executed"
            message = f"Mitigation action '{action}' executed automatically"
        else:
            status = "pending_approval"
            message = f"Mitigation action '{action}' requires manual approval"
        
        return {
            "risk_id": risk_id,
            "action": action,
            "status": status,
            "message": message,
            "estimated_impact_reduction": "25%",
            "cost_estimate": 5000.00,
        }

    async def get_weather_risks(self, region: str) -> dict:
        """Get weather-related risks for a region."""
        self.logger.info("Getting weather risks", region=region)
        
        # Simulated weather risk data
        return {
            "region": region,
            "current_conditions": "clear",
            "active_alerts": [],
            "forecast_risks": [
                {
                    "event": "Winter Storm",
                    "probability": 0.3,
                    "expected_date": (date.today() + timedelta(days=5)).isoformat(),
                    "potential_impact": "Road transport delays of 1-2 days",
                    "affected_routes": ["US-Midwest", "US-Northeast"],
                },
            ],
            "historical_events": 3,
            "risk_score": 25,
        }

    async def get_supplier_risks(self, vendor_id: str) -> dict:
        """Analyze supplier-specific risks."""
        self.logger.info("Getting supplier risks", vendor_id=vendor_id)
        
        # Simulated supplier risk data
        return {
            "vendor_id": vendor_id,
            "financial_health_score": 78,
            "delivery_trend": "stable",
            "concentration_risk": "medium",
            "alternative_suppliers": 3,
            "risk_factors": [
                {
                    "factor": "Single source for key component",
                    "severity": "medium",
                    "mitigation": "Qualify backup supplier",
                },
            ],
            "overall_risk_level": "medium",
            "recommendations": [
                "Maintain safety stock buffer",
                "Qualify one additional supplier",
                "Negotiate longer-term contract for price stability",
            ],
        }

    async def run_scenario(
        self,
        scenario_type: str,
        parameters: dict,
    ) -> dict:
        """Run what-if scenario analysis."""
        self.logger.info("Running scenario", scenario_type=scenario_type)
        
        # Get AI analysis
        try:
            chain = self.scenario_prompt | self.llm
            analysis_result = await chain.ainvoke({
                "scenario_type": scenario_type,
                "parameters": str(parameters),
            })
            analysis = analysis_result.content
        except Exception as e:
            self.logger.warning("AI scenario analysis failed", error=str(e))
            analysis = self._get_default_scenario_analysis(scenario_type)
        
        # Predefined scenario impacts
        scenario_impacts = {
            "port_closure": {
                "revenue_impact": -500000,
                "delay_days": 7,
                "affected_sku_pct": 35,
            },
            "supplier_failure": {
                "revenue_impact": -250000,
                "delay_days": 14,
                "affected_sku_pct": 15,
            },
            "demand_spike": {
                "revenue_impact": 100000,  # Opportunity
                "stockout_risk": "high",
                "urgency": "immediate",
            },
        }
        
        impact = scenario_impacts.get(scenario_type, {
            "revenue_impact": -100000,
            "delay_days": 3,
            "affected_sku_pct": 10,
        })
        
        return {
            "scenario_id": f"SCN-{uuid.uuid4().hex[:8].upper()}",
            "scenario_type": scenario_type,
            "parameters": parameters,
            "impact_assessment": impact,
            "analysis": analysis,
            "recommended_preparations": [
                "Increase safety stock for critical SKUs",
                "Identify alternative suppliers",
                "Prepare communication plan for customers",
            ],
        }

    def _calculate_risk_score(self, risks: list[RiskFactor]) -> float:
        """Calculate overall risk score from individual risks."""
        if not risks:
            return 0
        
        severity_weights = {
            RiskSeverity.LOW: 10,
            RiskSeverity.MEDIUM: 30,
            RiskSeverity.HIGH: 60,
            RiskSeverity.CRITICAL: 100,
        }
        
        total_weighted = sum(
            severity_weights[r.severity] * r.probability
            for r in risks
        )
        
        # Normalize to 0-100 scale
        max_possible = len(risks) * 100
        score = (total_weighted / max_possible) * 100 if max_possible > 0 else 0
        
        return round(min(score, 100), 1)

    async def _generate_recommendations(
        self,
        risk_factors: list[RiskFactor],
        risk_score: float,
        scope: str,
    ) -> list[str]:
        """Generate AI-powered risk recommendations."""
        try:
            risk_summary = "\n".join(
                f"- {r.title} ({r.severity.value}): {r.description}"
                for r in risk_factors[:5]
            )
            
            chain = self.risk_analysis_prompt | self.llm
            result = await chain.ainvoke({
                "risk_factors": risk_summary,
                "risk_score": risk_score,
                "scope": scope,
            })
            
            # Parse recommendations
            content = result.content
            recommendations = [
                line.strip().lstrip("•-123456789. ")
                for line in content.split("\n")
                if line.strip() and len(line.strip()) > 10
            ][:5]
            
            return recommendations if recommendations else self._default_recommendations()
            
        except Exception as e:
            self.logger.warning("AI recommendations failed", error=str(e))
            return self._default_recommendations()

    def _default_recommendations(self) -> list[str]:
        """Default risk recommendations."""
        return [
            "Monitor high-severity risks daily",
            "Review safety stock levels for affected SKUs",
            "Identify alternative shipping routes",
            "Communicate with key suppliers about contingency plans",
            "Update business continuity documentation",
        ]

    def _get_default_scenario_analysis(self, scenario_type: str) -> str:
        """Default scenario analysis text."""
        return (
            f"The {scenario_type} scenario would have significant operational impact. "
            "Recommend activating contingency plans, increasing safety stock, "
            "and proactive customer communication."
        )
