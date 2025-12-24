import os
from typing import Optional

import httpx

from logging_utils import get_logger, resolve_url


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://16.145.98.73:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")

logger = get_logger("ollama")


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
    host, port, ips = resolve_url(OLLAMA_URL)
    logger.info(
        "POST %s/api/chat host=%s port=%s ips=%s model=%s temp=%s system_len=%s user_len=%s host_header=%s",
        OLLAMA_URL,
        host,
        port,
        ips,
        payload["model"],
        temperature,
        len(system_prompt or ""),
        len(user_prompt),
        host_header or "-",
    )

    async with httpx.AsyncClient(timeout=60, headers=headers) as client:
        response = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
        logger.info("Ollama response status=%s bytes=%s", response.status_code, len(response.content))
        response.raise_for_status()
        data = response.json()

    return data["message"]["content"].strip()
