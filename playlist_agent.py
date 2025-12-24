import json
import os
import re

import uvicorn
import httpx
from a2a.client import ClientConfig, ClientFactory
from a2a.client.helpers import create_text_message_object
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.apps.rest import A2ARESTFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill, Message, TransportProtocol
from a2a.utils import new_agent_text_message
from a2a.utils.message import get_message_text

from logging_utils import get_logger, is_verbose, resolve_url
from ollama_client import ollama_chat


HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("ORCH_PORT", "9100"))
PUBLIC_URL = os.getenv("ORCH_PUBLIC_URL", f"http://localhost:{PORT}/")
SCOUT_PORT = os.getenv("SCOUT_PORT", "9101")
SCOUT_URL = os.getenv("SCOUT_URL", f"http://localhost:{SCOUT_PORT}/")
ROUTER_MODE = os.getenv("ROUTER_MODE", "llm").lower()

logger = get_logger("playlist_orch")


async def fetch_track_suggestions(user_prompt: str) -> str:
    host, port, ips = resolve_url(SCOUT_URL)
    logger.info(
        "Calling Track Scout at %s host=%s port=%s ips=%s",
        SCOUT_URL,
        host,
        port,
        ips,
    )
    if is_verbose():
        logger.info("Track Scout request payload=%s", {"prompt": user_prompt})
    client_config = ClientConfig(
        supported_transports=[TransportProtocol.http_json.value]
    )
    client = await ClientFactory.connect(SCOUT_URL, client_config=client_config)
    message = create_text_message_object(content=user_prompt)
    collected = []

    try:
        async for event in client.send_message(message):
            if isinstance(event, Message):
                text = get_message_text(event)
                if text:
                    collected.append(text)
    finally:
        await client.close()

    result = "\n".join(collected).strip()
    logger.info("Track Scout returned %s chars", len(result))
    return result


async def fetch_scout_agent_card() -> dict:
    url = f"{SCOUT_URL.rstrip('/')}/.well-known/agent-card.json"
    host, port, ips = resolve_url(url)
    logger.info("Fetching Track Scout agent card from %s host=%s port=%s ips=%s", url, host, port, ips)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    except Exception as exc:
        logger.warning("Failed to fetch agent card: %s", exc)
        return {}


def _extract_json(text: str) -> dict | None:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    blob = match.group(0)
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        return None


async def should_use_track_scout(user_prompt: str) -> bool:
    card = await fetch_scout_agent_card()
    agent_info = {
        "name": card.get("name"),
        "description": card.get("description"),
        "url": card.get("url"),
        "skills": [
            {
                "name": skill.get("name"),
                "description": skill.get("description"),
                "examples": skill.get("examples", []),
            }
            for skill in card.get("skills", [])
        ],
    }

    system_prompt = (
        "You are a routing assistant. Decide whether to call the Track Scout agent "
        "to help build a playlist. Respond with strict JSON only: "
        '{"use_scout": true/false, "reason": "short reason"}'
    )
    user_prompt_text = (
        f"User request: {user_prompt}\n\n"
        f"Available agent:\n{json.dumps(agent_info, ensure_ascii=True)}"
    )

    try:
        response_text = await ollama_chat(
            user_prompt_text,
            system_prompt=system_prompt,
            host_header="router.lab",
            temperature=0.0,
        )
    except Exception as exc:
        logger.warning("Router call failed: %s", exc)
        return True

    data = _extract_json(response_text) or {}
    decision = data.get("use_scout")
    if isinstance(decision, bool):
        logger.info("Router decision use_scout=%s reason=%s", decision, data.get("reason", "-"))
        return decision

    logger.warning("Router returned unparseable response: %s", response_text)
    return True


class PlaylistOrchestratorExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_input = (context.get_user_input() or "").strip()
        if not user_input:
            await event_queue.enqueue_event(
                new_agent_text_message(
                    "Tell me the vibe or occasion and I will build a playlist."
                )
            )
            return
        logger.info("Received request: %s", user_input)

        use_scout = True
        if ROUTER_MODE == "never":
            use_scout = False
        elif ROUTER_MODE == "llm":
            use_scout = await should_use_track_scout(user_input)
        logger.info("Router mode=%s use_scout=%s", ROUTER_MODE, use_scout)

        scout_text = ""
        if use_scout:
            try:
                scout_text = await fetch_track_suggestions(user_input)
            except Exception as exc:  # pragma: no cover - demo fallback
                await event_queue.enqueue_event(
                    new_agent_text_message(f"Track Scout error: {exc}")
                )
                return

        system_prompt = (
            "You are Playlist Builder. Use the track suggestions to craft a final playlist. "
            "Output format: Title line, short one-sentence description, then a numbered list "
            "of 10 tracks in 'Artist - Title — reason' format. Keep it concise."
        )

        if use_scout:
            combined_prompt = (
                f"User request: {user_input}\n\n"
                f"Track suggestions from Track Scout:\n{scout_text}\n\n"
                "Create the final playlist now."
            )
        else:
            combined_prompt = (
                f"User request: {user_input}\n\n"
                "Track Scout was not used for this request.\n\n"
                "Create the final playlist now."
            )

        try:
            playlist = await ollama_chat(
                combined_prompt,
                system_prompt=system_prompt,
                host_header="agent2.lab",
                temperature=0.6,
            )
        except Exception as exc:  # pragma: no cover - demo fallback
            await event_queue.enqueue_event(
                new_agent_text_message(f"Ollama error: {exc}")
            )
            return

        logger.info("Sending %s chars of playlist", len(playlist))
        await event_queue.enqueue_event(new_agent_text_message(playlist))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise Exception("Cancel not supported")


def build_app():
    agent_card = AgentCard(
        name="Playlist Orchestrator",
        description="Coordinates with another agent to build a music playlist.",
        url=PUBLIC_URL,
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=True),
        preferred_transport=TransportProtocol.http_json.value,
        default_input_modes=["text"],
        default_output_modes=["text"],
        skills=[
            AgentSkill(
                id="build_playlist",
                name="Build a playlist",
                description="Creates a playlist using another agent's suggestions.",
                tags=["music", "playlist", "a2a"],
                examples=["Late-night synthwave for coding"],
            )
        ],
    )

    request_handler = DefaultRequestHandler(
        agent_executor=PlaylistOrchestratorExecutor(),
        task_store=InMemoryTaskStore(),
    )

    app_builder = A2ARESTFastAPIApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
    return app_builder.build()


if __name__ == "__main__":
    uvicorn.run(build_app(), host=HOST, port=PORT)
