# Deployment

## Overview

Fibey Field Ops uses a **two resource group** deployment model:

| Environment | Resource Group | Managed By | Contents |
|-------------|---------------|------------|----------|
| `fibey-apps` | New RG via `azd` | `azure.yaml` + Bicep | Container Apps, Registry, Storage |
| `fibey-agent` | Existing RG | Portal / CLI (external) | Hosted Agent, Toolbox, AI Services |

This separation lets you tear down and redeploy the app services independently without affecting the hosted agent and Toolbox configuration.

## Resource group: fibey-apps (azd-managed)

Deployed with `azd up`. Contains:

| Component | Azure Service | Source | Port |
|-----------|---------------|--------|------|
| Chat UI | Container App | `ui/` | 80 |
| Gateway | Container App | `src/fibey/gateway/` | 8000 |
| Inventory MCP | Container App | `services/inventory-mcp/` | 8001 |
| Work Orders API | Container App | `services/work-orders-api/` | 8002 |
| Status Dashboard | Container App | `services/status-dashboard/` | 8003 |
| AI Search | Azure AI Search (Basic) | `services/foundry-iq-docs/` | — |
| Container Registry | ACR (Basic) | — | — |
| Storage Account | Blob Storage | `services/foundry-iq-docs/` | — |
| Log Analytics | Workspace | — | — |

### Deployment steps

```bash
# 1. Initialize azd environment
azd init -e fibey-apps

# 2. Set Foundry settings (from the fibey-agent resource group)
azd env set FOUNDRY_PROJECT_ENDPOINT "https://<account>.services.ai.azure.com/api/projects/<project>"
azd env set FOUNDRY_MODEL "<model-deployment-name>"
azd env set TOOLBOX_MCP_URL "https://<account>.services.ai.azure.com/api/projects/<project>/toolboxes/<name>/versions/<ver>/mcp?api-version=v1"

# 3. Provision and deploy (creates RG, builds images, deploys)
azd up

# 4. Upload FoundryIQ documents to blob storage
az storage blob upload-batch \
  --source services/foundry-iq-docs/docs/ \
  --destination foundry-iq-docs \
  --account-name <storage-account-from-output>
```

## Resource group: fibey-agent (externally managed)

This resource group is **not** managed by `azd`. It contains:

| Resource | Purpose |
|----------|---------|
| AI Foundry Project | Hosts the agent runtime |
| Foundry Toolbox | Single MCP endpoint dispatching to 4 tools |
| AI Services | Chat completions model deployment |

See `infra-agent/README.md` for setup instructions and how to capture the
endpoint values needed by the apps environment.

> **Note:** The Toolbox must be configured to point at the Container App
> FQDNs from the `fibey-apps` deployment (inventory-mcp, work-orders-api,
> status-dashboard). This is a manual step in the Foundry portal after
> both resource groups are set up.

## Environment variables

These are set via `azd env set` and injected into the gateway Container App
by the Bicep template:

| Variable | Description | Source |
|----------|-------------|--------|
| `FOUNDRY_PROJECT_ENDPOINT` | AI Foundry project endpoint | fibey-agent RG |
| `FOUNDRY_MODEL` | Model deployment name | fibey-agent RG |
| `TOOLBOX_MCP_URL` | Foundry Toolbox MCP endpoint (versioned URL) | fibey-agent RG |

## FoundryIQ Knowledge Base Setup

The deployed knowledge path is:

```text
services/foundry-iq-docs/docs/
→ Blob Storage container
→ AI Search indexer
→ AI Search index
→ Knowledge Source
→ Knowledge Base
→ MCP endpoint
→ Foundry connection
```

After `azd provision` (or after the infrastructure portion of `azd up`) completes:

1. **Upload documents to blob storage.** This repo already uses `services/foundry-iq-docs/docs/` as the upload source.
2. **Create the search index and indexer.** Run `./scripts/setup-knowledge-base.sh` to create the blob data source, `foundry-iq-docs-index`, semantic configuration `default`, and the indexer that ingests the text-only markdown files.
3. **Create the Knowledge Source.** Use the AI Search REST API with `api-version=2026-04-01` to create `fibey-field-ops-ks` with `kind: searchIndex`, pointing at `foundry-iq-docs-index`.
4. **Create the Knowledge Base.** Use the AI Search REST API with `api-version=2026-04-01` to create `fibey-field-ops-kb`, referencing `fibey-field-ops-ks`. Configure with `low` reasoning effort, `extractiveData` output mode, and a lightweight chat completion model (e.g. `gpt-4o-mini`) for query planning.
5. **Create the Foundry connection.** In the hosted agent AI Services account, create a `CognitiveSearch` connection with `ApiKey` auth pointing at the search service. Use this connection in the Toolbox with `azure_ai_search` tool type.
6. **Assign RBAC.** Grant the AI Services managed identity `Search Index Data Reader` and `Search Index Data Contributor` on the search service.

### Deployed components

| Layer | Name | Resource Group / Scope | Notes |
|-------|------|-------------------------|-------|
| Search service | `<env>-search` | `<resource-group>` | Azure AI Search, Basic SKU |
| Search index | `foundry-iq-docs-index` | Search service | 8 text documents, semantic ranking only, no vectors |
| Semantic config | `default` | `foundry-iq-docs-index` | `titleField=metadata_storage_name`, `contentField=content` |
| Knowledge source | `fibey-field-ops-ks` | AI Search REST API | `kind: searchIndex` via `2026-04-01` |
| Knowledge base | `fibey-field-ops-kb` | AI Search REST API | References `fibey-field-ops-ks` |
| MCP endpoint | `https://<search-service>.search.windows.net/knowledgebases/fibey-field-ops-kb/mcp` | AI Search | Exposed by the knowledge base |
| Foundry connection | `kb-fibey-field-ops-kb` | AI Services account | `RemoteTool` + `ProjectManagedIdentity` |
| RBAC | `Search Index Data Reader` | AI Services managed identity | Required on the search service |

The knowledge base retrieval was validated with semantic `intents` requests against `fibey-field-ops-ks`, returning references and source data:

```json
{
  "intents": [{"search": "How do I splice a fiber optic cable?", "type": "semantic"}],
  "knowledgeSourceParams": [{"knowledgeSourceName": "fibey-field-ops-ks", "kind": "searchIndex", "includeReferences": true, "includeReferenceSourceData": true}]
}
```

> **Note:** `2026-04-01` is the GA API version used here for knowledge sources and knowledge bases.
>
> **Note:** Azure AI Foundry workspaces currently allow up to **120 connections**. This workspace is already at **120/120**, so plan for cleanup or capacity management before adding more connections.

## Notes

- All Container Apps are configured with **minReplicas: 1** to avoid cold starts.
- The FoundryIQ documents are uploaded to blob storage and indexed separately — they are not part of the container deployment.
- The status dashboard can be set to internal-only ingress if browser automation is the only consumer.
- Infrastructure definitions live in `infra/` (Bicep modules). Toolbox registration inside Foundry is an operational step outside this repo.
