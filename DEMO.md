# DEMO — 7-Step Walkthrough

Live demo script for the Supply Chain Optimizer. Designed to be run in front of
an audience in ~10 minutes, showing capability ramp from no-input → multi-agent
orchestration → user-supplied data.

## Setup before the demo

Pick where you're driving from — both work, the URLs differ:

| Where | API base | Swagger UI |
|---|---|---|
| **Railway (public)** | `https://supply-chain-optimizer-production.up.railway.app` | `/docs` |
| **Local** | `http://localhost:8000` | `/docs` |

Before going on stage:

1. **Warm up the orchestrator.** First request after a Railway sleep adds ~10 s
   cold-start (the LangGraph workflow constructs five LLM-backed sub-agents).
   Hit `/health` and then run **Step 6** once privately so the audience sees
   the steady-state latency.
2. **Open two browser tabs:** `/docs` (for steps 1-7) and `/orchestrate` (for
   the polished view at step 6).
3. **Keep your uvicorn / Railway logs visible in a side panel.** Agent
   transitions log live (`Generating forecast … Analyzing risks … Workflow
   completed`) and reinforce that this is genuinely multi-agent, not one
   monolithic prompt.

## Generic Swagger UI flow (same every endpoint)

1. Click an endpoint row to expand.
2. Click **"Try it out"** (top-right of the expanded panel).
3. Fill in:
   - **Path params** (`{sku}`) — small text box at top of "Parameters".
   - **Query params** (`?horizon_days=30`) — text boxes next to each name.
   - **Request body** — big editable JSON area, pre-filled with an example.
   - **File** — "Choose File" button (multipart endpoints).
4. Click the big blue **Execute** button.
5. Scroll down to **Response body** for the JSON. The cURL command Swagger
   built is also shown — useful for sharing or scripting.

---

## The 7 steps

### 1. No input at all — proves the wiring works

- **GET `/api/v1/inventory/status`** → Try it out → Execute.
- ✅ Returns 10 SKUs × 4 warehouses, total inventory value ~$3M, 2 low-stock alerts.
- 💬 *"This is the data layer — no LLM call yet, instant response."*

### 2. Path parameter — first LLM call

- **GET `/api/v1/forecast/{sku}`** → `sku`: `SKU-001` → Execute.
- ✅ 30-day forecast with `predicted_demand`, P10/P50/P90 bands, trend, and
  Claude-generated `recommendations`.
- ⏱ ~10 s — this is your audience's first taste of LLM latency.

### 3. Path + query param — different SKU & horizon

- **GET `/api/v1/forecast/{sku}`** → `sku`: `SKU-005`, `horizon_days`: `60` → Execute.
- ✅ Confirms the system handles arbitrary SKUs and time horizons.

### 4. POST with a JSON body — risk analysis

- **POST `/api/v1/risk/analyze`** → Try it out → paste:

  ```json
  {"scope": "global", "time_horizon_days": 30}
  ```

  Execute.
- ✅ Risk score (22.9/100), 4 active risks (Red Sea / hurricane / supplier /
  trucking), Claude-written executive summary in `recommendations`.

### 5. POST with an enum — route optimization

- **POST `/api/v1/logistics/optimize`** → paste:

  ```json
  {
    "origin": "WH-ASIA-PACIFIC",
    "destination": "Newark, NJ, USA",
    "cargo_weight_kg": 1500,
    "priority": "urgent"
  }
  ```

  Execute.
- ✅ Recommended route + alternatives, each with mode, carrier, cost, transit days.

### 6. **The showcase** — full multi-agent workflow

Two ways to present this. Show **both** — start with Swagger to prove it's a
real API, then switch to the UI for the moneyshot.

**6a. Via Swagger (proves the API):**
- **POST `/api/v1/orchestrate/disruption`** → paste:

  ```json
  {
    "disruption_type": "port_congestion",
    "affected_items": ["SKU-001", "SKU-002"],
    "severity": "high"
  }
  ```

  Execute. ⏱ 30–60 s (three sequential Claude calls).
- ✅ `status: "completed"`, ~5 KB `decision` field (executive Markdown plan),
  3 `actions`, full `agent_outputs` trace.

**6b. Via the rendered UI (the moneyshot):**
- Open `/orchestrate` in the second tab.
- Pick disruption type and severity from dropdowns, tick SKUs, click
  **Run Workflow**.
- Right panel renders the Markdown decision as a real document (headers,
  tables, code blocks). Left panel shows the per-agent trace.
- 💬 *"The same API call, with the model's output rendered as the executive
  document it actually is."*

**Key talking point for step 6:** mention how Claude noticed something the
input never asked about — e.g., that an unrelated SKU is already low-stock at
the affected warehouse. That cross-agent reasoning is the architectural payoff.

### 7. Bring your own data — CSV upload

- **GET `/api/v1/data/template/{entity}`** → `entity`: `skus` → Execute.
  Copy the response (it's a CSV) into a text editor.
- Add a few rows. Example:

  ```csv
  sku,name,category
  WIDGET-A,Premium Widget,widgets
  WIDGET-B,Standard Widget,widgets
  GADGET-X,Industrial Gadget,gadgets
  ```

  Save as `my_skus.csv`.
- **POST `/api/v1/data/upload/{entity}`** → `entity`: `skus` →
  **Choose File** → pick `my_skus.csv` → Execute.
- ✅ `{"entity": "skus", "rows_loaded": 3}`.
- Re-run **Step 1** — `total_skus` is now `3` and shows your SKUs.
- **Reset:** **POST `/api/v1/data/reset`** → Execute. The original 10 SKUs return.
- 💬 *"Same five-line CSV upload works for inventory, sales history, warehouses,
  and vendors — see `/api/v1/data/template/{entity}` for each schema."*

---

## Closing talking points

- **What's real:** the multi-agent orchestration, the LLM synthesis, the
  HTTP API surface, the rendered UI, the data ingest pipeline.
- **What's mocked:** the underlying data (`src/data/sample_data.py`) and the
  active risk feed (`src/agents/risk_agent.py`). Both are replaceable — the
  CSV upload covers the data side; wiring a real risk feed is a single
  function swap.
- **What it costs:** a few cents per orchestrator run (3 Claude calls).
  Demo with `claude-sonnet-4-6` (~$0.02/call); for production accuracy
  swap to Opus.

## Recovery cheatsheet (if something goes wrong on stage)

| Symptom | Likely cause | One-line fix |
|---|---|---|
| 502 from Railway | Container sleeping or crashed | Refresh `/health`; first hit wakes it |
| All endpoints return canned text | `ANTHROPIC_API_KEY` not set or invalid | Railway → Variables → check key |
| `/docs` returns 404 | `DEBUG` is not `true` in Variables | Add `DEBUG=true`, redeploy |
| Orchestrator returns `status: "failed"` | LLM exception escaped a node | Check Deploy Logs for the traceback |
| Upload returns `Missing required columns` | CSV header doesn't match schema | Re-download the template and start fresh |
