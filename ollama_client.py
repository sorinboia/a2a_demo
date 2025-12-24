import os
from typing import Optional

import httpx


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://16.145.98.73:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")


async def ollama_chat(
    user_prompt: str,
    *,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    host_header: Optional[str] = None,
    temperature: Optional[float] = 0.7,
) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    payload = {
        "model": model or OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }
    if temperature is not None:
        payload["options"] = {"temperature": temperature}

    headers = {"Host": host_header} if host_header else None
    async with httpx.AsyncClient(timeout=60, headers=headers) as client:
        response = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()

    return data["message"]["content"].strip()
