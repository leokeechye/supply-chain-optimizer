# Deploying to Railway

This repo is configured to deploy to [Railway](https://railway.app) from the
included `Dockerfile`. `railway.json` pins the build to Docker and sets the
healthcheck to `/health`.

## 1. One-time setup

1. **Push the repo to GitHub** under your own account (Railway pulls from a
   GitHub remote you control). The default-branch HEAD is what gets deployed.
2. **Create a Railway project** → "Deploy from GitHub repo" → pick this repo.
   Railway will detect `Dockerfile` and `railway.json` automatically.

## 2. Environment variables

Set these in **Railway → Variables** (never commit them to git):

| Variable | Value | Why |
|---|---|---|
| `LLM_PROVIDER` | `anthropic` | Ollama is not viable on Railway without a heavy sidecar |
| `ANTHROPIC_API_KEY` | `sk-ant-…` | From https://console.anthropic.com/settings/keys |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Overrides the stale default in `src/config.py` |
| `DEBUG` | `true` (showcase) / `false` (prod) | `true` keeps `/docs` open and CORS at `*` |
| `APP_ENV` | `production` | Cosmetic; surfaces in `/health` response |

To use OpenAI instead, swap `LLM_PROVIDER=openai`, `OPENAI_API_KEY`,
`OPENAI_MODEL=gpt-4o`.

**Do not set `PORT`** — Railway injects it; the Dockerfile honors `$PORT` via
the `sh -c` `CMD`. Hardcoding it will break routing.

## 3. Build time

First deploy takes ~2 minutes. `requirements.txt` deliberately comments out
`prophet` (it compiles Stan from source, adding ~8–10 min, and the code uses
`numpy.polyfit` instead). Re-enable only if you wire real Prophet forecasts.

## 4. After the first deploy

Railway gives you a `*.up.railway.app` URL. Sanity-check these paths:

| Path | Expect |
|---|---|
| `/health` | `{"status":"healthy",...}` |
| `/docs` | Swagger UI (only when `DEBUG=true`) |
| `/orchestrate` | Redirects to the rendered UI |
| `/ui/orchestrate.html` | The flagship dashboard |
| `POST /api/v1/orchestrate/disruption` | LLM workflow, 30–60 s |

## 4b. Persisting the SQLite database (IMPORTANT)

Data (SKUs, warehouses, inventory, 1 year of sales history, vendors) lives in
a SQLite file at `./data/supply_chain.db`. On first boot the app creates the
schema and seeds it from `src/data/csv/*.csv`. CSV uploads via
`/api/v1/data/upload/{entity}` write through to this DB.

**Without a Volume, the DB file lives in ephemeral container storage and is
wiped on every redeploy** — the seed data reappears (it reseeds from the CSVs),
but any uploads are lost. To keep uploads across deploys:

1. Railway → service → **Settings → Volumes → Add Volume**.
2. Mount path: `/app/data` (the container's working dir is `/app`, so this maps
   to `./data`).
3. Redeploy. The SQLite file now persists on the volume.

No env var change is needed — the default path resolves to `./data/supply_chain.db`.
To put the DB elsewhere, set `SQLITE_PATH=/app/data/supply_chain.db` explicitly.

## 5. Promoting to a custom domain

Railway → Settings → Networking → "Generate Domain" gives a railway.app
subdomain immediately. For your own domain, add it under Custom Domains and
follow the CNAME instructions.

## 6. Cost shape

- Railway Hobby plan: ~$5–10/mo for an always-on idle container of this size.
- Anthropic: a few cents per orchestrator run (3 Claude calls each).
- Set Railway's per-service usage limits in case the workflow is hammered.

## 7. Common gotchas

- **502 / "service not available"**: the app likely bound the wrong port.
  Confirm the start command (Railway → Settings → Deploy) is *not* overriding
  the Dockerfile `CMD` with a hardcoded port. **Do not add `startCommand` to
  `railway.json`** — Railway runs it in exec form (no shell), so `$PORT`
  passes through to uvicorn as a literal string and the process crashes
  immediately. Let the Dockerfile `CMD` (which uses `sh -c`) handle binding.
- **`/docs` returns 404**: `DEBUG` is unset or `false`. Set `DEBUG=true`.
- **LLM calls return canned defaults**: the Anthropic key is missing or wrong.
  Check Deploy Logs for a `WARNING ... Decision generation failed` line — the
  `error=...` field has the cause.
- **Cold-start delay (~10 s) before the first LLM call**: orchestrator is
  module-cached (`src/api/routes/orchestrate.py::_orchestrator`); the first
  request after a new deploy or sleep pays the construction cost.
