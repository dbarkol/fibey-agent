# Hosted Agent Infrastructure (fibey-agent environment)

This folder is a placeholder for the Azure AI Foundry hosted agent and
Toolbox resources. These are managed **separately** from the Container Apps
infrastructure (see `../infra/`).

## Resource Group

The hosted agent and Toolbox live in an **existing** resource group that is
provisioned and managed outside of `azd`. Typical resources include:

| Resource | Purpose |
|----------|---------|
| AI Foundry Project | Hosts the agent runtime |
| Foundry Toolbox | Single MCP endpoint dispatching to tools |
| AI Services (model deployment) | Chat completions model |

## Why Separate?

The hosted agent is a managed Foundry resource with its own lifecycle,
identity, and networking requirements. Keeping it in a dedicated resource
group avoids coupling its lifecycle to the Container Apps deployments.

The Container Apps resource group (`fibey-apps`) is deployed with `azd up`
and can be torn down / recreated independently without affecting the agent.

## FoundryIQ knowledge base connection

The hosted agent environment also owns the Foundry connection that links the
agent to the FoundryIQ knowledge base MCP endpoint.

| Connection | Category | Auth | Purpose |
|------------|----------|------|---------|
| `kb-fibey-field-ops-kb` | `RemoteTool` | `ProjectManagedIdentity` | Connects the hosted agent to `https://fibey-apps-search.search.windows.net/knowledgebases/fibey-field-ops-kb/mcp` |

- Connections prefixed with `kb-` are reserved for knowledge base MCP
  connections.
- The AI Services managed identity used by the hosted agent must have
  `Search Index Data Reader` on the Azure AI Search service.
- This connection lets the agent call the knowledge base through MCP without
  embedding search credentials in app configuration.

## Configuration

After the hosted agent resource group is set up, capture these values and
supply them to the `fibey-apps` environment:

```bash
# Set in the fibey-apps azd environment
azd env set FOUNDRY_PROJECT_ENDPOINT "https://<your-project>.services.ai.azure.com"
azd env set FOUNDRY_MODEL "<model-deployment-name>"
azd env set TOOLBOX_MCP_URL "https://<your-project>.services.ai.azure.com/toolboxes/<name>/mcp"
```

These are passed as environment variables to the gateway Container App via
Bicep parameters.
