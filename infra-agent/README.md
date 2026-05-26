# Hosted Agent Infrastructure (fibey-agent)

This folder documents the Azure AI Foundry hosted agent deployment for Fibey.

## Target Environment

| Property | Value |
|----------|-------|
| Foundry Project | `e2e-tests-westus2` |
| Account | `e2e-tests-westus2-account.services.ai.azure.com` |
| Model | `gpt-4.1-mini` (GlobalStandard) |
| Toolbox | `fibey` (work orders, inventory, knowledge base) |

## Architecture

```
┌──────────────────────────────────────────────────┐
│  Azure AI Foundry (e2e-tests-westus2)            │
│                                                  │
│  ┌──────────────────┐   ┌──────────────────────┐ │
│  │  Hosted Agent    │──▶│  Foundry Toolbox      │ │
│  │  (fibey-agent)   │   │  (MCP endpoint)       │ │
│  │                  │   │  ├─ Work Orders API   │ │
│  │  ResponsesHost   │   │  ├─ Inventory MCP     │ │
│  │  + SkillsProvider│   │  └─ Knowledge Base    │ │
│  └──────────────────┘   └──────────────────────┘ │
│                                                  │
│  Model: gpt-4.1-mini                             │
└──────────────────────────────────────────────────┘
```

## Deployment

The hosted agent is deployed via `azd` using the `azure.ai.agent` host type.

### Prerequisites

1. Install the `azd` AI agents extension:
   ```bash
   azd extension install azure.ai.agents
   ```

2. Log in to Azure:
   ```bash
   azd auth login
   az login
   ```

### Deploy the Hosted Agent

```bash
# From the repo root
azd up
```

This will:
- Build the `Dockerfile.agent` container image (remote build)
- Deploy the agent to the Foundry project
- Provision the `gpt-4.1-mini` model deployment if needed

### Deploy Only the Agent (skip Container Apps)

```bash
azd deploy fibey-agent
```

### Environment Variables

Set in `agent.yaml` and injected by the Foundry platform:

| Variable | Source | Description |
|----------|--------|-------------|
| `FOUNDRY_PROJECT_ENDPOINT` | Auto-injected | Foundry project endpoint URL |
| `FOUNDRY_MODEL` | `agent.yaml` | Model deployment name |
| `TOOLBOX_MCP_URL` | `agent.yaml` | Toolbox MCP endpoint URL |

### Test the Agent

After deployment, test via the Foundry playground or API:

```bash
# Via az CLI
az ai agent create-run \
  --project-endpoint "https://e2e-tests-westus2-account.services.ai.azure.com/api/projects/e2e-tests-westus2" \
  --agent-name "fibey-agent"
```

## Files

| File | Purpose |
|------|---------|
| `agent.yaml` | Agent definition (kind, protocol, env vars, resources) |
| `azure.yaml` | azd service definition (host type, model deployment) |
| `Dockerfile.agent` | Container image for the hosted agent |
| `requirements.txt` | Python dependencies for the hosted agent |
| `src/fibey/agent/hosted.py` | Hosted agent entrypoint |

## Local vs Hosted Mode

The agent supports two modes:

| | Local Mode | Hosted Mode |
|---|-----------|-------------|
| **Entrypoint** | `src/fibey/agent/agent.py` | `src/fibey/agent/hosted.py` |
| **Server** | FastAPI gateway (`api_server.py`) | `ResponsesHostServer` |
| **History** | In-memory `AgentSession` | Managed by Foundry platform |
| **Toolbox auth** | `_AzureAuthTransport` (CLI cred) | Managed by platform |
| **Skills** | `SkillsProvider` ✅ | `SkillsProvider` ✅ |
| **MCP client** | `MCPStreamableHTTPTool` (local httpx) | `FoundryMCPTool` (server-side) |

## Foundry Toolbox

The Toolbox lives in the same project and provides a single MCP endpoint
that dispatches to three backend tools:

| Tool | Type | Backend |
|------|------|---------|
| Work Orders | OpenAPI | Container App (`work-orders-api`) |
| Inventory | MCP | Container App (`inventory-mcp`) |
| Knowledge Base | Azure AI Search | `foundry-iq-docs-index` (semantic) |

The Toolbox URL is set in `agent.yaml` and does not require separate auth
when accessed from within the same Foundry project.
