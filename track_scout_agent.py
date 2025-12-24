import os

import uvicorn
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.apps.rest import A2ARESTFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill, TransportProtocol
from a2a.utils import new_agent_text_message

from ollama_client import ollama_chat


HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("SCOUT_PORT", "9101"))
PUBLIC_URL = os.getenv("SCOUT_PUBLIC_URL", f"http://localhost:{PORT}/")


class TrackScoutExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_input = (context.get_user_input() or "").strip()
        if not user_input:
            await event_queue.enqueue_event(
                new_agent_text_message(
                    "Tell me a mood, genre, or activity and I will suggest tracks."
                )
            )
            return

        system_prompt = (
            "You are Track Scout. Suggest 10-12 tracks based on the user's request. "
            "Return only a plain list with one track per line in the form 'Artist - Title'. "
            "No extra commentary."
        )

        try:
            suggestions = await ollama_chat(user_input, system_prompt=system_prompt)
        except Exception as exc:  # pragma: no cover - demo fallback
            await event_queue.enqueue_event(
                new_agent_text_message(f"Ollama error: {exc}")
            )
            return

        await event_queue.enqueue_event(new_agent_text_message(suggestions))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise Exception("Cancel not supported")


def build_app():
    agent_card = AgentCard(
        name="Track Scout",
        description="Suggests tracks that match a playlist request.",
        url=PUBLIC_URL,
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=True),
        preferred_transport=TransportProtocol.http_json.value,
        default_input_modes=["text"],
        default_output_modes=["text"],
        skills=[
            AgentSkill(
                id="suggest_tracks",
                name="Suggest tracks",
                description="Provide track suggestions for a playlist request.",
                tags=["music", "playlist"],
                examples=["Upbeat indie pop for a road trip"],
            )
        ],
    )

    request_handler = DefaultRequestHandler(
        agent_executor=TrackScoutExecutor(),
        task_store=InMemoryTaskStore(),
    )

    app_builder = A2ARESTFastAPIApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
    return app_builder.build()


if __name__ == "__main__":
    uvicorn.run(build_app(), host=HOST, port=PORT)
