import os

import uvicorn
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

from ollama_client import ollama_chat


HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("ORCH_PORT", "9100"))
PUBLIC_URL = os.getenv("ORCH_PUBLIC_URL", f"http://localhost:{PORT}/")
SCOUT_PORT = os.getenv("SCOUT_PORT", "9101")
SCOUT_URL = os.getenv("SCOUT_URL", f"http://localhost:{SCOUT_PORT}/")


async def fetch_track_suggestions(user_prompt: str) -> str:
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

    return "\n".join(collected).strip()


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

        combined_prompt = (
            f"User request: {user_input}\n\n"
            f"Track suggestions from Track Scout:\n{scout_text}\n\n"
            "Create the final playlist now."
        )

        try:
            playlist = await ollama_chat(
                combined_prompt,
                system_prompt=system_prompt,
                temperature=0.6,
            )
        except Exception as exc:  # pragma: no cover - demo fallback
            await event_queue.enqueue_event(
                new_agent_text_message(f"Ollama error: {exc}")
            )
            return

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
