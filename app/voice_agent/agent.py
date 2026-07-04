"""
Voice Agent — LiveKit Agents process for voice screening.

Handles:
  • HTTP dispatch API (backend → agent: create room + SIP outbound call)
  • LiveKit Agent Worker (auto-joins rooms, runs conversation)
  • Conversation state machine (greeting → consent → screening → wrap-up)
  • Integration with Speech Service (STT/TTS) and Ollama Cloud (LLM)
"""
import asyncio
import io
import json
import logging
import os
import re
import struct
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Union

import httpx

from app.voice_agent.recruiter_conversation import RecruiterConversation, RecruiterContext, RecruiterState
from app.voice_agent.conversation import UnifiedConversation, InterviewContext, InterviewDepth
from app.voice_agent.vad_segmenter import SpeechSegmenter
from app.voice_agent.orchestrator import InterviewOrchestrator, OrchestratorContext, InterviewStage
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

load_dotenv()

logger = logging.getLogger("voice_agent")

# ─── Configuration ─────────────────────────────────────────────────────────────

SPEECH_SERVICE_URL = os.getenv("SPEECH_SERVICE_URL", "http://speech-service:8001")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL_VOICE", os.getenv("OLLAMA_MODEL", "qwen2.5:3b"))
ARIA_BACKEND_URL = os.getenv("ARIA_BACKEND_URL", "http://backend:8000")
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://livekit:7880")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
SIP_TRUNK_ID = os.getenv("SIP_TRUNK_ID", "twilio-aria")
SIP_OUTBOUND_NUMBER = os.getenv("SIP_OUTBOUND_NUMBER", "+18722789563")
SIP_TERMINATION_ADDRESS = os.getenv("SIP_TERMINATION_ADDRESS", "aria-staging.pstn.twilio.com")
SIP_AUTH_USERNAME = os.getenv("SIP_AUTH_USERNAME", "aria-livekit")
SIP_AUTH_PASSWORD = os.getenv("SIP_AUTH_PASSWORD", "Itslogical1.")
SIP_FROM_HOST = os.getenv("SIP_FROM_HOST", SIP_TERMINATION_ADDRESS)
SIP_TRANSPORT = os.getenv("SIP_TRANSPORT", "SIP_TRANSPORT_TCP")  # auto/udp/tcp/tls
AGENT_PORT = int(os.getenv("AGENT_PORT", "8002"))

# Conversation settings (defaults, overridden per-call by tenant config)
DEFAULT_BOT_NAME = "ARIA Assistant"
DEFAULT_CALL_DURATION_MAX = 420  # 7 minutes
DEFAULT_GREETING_STYLE = "professional"


# ─── Conversation States ──────────────────────────────────────────────────────

class CallState(str, Enum):
    GREETING = "greeting"
    CONSENT = "consent"
    INTRODUCTION = "introduction"
    SCREENING = "screening"
    FOLLOW_UP = "follow_up"
    WRAP_UP = "wrap_up"
    ANALYSIS = "analysis"
    ENDED = "ended"


@dataclass
class ScreeningContext:
    """Per-call context for the conversation state machine."""
    session_id: int
    tenant_id: int
    candidate_id: int
    candidate_name: str
    phone_number: str
    bot_name: str = DEFAULT_BOT_NAME
    greeting_style: str = DEFAULT_GREETING_STYLE
    call_duration_max: int = DEFAULT_CALL_DURATION_MAX
    consent_script: Optional[str] = None
    jd_title: Optional[str] = None
    jd_must_have_skills: list = field(default_factory=list)
    screening_questions: list = field(default_factory=list)
    current_question_idx: int = 0
    transcript: list = field(default_factory=list)
    state: CallState = CallState.GREETING
    call_start_time: float = 0.0
    consent_recorded: bool = False
    direction: str = "outbound"  # outbound / inbound
    callback_of_id: Optional[int] = None


# ─── Speech Service Client ────────────────────────────────────────────────────

class SpeechClient:
    """HTTP client for the Speech Service (STT/TTS/VAD)."""

    def __init__(self, base_url: str = SPEECH_SERVICE_URL):
        self.base_url = base_url
        self._client: Optional[httpx.AsyncClient] = None

    async def start(self):
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)

    async def stop(self):
        if self._client:
            await self._client.aclose()

    async def transcribe(self, audio_bytes: bytes, content_type: str = "audio/wav") -> str:
        """Send audio to STT, return transcribed text. Retries once on failure."""
        for attempt in range(2):
            try:
                resp = await self._client.post(
                    "/stt/transcribe",
                    content=audio_bytes,
                    headers={"Content-Type": content_type},
                )
                resp.raise_for_status()
                return resp.json().get("text", "")
            except Exception as e:
                if attempt == 0:
                    logger.warning("STT attempt 1 failed: %s — retrying", e)
                    await asyncio.sleep(0.5)
                else:
                    logger.error("STT attempt 2 failed: %s", e)
                    return ""

    async def synthesize(self, text: str, voice: str = "female") -> bytes:
        """Send text to TTS, return WAV audio bytes. Retries once on failure."""
        for attempt in range(2):
            try:
                resp = await self._client.post(
                    "/tts/synthesize",
                    json={"text": text, "voice": voice},
                )
                resp.raise_for_status()
                return await resp.aread()
            except Exception as e:
                if attempt == 0:
                    logger.warning("TTS attempt 1 failed: %s — retrying", e)
                    await asyncio.sleep(0.5)
                else:
                    logger.error("TTS attempt 2 failed: %s", e)
                    return b""

    async def detect_speech(self, audio_bytes: bytes) -> dict:
        """Send audio to VAD, return speech detection result."""
        resp = await self._client.post(
            "/vad/detect",
            content=audio_bytes,
            headers={"Content-Type": "audio/wav"},
        )
        resp.raise_for_status()
        return resp.json()

    async def health(self) -> dict:
        resp = await self._client.get("/health")
        resp.raise_for_status()
        return resp.json()


# ─── LLM Client ───────────────────────────────────────────────────────────────

class LLMClient:
    """HTTP client for Ollama Cloud LLM."""

    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.api_key = OLLAMA_API_KEY
        self.model = OLLAMA_MODEL

    async def chat(self, system_prompt: str, user_message: str, history: list = None) -> str:
        """Send a chat completion request to Ollama."""
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 512,
                    },
                },
                headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")

    async def generate(self, prompt: str) -> str:
        """Generate a short text completion via Ollama (used for follow-ups)."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 128,
                    },
                },
                headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")

    async def generate_screening_questions(self, jd_title: str, skills: list) -> list:
        """Generate 3-5 screening questions from JD must-have skills."""
        skills_str = ", ".join(skills) if skills else "general technical skills"
        system_prompt = (
            "You are an expert technical recruiter. Generate concise, open-ended "
            "screening questions for a phone interview. Each question should probe "
            "the candidate's depth of knowledge in a specific skill area. "
            "Return ONLY a JSON array of strings, no other text."
        )
        user_msg = (
            f"Role: {jd_title}\n"
            f"Must-have skills: {skills_str}\n"
            f"Generate 3-5 screening questions, one per key skill."
        )
        response = await self.chat(system_prompt, user_msg)
        try:
            # Try to parse JSON from response
            questions = json.loads(response)
            if isinstance(questions, list):
                return questions
        except json.JSONDecodeError:
            pass
        # Fallback: extract questions from text
        lines = [l.strip().lstrip("0123456789.-) ") for l in response.split("\n") if l.strip() and "?" in l]
        return lines[:5] if lines else [f"Tell me about your experience with {s}." for s in skills[:3]]


# ─── ARIA Backend Client ──────────────────────────────────────────────────────

class BackendClient:
    """HTTP client for ARIA Backend API — session state updates."""

    def __init__(self, base_url: str = ARIA_BACKEND_URL):
        self.base_url = base_url

    async def update_session(self, session_id: int, updates: dict):
        """Update voice screening session in the database."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.patch(
                f"{self.base_url}/api/voice/sessions/{session_id}",
                json=updates,
            )
            if resp.status_code != 200:
                logger.warning("Failed to update session %d: %s", session_id, resp.text)

    async def get_tenant_config(self, tenant_id: int) -> dict:
        """Get voice tenant config."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{self.base_url}/api/voice/internal/config/{tenant_id}",
            )
            if resp.status_code == 200:
                return resp.json()
            return {}

    async def get_candidate_info(self, tenant_id: int, candidate_id: int) -> dict:
        """Get candidate details."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{self.base_url}/api/voice/internal/candidate/{tenant_id}/{candidate_id}",
            )
            if resp.status_code == 200:
                return resp.json()
            return {}


# ─── Conversation Engine ──────────────────────────────────────────────────────

class ConversationEngine:
    """
    State machine for the screening conversation.

    Flow: GREETING → CONSENT → INTRODUCTION → SCREENING → FOLLOW_UP → WRAP_UP → ANALYSIS → ENDED
    """

    def __init__(self, ctx: ScreeningContext, speech: SpeechClient, llm: LLMClient, backend: BackendClient):
        self.ctx = ctx
        self.speech = speech
        self.llm = llm
        self.backend = backend
        self.history: list = []  # Chat history for LLM context

    def _build_system_prompt(self) -> str:
        # Naturalness: build dynamic personality + context
        style_map = {
            "friendly": "warm, friendly, and conversational — like a helpful colleague",
            "casual": "relaxed and casual but still professional",
            "professional": "polished, professional, and courteous",
        }
        personality = style_map.get(self.ctx.greeting_style, style_map["professional"])

        return (
            f"You are {self.ctx.bot_name}, a recruiter conducting a brief phone screening "
            f"for the position of {self.ctx.jd_title or 'the open role'}. "
            f"You are speaking with {self.ctx.candidate_name}.\n\n"
            f"## Personality\n"
            f"- Be {personality}\n"
            f"- Use natural speech patterns: brief acknowledgments ('Uh-huh', 'Got it', 'That makes sense')\n"
            f"- Vary your transitions — don't repeat the same phrase\n"
            f"- Mirror the candidate's energy: if they're nervous, be extra warm\n\n"
            f"## Rules\n"
            f"- Ask ONE question at a time, then WAIT for the response\n"
            f"- Keep your responses to 1-3 sentences (this is a phone call, not an email)\n"
            f"- If the candidate gives a weak answer, gently probe: 'Can you tell me more about that?'\n"
            f"- If the candidate gives a strong answer, acknowledge it and move on\n"
            f"- Never mention AI, algorithms, or automated systems — you are a real recruiter\n"
            f"- If the candidate asks about salary/benefits, say you'll have the recruiter follow up\n"
            f"- Stay within the {self.ctx.call_duration_max // 60}-minute time budget\n"
        )

    async def get_bot_response(self, user_text: str) -> str:
        """Get the bot's next response based on current state and user input."""
        # Check for edge cases first (silence, "I don't know", reschedule, etc.)
        edge_response = self.handle_edge_case(user_text)
        if edge_response and self.ctx.state in (CallState.SCREENING, CallState.FOLLOW_UP):
            # Log the edge case but still let LLM handle it naturally
            self.history.append({"role": "user", "content": user_text})
            self.history.append({"role": "assistant", "content": edge_response})
            return edge_response

        system_prompt = self._build_system_prompt()

        # Add state-specific instructions
        if self.ctx.state == CallState.GREETING:
            system_prompt += (
                "\n\nCURRENT STATE: Greeting the candidate. Confirm their identity."
            )
        elif self.ctx.state == CallState.CONSENT:
            consent = self.ctx.consent_script or (
                "Before we begin, I need to let you know that this call is being recorded "
                "for hiring evaluation purposes. Your responses will be used to assess your "
                "fit for the position. Do you consent to proceed with this recorded screening?"
            )
            system_prompt += f"\n\nCURRENT STATE: Obtaining consent. Say: {consent}"
        elif self.ctx.state == CallState.INTRODUCTION:
            system_prompt += (
                "\n\nCURRENT STATE: Introducing the role and asking if they have time."
            )
        elif self.ctx.state == CallState.SCREENING:
            q_idx = self.ctx.current_question_idx
            if q_idx < len(self.ctx.screening_questions):
                system_prompt += (
                    f"\n\nCURRENT STATE: Screening question {q_idx + 1} of {len(self.ctx.screening_questions)}. "
                    f"Ask: '{self.ctx.screening_questions[q_idx]}'"
                )
        elif self.ctx.state == CallState.FOLLOW_UP:
            system_prompt += "\n\nCURRENT STATE: Following up on a weak answer. Probe deeper."
        elif self.ctx.state == CallState.WRAP_UP:
            system_prompt += (
                "\n\nCURRENT STATE: Wrapping up. Ask if they have questions, "
                "explain next steps, and say goodbye."
            )

        response = await self.llm.chat(system_prompt, user_text, self.history)

        # Update history
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": response})

        # Keep history manageable (last 20 turns)
        if len(self.history) > 40:
            self.history = self.history[-40:]

        return response

    def advance_state(self):
        """Move to the next conversation state."""
        transitions = {
            CallState.GREETING: CallState.CONSENT,
            CallState.CONSENT: CallState.INTRODUCTION,
            CallState.INTRODUCTION: CallState.SCREENING,
            CallState.SCREENING: CallState.FOLLOW_UP if self.ctx.current_question_idx < len(self.ctx.screening_questions) else CallState.WRAP_UP,
            CallState.FOLLOW_UP: CallState.SCREENING,
            CallState.WRAP_UP: CallState.ANALYSIS,
            CallState.ANALYSIS: CallState.ENDED,
        }
        new_state = transitions.get(self.ctx.state, CallState.ENDED)
        logger.info("State transition: %s → %s", self.ctx.state.value, new_state.value)
        self.ctx.state = new_state

    def check_time_budget(self) -> bool:
        """Return True if still within time budget."""
        elapsed = time.time() - self.ctx.call_start_time
        return elapsed < self.ctx.call_duration_max

    def handle_edge_case(self, user_text: str) -> Optional[str]:
        """
        Detect and handle edge cases in candidate speech.
        Returns a response string if an edge case was handled, else None.
        """
        text = user_text.strip().lower()

        # Silence / no response
        if not text or text in {"[silence]", "[no speech detected]", ""}:
            return "I didn't quite catch that. Could you repeat what you said?"

        # Candidate doesn't know / unsure
        if any(p in text for p in ["i don't know", "i'm not sure", "can't think of", "no idea"]):
            return "That's okay — let me rephrase. Can you think of any example, even from a different context?"

        # Candidate asks to reschedule / not a good time
        if any(p in text for p in ["not a good time", "can we reschedule", "call back later", "busy right now"]):
            return (
                "No problem at all! I'll let the recruiting team know. "
                "They'll reach out to schedule a better time. Thanks for your time today!"
            )

        # Candidate asks about compensation
        if any(p in text for p in ["salary", "pay", "compensation", "benefits", "how much"]):
            return (
                "Great question! The recruiter will be able to discuss compensation details "
                "during the next stage. For now, let's continue with the screening."
            )

        # Candidate asks if this is AI / robot
        if any(p in text for p in ["are you a robot", "are you ai", "is this automated", "am i talking to a bot"]):
            return "Ha! I appreciate the question. Let's keep going — I'd love to hear more about your experience."

        # Very short / unclear response
        if len(text.split()) <= 1 and text not in {"yes", "no", "yeah", "nope", "sure", "okay", "ok"}:
            return "Could you elaborate a bit more on that?"

        return None  # No edge case detected

    def get_transition_phrase(self) -> str:
        """Return a natural transition phrase between questions."""
        import random
        transitions = [
            "Great, thanks for sharing. ",
            "That's helpful context. ",
            "Interesting — thanks. ",
            "Got it. ",
            "Makes sense. ",
            "Appreciate that. ",
            "Thanks for explaining. ",
        ]
        return random.choice(transitions)


# ─── Agent Entrypoint ─────────────────────────────────────────────────────────

async def run_outbound_screening(ctx: ScreeningContext):
    """
    Run a full outbound screening call.

    This is the main entry point called when a screening session is triggered.
    In Phase 1, this is a skeleton that will be connected to LiveKit SIP in Phase 1.4.
    """
    speech = SpeechClient()
    llm = LLMClient()
    backend = BackendClient()
    engine = ConversationEngine(ctx, speech, llm, backend)

    try:
        await speech.start()
        ctx.call_start_time = time.time()

        logger.info(
            "Starting outbound screening session=%d candidate=%s phone=%s",
            ctx.session_id, ctx.candidate_name, ctx.phone_number,
        )

        # Update session status to in_progress
        await backend.update_session(ctx.session_id, {"status": "in_progress"})

        # Generate screening questions from JD skills
        if ctx.jd_must_have_skills:
            ctx.screening_questions = await llm.generate_screening_questions(
                ctx.jd_title or "the role",
                ctx.jd_must_have_skills,
            )
            logger.info("Generated %d screening questions", len(ctx.screening_questions))

        # ── Main conversation loop ──
        # In Phase 1.4, this will be connected to LiveKit's audio stream.
        # For now, the conversation engine is ready but needs LiveKit integration.

        logger.info("Conversation engine ready for session %d (state: %s)", ctx.session_id, ctx.state.value)

        # Phase 1.4: LiveKit SIP integration will wire audio here
        # For now, mark as skeleton complete
        logger.info(
            "Screening session %d — conversation engine initialized. "
            "Awaiting LiveKit SIP connection (Phase 1.4).",
            ctx.session_id,
        )

    except Exception as e:
        logger.error("Screening session %d failed: %s", ctx.session_id, e, exc_info=True)
        await backend.update_session(ctx.session_id, {
            "status": "failed",
            "error_log": str(e),
        })
    finally:
        await speech.stop()


async def handle_inbound_callback(ctx: ScreeningContext):
    """
    Handle an inbound call from a candidate (callback after missed call).

    Path A: Pending session found → connect to full screening with context
    Path B: No pending session → polite redirect
    """
    speech = SpeechClient()
    llm = LLMClient()
    backend = BackendClient()
    engine = ConversationEngine(ctx, speech, llm, backend)

    try:
        await speech.start()
        ctx.call_start_time = time.time()
        ctx.direction = "inbound"

        logger.info(
            "Handling inbound callback session=%d phone=%s callback_of=%s",
            ctx.session_id, ctx.phone_number, ctx.callback_of_id,
        )

        if ctx.callback_of_id:
            # Path A: Candidate is calling back about a specific missed call
            logger.info("Path A: Connecting to screening for callback_of=%d", ctx.callback_of_id)
            # Skip greeting/consent — use contextual greeting
            ctx.state = CallState.INTRODUCTION
            await backend.update_session(ctx.session_id, {"status": "in_progress"})
        else:
            # Path B: No pending session — polite redirect
            logger.info("Path B: No pending session — polite redirect")
            greeting = (
                "Hi, thanks for calling back! This is an automated line from our recruiting team. "
                "If you're expecting a screening call, a recruiter will follow up shortly. "
                "Have a great day!"
            )
            # In Phase 1.4, this would be spoken via TTS
            logger.info("Inbound redirect: %s", greeting)
            ctx.state = CallState.ENDED

    except Exception as e:
        logger.error("Inbound callback session %d failed: %s", ctx.session_id, e, exc_info=True)
    finally:
        await speech.stop()


# ─── LiveKit SIP Dispatcher ───────────────────────────────────────────────────

class LiveKitSIPDispatcher:
    """Creates LiveKit rooms and dials out via SIP to candidates."""

    def __init__(self):
        self.lk_url = LIVEKIT_URL.replace("ws://", "http://").replace("wss://", "https://")
        self.api_key = LIVEKIT_API_KEY
        self.api_secret = LIVEKIT_API_SECRET
        self._resolved_trunk_id: Optional[str] = None

    async def resolve_sip_trunk_id(self, api) -> str:
        """
        Resolve or create the LiveKit SIP trunk for Twilio outbound calls.

        Trunks must be created programmatically via the LiveKit API because
        the server YAML config does not support SIP trunk definitions.
        """
        if self._resolved_trunk_id:
            return self._resolved_trunk_id

        # Step 1: List existing outbound trunks
        try:
            from livekit.protocol.sip import (
                ListSIPOutboundTrunkRequest,
                DeleteSIPTrunkRequest,
                SIPTransport,
            )
            transport_map = {
                "SIP_TRANSPORT_AUTO": SIPTransport.SIP_TRANSPORT_AUTO,
                "SIP_TRANSPORT_UDP": SIPTransport.SIP_TRANSPORT_UDP,
                "SIP_TRANSPORT_TCP": SIPTransport.SIP_TRANSPORT_TCP,
                "SIP_TRANSPORT_TLS": SIPTransport.SIP_TRANSPORT_TLS,
            }
            desired_transport = transport_map.get(SIP_TRANSPORT, SIPTransport.SIP_TRANSPORT_TCP)
            desired_from_host = SIP_FROM_HOST

            resp = await api.sip.list_outbound_trunk(ListSIPOutboundTrunkRequest())
            trunks = list(resp.items) if resp and resp.items else []
            logger.info("LiveKit SIP outbound trunks found: %d", len(trunks))
            for trunk in trunks:
                trunk_id = trunk.sip_trunk_id or ''
                trunk_name = trunk.name or ''
                trunk_addr = trunk.address or ''
                trunk_transport = trunk.transport
                trunk_from_host = trunk.from_host or ''
                logger.info(
                    "  trunk: id=%s name=%s address=%s numbers=%s transport=%s from_host=%s",
                    trunk_id, trunk_name, trunk_addr, list(trunk.numbers),
                    SIPTransport.Name(trunk_transport) if trunk_transport is not None else "auto",
                    trunk_from_host,
                )
                # Match by exact termination address or configured name
                if (trunk_addr == SIP_TERMINATION_ADDRESS or
                        trunk_name == SIP_TRUNK_ID or
                        trunk_id == SIP_TRUNK_ID):
                    # If the trunk exists but settings changed, delete and recreate it.
                    if trunk_transport != desired_transport or trunk_from_host != desired_from_host:
                        logger.warning(
                            "Existing trunk %s settings do not match (transport=%s from_host=%s); recreating",
                            trunk_id, SIPTransport.Name(trunk_transport) if trunk_transport is not None else "auto",
                            trunk_from_host,
                        )
                        try:
                            await api.sip.delete_sip_trunk(DeleteSIPTrunkRequest(sip_trunk_id=trunk_id))
                            logger.info("Deleted stale SIP trunk: %s", trunk_id)
                        except Exception as del_err:
                            logger.error("Failed to delete stale SIP trunk %s: %s", trunk_id, del_err)
                        break
                    self._resolved_trunk_id = trunk_id
                    logger.info("Resolved existing SIP trunk: %s (name=%s)", trunk_id, trunk_name)
                    return trunk_id
        except Exception as e:
            logger.warning("Failed to list SIP trunks: %s", e)

        # Step 2: No matching trunk — create one via API
        logger.info("No Twilio SIP trunk found — creating via LiveKit API...")
        trunk_id = await self._create_sip_trunk(api)
        if trunk_id:
            self._resolved_trunk_id = trunk_id
            return trunk_id

        # Step 3: Last resort fallback
        logger.error("Could not create SIP trunk — using env var as fallback: %s", SIP_TRUNK_ID)
        self._resolved_trunk_id = SIP_TRUNK_ID
        return SIP_TRUNK_ID

    async def _create_sip_trunk(self, api) -> Optional[str]:
        """Create a SIP outbound trunk via the LiveKit API."""
        try:
            from livekit.protocol.sip import (
                CreateSIPOutboundTrunkRequest,
                SIPOutboundTrunkInfo,
                SIPTransport,
            )
            transport_map = {
                "SIP_TRANSPORT_AUTO": SIPTransport.SIP_TRANSPORT_AUTO,
                "SIP_TRANSPORT_UDP": SIPTransport.SIP_TRANSPORT_UDP,
                "SIP_TRANSPORT_TCP": SIPTransport.SIP_TRANSPORT_TCP,
                "SIP_TRANSPORT_TLS": SIPTransport.SIP_TRANSPORT_TLS,
            }
            transport = transport_map.get(SIP_TRANSPORT, SIPTransport.SIP_TRANSPORT_TCP)
            req = CreateSIPOutboundTrunkRequest(
                trunk=SIPOutboundTrunkInfo(
                    name=SIP_TRUNK_ID,
                    address=SIP_TERMINATION_ADDRESS,
                    numbers=[SIP_OUTBOUND_NUMBER],
                    auth_username=SIP_AUTH_USERNAME,
                    auth_password=SIP_AUTH_PASSWORD,
                    transport=transport,
                    from_host=SIP_FROM_HOST,
                )
            )
            result = await api.sip.create_outbound_trunk(req)
            trunk_id = result.sip_trunk_id
            logger.info(
                "Created SIP outbound trunk: id=%s name=%s transport=%s from_host=%s",
                trunk_id, result.name, SIP_TRANSPORT, SIP_FROM_HOST,
            )
            return trunk_id
        except ImportError as e:
            logger.error("SIPOutboundTrunkInfo not available in livekit.protocol.sip: %s", e)
        except Exception as e:
            logger.error("SIP outbound trunk creation failed: %s", e)

        return None

    def _create_agent_token(self, room_name: str, identity: str = "aria-agent") -> str:
        """Generate a LiveKit access token for the agent participant."""
        from livekit.api import AccessToken, VideoGrants
        token = AccessToken(self.api_key, self.api_secret)
        token.with_identity(identity)
        token.with_name("ARIA Assistant")
        token.with_grants(VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
        ))
        return token.to_jwt()

    async def dispatch_call(
        self,
        session_id: int,
        phone_number: str,
        candidate_name: str,
    ) -> dict:
        """Create a LiveKit room and initiate SIP outbound call to the candidate."""
        from livekit.api import LiveKitAPI, CreateSIPParticipantRequest

        room_name = f"voice-screen-{session_id}"
        participant_identity = f"candidate-{session_id}"

        api = LiveKitAPI(self.lk_url, self.api_key, self.api_secret)

        try:
            # 1. Resolve actual SIP trunk ID from LiveKit
            trunk_id = await self.resolve_sip_trunk_id(api)

            # 2. Create room (SDK requires CreateRoomRequest protobuf object)
            from livekit.protocol.room import CreateRoomRequest
            await api.room.create_room(CreateRoomRequest(
                name=room_name,
                empty_timeout=120,
                max_participants=2,
            ))
            logger.info("Room created: %s", room_name)

            # 3. Create SIP participant (triggers outbound PSTN call)
            # Normalize phone to E.164: strip spaces/dashes, keep only + and digits
            sip_phone = re.sub(r'[^\d+]', '', phone_number)
            sip_req = CreateSIPParticipantRequest(
                sip_trunk_id=trunk_id,
                sip_call_to=sip_phone,
                room_name=room_name,
                participant_identity=participant_identity,
                participant_name=candidate_name,
                hide_phone_number=False,
            )
            await api.sip.create_sip_participant(sip_req)
            logger.info(
                "SIP participant created: room=%s phone=%s (raw=%s) trunk=%s",
                room_name, sip_phone, phone_number, trunk_id,
            )

            # 3. Generate agent token for the voice agent worker to join
            agent_token = self._create_agent_token(room_name)

            return {
                "room_name": room_name,
                "agent_token": agent_token,
                "lk_url": LIVEKIT_URL,
            }
        finally:
            await api.aclose()


# ─── Audio Publishing ──────────────────────────────────────────────────────────

def _strip_wav_header(data: bytes) -> bytes:
    """Strip WAV file header to get raw PCM samples.

    Speech service returns complete WAV files. LiveKit AudioFrame needs raw PCM.
    Standard WAV header is 44 bytes (RIFF + fmt + data chunk header).
    """
    if data[:4] == b'RIFF' and data[8:12] == b'WAVE':
        # Find the 'data' sub-chunk
        offset = 12
        while offset < len(data) - 8:
            chunk_id = data[offset:offset + 4]
            chunk_size = int.from_bytes(data[offset + 4:offset + 8], 'little')
            if chunk_id == b'data':
                return data[offset + 8:offset + 8 + chunk_size]
            offset += 8 + chunk_size
    return data  # Already raw PCM


def _pcm_to_wav(pcm_data: bytes, sample_rate: int, channels: int = 1, sample_width: int = 2) -> bytes:
    """Wrap raw PCM bytes in a WAV header so the speech service can resample correctly."""
    num_samples = len(pcm_data) // sample_width
    byte_rate = sample_rate * channels * sample_width
    block_align = channels * sample_width
    data_size = len(pcm_data)

    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF', 36 + data_size, b'WAVE',
        b'fmt ', 16,
        1,  # PCM format
        channels, sample_rate, byte_rate, block_align, sample_width * 8,
        b'data', data_size,
    )
    return header + pcm_data


async def _notify_backend_complete(session_id: str, result: dict):
    """Notify backend that interview has completed (unified endpoint)."""
    backend_url = os.getenv("BACKEND_URL", ARIA_BACKEND_URL)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{backend_url}/api/interviews/internal/complete",
                json={"session_id": session_id, "result": result},
            )
            resp.raise_for_status()
            logger.info("Notified backend of interview completion: session=%s status=%d", session_id, resp.status_code)
    except Exception as e:
        logger.error("Failed to notify backend of interview completion: session=%s error=%s", session_id, e)


async def _publish_audio(room, audio_source, pcm_data: bytes, sample_rate: int):
    """Publish raw PCM audio to the LiveKit room via the agent's audio track.

    Handles WAV→PCM conversion, frame splitting (20ms chunks), and track publishing.
    LiveKit expects small audio frames (~20ms). Sending the entire TTS output as
    one frame can silently fail or cause audio glitches.
    """
    from livekit import rtc

    pcm = _strip_wav_header(pcm_data)
    if not pcm:
        logger.warning("Empty audio data — skipping publish")
        return

    # 20ms frames = 320 samples at 16kHz, 2 bytes per sample = 640 bytes
    FRAME_SAMPLES = int(sample_rate * 0.02)  # 20ms
    FRAME_BYTES = FRAME_SAMPLES * 2  # 16-bit PCM

    total_samples = len(pcm) // 2
    if total_samples == 0:
        logger.warning("No audio samples after WAV header strip — skipping")
        return

    frames_published = 0
    offset = 0
    while offset + FRAME_BYTES <= len(pcm):
        chunk = pcm[offset:offset + FRAME_BYTES]
        frame = rtc.AudioFrame(
            data=chunk,
            sample_rate=sample_rate,
            num_channels=1,
            samples_per_channel=FRAME_SAMPLES,
        )
        try:
            await audio_source.capture_frame(frame)
            frames_published += 1
        except Exception as e:
            logger.warning("capture_frame failed at offset %d: %s", offset, e)
            break
        # Small delay to let LiveKit process the frame
        await asyncio.sleep(0.02)
        offset += FRAME_BYTES

    # Handle any remaining partial frame
    if offset < len(pcm):
        remaining = pcm[offset:]
        remaining_samples = len(remaining) // 2
        if remaining_samples > 0:
            frame = rtc.AudioFrame(
                data=remaining,
                sample_rate=sample_rate,
                num_channels=1,
                samples_per_channel=remaining_samples,
            )
            try:
                await audio_source.capture_frame(frame)
                frames_published += 1
            except Exception as e:
                logger.warning("capture_frame failed for partial frame: %s", e)

    logger.info("Published %d audio frames (%d samples, %.1fs)",
                frames_published, total_samples, total_samples / sample_rate)


# ─── LiveKit Agent Worker ─────────────────────────────────────────────────────

class VoiceAgentWorker:
    """
    Joins LiveKit rooms and runs the conversation engine.

    When a SIP participant (candidate) joins a voice-screen room,
    this worker joins as the ARIA agent, handles audio via the
    Speech Service, and drives the conversation state machine.
    """

    def __init__(self):
        self._active_sessions: dict = {}

    async def handle_room(self, room_name: str, agent_token: str, session_ctx: ScreeningContext):
        """Join a LiveKit room and run the screening conversation."""
        from livekit import rtc

        room = rtc.Room()
        speech = SpeechClient()
        llm = LLMClient()
        backend = BackendClient()
        engine = ConversationEngine(session_ctx, speech, llm, backend)

        # VAD-driven speech segmentation (replaces fixed 3-second buffer)
        TTS_SAMPLE_RATE = 16000
        actual_sample_rate: Optional[int] = None
        segmenter: Optional[SpeechSegmenter] = None

        # Persistent audio source for agent → candidate playback
        audio_source = rtc.AudioSource(TTS_SAMPLE_RATE, 1)

        async def _process_track(track, publication, participant):
            """Async body for processing a subscribed audio track."""
            nonlocal actual_sample_rate, segmenter
            if hasattr(track, 'kind') and track.kind == 1:  # AUDIO
                logger.info(
                    "Audio track subscribed: participant=%s session=%d",
                    participant.identity, session_ctx.session_id,
                )
                stream = rtc.AudioStream(track)

                async for event in stream:
                    frame = event.frame
                    frame_rate = frame.sample_rate
                    if actual_sample_rate is None:
                        actual_sample_rate = frame_rate
                        segmenter = SpeechSegmenter(sample_rate=frame_rate)
                        logger.info("Detected audio track sample rate: %d Hz — VAD segmenter initialized", frame_rate)

                    segmenter.add_audio(bytes(frame.data))

                    for segment_pcm in segmenter.get_speech_segments():
                        wav_data = _pcm_to_wav(segment_pcm, frame_rate)
                        text = await speech.transcribe(wav_data, "audio/wav")
                        if text.strip():
                            session_ctx.transcript.append({
                                "role": "candidate",
                                "text": text,
                                "timestamp": time.time(),
                            })
                            logger.info("Candidate said: %s", text)

                            # Get bot response
                            bot_text = await engine.get_bot_response(text)
                            if bot_text:
                                session_ctx.transcript.append({
                                    "role": "bot",
                                    "text": bot_text,
                                    "timestamp": time.time(),
                                })
                                logger.info("Bot responds: %s", bot_text)

                                # Synthesize speech and publish to room
                                audio_out = await speech.synthesize(bot_text)
                                if audio_out:
                                    await _publish_audio(room, audio_source, audio_out, TTS_SAMPLE_RATE)

                            # Advance conversation state
                            engine.advance_state()

                            # Check for call end conditions
                            if not engine.check_time_budget():
                                logger.info("Time budget exceeded, ending call")
                                session_ctx.state = CallState.ENDED
                            if "reschedule" in text.lower() or "not a good time" in text.lower():
                                session_ctx.state = CallState.ENDED

        def on_track_subscribed(track, publication, participant):
            """Sync wrapper — LiveKit .on() does not support async callbacks."""
            asyncio.create_task(_process_track(track, publication, participant))

        room.on("track_subscribed", on_track_subscribed)

        try:
            await speech.start()
            session_ctx.call_start_time = time.time()

            # Connect to the room
            await room.connect(LIVEKIT_URL, agent_token)
            logger.info("Agent joined room: %s (session=%d)", room_name, session_ctx.session_id)

            # Publish the audio source as a track so the candidate can hear the agent
            try:
                from livekit import rtc
                track = rtc.LocalAudioTrack.create_audio_track("aria-agent", audio_source)
                options = rtc.TrackPublishOptions()
                options.source = rtc.TrackSource.SOURCE_MICROPHONE
                await room.local_participant.publish_track(track, options)
                logger.info("Audio track published to room")
            except Exception as pub_err:
                logger.error("Failed to publish audio track: %s", pub_err, exc_info=True)

            # Update backend
            await backend.update_session(session_ctx.session_id, {"status": "in_progress"})

            # Generate screening questions
            if session_ctx.jd_must_have_skills:
                session_ctx.screening_questions = await llm.generate_screening_questions(
                    session_ctx.jd_title or "the role",
                    session_ctx.jd_must_have_skills,
                )
                logger.info("Generated %d screening questions", len(session_ctx.screening_questions))

            # Deliver initial greeting via TTS
            greeting = (
                f"Hi, is this {session_ctx.candidate_name}? "
                f"This is {session_ctx.bot_name} calling about the {session_ctx.jd_title or 'open'} position."
            )
            session_ctx.transcript.append({"role": "bot", "text": greeting, "timestamp": time.time()})
            audio_out = await speech.synthesize(greeting)
            if audio_out:
                await _publish_audio(room, audio_source, audio_out, TTS_SAMPLE_RATE)
                logger.info("Greeting published for session %d", session_ctx.session_id)

            # Keep the call alive until ended or max duration
            while session_ctx.state != CallState.ENDED and engine.check_time_budget():
                await asyncio.sleep(1)

            # Call ended — save transcript and update backend
            logger.info(
                "Call ended: session=%d state=%s duration=%.1fs",
                session_ctx.session_id, session_ctx.state.value,
                time.time() - session_ctx.call_start_time,
            )

            await backend.update_session(session_ctx.session_id, {
                "status": "completed",
                "transcript_json": json.dumps(session_ctx.transcript),
                "duration_seconds": int(time.time() - session_ctx.call_start_time),
            })

        except Exception as e:
            logger.error("Agent session %d failed: %s", session_ctx.session_id, e, exc_info=True)
            await backend.update_session(session_ctx.session_id, {
                "status": "failed",
                "error_log": str(e),
            })
        finally:
            await speech.stop()
            try:
                await room.disconnect()
            except Exception:
                pass

    async def handle_unified_room(self, room_name: str, agent_token: str, interview_ctx: InterviewContext):
        """
        Join a LiveKit room and run the unified conversation engine.
        Handles all depth modes (quick / standard / deep) via UnifiedConversation.
        """
        from livekit import rtc

        room = rtc.Room()
        speech = SpeechClient()
        llm = LLMClient()
        backend = BackendClient()
        conversation = UnifiedConversation(interview_ctx, llm, speech)

        # VAD-driven speech segmentation (replaces fixed 3-second buffer)
        TTS_SAMPLE_RATE = 16000  # Our TTS audio source rate
        actual_sample_rate: Optional[int] = None
        segmenter: Optional[SpeechSegmenter] = None

        # Persistent audio source for agent → candidate playback
        audio_source = rtc.AudioSource(TTS_SAMPLE_RATE, 1)

        async def _process_track(track, publication, participant):
            """Async body for processing a subscribed audio track."""
            nonlocal actual_sample_rate, segmenter
            if hasattr(track, 'kind') and track.kind == 1:  # AUDIO
                logger.info(
                    "Audio track subscribed: participant=%s session=%s",
                    participant.identity, interview_ctx.session_id,
                )
                stream = rtc.AudioStream(track)

                async for event in stream:
                    frame = event.frame
                    frame_rate = frame.sample_rate
                    if actual_sample_rate is None:
                        actual_sample_rate = frame_rate
                        segmenter = SpeechSegmenter(sample_rate=frame_rate)
                        logger.info("Detected audio track sample rate: %d Hz — VAD segmenter initialized", frame_rate)

                    # Feed audio to VAD segmenter
                    segmenter.add_audio(bytes(frame.data))

                    # Check for completed speech segments
                    for segment_pcm in segmenter.get_speech_segments():
                        # Wrap PCM in WAV header with correct sample rate
                        wav_data = _pcm_to_wav(segment_pcm, frame_rate)
                        text = await speech.transcribe(wav_data, "audio/wav")
                        if text.strip():
                            logger.info("Candidate said: %s", text)

                            # Get bot response via unified engine
                            bot_text = await conversation.handle_response(text)
                            if bot_text:
                                logger.info("Bot responds: %s", bot_text)

                                # Synthesize speech and publish to room
                                audio_out = await speech.synthesize(bot_text)
                                if audio_out:
                                    await _publish_audio(room, audio_source, audio_out, TTS_SAMPLE_RATE)

                            # Check for call end conditions
                            if conversation.is_complete():
                                logger.info("Unified conversation complete, ending call")
                                break

                            if interview_ctx.started_at and interview_ctx.elapsed > interview_ctx.time_budget:
                                logger.info("Time budget exceeded, ending call")
                                break

        def on_track_subscribed(track, publication, participant):
            """Sync wrapper — LiveKit .on() does not support async callbacks."""
            asyncio.create_task(_process_track(track, publication, participant))

        room.on("track_subscribed", on_track_subscribed)

        try:
            await speech.start()
            interview_ctx.started_at = time.time()

            # Connect to the room
            await room.connect(LIVEKIT_URL, agent_token)
            logger.info("Agent joined room: %s (session=%s depth=%s)", room_name, interview_ctx.session_id, interview_ctx.depth.value)

            # Publish the audio source as a track so the candidate can hear the agent
            try:
                track = rtc.LocalAudioTrack.create_audio_track("aria-agent", audio_source)
                options = rtc.TrackPublishOptions()
                options.source = rtc.TrackSource.SOURCE_MICROPHONE
                await room.local_participant.publish_track(track, options)
                logger.info("Audio track published to room")
            except Exception as pub_err:
                logger.error("Failed to publish audio track: %s", pub_err, exc_info=True)

            # Update backend
            try:
                await backend.update_session(int(interview_ctx.session_id), {"status": "in_progress"})
            except Exception:
                pass

            # Deliver initial greeting via TTS
            greeting = await conversation.get_greeting()
            interview_ctx.transcript.append({"speaker": "bot", "text": greeting, "timestamp": 0.0, "state": "greeting"})
            logger.info("Greeting text: %s", greeting[:100])
            audio_out = await speech.synthesize(greeting)
            if audio_out:
                logger.info("TTS returned %d bytes for greeting", len(audio_out))
                await _publish_audio(room, audio_source, audio_out, TTS_SAMPLE_RATE)
                logger.info("Greeting published for session %s", interview_ctx.session_id)
            else:
                logger.error("TTS returned empty audio for greeting — speech service may be unreachable at %s", SPEECH_SERVICE_URL)

            # Keep the call alive until ended or max duration
            while not conversation.is_complete():
                if interview_ctx.started_at and interview_ctx.elapsed > interview_ctx.time_budget:
                    logger.info("Max duration reached for session %s", interview_ctx.session_id)
                    break
                await asyncio.sleep(1)

            # Call ended — finalize and notify backend
            duration = int(interview_ctx.elapsed)
            logger.info(
                "Call ended: session=%s state=%s depth=%s duration=%ds",
                interview_ctx.session_id, interview_ctx.current_state.value,
                interview_ctx.depth.value, duration,
            )

            result = conversation.get_result()
            await _notify_backend_complete(interview_ctx.session_id, result)

        except Exception as e:
            logger.error("Unified session %s failed: %s", interview_ctx.session_id, e, exc_info=True)
            try:
                await backend.update_session(int(interview_ctx.session_id), {
                    "status": "failed",
                    "error_log": str(e),
                })
            except Exception:
                pass
        finally:
            await speech.stop()
            try:
                await room.disconnect()
            except Exception:
                pass

    async def handle_recruiter_room(self, room_name: str, agent_token: str, session_ctx: RecruiterContext):
        """Join a LiveKit room and run the AI Recruiter interview conversation."""
        from livekit import rtc

        room = rtc.Room()
        speech = SpeechClient()
        llm = LLMClient()
        backend = BackendClient()
        conversation = RecruiterConversation(session_ctx, speech, llm)

        # VAD-driven speech segmentation (replaces fixed 3-second buffer)
        TTS_SAMPLE_RATE = 16000
        actual_sample_rate: Optional[int] = None
        segmenter: Optional[SpeechSegmenter] = None

        # Persistent audio source for agent → candidate playback
        audio_source = rtc.AudioSource(TTS_SAMPLE_RATE, 1)

        async def _process_track(track, publication, participant):
            """Async body for processing a subscribed audio track."""
            nonlocal actual_sample_rate, segmenter
            if hasattr(track, 'kind') and track.kind == 1:  # AUDIO
                logger.info(
                    "Audio track subscribed: participant=%s session=%s",
                    participant.identity, session_ctx.session_id,
                )
                stream = rtc.AudioStream(track)

                async for event in stream:
                    frame = event.frame
                    frame_rate = frame.sample_rate
                    if actual_sample_rate is None:
                        actual_sample_rate = frame_rate
                        segmenter = SpeechSegmenter(sample_rate=frame_rate)
                        logger.info("Detected audio track sample rate: %d Hz — VAD segmenter initialized", frame_rate)

                    segmenter.add_audio(bytes(frame.data))

                    for segment_pcm in segmenter.get_speech_segments():
                        wav_data = _pcm_to_wav(segment_pcm, frame_rate)
                        text = await speech.transcribe(wav_data, "audio/wav")
                        if text.strip():
                            logger.info("Candidate said: %s", text)

                            # Get bot response
                            bot_text = await conversation.handle_candidate_speech(text)
                            if bot_text:
                                logger.info("Bot responds: %s", bot_text)

                                # Synthesize speech and publish to room
                                audio_out = await speech.synthesize(bot_text)
                                if audio_out:
                                    await _publish_audio(room, audio_source, audio_out, TTS_SAMPLE_RATE)

                            # Check for call end conditions
                            if conversation.is_complete():
                                logger.info("Recruiter conversation complete, ending call")
                                break

                            elapsed = time.time() - session_ctx.start_time
                            if elapsed > session_ctx.target_duration_seconds:
                                logger.info("Recruiter time budget exceeded, ending call")
                                break

        def on_track_subscribed(track, publication, participant):
            """Sync wrapper — LiveKit .on() does not support async callbacks."""
            asyncio.create_task(_process_track(track, publication, participant))

        room.on("track_subscribed", on_track_subscribed)

        try:
            await speech.start()

            # Connect to the room
            await room.connect(LIVEKIT_URL, agent_token)
            logger.info("Agent joined room: %s (session=%s)", room_name, session_ctx.session_id)

            # Publish the audio source as a track so the candidate can hear the agent
            try:
                track = rtc.LocalAudioTrack.create_audio_track("aria-agent", audio_source)
                options = rtc.TrackPublishOptions()
                options.source = rtc.TrackSource.SOURCE_MICROPHONE
                await room.local_participant.publish_track(track, options)
                logger.info("Audio track published to room")
            except Exception as pub_err:
                logger.error("Failed to publish audio track: %s", pub_err, exc_info=True)

            # Update backend
            await backend.update_session(int(session_ctx.session_id), {"status": "in_progress"})

            # Start the interview and deliver greeting
            greeting = await conversation.start()
            if greeting:
                audio_out = await speech.synthesize(greeting)
                if audio_out:
                    await _publish_audio(room, audio_source, audio_out, TTS_SAMPLE_RATE)
                    logger.info("Recruiter greeting published for session %s", session_ctx.session_id)

            # Keep the call alive until complete or max duration
            while not conversation.is_complete():
                elapsed = time.time() - session_ctx.start_time
                if elapsed > session_ctx.target_duration_seconds:
                    logger.info("Recruiter max duration reached")
                    break
                await asyncio.sleep(1)

            # Call ended — finalize and notify backend
            duration = int(time.time() - session_ctx.start_time)
            logger.info(
                "Recruiter call ended: session=%s state=%s duration=%ds",
                session_ctx.session_id, session_ctx.current_state.value, duration,
            )

            result = await conversation.end_call()
            await _notify_backend_complete(session_ctx.session_id, result)

        except Exception as e:
            logger.error("Recruiter session %s failed: %s", session_ctx.session_id, e, exc_info=True)
            try:
                await backend.update_session(int(session_ctx.session_id), {
                    "status": "failed",
                    "error_log": str(e),
                })
            except Exception:
                pass
        finally:
            await speech.stop()
            try:
                await room.disconnect()
            except Exception:
                pass

    async def handle_orchestrator_room(self, room_name: str, agent_token: str, orch_ctx: OrchestratorContext):
        """
        Join a LiveKit room and run the Interview Orchestrator.
        This is the primary handler — replaces handle_unified_room for new interviews.
        Uses VAD-driven speech segmentation, real-time answer evaluation,
        and dynamic question planning.
        """
        from livekit import rtc

        room = rtc.Room()
        speech = SpeechClient()
        llm = LLMClient()
        backend = BackendClient()
        orchestrator = InterviewOrchestrator(orch_ctx, llm, speech)

        TTS_SAMPLE_RATE = 16000
        actual_sample_rate: Optional[int] = None
        segmenter: Optional[SpeechSegmenter] = None

        audio_source = rtc.AudioSource(TTS_SAMPLE_RATE, 1)

        async def _process_track(track, publication, participant):
            """Async body for processing a subscribed audio track."""
            nonlocal actual_sample_rate, segmenter
            if hasattr(track, 'kind') and track.kind == 1:  # AUDIO
                logger.info(
                    "Audio track subscribed: participant=%s session=%s",
                    participant.identity, orch_ctx.session_id,
                )
                stream = rtc.AudioStream(track)

                async for event in stream:
                    frame = event.frame
                    frame_rate = frame.sample_rate
                    if actual_sample_rate is None:
                        actual_sample_rate = frame_rate
                        segmenter = SpeechSegmenter(sample_rate=frame_rate)
                        logger.info("Detected audio track sample rate: %d Hz — VAD segmenter initialized", frame_rate)

                    segmenter.add_audio(bytes(frame.data))

                    for segment_pcm in segmenter.get_speech_segments():
                        wav_data = _pcm_to_wav(segment_pcm, frame_rate)
                        text = await speech.transcribe(wav_data, "audio/wav")
                        segment_duration = len(segment_pcm) // 2 / frame_rate
                        if text.strip():
                            logger.info("Candidate said: %s", text)

                            bot_text = await orchestrator.handle_candidate_response(text)
                            if bot_text:
                                logger.info("Bot responds: %s", bot_text)
                                audio_out = await speech.synthesize(bot_text)
                                if audio_out:
                                    await _publish_audio(room, audio_source, audio_out, TTS_SAMPLE_RATE)

                            if orchestrator.is_complete():
                                logger.info("Interview orchestrator complete, ending call")
                                break

                            if orch_ctx.time_remaining < 30:
                                logger.info("Time budget exceeded, ending call")
                                break
                        elif segment_duration > 0.5:
                            # Speech was detected but STT returned empty — ask the candidate to repeat
                            logger.warning(
                                "STT returned empty for %.1fs speech segment; asking candidate to repeat",
                                segment_duration,
                            )
                            repeat_prompt = "I'm sorry, I didn't catch that. Could you please repeat?"
                            audio_out = await speech.synthesize(repeat_prompt)
                            if audio_out:
                                await _publish_audio(room, audio_source, audio_out, TTS_SAMPLE_RATE)

        def on_track_subscribed(track, publication, participant):
            asyncio.create_task(_process_track(track, publication, participant))

        room.on("track_subscribed", on_track_subscribed)

        try:
            await speech.start()
            orch_ctx.started_at = time.time()

            await room.connect(LIVEKIT_URL, agent_token)
            logger.info("Orchestrator agent joined room: %s (session=%s)", room_name, orch_ctx.session_id)

            try:
                track = rtc.LocalAudioTrack.create_audio_track("aria-agent", audio_source)
                options = rtc.TrackPublishOptions()
                options.source = rtc.TrackSource.SOURCE_MICROPHONE
                await room.local_participant.publish_track(track, options)
                logger.info("Audio track published to room")
            except Exception as pub_err:
                logger.error("Failed to publish audio track: %s", pub_err, exc_info=True)

            try:
                await backend.update_session(int(orch_ctx.session_id), {"status": "in_progress"})
            except Exception:
                pass

            # Start the interview with the greeting
            greeting = await orchestrator.start()
            orch_ctx.transcript.append({
                "speaker": "bot", "text": greeting,
                "timestamp": 0.0, "stage": "introduction",
            })
            logger.info("Greeting text: %s", greeting[:100])
            audio_out = await speech.synthesize(greeting)
            if audio_out:
                logger.info("TTS returned %d bytes for greeting", len(audio_out))
                await _publish_audio(room, audio_source, audio_out, TTS_SAMPLE_RATE)
                logger.info("Greeting published for session %s", orch_ctx.session_id)
            else:
                logger.error("TTS returned empty audio for greeting — speech service may be unreachable at %s", SPEECH_SERVICE_URL)

            # Keep the call alive until interview ends or max duration
            while not orchestrator.is_complete():
                if orch_ctx.time_remaining < 10:
                    logger.info("Max duration reached for session %s", orch_ctx.session_id)
                    break
                await asyncio.sleep(1)

            # Call ended — finalize and notify backend
            duration = int(orch_ctx.elapsed)
            logger.info(
                "Interview ended: session=%s duration=%ds answers=%d",
                orch_ctx.session_id, duration, len(orch_ctx.questions_responses),
            )

            result = orchestrator.get_result()
            await _notify_backend_complete(orch_ctx.session_id, result)

        except Exception as e:
            logger.error("Orchestrator session %s failed: %s", orch_ctx.session_id, e, exc_info=True)
            try:
                await backend.update_session(int(orch_ctx.session_id), {
                    "status": "failed",
                    "error_log": str(e),
                })
            except Exception:
                pass
        finally:
            await speech.stop()
            try:
                await room.disconnect()
            except Exception:
                pass

    async def dispatch_and_run(self, session_ctx, room_info: dict, depth: str = "quick"):
        """Dispatch a call and run the appropriate agent handler in the room."""
        if isinstance(session_ctx, OrchestratorContext):
            handler = self.handle_orchestrator_room(
                room_info["room_name"],
                room_info["agent_token"],
                session_ctx,
            )
        elif isinstance(session_ctx, InterviewContext):
            handler = self.handle_unified_room(
                room_info["room_name"],
                room_info["agent_token"],
                session_ctx,
            )
        else:
            # Legacy fallback for ScreeningContext / RecruiterContext
            handler = self.handle_unified_room(
                room_info["room_name"],
                room_info["agent_token"],
                session_ctx,
            )
        sid = str(getattr(session_ctx, 'session_id', 'unknown'))
        task = asyncio.create_task(handler)
        self._active_sessions[sid] = task
        task.add_done_callback(
            lambda t: self._active_sessions.pop(sid, None)
        )


# Shared worker instance
worker = VoiceAgentWorker()


# ─── FastAPI Dispatch Server ──────────────────────────────────────────────────

app = FastAPI(title="ARIA Voice Agent", version="1.0.0")

sip_dispatcher = LiveKitSIPDispatcher()


# Backward-compat mapping: legacy mode → new depth
_MODE_TO_DEPTH = {
    "screening": "quick",
    "recruiter": "deep",
}


class DispatchRequest(BaseModel):
    session_id: int
    phone_number: str
    candidate_name: str
    tenant_id: int
    candidate_id: int
    jd_title: Optional[str] = None
    jd_must_have_skills: Optional[list] = None
    depth: str = "quick"     # "quick" | "standard" | "deep"
    mode: Optional[str] = None  # DEPRECATED — maps to depth for backward compat
    interview_strategy: Optional[dict] = None
    interview_config: Optional[dict] = None

    @property
    def effective_depth(self) -> str:
        """Resolve depth, falling back to legacy mode field."""
        if self.mode and self.mode in _MODE_TO_DEPTH:
            return _MODE_TO_DEPTH[self.mode]
        return self.depth


class DispatchResponse(BaseModel):
    success: bool
    room_name: Optional[str] = None
    message: str


@app.get("/health")
async def health():
    return {"status": "ok", "service": "voice-agent"}


@app.post("/dispatch", response_model=DispatchResponse)
async def dispatch_call(req: DispatchRequest):
    """
    Triggered by backend scheduler when it's time to place a call.
    Creates a LiveKit room and initiates a SIP outbound call to the candidate.
    The agent worker then joins the room and runs the conversation.
    """
    try:
        # 1. Create room + SIP outbound call
        room_info = await sip_dispatcher.dispatch_call(
            session_id=req.session_id,
            phone_number=req.phone_number,
            candidate_name=req.candidate_name,
        )

        # 2. Fetch tenant config and candidate context
        backend = BackendClient()
        tenant_config = await backend.get_tenant_config(req.tenant_id)
        candidate_info = await backend.get_candidate_info(req.tenant_id, req.candidate_id)

        # 3. Build orchestrator context with full candidate data
        depth = req.effective_depth
        # Prefer the actual configured duration; fall back to depth-based mapping
        interview_config = req.interview_config or {}
        duration_minutes = interview_config.get("duration_minutes")
        if duration_minutes and isinstance(duration_minutes, (int, float)) and duration_minutes > 0:
            duration_s = int(duration_minutes * 60)
        else:
            duration_s = {"quick": 300, "standard": 900, "deep": 1200}.get(depth, 1200)

        orch_ctx = OrchestratorContext(
            session_id=str(req.session_id),
            candidate_name=req.candidate_name or "there",
            company_name=tenant_config.get("company_name", "the company"),
            jd_title=req.jd_title or "",
            bot_name=tenant_config.get("bot_name", "ARIA"),
            tenant_id=req.tenant_id,
            candidate_id=req.candidate_id,
            phone_number=req.phone_number,
            candidate_context=candidate_info,
            role_context={
                "title": req.jd_title or "",
                "required_skills": req.jd_must_have_skills or [],
            },
            screening_result=req.interview_strategy or {},
            total_duration_s=duration_s,
        )

        # 4. Launch agent worker in the room (non-blocking)
        await worker.dispatch_and_run(orch_ctx, room_info, depth=depth)

        return DispatchResponse(
            success=True,
            room_name=room_info["room_name"],
            message=f"SIP call initiated to {req.phone_number} in room {room_info['room_name']}",
        )

    except Exception as e:
        logger.error("Dispatch failed for session %d: %s", req.session_id, e, exc_info=True)
        # Update backend session status on failure
        try:
            backend = BackendClient()
            await backend.update_session(req.session_id, {
                "status": "failed",
                "error_log": f"Dispatch failed: {str(e)}",
            })
        except Exception:
            pass

        return DispatchResponse(
            success=False,
            message=f"Dispatch failed: {str(e)}",
        )


# ─── Main ──────────────────────────────────────────────────────────────────────

async def main():
    """Voice Agent entrypoint — starts FastAPI dispatch server."""
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    logger.info("════════════════════════════════════════════")
    logger.info("  ARIA Voice Agent — Starting")
    logger.info("  Speech Service: %s", SPEECH_SERVICE_URL)
    logger.info("  LiveKit: %s", LIVEKIT_URL)
    logger.info("  Ollama: %s (model: %s)", OLLAMA_BASE_URL, OLLAMA_MODEL)
    logger.info("  SIP Trunk: %s (outbound: %s, termination: %s)", SIP_TRUNK_ID, SIP_OUTBOUND_NUMBER, SIP_TERMINATION_ADDRESS)
    logger.info("  Dispatch API: http://0.0.0.0:%d", AGENT_PORT)
    logger.info("════════════════════════════════════════════")

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=AGENT_PORT,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
