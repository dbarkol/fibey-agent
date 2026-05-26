"""Fibey Agent — Foundry hosted agent entrypoint.

Deployed to Azure AI Foundry as a hosted agent using the responses protocol.
Follows the foundry-samples agent-framework pattern.

Architecture (hosted mode):
    Single agent with:
    - Foundry Toolbox MCP tool (work orders, inventory, knowledge base)
    - SkillsProvider for deterministic routing (field-briefing,
      inventory-lookup, knowledge-retrieval, work-order-management,
      work-order-preparation)

Environment variables (auto-injected by Foundry hosting):
    FOUNDRY_PROJECT_ENDPOINT — project endpoint URL

Environment variables (set in agent.yaml):
    FOUNDRY_MODEL — model deployment name (e.g. gpt-4.1-mini)
    TOOLBOX_MCP_URL — Foundry Toolbox MCP endpoint URL
"""

import logging
import os
from pathlib import Path

from agent_framework import Agent, SkillsProvider
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "system_prompt.md"
SKILLS_DIR = Path(__file__).parent / "skills"


def _load_system_prompt() -> str:
    if SYSTEM_PROMPT_PATH.exists():
        return SYSTEM_PROMPT_PATH.read_text()
    return "You are Fibey, a helpful AI assistant for fiber optics field operations."


def main() -> None:
    """Start the hosted agent server."""
    client = FoundryChatClient()

    # --- Toolbox MCP Tool ---
    tools: list = []
    toolbox_url = os.environ.get("TOOLBOX_MCP_URL", "")
    if toolbox_url:
        logger.info("Registering Toolbox MCP: %s", toolbox_url[:80])
        try:
            tools.append(client.get_mcp_tool(
                name="toolbox",
                url=toolbox_url,
                approval_mode="never_require",
            ))
        except Exception as exc:
            logger.warning("Failed to register Toolbox MCP: %s", exc)
    else:
        logger.warning("TOOLBOX_MCP_URL not set — agent will have no tools")

    # --- Skills ---
    skills_provider = None
    if SKILLS_DIR.is_dir():
        skills_provider = SkillsProvider.from_paths(
            skill_paths=str(SKILLS_DIR),
        )
        logger.info("Loaded skills from %s", SKILLS_DIR)

    agent = Agent(
        client=client,
        name="fibey",
        instructions=_load_system_prompt(),
        tools=tools,
        context_providers=[skills_provider] if skills_provider else None,
        default_options={"store": False},
    )

    server = ResponsesHostServer(agent)
    server.run()


if __name__ == "__main__":
    main()
