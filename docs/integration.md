# Integrating the CU + Foundry IQ Extensions

This document describes the additive Content Understanding (CU) and Foundry
IQ CU-demo extensions introduced in the `cu_refactor_v2` branch and explains
how they coexist with the `main` branch behavior.

## Design goals

1. **Additive by default.** With every CU/IQ environment variable unset, the
   agent behaves identically to `main`: same prompt, same tools, same logs.
2. **Opt-in via env vars.** Each capability is gated by an explicit env var,
   so a deployment that does not configure CU never pays the prompt-size,
   logging, or context-provider cost.
3. **Integration-friendly.** No shared resource is mutated; both ingestion
   modes of the Foundry IQ demo create their own indexes/connections/KBs
   with non-overlapping names (`fibey-iq-minimal-kb`,
   `fibey-iq-standard-kb`).

## Compatibility matrix

| Env state | Behavior |
|---|---|
| All CU/IQ env vars unset | Identical to `main`. Base system prompt only. No CU context provider. No IQ MCP tool. |
| `AZURE_CONTENTUNDERSTANDING_ENDPOINT` set, `cu_mode=none` | No CU provider attached. Base prompt only. (Same as main.) |
| `AZURE_CONTENTUNDERSTANDING_ENDPOINT` set, `cu_mode=basic\|work_order` | CU provider attached. CU-specific prompt appended. UI shows the mode selector and "+" attach button. |
| `FOUNDRY_IQ_MINIMAL_MCP_URL` + `FOUNDRY_IQ_STANDARD_MCP_URL` set, `foundry_iq_mode=none` | No extra MCP tool. (Same as main.) |
| Both IQ URLs set, `foundry_iq_mode=minimal\|standard` | The selected IQ KB MCP is added **alongside** the Toolbox/local tools, not in place of them. |
| IQ mode requested but URLs not set | Warning logged, no tool added. |

## Modes vs flags

| Concept | Selected by | Layer |
|---|---|---|
| `AGENT_MODE=local` | env var | Module-level. Default. Connects to Foundry Toolbox if `TOOLBOX_MCP_URL` is set, otherwise silent local-direct fallback (back-compat). |
| `AGENT_MODE=local-direct` | env var | Module-level. Explicit Toolbox bypass; connects directly to localhost services. Preferred when the Toolbox is unavailable. |
| `cu_mode` | per-request arg from gateway | Runtime. One of `none` / `basic` / `work_order`. Drives the CU context provider and the CU-specific prompt section. |
| `foundry_iq_mode` | per-request arg from gateway | Runtime. One of `none` / `minimal` / `standard`. Drives which IQ KB MCP is added for the run. |

## Toolbox bug follow-up

The original Option-2 plan was to register the Foundry IQ KBs **inside** the
Foundry Toolbox so all knowledge tools flow through one MCP endpoint. This
is currently blocked by an upstream issue: the Toolbox MCP server does not
return an `Mcp-Session-Id` header in the initialize response, which causes
the MCP Python SDK to drop the session and any follow-up `tools/list` call
to fail with `Session terminated`. While the bug is open we keep the
defensive `_create_foundry_iq_mcp` path. Once the Toolbox is fixed, the
IQ KBs can be re-registered upstream and that helper can be removed in a
follow-up PR.

## Testing

Unit tests asserting the additive guarantees live in
[`tests/test_agent_additive.py`](../tests/test_agent_additive.py). Run them
locally with:

```bash
uv run pytest tests/test_agent_additive.py -v
```

CU live tests (require `AZURE_CONTENTUNDERSTANDING_ENDPOINT` and Azure
credentials):

```bash
uv run pytest content-understanding/tests/ -v
```

## Related files

- [`src/fibey/agent/agent.py`](../src/fibey/agent/agent.py) — flag definitions, `create_agent`, `_create_foundry_iq_mcp`
- [`src/fibey/agent/prompts/system_prompt.md`](../src/fibey/agent/prompts/system_prompt.md) — base prompt (always loaded)
- [`src/fibey/agent/prompts/system_prompt_cu.md`](../src/fibey/agent/prompts/system_prompt_cu.md) — appended only when CU is active
- [`content-understanding/README.md`](../content-understanding/README.md) — CU analyzer setup and demo walkthrough
- [`services/foundry-iq-docs/content-understanding/FOUNDRY_IQ_SETUP.md`](../services/foundry-iq-docs/content-understanding/FOUNDRY_IQ_SETUP.md) — Foundry IQ minimal vs standard ingestion setup
