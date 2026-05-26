# Fibey Field Ops

Fibey Field Ops is a demo for **fiber optics field operations** built with **Azure AI Foundry Hosted Agents** and the **Foundry Toolbox**. The agent helps field technicians quickly check parts inventory, manage work orders, find procedures and safety guidance, and verify network/service status.

## Architecture

The Fibey agent can run in three deployment modes:

### 1. Local Development Mode
```text
┌───────────────┐   POST /api/chat   ┌────────────────┐   Direct Call   ┌────────────────────────┐
│ React UI      │ ─────────────────► │ FastAPI Gateway│ ──────────────► │ Agent (in-process)     │
│ + Activity    │ ◄──── SSE stream ─ │ (:8080)        │                 │ agent-framework        │
└───────────────┘                    └────────────────┘                 └──────────┬─────────────┘
                                                                                    │
                                                                         Foundry Toolbox MCP
                                                                                    │
                          ┌──────────────────┬───────────────────┬────────────────────┬───────────────────┐
                          │ inventory-mcp    │ work-orders-api   │ FoundryIQ KB       │ status dashboard  │
                          │ parts + stock    │ work order CRUD   │ procedures + safety│ browser automation│
                          └──────────────────┴───────────────────┴────────────────────┴───────────────────┘
```

### 2. Container Apps Mode (Recommended for Production)
```text
┌───────────────┐   POST /api/chat   ┌────────────────┐   Proxy + SSE   ┌────────────────────────┐
│ React UI      │ ─────────────────► │ FastAPI Gateway│ ──────────────► │ Agent Service          │
│ (nginx)       │ ◄──── SSE stream ─ │ (Container App)│                 │ (Container App)        │
└───────────────┘                    └────────────────┘                 │ + agent-framework      │
                                                                         │ + Managed Identity     │
                                                                         └──────────┬─────────────┘
                                                                                    │
                                                                         Foundry Toolbox MCP
                                                                         (api-version=v1)
                                                                                    │
                          ┌──────────────────┬───────────────────┬────────────────────┐
                          │ Work Orders API  │ Inventory MCP     │ Knowledge Base     │
                          │ (Container App)  │ (Container App)   │ (AI Search + Blob) │
                          └──────────────────┴───────────────────┴────────────────────┘
```

### 3. Foundry Hosted Mode
```text
┌───────────────┐   POST /api/chat   ┌────────────────┐   Proxy + SSE   ┌────────────────────────┐
│ React UI      │ ─────────────────► │ FastAPI Gateway│ ──────────────► │ Foundry Hosted Agent   │
│ + Activity    │ ◄──── SSE stream ─ │ (:8080)        │                 │ (Managed by Foundry)   │
└───────────────┘                    └────────────────┘                 └────────────────────────┘
```

## What the agent can do

- Look up fiber parts, SKUs, stock levels, and inventory locations
- View, create, and update work orders
- Retrieve splicing procedures, safety protocols, and troubleshooting guidance
- Check current network or service status from the dashboard

## Prerequisites

- Python 3.12+
- Node.js 20+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Azure CLI + azd CLI
- An Azure AI Foundry project with deployed models

## Quick start

```bash
# 1) Install root and UI dependencies
./scripts/setup.sh

# 2) Start the main app
./scripts/start-dev.sh

# 3) In separate terminals, start local toolbox services as needed
cd services/inventory-mcp && uv sync && uv run python server.py
cd services/work-orders-api && uv sync && uv run python server.py
cd services/status-dashboard/public && python -m http.server 8003
```

Local endpoints:
- UI: `http://localhost:5173`
- Gateway: `http://localhost:8080`
- Inventory MCP: `http://localhost:8001`
- Work Orders API: `http://localhost:8002`
- Status Dashboard: `http://localhost:8003`

FoundryIQ source documents live under `services/foundry-iq-docs/docs/` and are uploaded to blob storage, indexed by AI Search, and exposed via a knowledge base MCP endpoint.

## Environment variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Description |
|----------|-------------|
| `AGENT_MODE` | `local`, `hosted`, or `containerapp` |
| `FOUNDRY_PROJECT_ENDPOINT` | Foundry project endpoint |
| `FOUNDRY_MODEL` | Model deployment name (e.g., `gpt-4`) |
| `HOSTED_AGENT_NAME` | Hosted agent name (hosted mode only) |
| `CONTAINERAPP_AGENT_URL` | Agent service URL (containerapp mode only) |
| `TOOLBOX_MCP_URL` | Foundry Toolbox MCP endpoint (without api-version - automatically appended) |

**Important:** The `TOOLBOX_MCP_URL` should NOT include the `api-version` query parameter. The agent code automatically appends `?api-version=v1` to the URL. This is a critical requirement discovered during integration - the Toolbox MCP endpoint requires `api-version=v1` (not date-based versions like `2024-08-01-preview`).

## Project structure

```text
src/fibey/gateway/          # FastAPI chat gateway
src/fibey/agent/            # Field ops agent prompt and orchestration
services/inventory-mcp/     # Inventory MCP server
services/work-orders-api/   # Work orders FastAPI service
services/status-dashboard/  # Static status dashboard
services/foundry-iq-docs/   # FoundryIQ source documents
ui/                         # React frontend
infra/                      # Azure Bicep infrastructure (fibey-apps RG)
infra-agent/                # Hosted agent resource group docs
scripts/                    # Setup and deployment helper scripts
docs/                       # Architecture, deployment, and dev docs
```

## Deployment to Azure

To deploy the full stack to Azure Container Apps:

```bash
# Login to Azure
az login
azd auth login

# Provision infrastructure and deploy services
azd up
```

This will:
1. Create Azure Container Apps environment
2. Deploy UI (nginx)
3. Deploy Gateway (FastAPI) in `containerapp` mode
4. Deploy Agent Service (agent-framework with Toolbox MCP)
5. Deploy backend services (work orders API, inventory MCP)
6. Configure managed identities and RBAC roles

For detailed deployment instructions, see [docs/deployment.md](docs/deployment.md).

**Production endpoints** (after deployment):
- UI: `https://fibey-apps-ui.<env-subdomain>.azurecontainerapps.io/`
- Gateway: `https://fibey-apps-gateway.<env-subdomain>.azurecontainerapps.io/`
- Agent Service: `https://fibey-apps-agent-service.<env-subdomain>.azurecontainerapps.io/`

## Documentation

See the `docs/` folder for more detail:
- `docs/architecture.md`
- `docs/local-development.md`
- `docs/deployment.md`