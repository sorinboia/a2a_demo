# A2A Demo Agent Instructions

This repo is a minimal Agent‑to‑Agent (A2A) demo using the Google A2A Python SDK and Ollama (Qwen). You talk to the **Playlist Orchestrator** agent, which calls the **Track Scout** agent to get suggestions and then builds a playlist.

## Architecture

- `track_scout_agent.py`: A2A server that suggests tracks.
- `playlist_agent.py`: A2A server that orchestrates with Track Scout and composes the final playlist.
- `client.py`: Simple CLI to talk to the Playlist Orchestrator.
- `ollama_client.py`: Shared helper to call the Ollama chat API.

## Prereqs

- Python 3.10+
- Ollama reachable at the default endpoint
- Qwen model available on Ollama

Defaults in `ollama_client.py`:

- `OLLAMA_URL`: `http://16.145.98.73:11434`
- `OLLAMA_MODEL`: `qwen3:8b`

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run (one‑command)

```bash
./run_demo.sh "Short chill playlist, 10 tracks"
```

This starts both agents in the background, runs the client, and then shuts the agents down.

Logs:

- `SCOUT_LOG` (default `/tmp/a2a_track_scout.log`)
- `ORCH_LOG` (default `/tmp/a2a_playlist_orch.log`)

## Run (manual)

Terminal 1:

```bash
python track_scout_agent.py
```

Terminal 2:

```bash
python playlist_agent.py
```

Terminal 3:

```bash
python client.py "Upbeat indie pop for a road trip"
```

## Environment overrides

```bash
export OLLAMA_URL="http://16.145.98.73:11434"
export OLLAMA_MODEL="qwen3:8b"
export SCOUT_PORT=9101
export ORCH_PORT=9100
```

## Ports

- Track Scout: `9101`
- Playlist Orchestrator: `9100`

## Notes

- The A2A servers are configured for REST transport (`HTTP+JSON`).
- If you change ports, update `SCOUT_PORT`/`ORCH_PORT` (or `SCOUT_URL`/`ORCH_URL`).

## Troubleshooting

- If the client hangs, check the agent logs in `/tmp/` and verify Ollama is reachable.
- If Ollama returns empty responses, the model may be configured to return only “thinking”; try another Qwen tag or adjust the system prompt in `track_scout_agent.py` / `playlist_agent.py`.
