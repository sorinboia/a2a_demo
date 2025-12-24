import asyncio
import os
import sys

from a2a.client import ClientConfig, ClientFactory
from a2a.client.helpers import create_text_message_object
from a2a.types import Message, TransportProtocol
from a2a.utils.message import get_message_text


ORCH_URL = os.getenv("ORCH_URL", "http://localhost:9100/")


async def run(prompt: str) -> None:
    client_config = ClientConfig(
        supported_transports=[TransportProtocol.http_json.value]
    )
    client = await ClientFactory.connect(ORCH_URL, client_config=client_config)
    message = create_text_message_object(content=prompt)

    try:
        async for event in client.send_message(message):
            if isinstance(event, Message):
                text = get_message_text(event)
                if text:
                    print(text)
    finally:
        await client.close()


def main() -> None:
    prompt = " ".join(sys.argv[1:]).strip()
    if not prompt:
        prompt = input("Playlist request: ").strip()
    if not prompt:
        print("Please provide a request.")
        return

    asyncio.run(run(prompt))


if __name__ == "__main__":
    main()
