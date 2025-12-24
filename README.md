# A2A Playlist Demo (Ollama + Qwen)

A basic agent-to-agent demo using the Google A2A Python SDK. You talk to the **Playlist Orchestrator**, which calls the **Track Scout** agent to get suggestions and then composes a playlist.

## Prereqs

- Python 3.10+
- Ollama running locally
- A Qwen model pulled (example below)

```bash
ollama pull qwen3:8b
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the agents

Terminal 1 (Track Scout):

```bash
python track_scout_agent.py
```

Terminal 2 (Playlist Orchestrator):

```bash
python playlist_agent.py
```

## Interact

Terminal 3:

```bash
python client.py "Upbeat indie pop for a road trip"
```

## Config

Environment variables you can override:

- `OLLAMA_URL` (default `http://16.145.98.73:11434`)
- `OLLAMA_MODEL` (default `qwen3:8b`)
- `SCOUT_PORT` (default `9101`)
- `SCOUT_URL` (default `http://localhost:9101/`)
- `ORCH_PORT` (default `9100`)
- `ORCH_URL` (default `http://localhost:9100/`)
- `SCOUT_PUBLIC_URL` / `ORCH_PUBLIC_URL` (agent card URL if you need to expose externally)

## One-command demo

This starts both agents in the background, runs the client, then shuts the agents down.

```bash
./run_demo.sh "Short chill playlist, 10 tracks"
```

Logs (override via env vars if you want):

- `SCOUT_LOG` (default `/tmp/a2a_track_scout.log`)
- `ORCH_LOG` (default `/tmp/a2a_playlist_orch.log`)
