"""Supply Chain Optimizer - Orchestrator Routes.

Exposes the multi-agent LangGraph workflow over HTTP so the flagship
"Red Sea Port Congestion" demo from the README is reachable from /docs.
"""

from fastapi import APIRouter, HTTPException
import structlog

from src.api.schemas import (
    DisruptionRequest,
    OrchestrationRequest,
    OrchestrationResponse,
)
from src.agents.orchestrator import SupplyChainOrchestrator

router = APIRouter()
logger = structlog.get_logger(__name__)

# SupplyChainOrchestrator.__init__ constructs five LLM-backed sub-agents, so
# we cache a single instance for the process rather than rebuild it per
# request. Lazy so module import stays cheap and so a missing API key only
# raises on first call, not at app startup.
_orchestrator: SupplyChainOrchestrator | None = None


def _get_orchestrator() -> SupplyChainOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SupplyChainOrchestrator()
    return _orchestrator


@router.post("/disruption", response_model=OrchestrationResponse)
async def orchestrate_disruption(
    request: DisruptionRequest,
) -> OrchestrationResponse:
    """Run the full multi-agent workflow for a supply chain disruption.

    Drives the LangGraph state machine through:
    analyze_situation -> forecast_demand -> check_inventory -> assess_risks
    -> optimize_logistics -> coordinate_vendors -> make_decision

    The final node synthesizes every sub-agent's output via the configured
    LLM (see LLM_PROVIDER in .env) into a strategic decision and a list of
    extracted actions. Expect 30-60s end-to-end depending on the provider.
    """
    logger.info(
        "Disruption orchestration request",
        type=request.disruption_type,
        severity=request.severity.value,
    )
    try:
        orch = _get_orchestrator()
        result = await orch.handle_disruption(
            disruption_type=request.disruption_type,
            affected_items=request.affected_items,
            severity=request.severity.value,
        )
        return OrchestrationResponse(**result)
    except Exception as e:
        logger.error("Disruption orchestration failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run", response_model=OrchestrationResponse)
async def orchestrate_run(
    request: OrchestrationRequest,
) -> OrchestrationResponse:
    """Run the orchestrator with an arbitrary task_type + parameters.

    Recognized task_types (see orchestrator._extract_actions):
    - 'reorder'              -> create_purchase_order
    - 'reroute'              -> reroute_shipment
    - 'disruption_response'  -> contingency / notify / evaluate routes

    Any other value still runs the full graph; only the post-decision
    action extraction is task-specific.
    """
    logger.info("Orchestration request", task_type=request.task_type)
    try:
        orch = _get_orchestrator()
        result = await orch.run(
            task_type=request.task_type,
            parameters=request.parameters,
        )
        return OrchestrationResponse(**result)
    except Exception as e:
        logger.error("Orchestration failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
