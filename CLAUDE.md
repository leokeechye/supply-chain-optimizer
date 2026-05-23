# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
pip install -r requirements.txt                # install deps
cp .env.example .env                           # then edit if needed (defaults to Ollama@localhost:11434 / llama4)
uvicorn src.main:app --reload                  # run API on :8000 (docs at /docs when DEBUG=true)
python -m src.main                             # equivalent, uses host/port from settings

docker-compose up -d                           # api + ollama + redis stack
docker exec -it supply-chain-optimizer-ollama-1 ollama pull llama4   # first-run model fetch

pytest                                          # all tests (config in pytest.ini, asyncio_mode=auto)
pytest tests/test_agents.py                     # one file
pytest tests/test_agents.py::TestDemandForecastingAgent::test_generate_forecast   # one test
pytest --cov=src                                # coverage

black src tests                                 # format
ruff check src tests                            # lint
mypy src                                        # type-check
```

Python ≥3.12 (Dockerfile pins `python:3.12-slim`; README badges/text inconsistently say 3.11/3.12/3.14 — go by the Dockerfile).

## Architecture

FastAPI app where every HTTP route delegates to a specialized LangChain agent. All agents inherit from `src/agents/base.py::BaseAgent`, which auto-instantiates an LLM via `settings.llm_provider` (`ollama` / `openai` / `anthropic`) — so swapping providers is purely an env-var change; never hardcode an LLM client in an agent.

### Request flow

`src/main.py::create_app()` mounts `src/api/__init__.py::router` under `/api/v1`. That router stitches together five sub-routers in `src/api/routes/` (forecast, inventory, logistics, risk, vendors), each backed by its sibling agent in `src/agents/`. Pydantic request/response shapes for every route live in **one file**: `src/api/schemas.py` — update schemas there, not next to the route.

### The orchestrator

`src/agents/orchestrator.py::SupplyChainOrchestrator` builds a 7-node LangGraph workflow (`analyze_situation → forecast_demand → check_inventory → assess_risks → optimize_logistics → coordinate_vendors → make_decision`) and exposes `.run(task_type, parameters)` plus `.handle_disruption(...)`.

It's reachable over HTTP via `POST /api/v1/orchestrate/disruption` and `POST /api/v1/orchestrate/run` (see `src/api/routes/orchestrate.py`). The route file caches a single `SupplyChainOrchestrator` at module level (`_orchestrator`) because `__init__` constructs five LLM-backed sub-agents — do not switch to per-request construction. Lazy init means a missing API key surfaces on first call rather than at app startup.

`AgentState` in `orchestrator.py` is a `TypedDict` — LangGraph relies on the declared fields to propagate state between nodes. A bare `dict`/`dict`-subclass silently drops keys and the first node hits `KeyError`. Keep it a TypedDict and add fields explicitly when extending.

### Data layer is mocked

Despite the README's "SAP/Oracle/IoT/EasyPost" architecture diagram, all agent inputs come from `src/data/sample_data.py` (in-memory SKUs, warehouses, vendors, randomly-generated historical sales). There is no database connection, no `aiosqlite` setup, no real carrier integrations. `prophet` is in `requirements.txt` but unused — `DemandForecastingAgent` does forecasting with `numpy.polyfit` + standard-deviation bands, not Prophet. Treat the sample-data module as the substitution point when wiring real data.

### LLM failure handling pattern

Every orchestrator node and every recommendation-generating method wraps the LLM call in `try/except` and falls back to a `_default_*` helper (see `orchestrator.py:296-365`, `forecast_agent.py:185-243`). Preserve this pattern when adding new LLM-driven logic — Ollama may be down, the model may not be pulled, or the JSON parse may fail; routes should still return a usable response.

### Tests mock the LLM

`tests/test_agents.py` patches `src.agents.base.get_settings` and `src.agents.base.ChatOllama` to inject a `MagicMock` LLM (see the `mock_settings` / `forecast_agent` fixtures). New agent tests should follow the same fixture pattern — do not require a running Ollama for the test suite.
