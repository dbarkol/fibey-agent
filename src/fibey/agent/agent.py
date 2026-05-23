"""
Single agent definition with Foundry Toolbox MCP connection.

The agent calls the Toolbox as one MCP endpoint; the Toolbox dispatches
to individual tools (FoundryIQ, WorkIQ, custom MCP, FabricIQ) behind the scenes.
"""

import asyncio
import os
import logging
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, AsyncGenerator

import httpx
from azure.identity import AzureCliCredential, DefaultAzureCredential
from agent_framework import (
    Agent,
    AgentResponseUpdate,
    AgentSession,
    MCPStreamableHTTPTool,
    ResponseStream,
)
from agent_framework.foundry import FoundryChatClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "system_prompt.md"
_TOKEN_SCOPE = "https://ai.azure.com/.default"


def _load_system_prompt() -> str:
    """Load the system prompt from markdown file."""
    if SYSTEM_PROMPT_PATH.exists():
        return SYSTEM_PROMPT_PATH.read_text()
    return "You are Fibey, a helpful AI assistant."


def _get_credential():
    """Get Azure credential, preferring CLI for local dev."""
    try:
        cred = AzureCliCredential()
        cred.get_token(_TOKEN_SCOPE)
        return cred
    except Exception:
        return DefaultAzureCredential()


def _get_token_sync(credential) -> str:
    return credential.get_token(_TOKEN_SCOPE).token


class _AzureAuthTransport(httpx.AsyncHTTPTransport):
    """httpx transport that injects a bearer token on every request,
    including the MCP initialize handshake."""

    def __init__(self, credential, **kwargs: Any):
        super().__init__(**kwargs)
        self._credential = credential

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        loop = asyncio.get_running_loop()
        token = await loop.run_in_executor(None, _get_token_sync, self._credential)
        request.headers["Authorization"] = f"Bearer {token}"
        request.headers["Foundry-Features"] = "Toolboxes=V1Preview"
        return await super().handle_async_request(request)


def _create_toolbox_mcp(credential) -> MCPStreamableHTTPTool | None:
    """Create the Toolbox MCP tool if endpoint is configured."""
    toolbox_url = os.getenv("TOOLBOX_MCP_URL", "")
    if not toolbox_url:
        logger.warning("TOOLBOX_MCP_URL not set — running without Toolbox")
        return None

    auth_http_client = httpx.AsyncClient(
        transport=_AzureAuthTransport(credential),
        timeout=httpx.Timeout(60.0, connect=10.0),
    )

    def header_provider(kwargs: dict[str, Any] | None = None) -> dict[str, str]:
        token = credential.get_token(_TOKEN_SCOPE).token
        return {
            "Authorization": f"Bearer {token}",
            "Foundry-Features": "Toolboxes=V1Preview",
        }

    return MCPStreamableHTTPTool(
        name="toolbox",
        url=toolbox_url,
        http_client=auth_http_client,
        header_provider=header_provider,
        load_prompts=False,
    )


def create_agent() -> tuple[Agent, list]:
    """Create the agent with Foundry client and Toolbox MCP connection."""
    credential = _get_credential()

    client = FoundryChatClient(
        credential=credential,
    )

    tools = []
    toolbox_mcp = _create_toolbox_mcp(credential)
    if toolbox_mcp:
        tools.append(toolbox_mcp)

    agent = Agent(
        client=client,
        name="fibey",
        instructions=_load_system_prompt(),
        tools=tools,
    )

    return agent, tools


async def run_agent(message: str, session: dict) -> AsyncGenerator[dict, None]:
    """
    Run the agent and yield streaming events.

    Events yielded:
    - {"type": "delta", "content": "..."}
    - {"type": "activity", "tool": "...", "status": "...", "detail": "..."}
    - {"type": "citation", "source": "...", "url": "..."}
    """
    agent, tools = create_agent()

    agent_session = session.get("agent_session")
    if not agent_session:
        agent_session = AgentSession()
        session["agent_session"] = agent_session

    async with AsyncExitStack() as stack:
        # Initialize MCP tools
        for tool in tools:
            if isinstance(tool, MCPStreamableHTTPTool):
                await stack.enter_async_context(tool)

        stream = agent.run(
            message,
            stream=True,
            session=agent_session,
        )

        # Track tool calls to deduplicate streaming repeats and map results back
        seen_calls: set[str] = set()
        seen_results: set[str] = set()
        call_id_to_name: dict[str, str] = {}

        async for update in stream:
            update: AgentResponseUpdate

            if update.contents:
                for content in update.contents:
                    ctype = content.type

                    if ctype == "text":
                        yield {"type": "delta", "content": content.text or ""}

                    elif ctype in ("mcp_server_tool_call", "function_call"):
                        tool_name = getattr(content, "tool_name", None) or getattr(content, "name", None) or "tool"
                        call_id = getattr(content, "call_id", None) or tool_name
                        call_id_to_name[call_id] = tool_name
                        if call_id not in seen_calls:
                            seen_calls.add(call_id)
                            yield {
                                "type": "activity",
                                "tool": tool_name,
                                "status": "running",
                                "detail": f"Calling {tool_name}...",
                            }

                    elif ctype in ("mcp_server_tool_result", "function_result"):
                        call_id = getattr(content, "call_id", None) or ""
                        tool_name = call_id_to_name.get(call_id) or getattr(content, "tool_name", None) or getattr(content, "name", None) or "tool"
                        if call_id not in seen_results:
                            seen_results.add(call_id)
                            yield {
                                "type": "activity",
                                "tool": tool_name,
                                "status": "complete",
                                "detail": f"Completed {tool_name}",
                            }

