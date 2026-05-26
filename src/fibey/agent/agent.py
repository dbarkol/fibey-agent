"""
Single agent definition with Foundry Toolbox MCP connection.

The agent calls the Toolbox as one MCP endpoint; the Toolbox dispatches
to individual tools (FoundryIQ, Work Orders OpenAPI, Inventory MCP) behind
the scenes.  When the Toolbox is configured, FoundryIQ provides knowledge
base retrieval; otherwise a local Azure AI Search function tool is used
as a fallback.
"""

import asyncio
import os
import json
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
    FileSkillsSource,
    FunctionTool,
    MCPStreamableHTTPTool,
    ResponseStream,
    SkillsProvider,
)
from agent_framework.foundry import FoundryChatClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "system_prompt.md"
SKILLS_PATH = Path(__file__).parent / "skills"
_TOKEN_SCOPE = "https://ai.azure.com/.default"

# Azure AI Search configuration for direct KB queries
_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "")
_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX", "foundry-iq-docs-index")
_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY", "")


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


async def knowledge_base_search(query: str, top: int = 5) -> str:
    """Search the fiber optics field operations knowledge base.

    Searches across procedures, safety protocols, troubleshooting guides,
    equipment specs, cable types, installation standards, OTDR testing,
    and network architecture documentation.

    Args:
        query: The search query describing what you need to find.
        top: Maximum number of results to return (default 5).

    Returns:
        JSON string with search results including document name and content.
    """
    if not _SEARCH_API_KEY:
        return json.dumps({"error": "AZURE_SEARCH_API_KEY not configured"})

    search_url = f"{_SEARCH_ENDPOINT}/indexes/{_SEARCH_INDEX}/docs/search?api-version=2024-07-01"
    payload = {
        "search": query,
        "queryType": "semantic",
        "semanticConfiguration": "default",
        "top": top,
        "select": "content,metadata_storage_name",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            search_url,
            json=payload,
            headers={"api-key": _SEARCH_API_KEY, "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

    results = []
    for doc in data.get("value", []):
        results.append({
            "source": doc.get("metadata_storage_name", "unknown"),
            "content": doc.get("content", ""),
        })

    return json.dumps({"results": results, "count": len(results)})


def _create_kb_search_tool() -> FunctionTool | None:
    """Create the knowledge base search tool if search is configured."""
    if not _SEARCH_API_KEY:
        logger.warning("AZURE_SEARCH_API_KEY not set — running without KB search")
        return None

    return FunctionTool(
        name="knowledge_base",
        description=(
            "Search the fiber optics field operations knowledge base. "
            "Covers: splicing procedures, safety protocols, OTDR testing, "
            "cable types, equipment specs, installation standards, "
            "network architecture, and troubleshooting guides."
        ),
        func=knowledge_base_search,
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

    # Only add the local KB tool when Toolbox is NOT configured
    # (Toolbox provides knowledge_base via azure_ai_search / FoundryIQ)
    if not toolbox_mcp:
        kb_tool = _create_kb_search_tool()
        if kb_tool:
            tools.append(kb_tool)

    skills_provider = None
    if SKILLS_PATH.is_dir():
        skills_source = FileSkillsSource(SKILLS_PATH)
        skills_provider = SkillsProvider(skills_source)

    agent = Agent(
        client=client,
        name="fibey",
        instructions=_load_system_prompt(),
        tools=tools,
        context_providers=[skills_provider] if skills_provider else None,
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
        seen_skill_loads: set[str] = set()  # dedupe repeated load_skill for same skill
        seen_tool_args: set[str] = set()    # dedupe repeated tool calls with same args
        call_id_to_name: dict[str, str] = {}
        pending_args: dict[str, str] = {}
        suppressed_call_ids: set[str] = set()  # call_ids whose events should be hidden

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
                        # Accumulate arguments across streaming chunks
                        raw_args = getattr(content, "arguments", None) or ""
                        if isinstance(raw_args, dict):
                            import json as _json
                            raw_args = _json.dumps(raw_args)
                        if call_id not in pending_args:
                            pending_args[call_id] = raw_args
                            # Try to detect duplicates early (works when args arrive in one chunk)
                            skip = False
                            if tool_name == "load_skill":
                                try:
                                    parsed = _json.loads(raw_args) if raw_args else {}
                                    skill_key = parsed.get("skill_name", "")
                                except Exception:
                                    skill_key = ""
                                if skill_key and skill_key in seen_skill_loads:
                                    skip = True
                                elif skill_key:
                                    seen_skill_loads.add(skill_key)
                            elif raw_args:
                                try:
                                    _json.loads(raw_args)  # only dedup if args are complete JSON
                                    tool_args_key = f"{tool_name}::{raw_args}"
                                    if tool_args_key in seen_tool_args:
                                        skip = True
                                        suppressed_call_ids.add(call_id)
                                except (ValueError, TypeError):
                                    pass  # incomplete args, can't dedup yet
                            if not skip:
                                # Emit an early "running" activity so the UI shows a spinner
                                yield {
                                    "type": "activity",
                                    "tool": tool_name,
                                    "call_id": call_id,
                                    "status": "running",
                                    "detail": f"Calling {tool_name}...",
                                }
                        else:
                            pending_args[call_id] += raw_args

                    elif ctype in ("mcp_server_tool_result", "function_result"):
                        call_id = getattr(content, "call_id", None) or ""
                        tool_name = call_id_to_name.get(call_id) or getattr(content, "tool_name", None) or getattr(content, "name", None) or "tool"

                        # Emit the "running" activity with full accumulated args
                        if call_id not in seen_calls:
                            seen_calls.add(call_id)
                            args_str = pending_args.get(call_id, "")
                            import json as _json

                            # Suppress duplicate load_skill for same skill name
                            if tool_name == "load_skill":
                                try:
                                    parsed = _json.loads(args_str) if args_str else {}
                                    skill_name = parsed.get("skill_name", "")
                                except Exception:
                                    skill_name = ""
                                if skill_name and skill_name in seen_skill_loads:
                                    seen_results.add(call_id)
                                    suppressed_call_ids.add(call_id)
                                    continue
                                if skill_name:
                                    seen_skill_loads.add(skill_name)
                                    detail = f"Loading skill: {skill_name}"
                                else:
                                    detail = f"Calling {tool_name}..."
                            else:
                                # Suppress duplicate tool calls with identical name+args
                                tool_args_key = f"{tool_name}::{args_str}"
                                if tool_args_key in seen_tool_args:
                                    seen_results.add(call_id)
                                    suppressed_call_ids.add(call_id)
                                    continue
                                seen_tool_args.add(tool_args_key)

                                detail = f"Calling {tool_name}..."
                                try:
                                    parsed = _json.loads(args_str) if args_str else {}
                                    if isinstance(parsed, dict):
                                        for key in ("work_order_id", "part_id", "query"):
                                            val = parsed.get(key)
                                            if val:
                                                detail = f"Calling {tool_name} ({key}={val})"
                                                break
                                except Exception:
                                    pass
                            yield {
                                "type": "activity",
                                "tool": tool_name,
                                "call_id": call_id,
                                "status": "running",
                                "detail": detail,
                                "args": args_str,
                            }

                        # Emit the "complete" activity
                        if call_id not in seen_results:
                            seen_results.add(call_id)
                            yield {
                                "type": "activity",
                                "tool": tool_name,
                                "call_id": call_id,
                                "status": "complete",
                                "detail": f"Completed {tool_name}",
                            }

                    else:
                        # Log unknown content types for debugging
                        import logging
                        logging.getLogger(__name__).debug(
                            "Unknown content type: %s attrs=%s",
                            ctype,
                            {k: str(v)[:100] for k, v in vars(content).items()} if hasattr(content, '__dict__') else str(content)[:200]
                        )

