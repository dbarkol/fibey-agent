import os
import uuid
import json
import logging
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI(title="Fibey Agent Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store
sessions: dict[str, dict] = {}

AGENT_MODE = os.getenv("AGENT_MODE", "local")


def _sse(event: str, data: dict | str) -> str:
    """Format a server-sent event."""
    payload = json.dumps(data) if isinstance(data, dict) else data
    return f"event: {event}\ndata: {payload}\n\n"


async def _run_local(message: str, session_id: str) -> AsyncGenerator[str, None]:
    """Run the agent locally and stream SSE events."""
    from fibey.agent.agent import run_agent

    session = sessions.setdefault(session_id, {})

    try:
        async for event in run_agent(message, session):
            if event["type"] == "delta":
                yield _sse("delta", {"content": event["content"]})
            elif event["type"] == "activity":
                yield _sse("activity", {
                    "tool": event.get("tool", ""),
                    "call_id": event.get("call_id", ""),
                    "status": event.get("status", ""),
                    "detail": event.get("detail", ""),
                    "args": event.get("args", ""),
                    "result": event.get("result", ""),
                })
            elif event["type"] == "citation":
                yield _sse("citation", {
                    "source": event.get("source", ""),
                    "url": event.get("url", ""),
                })
    except Exception as e:
        logger.exception("Agent error")
        yield _sse("error", {"message": str(e)})

    yield _sse("done", "[DONE]")


async def _run_hosted(message: str, session_id: str) -> AsyncGenerator[str, None]:
    """Proxy to the Foundry-hosted agent.

    Note: When the agent is deployed as a hosted agent, it runs via
    ResponsesHostServer and clients talk to the Foundry Responses API
    directly — this gateway proxy is not used. This stub remains for
    local testing of the hosted mode configuration.
    """
    yield _sse("error", {
        "message": "Hosted mode is active. The agent runs via Foundry Responses API — "
                   "connect to the Foundry project endpoint directly, not through this gateway."
    })
    yield _sse("done", "[DONE]")


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    message = body.get("message", "")
    session_id = body.get("session_id", str(uuid.uuid4()))

    if AGENT_MODE == "hosted":
        generator = _run_hosted(message, session_id)
    else:
        generator = _run_local(message, session_id)

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Session-Id": session_id,
        },
    )


@app.post("/api/sessions/reset")
async def reset_session(request: Request):
    body = await request.json()
    session_id = body.get("session_id", "")
    sessions.pop(session_id, None)
    return {"status": "ok"}


@app.get("/api/health")
async def health():
    return {"status": "healthy", "mode": AGENT_MODE}
