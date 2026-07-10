# LiveKit Cloud Voice — Option B (full cloud)

Move all voice screening to LiveKit Cloud for lower-latency STT/TTS (Deepgram + Cartesia)
and managed agent hosting. ARIA screening logic (kit-driven orchestrator) is preserved.

## Architecture

```
Backend scheduler (LIVEKIT_CLOUD_VOICE=1)
    → LiveKit Cloud API: create room + SIP dial + dispatch agent "ARIA"
        → Cloud Agent (cloud_agent.py)
            → Deepgram Nova-2 STT (streaming)
            → KitDrivenOrchestrator (ARIA screening script)
            → Cartesia Sonic TTS
            → Callback → ARIA backend /api/interviews/internal/complete
```

**Removed from VPS when cloud mode is on:** `livekit`, `livekit-sip`, `livekit-redis`, `speech-service`, `voice-agent`

## Prerequisites

1. LiveKit Cloud project (ARIA) with API keys
2. Agent created in dashboard named **ARIA** (must match `LIVEKIT_AGENT_NAME`)
3. Twilio SIP trunk pointed at your LiveKit Cloud SIP URI (`sip:xxxxx.sip.livekit.cloud`)
4. LiveKit CLI installed: https://docs.livekit.io/home/cli/

## Step 1 — Deploy the cloud agent

From the repo root:

```bash
# Link project (one-time)
lk cloud auth
lk project list

# Set secrets on the cloud agent
lk agent update-secrets \
  --secrets "ARIA_BACKEND_URL=https://your-aria-domain.com" \
  --secrets "INTERNAL_SERVICE_SECRET=your-shared-secret" \
  --secrets "GEMINI_API_KEY=your-gemini-key"

# Deploy
lk agent deploy --config livekit.toml
```

Or use **Deploy agent** in the LiveKit dashboard after connecting your repo.

### Pipeline settings (dashboard → Models & Voice)

Match your dashboard configuration:

| Setting | Recommended |
|---------|-------------|
| Pipeline mode | STT-LLM-TTS pipeline |
| STT | Deepgram Nova-2, English |
| TTS | Cartesia Sonic 1, Blake (or preferred voice) |
| LLM | Gemma 3 27B (fallback; kit mode bypasses per-turn LLM) |
| Noise cancellation | BVC Telephony (enabled in code for SIP) |

Env vars on the cloud agent (optional overrides):

```env
LIVEKIT_AGENT_NAME=ARIA
LIVEKIT_STT_MODEL=deepgram/nova-2
LIVEKIT_TTS_MODEL=cartesia/sonic-1
LIVEKIT_TTS_VOICE=<cartesia-voice-id>
```

## Step 2 — Configure SIP in LiveKit Cloud

1. LiveKit dashboard → **Telephony** → **SIP trunks**
2. Create outbound trunk with your Twilio termination address
3. Link your Twilio phone number

The backend/agent will also auto-create trunks via API if `SIP_*` env vars are set.

## Step 3 — Enable cloud dispatch on ARIA backend

On your main VPS `.env` / Portainer stack:

```env
LIVEKIT_CLOUD_VOICE=1
LIVEKIT_URL=wss://aria-tiq3bh9q.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret-min-32-chars
LIVEKIT_AGENT_NAME=ARIA

# Twilio SIP (same as before)
SIP_TRUNK_ID=twilio-aria
SIP_OUTBOUND_NUMBER=+1xxxxxxxxxx
SIP_TERMINATION_ADDRESS=your.pstn.twilio.com
SIP_AUTH_USERNAME=aria-livekit
SIP_AUTH_PASSWORD=your-twilio-sip-password

# Backend URL the cloud agent calls back to
ARIA_BACKEND_URL=https://your-aria-domain.com
INTERNAL_SERVICE_SECRET=your-shared-secret
```

Remove or stop these Docker services on the VPS:

- `staging-livekit`
- `staging-livekit-sip`
- `staging-livekit-redis`
- `staging-speech-service`
- `staging-voice-agent`

## Step 4 — Test

1. In LiveKit dashboard → Agent → **Test agent** → Start call (browser test)
2. Schedule a screening call in ARIA → verify session goes `ringing` → `in_progress` → `completed`
3. Check LiveKit **Session** / **Metrics** tabs for latency and transcripts

## Why this is faster and more natural

| Improvement | Source |
|-------------|--------|
| Streaming STT | Deepgram Nova-2 via LiveKit Inference (words while speaking) |
| Low-latency TTS | Cartesia Sonic (cloud-hosted, no VPS round-trip) |
| Better turn-taking | LiveKit VAD + endpointing (`min_endpointing_delay=0.4s`) |
| Phone noise handling | BVC Telephony noise cancellation |
| No cross-container hops | STT/TTS/agent colocated on LiveKit Cloud |

Kit-driven screening keeps **deterministic** question flow (reliable for hiring). Dynamic orchestrator still uses Gemini via `turn_planner.py` when no kit is available.

## Realtime model (optional upgrade)

For even lower latency, switch dashboard **Pipeline mode** to **Realtime model** (e.g. Gemini Live). That requires refactoring `cloud_agent.py` to use `google.beta.realtime.RealtimeModel` instead of the STT-LLM-TTS pipeline. Kit-driven deterministic flow is harder to preserve in realtime mode — test thoroughly before switching.

## Rollback

Set `LIVEKIT_CLOUD_VOICE=0` and restart the self-hosted voice stack (`docker-compose.main.staging.yml` voice services).

## Files

| File | Purpose |
|------|---------|
| `app/voice_agent/cloud_agent.py` | LiveKit Cloud agent entrypoint |
| `app/voice_agent/livekit_dispatch.py` | Room + SIP + agent dispatch API |
| `app/backend/services/livekit_cloud_dispatch.py` | Backend cloud dispatch wrapper |
| `app/voice_agent/Dockerfile.cloud` | Container for `lk agent deploy` |
| `livekit.toml` | LiveKit CLI deploy config |
