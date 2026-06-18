# Voice Screening Bot — Full Implementation Plan

## Confirmed Architecture Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Telephony | LiveKit SIP (PSTN) | Bot calls candidate's phone; ~$0.004/min; supports inbound callbacks |
| STT | Parakeet TDT 1.1B | Fastest open-source streaming STT; ~2 GB RAM; English-only |
| TTS | Kokoro 82M (Phase 1) → Orpheus 1B (Phase 6) | Kokoro for fast CPU validation; Orpheus for naturalness + voice cloning |
| VAD | Silero VAD v5 | Industry standard; 2 MB; negligible resources |
| LLM | Ollama Cloud (gemma4:31b) | Reuse existing; no infrastructure change |
| Orchestration | LiveKit Agents (Python) | One framework for SIP + STT + TTS + LLM + inbound routing |
| Infrastructure | VPS-first (CPU-only, 48 GB RAM, ~28 GB free) | Validate feature before GPU investment |
| Questions | Dynamic from JD must-have skills | Not pre-defined templates |
| Language | English only | Per earlier decision |
| Call duration | 5–7 minutes hard limit | Optimized for quick screening |
| Retry policy | 3-tier: 24h → 48h → escalate; callback cancels remaining retries | Per earlier decision |
| Compliance | Consent announcement, timezone-aware (9AM–6PM), DNC handling | Per earlier decision |
| Inbound calls | Candidate callback → check pending session → connect or redirect | Real-world edge case handling |
| Multi-tenant | Full customization per tenant (bot identity, phone, scheduling, compliance, retry) | SaaS requirement |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  VPS (48 GB RAM, 8 CPU, no GPU) — ~28 GB free                   │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  LiveKit Server (new, ~1 GB RAM)                           │ │
│  │  • WebRTC SFU + SIP trunking                               │ │
│  │  • Outbound PSTN calls + Inbound call routing              │ │
│  └──────────────┬─────────────────────────────────────────────┘ │
│                 │ SIP/PSTN                                       │
│                 ▼                                                │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Speech Service (new, ~4 GB RAM)                           │ │
│  │  • Parakeet TDT 1.1B (STT)                                 │ │
│  │  • Kokoro 82M → Orpheus 1B (TTS)                           │ │
│  │  • Silero VAD v5                                           │ │
│  └──────────────┬─────────────────────────────────────────────┘ │
│                 │ gRPC / HTTP                                    │
│                 ▼                                                │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Voice Agent — LiveKit Agents (new, ~2 GB RAM)             │ │
│  │  • Outbound Agent: full screening conversation             │ │
│  │  • Inbound Agent: callback handler (2-path)                │ │
│  │  • Conversation state machine (LangGraph-style)            │ │
│  └──────────────┬─────────────────────────────────────────────┘ │
│                 │ HTTP API                                       │
│                 ▼                                                │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  ARIA Backend (existing FastAPI)                           │ │
│  │  • Ollama Cloud (gemma4:31b) — conversation LLM            │ │
│  │  • JD parser → extract must-have skills → generate Qs      │ │
│  │  • Candidate management + scoring engine                   │ │
│  │  • VoiceTenantConfig (per-tenant settings)                 │ │
│  │  • PostgreSQL + Alembic                                    │ │
│  │  • Celery + Redis (call scheduling + retries)              │ │
│  └────────────────────────────────────────────────────────────┘ │
──────────────────────────────────────────────────────────────────┘
         │
         │ Outbound call (~$0.004/min via LiveKit SIP)
         │ Inbound call (candidate callback — same number)
         ▼
  Candidate's Phone Number
```

---

## New Database Models

### VoiceTenantConfig (one per tenant)
```
id, tenant_id (unique FK), bot_name, bot_voice_gender,
bot_voice_sample_url (nullable S3 URL),
outbound_phone_number (E.164), caller_id_name,
business_hours_start, business_hours_end,
allowed_days (JSON), timezone,
consent_script (nullable — default if null),
greeting_style (professional/casual/friendly),
call_duration_min (default 5), call_duration_max (default 7),
max_retries (default 3), retry_intervals (JSON: [24, 48]),
escalation_contact_id (FK → team_members, nullable),
assessment_detail_level (brief/full),
auto_update_status (bool, default true),
follow_up_aggressiveness (low/medium/high),
created_at, updated_at
```

### VoiceScreeningSession
```
id, tenant_id (FK), candidate_id (FK), jd_id (FK),
phone_number, direction (outbound/inbound),
callback_of_id (FK → self, nullable — links callback to original),
status (scheduled/ringing/in_progress/completed/failed/no_answer/voicemail),
scheduled_at, started_at, ended_at,
transcript_json, assessment_json,
duration_seconds, retry_count,
consent_recorded (bool), call_sid,
error_log (nullable), created_at, updated_at
```

### VoiceTranscriptEntry
```
id, session_id (FK), speaker (bot/candidate),
text, timestamp, audio_url (nullable)
```

---

## New Dependencies

### Python (requirements.txt)
```
livekit-agents>=0.12.0
livekit-api>=0.7.0
livekit-protocol>=0.6.0
torch>=2.1.0          # CPU-only for Parakeet + Kokoro
torchaudio>=2.1.0
transformers>=4.40.0
accelerate>=0.30.0
silero-vad>=5.0
```

### Docker Compose (new containers)
```yaml
livekit:         # LiveKit Server — ~1 GB RAM
speech-service:  # Parakeet + Kokoro + Silero — ~4 GB RAM
voice-agent:     # LiveKit Agent process — ~2 GB RAM
```
Total additional RAM: ~7 GB (fits in ~28 GB free)

---

## Task 1: Infrastructure + Voice Loop (Phase 1 — ~2 weeks)

**Goal**: Prove the bot can make a phone call and have a basic conversation.

### 1.1 Database Foundation
- Create `VoiceTenantConfig`, `VoiceScreeningSession`, `VoiceTranscriptEntry` SQLAlchemy models
- Alembic migration for all three tables
- Seed default `VoiceTenantConfig` for all existing tenants
- Basic CRUD API: `GET/PUT /api/voice/settings` (tenant-scoped, auth-protected)

### 1.2 Docker Compose Additions
- Add `livekit` service to `docker-compose.prod.yml` (LiveKit Server image)
- Add `speech-service` container (custom Dockerfile: Parakeet TDT + Kokoro + Silero VAD)
- Add `voice-agent` container (LiveKit Agents Python process)
- Configure Nginx proxy rules for LiveKit WebSocket endpoints
- Resource limits: livekit (1 GB), speech-service (4 GB), voice-agent (2 GB)

### 1.3 Speech Service
- Implement Parakeet TDT 1.1B STT endpoint (streaming audio → text)
- Implement Kokoro 82M TTS endpoint (text → audio stream)
- Implement Silero VAD v5 endpoint (audio → speech/silence events)
- Health check + model warmup on container start
- CPU-only inference with torch CPU backend

### 1.4 Voice Agent — Basic Outbound
- LiveKit Agents setup with SIP outbound capability
- Hardcoded test script: greeting → listen → respond → goodbye
- Connect to Ollama Cloud for LLM responses
- Test: bot calls a real phone number and completes a basic exchange

### 1.5 Inbound Call Routing
- Configure phone number for inbound calls (same number as outbound)
- LiveKit SIP inbound route → separate "inbound agent"
- Inbound agent: lookup caller number → check pending session → connect or redirect

### Deliverable
Bot can call a phone number, conduct a basic conversation, and handle a callback.

---

## Task 2: Conversation Intelligence (Phase 2 — ~3 weeks)

**Goal**: Bot conducts a real screening conversation using JD skills.

### 2.1 LangGraph Conversation State Machine
States and transitions:
- `GREETING` → "Hi, this is [bot_name] from [company]. Am I speaking with [candidate]?"
- `CONSENT` → Play tenant's consent script (or default). Must get verbal consent.
- `INTRODUCTION` → "I'm calling about the [role] position at [company]. Got a few minutes?"
- `SCREENING` → Ask questions dynamically generated from JD must-have skills
- `FOLLOW_UP` → Probe deeper based on answer quality (tenant's aggressiveness setting)
- `WRAP_UP` → "Any questions for me?" + next steps + goodbye
- `ANALYSIS` → Post-call: trigger structured assessment generation

Transitions driven by:
- Candidate responses (LLM evaluates in real-time)
- Time budget (5-7 min hard limit from tenant config)
- Silence detection (no response → gentle prompt → retry → end call)
- Interruption handling (candidate talks while bot speaks → bot stops)

### 2.2 Dynamic Question Generation
- Integrate with existing JD parser service
- Extract must-have skills from JD
- LLM generates 3-5 screening questions from skills (per call)
- Questions stored in session for post-call analysis mapping

### 2.3 Tenant Config Integration
- Bot greeting uses tenant's `bot_name`, `caller_id_name`, `greeting_style`
- Consent script uses tenant's `consent_script` or default
- Call duration enforced from tenant's `call_duration_min/max`
- Follow-up depth from tenant's `follow_up_aggressiveness`

### 2.4 Inbound Callback Agent
- Path A (pending session found): "Hi [Name], I tried reaching you earlier about [role]..." → full screening
- Path B (no session): Polite redirect + optional SMS with scheduling link
- Callback cancels remaining retry attempts for the original session

### Deliverable
Bot conducts a full 5-7 min screening call with dynamic, skill-based questions. Handles inbound callbacks correctly.

---

## Task 3: Post-Call Analysis + Storage (Phase 3 — ~1.5 weeks)

**Goal**: After each call, generate structured assessment and update candidate record.

### 3.1 Transcript Storage
- Store full speaker-labeled transcript in `VoiceTranscriptEntry`
- Store audio recording URL (LiveKit Egress or Twilio recording)
- Update `VoiceScreeningSession` with `transcript_json`, `duration_seconds`, `status`

### 3.2 Structured Assessment Generation
LLM generates (reusing existing `transcript_service.py` pattern):
- Per-question assessment: question → answer → rating (1-5) → evidence quote
- Skill proficiency scores (mapped to JD must-haves)
- Communication/clarity score
- Overall recommendation: Strong Yes / Yes / Maybe / No / Strong No
- Risk flags (inconsistencies, vague answers, concerns)
- Summary narrative

### 3.3 Candidate Pipeline Integration
- Store `assessment_json` in `VoiceScreeningSession`
- If tenant's `auto_update_status = true`: update candidate status in existing pipeline
- Create `ScreeningResult` record linking voice session to candidate
- Assessment detail level respects tenant's `assessment_detail_level` setting

### Deliverable
After each call, recruiter sees full transcript + structured assessment on candidate page.

---

## Task 4: Scheduling + Compliance + Retry (Phase 4 — ~1.5 weeks)

**Goal**: Recruiter can schedule calls; system handles compliance and retries.

### 4.1 Call Scheduling (Celery)
- Celery task: schedule call at tenant-configured time
- Timezone-aware: convert candidate's local time → UTC → schedule
- Business hours enforcement: only schedule within tenant's `business_hours_start/end` + `allowed_days`
- Candidate timezone: use candidate's timezone or fall back to tenant's

### 4.2 Retry Logic
- 3-tier: retry after 24h → 48h → escalate
- Retry intervals from tenant's `retry_intervals` config
- Max retries from tenant's `max_retries` config
- **Callback cancellation**: if candidate calls back, cancel all pending retries
- Escalation: notify `escalation_contact_id` with contextual notes

### 4.3 Compliance
- Consent recording: mandatory announcement before any questions
- Timezone-aware scheduling: 9 AM–6 PM candidate local time (configurable per tenant)
- DNC handling: flag numbers that opt out; skip on future scheduling
- Call recording disclosure in consent script

### 4.4 Notifications
- Email to recruiter on call completion (with assessment summary link)
- Email to recruiter on call failure (with retry status)
- Email to recruiter on escalation (all retries exhausted)

### Deliverable
Recruiter schedules a call → system handles everything (scheduling, retries, compliance) → recruiter gets results.

---

## Task 5: Frontend Integration (Phase 5 — ~2 weeks)

**Goal**: Full recruiter UI for the voice screening workflow.

### 5.1 Voice Settings Page (Settings → Voice Screening)
- Bot Identity: name, gender, voice sample upload
- Phone Number: outbound number display + change (Phase 4: per-tenant provisioning)
- Scheduling: timezone, business hours, allowed days
- Conversation: greeting style, duration limits, follow-up depth
- Compliance: consent script (default/custom), DNC handling
- Retry: max retries, intervals, escalation contact

### 5.2 Schedule Call UI
- "Schedule Voice Screening" button on candidate detail page
- Modal: confirm phone number, pick date/time, select JD
- Validation: phone format, time within business hours

### 5.3 Call Status + Live View
- Status indicator on candidate card: scheduled / ringing / in-progress / completed / failed
- No live monitoring (per earlier decision — no real-time listening)

### 5.4 Transcript Viewer
- Speaker-labeled conversation with timestamps
- Expandable per-question sections
- Audio playback (if recording stored)

### 5.5 Assessment Display
- Bot's evaluation panel on candidate detail page
- Per-question ratings with evidence quotes
- Skill proficiency radar/bar chart
- Overall recommendation badge
- Integrated alongside existing screening scores

### 5.6 Retry/Reschedule Actions
- "Reschedule" button for failed calls
- "Cancel pending retries" action
- Manual override of candidate status

### Deliverable
Full recruiter UX: configure bot, schedule calls, monitor status, review transcripts and assessments.

---

## Task 6: Polish + Naturalness (Phase 6 — ~1 week)

**Goal**: Make the bot sound and behave like a real recruiter.

### 6.1 TTS Upgrade
- Swap Kokoro 82M → Orpheus 1B
- Voice cloning: if tenant uploaded a voice sample, clone it
- Emotion/prosody tuning for recruiter personality

### 6.2 Conversation Naturalness
- Filler responses: "mm-hmm", "that's great", "interesting, tell me more"
- Adaptive follow-ups: weak answer → probe; strong answer → move on
- Natural pauses and pacing (not robotic speed)
- Handle tangents gracefully (candidate goes off-topic → gentle redirect)

### 6.3 Latency Optimization
- Target <2s total response time (STT → LLM → TTS)
- Stream TTS audio as soon as first tokens arrive (don't wait for full response)
- Pre-load models, keep warm between calls

### 6.4 Edge Cases
- Voicemail detection → leave brief message → mark as voicemail
- Bad audio quality → "I'm having trouble hearing you, could you repeat that?"
- Candidate asks to reschedule → "No problem, I'll note that and someone will follow up"
- Candidate asks for a human → "I'll connect you with a recruiter" → escalate

### Deliverable
Bot feels natural, not robotic. Handles real-world conversation edge cases gracefully.

---

## Cost Summary

| Item | Monthly Cost (500 calls) |
|---|---|
| LiveKit SIP telephony | ~$15-25 |
| Shared phone number (Phase 1) | ~$1.15 |
| Per-tenant numbers (Phase 4, 10 tenants) | ~$11.50 |
| Ollama Cloud (existing) | Already paid |
| VPS + new containers (CPU) | $0 (existing infra) |
| **Total incremental** | **~$28-38/mo** |

---

## Timeline

| Phase | Duration | Cumulative |
|---|---|---|
| Task 1: Infrastructure + Voice Loop | 2 weeks | 2 weeks |
| Task 2: Conversation Intelligence | 3 weeks | 5 weeks |
| Task 3: Post-Call Analysis + Storage | 1.5 weeks | 6.5 weeks |
| Task 4: Scheduling + Compliance + Retry | 1.5 weeks | 8 weeks |
| Task 5: Frontend Integration | 2 weeks | 10 weeks |
| Task 6: Polish + Naturalness | 1 week | 11 weeks |
| **Total** | | **~11 weeks** |

---

## What Stays Unchanged

- ARIA Backend core (new routes added, existing untouched)
- Ollama Cloud (reused as-is)
- PostgreSQL + Alembic (new migration only)
- Celery + Redis (reused for scheduling)
- React Frontend (new components added)
- Nginx (new proxy rules for LiveKit)
- CI/CD pipeline (updated to build new containers)
