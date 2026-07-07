# Voice split deployment (staging)

Run the main app and voice stack on separate VPS instances without changing the monolithic `docker-compose.staging.yml` workflow.

## Architecture

| VPS | Compose file | Stack name | Role |
|-----|--------------|------------|------|
| 12 vCPU / 48 GB | `docker-compose.main.staging.yml` | `aria-staging-main` | Postgres, backend, frontend, nginx, local Ollama (analysis) |
| 4 vCPU / 8 GB | `docker-compose.voice.staging.yml` | `aria-staging-voice` | LiveKit, SIP, speech-service, voice-agent |

Monolithic staging (`docker-compose.staging.yml`) remains valid for single-host deployments.

## Cross-VPS wiring

**Main → Voice**

- `VOICE_AGENT_URL=http://<voice-vps-public-ip>:8002`
- Backend calls `POST /dispatch` on the voice agent to start outbound screening calls.

**Voice → Main**

- `ARIA_BACKEND_URL=http://<main-vps-ip-or-domain>` (or `https://` if TLS terminates on main nginx)
- `INTERNAL_SERVICE_SECRET` must match on both stacks (voice agent sends `X-Internal-Secret` to `/api/voice/internal/*`).

Generate a shared secret:

```bash
openssl rand -hex 32
```

## Portainer stacks

### Main (`aria-staging-main`)

1. Paste `docker-compose.main.staging.yml`.
2. Set env from `.env.staging.main.example`.
3. Ensure the voice VPS can reach main on port 80/443 if voice needs HTTPS callbacks (internal routes use the secret, not IP allowlists).

### Voice (`aria-staging-voice`)

1. Paste `docker-compose.voice.staging.yml`.
2. Set env from `.env.staging.voice.example`.
3. Set `STAGING_LIVEKIT_NODE_IP` to this VPS public IP.
4. Open firewall:
   - TCP: `7890`, `7891`, `8002`, `5060`
   - UDP: `7892`, `10000-10100`, `50000-50200`, `5060`

## Resource limits (voice VPS)

- `MAX_CONCURRENT_CALLS=1` — reject a second outbound call when one screen is active (4-core CPU).
- `STT_ENGINE=faster_whisper`, `STT_MODEL=tiny`, `STT_COMPUTE_TYPE=int8` — lower RAM and latency vs OpenAI Whisper.
- Voice LLM stays on Ollama Cloud (`OLLAMA_MODEL_VOICE=qwen3.5:cloud`); analysis LLM runs locally on main (`qwen2.5:3b`).

## Health checks

| Service | URL |
|---------|-----|
| Main backend | `GET /health` via nginx |
| Voice agent | `GET http://<voice-ip>:8002/health` — shows `active_calls`, `max_concurrent_calls` |
| Speech | `GET http://speech-service:8001/health` (from voice network) — shows `stt_engine`, `stt_model` |

## Smoke test

1. Deploy main stack; confirm Ollama warmup pulled `qwen2.5:3b`.
2. Deploy voice stack; confirm `/health` on port 8002.
3. From the UI, trigger one outbound voice screen.
4. Confirm transcript updates in backend and analysis completes on main.

## Upgrade path

When traffic grows, move voice to a 6 vCPU / 12 GB VPS and raise `MAX_CONCURRENT_CALLS` to `2`.

## Docker images

After code changes to `app/speech_service` or `app/voice_agent`, rebuild and push:

- `revanth2245/resume-speech-service:staging`
- `revanth2245/resume-voice-agent:staging`

Watchtower on each stack rolls staging-tagged images automatically.
