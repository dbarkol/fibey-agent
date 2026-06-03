# Fibey Field Ops

Fibey is a runnable demo of an agent that connects to four different
backend systems — inventory, work orders, a knowledge base, and a status
dashboard — through **one** endpoint: the **Azure AI Foundry Toolbox**.

This sample also includes an optional Content Understanding (CU) extension. CU
is additive: when CU environment variables are unset, behavior remains the same
as the base Toolbox flow.

## What the agent can do

- Look up fiber parts, SKUs, stock levels, and inventory locations
- View, create, and update work orders
- Retrieve splicing procedures, safety protocols, and troubleshooting guidance
- Check current network or service status

## Architecture (local mode)

```text
┌──────────────┐  /api/chat  ┌──────────────────┐  in-proc  ┌──────────────────┐
│  React UI    │ ──────────► │  FastAPI Gateway │ ────────► │  Fibey Agent     │
│  + Activity  │ ◄── SSE ─── │  (:8080)         │           │  (agent-fw)      │
└──────────────┘             └──────────────────┘           └────────┬─────────┘
                                                                     │
                                                         Foundry Toolbox MCP
                                                                     │
              ┌────────────────┬───────────────────┬─────────────────┐
              │ inventory-mcp  │ work-orders-api   │ FoundryIQ KB    │
              │   (:8001)      │    (:8002)        │ (AI Search)     │
              └────────────────┴───────────────────┴─────────────────┘
```

The sample also ships **containerapp** and **hosted** modes — see
[docs/architecture.md](docs/architecture.md).

## Prerequisites

- Python 3.12+
- Node.js 20+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Azure CLI (`az`) + Azure Developer CLI (`azd`) — only needed for cloud deploy
- An Azure AI Foundry project with a deployed model and a configured Toolbox

## Quickstart (local)

```bash
# 1) Install Python and UI dependencies
./scripts/setup.sh

# 2) Copy and edit environment variables
cp .env.example .env

# Fastest no-cloud path (recommended first run): local-direct
# This bypasses Foundry Toolbox and uses local services on :8001/:8002
AGENT_MODE=local-direct

# 3) Start the gateway + UI
AGENT_MODE=local-direct ./scripts/start-dev.sh

# 4) In separate terminals, start local backends
cd services/inventory-mcp     && uv sync && uv run python server.py
cd services/work-orders-api   && uv sync && uv run python server.py
cd services/status-dashboard/public && python -m http.server 8003
```

After this works, you can switch to `AGENT_MODE=local` and set
`FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_MODEL`, and `TOOLBOX_MCP_URL` to test the
real Foundry Toolbox path.

Open the UI at <http://localhost:5173>.

| Service | Local URL |
|---|---|
| UI | `http://localhost:5173` |
| Gateway | `http://localhost:8080` |
| Inventory MCP | `http://localhost:8001` |
| Work Orders API | `http://localhost:8002` |
| Status Dashboard | `http://localhost:8003` |

> **Toolbox URL gotcha:** `TOOLBOX_MCP_URL` should **not** include
> `?api-version=v1`. The agent code auto-appends it. The Toolbox MCP
> endpoint requires `api-version=v1` (not a date-based version).

## Deploy to Azure

The full stack (UI, gateway, agent service, work-orders API, inventory MCP,
AI Search, blob storage) deploys to Azure Container Apps via `azd`:

```bash
az login
azd auth login
azd up
```

See [docs/deployment.md](docs/deployment.md) for the full deployment guide,
including FoundryIQ knowledge base setup and post-deploy RBAC.

## Optional Content Understanding (CU)

For CU testing in local development, use `AGENT_MODE=local-direct`.
This avoids toolbox auth/network issues during file-upload flows and keeps
the CU path deterministic while iterating on prompts/UI.

CU can be enabled in two layers depending on your goal:

1. Runtime upload parsing for chat requests.
2. Foundry IQ ingestion comparison (minimal vs standard extraction).

Set optional environment variables in `.env` as needed:

| Variable | Purpose |
|---|---|
| `AZURE_CONTENTUNDERSTANDING_ENDPOINT` | Enables CU-based file parsing for uploads in chat. |
| `FOUNDRY_IQ_MINIMAL_MCP_URL` | Optional MCP URL for minimal-ingestion Foundry IQ KB. |
| `FOUNDRY_IQ_STANDARD_MCP_URL` | Optional MCP URL for standard (CU-enhanced) Foundry IQ KB. |
| `AZURE_CONTENTUNDERSTANDING_KEY` | Optional key used by standard indexing setup flows. |
| `CU_VERBOSE_LOGGING` | Optional verbose CU logs (`1`, `true`, `yes`, `on`). |

When `AZURE_CONTENTUNDERSTANDING_ENDPOINT` is set, the UI enables file
attachments and CU mode selection. Full walkthrough:
[content-understanding/README.md](content-understanding/README.md).

## Documentation

| Doc | When to read it |
|---|---|
| [`docs/toolbox-integration.md`](docs/toolbox-integration.md) | The integration recipe (custom `httpx.Auth`, headers, MCP gotchas) |
| [`docs/architecture.md`](docs/architecture.md) | Full system diagram, components, streaming protocol, agent modes |
| [`docs/local-development.md`](docs/local-development.md) | All env vars, running individual services, testing the gateway API |
| [`docs/deployment.md`](docs/deployment.md) | Azure deployment via `azd`, knowledge base setup, RBAC |
| [`docs/session-overview.md`](docs/session-overview.md) | High-level narrative for the BRK242 reference copy |
| [`infra-agent/README.md`](infra-agent/README.md) | Foundry-hosted agent infrastructure notes |

## Project layout

```text
src/fibey/                # Python package: agent + gateway
services/
  inventory-mcp/          # MCP inventory server (port 8001)
  work-orders-api/        # FastAPI work-orders service (port 8002)
  status-dashboard/       # Static service-status dashboard (port 8003)
  foundry-iq-docs/        # Markdown source for the FoundryIQ knowledge base
ui/                       # React + TypeScript + Tailwind frontend
infra/                    # Bicep modules for Container Apps + AI Search + blob
infra-agent/              # Foundry-hosted agent infra notes
scripts/                  # setup.sh, start-dev.sh, setup-knowledge-base.sh
docs/                     # Architecture, deployment, local-dev, integration docs
```

## License

Licensed under the MIT License — see [LICENSE](LICENSE).
