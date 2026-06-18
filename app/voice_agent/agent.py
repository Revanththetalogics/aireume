"""
Voice Agent — LiveKit Agents process for voice screening.

Handles:
  • HTTP dispatch API (backend → agent: create room + SIP outbound call)
  • LiveKit Agent Worker (auto-joins rooms, runs conversation)
  • Conversation state machine (greeting → consent → screening → wrap-up)
  • Integration with Speech Service (STT/TTS) and Ollama Cloud (LLM)
"""
import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

load_dotenv()

logger = logging.getLogger("voice_agent")

# ─── Configuration ─────────────────────────────────────────────────────────────

SPEECH_SERVICE_URL = os.getenv("SPEECH_SERVICE_URL", "http://speech-service:8001")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")
ARIA_BACKEND_URL = os.getenv("ARIA_BACKEND_URL", "http://backend:8000")
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://livekit:7880")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
SIP_TRUNK_ID = os.getenv("SIP_TRUNK_ID", "twilio-aria")
SIP_OUTBOUND_NUMBER = os.getenv("SIP_OUTBOUND_NUMBER", "+18722789563")
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

    def _create_agent_token(self, room_name: str, identity: str = "aria-agent") -> str:
        """Generate a LiveKit access token for the agent participant."""
        from livekit.api import AccessToken, VideoGrant
        token = AccessToken(self.api_key, self.api_secret)
        token.with_identity(identity)
        token.with_name("ARIA Assistant")
        grant = VideoGrant(
            room=room_name,
            room_join=True,
            can_publish=True,
            can_subscribe=True,
        )
        token.with_grants(grant)
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
            # 1. Create room
            await api.room.create_room(name=room_name, empty_timeout=120, max_participants=2)
            logger.info("Room created: %s", room_name)

            # 2. Create SIP participant (triggers outbound PSTN call)
            sip_req = CreateSIPParticipantRequest(
                sip_trunk_id=SIP_TRUNK_ID,
                sip_call_to=phone_number,
                room_name=room_name,
                participant_identity=participant_identity,
                participant_name=candidate_name,
                hide_phone_number=False,
            )
            await api.sip.create_sip_participant(sip_req)
            logger.info(
                "SIP participant created: room=%s phone=%s trunk=%s",
                room_name, phone_number, SIP_TRUNK_ID,
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

        # Audio buffer for STT (accumulate ~3s of audio per chunk)
        audio_buffer = bytearray()
        SAMPLE_RATE = 16000
        CHUNK_DURATION_SEC = 3.0
        CHUNK_SIZE = int(SAMPLE_RATE * 2 * CHUNK_DURATION_SEC)  # 16-bit samples

        async def on_track_subscribed(track, publication, participant):
            """Called when a participant's audio track is subscribed."""
            if hasattr(track, 'kind') and track.kind == 1:  # AUDIO
                logger.info(
                    "Audio track subscribed: participant=%s session=%d",
                    participant.identity, session_ctx.session_id,
                )
                stream = rtc.AudioStream(track)

                async for event in stream:
                    frame = event.frame
                    audio_buffer.extend(frame.data)

                    if len(audio_buffer) >= CHUNK_SIZE:
                        chunk = bytes(audio_buffer[:CHUNK_SIZE])
                        audio_buffer.clear()

                        # Transcribe
                        text = await speech.transcribe(chunk, "audio/wav")
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

                                # Synthesize speech
                                audio_out = await speech.synthesize(bot_text)
                                if audio_out:
                                    # Publish audio back to room
                                    source = rtc.AudioSource(SAMPLE_RATE, 1)
                                    audio_frame = rtc.AudioFrame(
                                        data=audio_out,
                                        sample_rate=SAMPLE_RATE,
                                        num_channels=1,
                                        samples_per_channel=len(audio_out) // 2,
                                    )
                                    await source.capture_frame(audio_frame)

                            # Advance conversation state
                            engine.advance_state()

                            # Check for call end conditions
                            if not engine.check_time_budget():
                                logger.info("Time budget exceeded, ending call")
                                session_ctx.state = CallState.ENDED
                            if "reschedule" in text.lower() or "not a good time" in text.lower():
                                session_ctx.state = CallState.ENDED

        room.on("track_subscribed", on_track_subscribed)

        try:
            await speech.start()
            session_ctx.call_start_time = time.time()

            # Connect to the room
            await room.connect(LIVEKIT_URL, agent_token)
            logger.info("Agent joined room: %s (session=%d)", room_name, session_ctx.session_id)

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
                logger.info("Playing greeting for session %d", session_ctx.session_id)

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
                "transcript": json.dumps(session_ctx.transcript),
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

    async def dispatch_and_run(self, session_ctx: ScreeningContext, room_info: dict):
        """Dispatch a call and run the agent in the room."""
        task = asyncio.create_task(
            self.handle_room(
                room_info["room_name"],
                room_info["agent_token"],
                session_ctx,
            )
        )
        self._active_sessions[session_ctx.session_id] = task
        task.add_done_callback(
            lambda t: self._active_sessions.pop(session_ctx.session_id, None)
        )


# Shared worker instance
worker = VoiceAgentWorker()


# ─── FastAPI Dispatch Server ──────────────────────────────────────────────────

app = FastAPI(title="ARIA Voice Agent", version="1.0.0")

sip_dispatcher = LiveKitSIPDispatcher()


class DispatchRequest(BaseModel):
    session_id: int
    phone_number: str
    candidate_name: str
    tenant_id: int
    candidate_id: int
    jd_title: Optional[str] = None
    jd_must_have_skills: Optional[list] = None


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

        # 2. Build screening context
        ctx = ScreeningContext(
            session_id=req.session_id,
            tenant_id=req.tenant_id,
            candidate_id=req.candidate_id,
            candidate_name=req.candidate_name,
            phone_number=req.phone_number,
            jd_title=req.jd_title,
            jd_must_have_skills=req.jd_must_have_skills or [],
        )

        # 3. Launch agent worker in the room (non-blocking)
        await worker.dispatch_and_run(ctx, room_info)

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
    logger.info("  SIP Trunk: %s (outbound: %s)", SIP_TRUNK_ID, SIP_OUTBOUND_NUMBER)
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
