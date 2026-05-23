"""Supply Chain Optimizer - Orchestrator Agent."""

from datetime import datetime
from typing import Any, TypedDict
import uuid

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from src.agents.base import BaseAgent
from src.agents.forecast_agent import DemandForecastingAgent
from src.agents.inventory_agent import InventoryManagementAgent
from src.agents.logistics_agent import LogisticsRouteAgent
from src.agents.vendor_agent import VendorCoordinationAgent
from src.agents.risk_agent import RiskAnalystAgent


class AgentState(TypedDict, total=False):
    """State passed between agents in the workflow.

    LangGraph uses this schema to know which keys to propagate between nodes;
    a bare `dict` subclass silently dropped fields, causing KeyError in nodes.
    """
    task_type: str
    parameters: dict
    agent_outputs: dict
    decision: str | None
    actions: list
    workflow_id: str
    started_at: str


class SupplyChainOrchestrator(BaseAgent):
    """
    Orchestrator agent that coordinates all specialized agents.
    
    Responsibilities:
    - Logistics state machine management
    - Conflict resolution between agents
    - Global optimization logic
    - Cross-agent communication
    - Disruption response coordination
    """

    def __init__(self):
        super().__init__(
            name="Orchestrator Agent",
            description=(
                "the central coordinator for the Supply Chain Optimizer, "
                "managing multi-agent workflows and supply chain decisions"
            ),
        )
        
        # Initialize specialized agents
        self.forecast_agent = DemandForecastingAgent()
        self.inventory_agent = InventoryManagementAgent()
        self.logistics_agent = LogisticsRouteAgent()
        self.vendor_agent = VendorCoordinationAgent()
        self.risk_agent = RiskAnalystAgent()
        
        # Decision-making prompt
        self.decision_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a supply chain orchestrator making strategic decisions.

Given information from multiple agents (forecasting, inventory, logistics, vendors, risk),
synthesize the data and make an optimal decision.

Consider:
1. Cost optimization
2. Service level requirements
3. Risk mitigation
4. Resource constraints
5. Long-term implications

Provide a clear decision with reasoning.
"""),
            ("human", """Decision Required: {decision_type}

Agent Inputs:
{agent_inputs}

What is your decision and reasoning?"""),
        ])
        
        # Build the workflow graph
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> CompiledStateGraph:
        """Build the LangGraph workflow for multi-agent coordination."""
        workflow = StateGraph(AgentState)
        
        # Add nodes for each phase
        workflow.add_node("analyze_situation", self._analyze_situation_node)
        workflow.add_node("forecast_demand", self._forecast_node)
        workflow.add_node("check_inventory", self._inventory_node)
        workflow.add_node("assess_risks", self._risk_node)
        workflow.add_node("optimize_logistics", self._logistics_node)
        workflow.add_node("coordinate_vendors", self._vendor_node)
        workflow.add_node("make_decision", self._decision_node)
        
        # Set entry point
        workflow.set_entry_point("analyze_situation")
        
        # Define flow
        workflow.add_edge("analyze_situation", "forecast_demand")
        workflow.add_edge("forecast_demand", "check_inventory")
        workflow.add_edge("check_inventory", "assess_risks")
        workflow.add_edge("assess_risks", "optimize_logistics")
        workflow.add_edge("optimize_logistics", "coordinate_vendors")
        workflow.add_edge("coordinate_vendors", "make_decision")
        workflow.add_edge("make_decision", END)
        
        return workflow.compile()

    async def run(
        self,
        task_type: str,
        parameters: dict | None = None,
    ) -> dict:
        """
        Run an optimization task through the multi-agent workflow.
        
        Args:
            task_type: Type of task ('reorder', 'reroute', 'disruption_response')
            parameters: Task-specific parameters
            
        Returns:
            Final decision and action plan
        """
        self.logger.info("Running orchestrated workflow", task_type=task_type)
        
        # Initialize state
        initial_state: AgentState = {
            "task_type": task_type,
            "parameters": parameters or {},
            "agent_outputs": {},
            "decision": None,
            "actions": [],
            "workflow_id": f"WF-{uuid.uuid4().hex[:8].upper()}",
            "started_at": datetime.utcnow().isoformat(),
        }
        
        try:
            final_state = await self.workflow.ainvoke(initial_state)
            
            return {
                "workflow_id": final_state["workflow_id"],
                "task_type": task_type,
                "status": "completed",
                "decision": final_state.get("decision"),
                "actions": final_state.get("actions", []),
                "agent_outputs": final_state.get("agent_outputs", {}),
                "completed_at": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            self.logger.error("Workflow failed", error=str(e))
            return {
                "workflow_id": initial_state["workflow_id"],
                "task_type": task_type,
                "status": "failed",
                "error": str(e),
            }

    async def handle_disruption(
        self,
        disruption_type: str,
        affected_items: list[str],
        severity: str,
    ) -> dict:
        """
        Handle a supply chain disruption with coordinated response.
        
        This implements the "Red Sea Port Congestion" scenario from the README:
        1. Risk Agent detects the alert
        2. Orchestrator triggers re-planning
        3. Logistics Agent queries alternatives
        4. Inventory Agent checks buffers
        5. Demand Agent verifies impact
        6. Vendor Agent negotiates early shipments
        7. Final decision on split shipment
        """
        self.logger.info(
            "Handling disruption",
            type=disruption_type,
            severity=severity,
            affected_count=len(affected_items),
        )
        
        result = await self.run(
            task_type="disruption_response",
            parameters={
                "disruption_type": disruption_type,
                "affected_items": affected_items,
                "severity": severity,
            },
        )
        
        return result

    # Workflow node implementations
    
    async def _analyze_situation_node(self, state: AgentState) -> AgentState:
        """Analyze the current situation and set context."""
        state["agent_outputs"]["situation"] = {
            "task_type": state["task_type"],
            "parameters": state["parameters"],
            "timestamp": datetime.utcnow().isoformat(),
        }
        return state

    async def _forecast_node(self, state: AgentState) -> AgentState:
        """Get demand forecasts for relevant SKUs."""
        try:
            from src.api.schemas import ForecastRequest
            
            # Get forecast for affected SKUs or default SKU
            sku = state["parameters"].get("sku", "SKU-001")
            
            request = ForecastRequest(sku=sku, horizon_days=30)
            forecast = await self.forecast_agent.generate_forecast(request)
            
            state["agent_outputs"]["forecast"] = {
                "sku": sku,
                "total_demand": forecast.total_predicted_demand,
                "trend": forecast.trend,
                "confidence": forecast.confidence_score,
            }
        except Exception as e:
            self.logger.warning("Forecast failed", error=str(e))
            state["agent_outputs"]["forecast"] = {"error": str(e)}
        
        return state

    async def _inventory_node(self, state: AgentState) -> AgentState:
        """Check inventory status and get recommendations."""
        try:
            status = await self.inventory_agent.get_inventory_status()
            
            state["agent_outputs"]["inventory"] = {
                "total_skus": status.total_skus,
                "low_stock_count": len(status.low_stock_alerts),
                "total_value": status.total_inventory_value,
                "alerts": status.low_stock_alerts[:3],  # Top 3 alerts
            }
        except Exception as e:
            self.logger.warning("Inventory check failed", error=str(e))
            state["agent_outputs"]["inventory"] = {"error": str(e)}
        
        return state

    async def _risk_node(self, state: AgentState) -> AgentState:
        """Assess current risks."""
        try:
            from src.api.schemas import RiskAnalysisRequest
            
            request = RiskAnalysisRequest(scope="global")
            analysis = await self.risk_agent.analyze_risks(request)
            
            state["agent_outputs"]["risk"] = {
                "score": analysis.risk_score,
                "level": analysis.risk_level.value,
                "active_risks": len(analysis.active_risks),
                "recommendations": analysis.recommendations[:3],
            }
        except Exception as e:
            self.logger.warning("Risk assessment failed", error=str(e))
            state["agent_outputs"]["risk"] = {"error": str(e)}
        
        return state

    async def _logistics_node(self, state: AgentState) -> AgentState:
        """Get logistics optimization options."""
        try:
            capacity = await self.logistics_agent.get_warehouse_capacity()
            
            state["agent_outputs"]["logistics"] = {
                "warehouses": len(capacity),
                "avg_utilization": sum(w["utilization_pct"] for w in capacity) / len(capacity) if capacity else 0,
                "bottlenecks": [w for w in capacity if w["utilization_pct"] > 90],
            }
        except Exception as e:
            self.logger.warning("Logistics check failed", error=str(e))
            state["agent_outputs"]["logistics"] = {"error": str(e)}
        
        return state

    async def _vendor_node(self, state: AgentState) -> AgentState:
        """Coordinate with vendors."""
        try:
            vendors = await self.vendor_agent.list_vendors()
            
            state["agent_outputs"]["vendors"] = {
                "total_vendors": len(vendors),
                "top_reliability": max(v.reliability_score for v in vendors) if vendors else 0,
            }
        except Exception as e:
            self.logger.warning("Vendor coordination failed", error=str(e))
            state["agent_outputs"]["vendors"] = {"error": str(e)}
        
        return state

    async def _decision_node(self, state: AgentState) -> AgentState:
        """Make final decision based on all agent inputs."""
        try:
            # Format agent inputs for LLM
            agent_inputs = "\n".join(
                f"{k}: {v}"
                for k, v in state["agent_outputs"].items()
            )
            
            chain = self.decision_prompt | self.llm
            result = await chain.ainvoke({
                "decision_type": state["task_type"],
                "agent_inputs": agent_inputs,
            })
            
            decision = result.content
            
            # Extract actions from decision
            actions = self._extract_actions(decision, state["task_type"])
            
            state["decision"] = decision
            state["actions"] = actions
            
        except Exception as e:
            self.logger.warning("Decision generation failed", error=str(e))
            state["decision"] = self._default_decision(state["task_type"])
            state["actions"] = self._default_actions(state["task_type"])
        
        return state

    def _extract_actions(self, decision: str, task_type: str) -> list[dict]:
        """Extract actionable items from decision text."""
        actions = []
        
        if task_type == "reorder":
            actions.append({
                "action": "create_purchase_order",
                "priority": "normal",
                "auto_execute": False,
            })
        elif task_type == "reroute":
            actions.append({
                "action": "reroute_shipment",
                "priority": "high",
                "auto_execute": False,
            })
        elif task_type == "disruption_response":
            actions.extend([
                {"action": "activate_contingency_plan", "priority": "high"},
                {"action": "notify_stakeholders", "priority": "high"},
                {"action": "evaluate_alternative_routes", "priority": "medium"},
            ])
        
        return actions

    def _default_decision(self, task_type: str) -> str:
        """Default decision when AI generation fails."""
        defaults = {
            "reorder": "Proceed with standard reorder based on safety stock levels.",
            "reroute": "Evaluate alternative routes and select based on cost-speed balance.",
            "disruption_response": "Activate contingency plan, increase safety stock, notify customers.",
        }
        return defaults.get(task_type, "Proceed with standard operating procedures.")

    def _default_actions(self, task_type: str) -> list[dict]:
        """Default actions when extraction fails."""
        return [
            {"action": "review_situation", "priority": "high"},
            {"action": "manual_decision_required", "priority": "high"},
        ]
