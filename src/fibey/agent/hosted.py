"""
Hosted-mode entrypoint for Foundry Agent Service.

In hosted mode, the agent is deployed as a container and runs via
ResponsesHostServer. The Toolbox MCP is registered via FoundryChatClient.
"""

import os
import logging
from pathlib import Path
from typing import AsyncGenerator

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "system_prompt.md"


def _load_system_prompt() -> str:
    if SYSTEM_PROMPT_PATH.exists():
        return SYSTEM_PROMPT_PATH.read_text()
    return "You are Fibey, a helpful AI assistant."


def create_hosted_agent() -> Agent:
    """Create the agent for Foundry hosted deployment."""
    client = FoundryChatClient()

    tools = []
    toolbox_url = os.getenv("TOOLBOX_MCP_URL", "")
    if toolbox_url:
        toolbox_mcp = client.get_mcp_tool(
            name="toolbox",
            url=toolbox_url,
            approval_mode="never_require",
        )
        tools.append(toolbox_mcp)

    agent = Agent(
        client=client,
        name="fibey",
        instructions=_load_system_prompt(),
        tools=tools,
    )

    return agent


async def run_hosted_agent(message: str, session: dict) -> AsyncGenerator[dict, None]:
    """
    Proxy to the Foundry-hosted agent and yield streaming events.

    In production, the hosted agent runs via ResponsesHostServer and this
    function is not called. This is used by the gateway when AGENT_MODE=hosted
    to proxy to the remote hosted agent endpoint.
    """
    project_endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT", "")
    agent_name = os.getenv("HOSTED_AGENT_NAME", "")

    if not project_endpoint or not agent_name:
        yield {
            "type": "delta",
            "content": "⚠️ Hosted mode requires FOUNDRY_PROJECT_ENDPOINT and HOSTED_AGENT_NAME environment variables.",
        }
        return

    # TODO: Implement Responses API proxy
    # 1. Create or reuse agent session via azure-ai-projects SDK
    # 2. Send message with session["agent_session_id"] and session["previous_response_id"]
    # 3. Stream response events, translating Responses API events to our SSE format
    # 4. Update session state

    yield {
        "type": "delta",
        "content": f"Hosted mode is configured for agent '{agent_name}' at '{project_endpoint}', but the Responses API proxy is not yet implemented.",
    }


def main():
    """Entrypoint for Foundry Agent Service container."""
    agent = create_hosted_agent()
    ResponsesHostServer(agent).run()


if __name__ == "__main__":
    main()
