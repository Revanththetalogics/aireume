"""
ARIA Voice Screening — LiveKit Cloud Agent (Option B).

Pipeline (matches LiveKit Cloud dashboard):
  STT: Deepgram Nova-2
  TTS: Cartesia Sonic
  Turn detection: LiveKit Inference VAD + built-in turn handling

Screening logic stays in ARIA orchestrators (kit-driven or dynamic).
The cloud LLM is bypassed for kit mode via a custom ``llm_node``.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, AsyncIterable, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("aria.cloud_agent")

AGENT_NAME = os.getenv("LIVEKIT_AGENT_NAME", "ARIA")
STT_MODEL = os.getenv("LIVEKIT_STT_MODEL", "deepgram/nova-2")
STT_LANGUAGE = os.getenv("LIVEKIT_STT_LANGUAGE", "en")
TTS_MODEL = os.getenv("LIVEKIT_TTS_MODEL", "cartesia/sonic-1")
TTS_VOICE = os.getenv("LIVEKIT_TTS_VOICE", "").strip() or None
LLM_MODEL = os.getenv("LIVEKIT_LLM_MODEL", "google/gemma-3-27b-it")
ARIA_BACKEND_URL = os.getenv("ARIA_BACKEND_URL", "http://backend:8000")
INTERNAL_SERVICE_SECRET = os.getenv("INTERNAL_SERVICE_SECRET", "dev-internal-service-secret")
INTERNAL_HEADERS = {"X-Internal-Secret": INTERNAL_SERVICE_SECRET}


def _extract_last_user_message(chat_ctx) -> str:
    items = list(getattr(chat_ctx, "items", []) or [])
    for item in reversed(items):
        role = getattr(item, "role", None)
        if role == "user":
            text = getattr(item, "text_content", None) or getattr(item, "content", "")
            if isinstance(text, list):
                text = " ".join(str(part) for part in text)
            return str(text or "").strip()
    return ""


async def _notify_backend_complete(session_id: str, result: dict, backend_url: str) -> None:
    import httpx

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{backend_url}/api/interviews/internal/complete",
                json={"session_id": session_id, "result": result},
                headers=INTERNAL_HEADERS,
            )
            resp.raise_for_status()
            logger.info("Backend notified: session=%s", session_id)
    except Exception as e:
        logger.error("Failed to notify backend session=%s: %s", session_id, e)


async def _update_session(session_id: int, updates: dict, backend_url: str) -> None:
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.patch(
                f"{backend_url}/api/voice/sessions/{session_id}",
                json=updates,
                headers=INTERNAL_HEADERS,
            )
    except Exception as e:
        logger.warning("Session update failed session=%s: %s", session_id, e)


def _build_orchestrator(metadata: dict[str, Any]):
    from app.voice_agent.kit_orchestrator import KitDrivenOrchestrator
    from app.voice_agent.orchestrator import InterviewOrchestrator, OrchestratorContext

    interview_config = metadata.get("interview_config") or {}
    depth = metadata.get("depth") or "quick"
    duration_minutes = interview_config.get("duration_minutes")
    if duration_minutes and isinstance(duration_minutes, (int, float)) and duration_minutes > 0:
        duration_s = int(duration_minutes * 60)
    else:
        duration_s = {"quick": 300, "standard": 900, "deep": 1200}.get(depth, 1200)

    tenant_config = metadata.get("tenant_config") or {}
    orch_ctx = OrchestratorContext(
        session_id=str(metadata["session_id"]),
        candidate_name=metadata.get("candidate_name") or "there",
        company_name=tenant_config.get("company_name", "the company"),
        jd_title=metadata.get("jd_title") or "",
        bot_name=tenant_config.get("bot_name", "ARIA"),
        tenant_id=metadata.get("tenant_id"),
        candidate_id=metadata.get("candidate_id"),
        phone_number=metadata.get("phone_number"),
        candidate_context=metadata.get("candidate_context") or {},
        role_context={
            "title": metadata.get("jd_title") or "",
            "required_skills": metadata.get("jd_must_have_skills") or [],
        },
        screening_result=metadata.get("interview_strategy") or {},
        total_duration_s=duration_s,
    )

    kit_questions = []
    interview_kit = metadata.get("interview_kit") or {}
    if isinstance(interview_kit, dict):
        kit_questions = interview_kit.get("questions") or []

    if kit_questions:
        logger.info(
            "Kit-driven cloud session=%s questions=%d",
            orch_ctx.session_id,
            len(kit_questions),
        )
        return KitDrivenOrchestrator(orch_ctx, kit_questions), orch_ctx, "kit"

    logger.warning(
        "No kit questions for session=%s — using dynamic orchestrator",
        orch_ctx.session_id,
    )
    return InterviewOrchestrator(orch_ctx, None, None), orch_ctx, "dynamic"


def _create_server():
    from livekit.agents import Agent, AgentServer, AgentSession, JobContext, cli, inference

    try:
        from livekit.agents.voice import room_io
        RoomInputOptions = room_io.RoomInputOptions
    except ImportError:
        RoomInputOptions = None  # type: ignore

    try:
        from livekit.plugins import noise_cancellation
    except ImportError:
        noise_cancellation = None  # type: ignore

    server = AgentServer()

    class ScreeningAgent(Agent):
        """ARIA screening agent — orchestrator drives replies, cloud handles STT/TTS."""

        def __init__(self, orchestrator, orch_ctx, mode: str, **kwargs):
            super().__init__(**kwargs)
            self.orchestrator = orchestrator
            self.orch_ctx = orch_ctx
            self.mode = mode
            self._greeting_done = False

        async def on_enter(self) -> None:
            greeting = await self.orchestrator.start()
            self.orch_ctx.transcript.append(
                {
                    "speaker": "bot",
                    "text": greeting,
                    "timestamp": 0.0,
                    "stage": "introduction",
                }
            )
            await self.session.say(greeting, allow_interruptions=True)
            self._greeting_done = True
            logger.info("Greeting sent session=%s", self.orch_ctx.session_id)

        async def llm_node(self, chat_ctx, tools, model_settings) -> AsyncIterable[str]:
            user_text = _extract_last_user_message(chat_ctx)
            if not user_text:
                return

            bot_text = await self.orchestrator.handle_candidate_response(user_text)
            if bot_text:
                yield bot_text
            if self.orchestrator.is_complete():
                logger.info("Interview complete session=%s", self.orch_ctx.session_id)

    @server.rtc_session(agent_name=AGENT_NAME)
    async def entrypoint(ctx: JobContext) -> None:
        await ctx.connect()
        raw = ctx.job.metadata or "{}"
        metadata = json.loads(raw) if isinstance(raw, str) else (raw or {})
        session_id = int(metadata.get("session_id") or 0)
        logger.info("Cloud agent job started session=%s room=%s", session_id, ctx.room.name)

        orchestrator, orch_ctx, mode = _build_orchestrator(metadata)
        backend_url = metadata.get("aria_backend_url") or ARIA_BACKEND_URL
        await _update_session(session_id, {"status": "in_progress"}, backend_url)

        tts_kwargs: dict[str, Any] = {}
        if TTS_VOICE:
            tts_kwargs["voice"] = TTS_VOICE

        session = AgentSession(
            stt=inference.STT(STT_MODEL, language=STT_LANGUAGE),
            tts=inference.TTS(TTS_MODEL, **tts_kwargs),
            vad=inference.VAD(),
            llm=inference.LLM(LLM_MODEL),
            min_endpointing_delay=0.4,
            max_endpointing_delay=1.2,
        )

        agent = ScreeningAgent(
            orchestrator=orchestrator,
            orch_ctx=orch_ctx,
            mode=mode,
            instructions=(
                "You are ARIA, a professional phone screener for hiring. "
                "Keep responses concise and conversational for phone calls."
            ),
        )

        start_kwargs: dict[str, Any] = {"agent": agent, "room": ctx.room}
        if RoomInputOptions and noise_cancellation:
            start_kwargs["room_input_options"] = RoomInputOptions(
                noise_cancellation=noise_cancellation.BVCTelephony(),
            )

        await session.start(**start_kwargs)

        try:
            while not orchestrator.is_complete():
                if orch_ctx.time_remaining < 10:
                    logger.info("Time budget reached session=%s", session_id)
                    break
                await asyncio.sleep(1)
        finally:
            result = orchestrator.get_result()
            result["voice_pipeline"] = "livekit_cloud"
            result["stt_model"] = STT_MODEL
            result["tts_model"] = TTS_MODEL
            await _notify_backend_complete(orch_ctx.session_id, result, backend_url)
            await _update_session(
                session_id,
                {
                    "status": "completed",
                    "duration_seconds": int(orch_ctx.elapsed),
                },
                backend_url,
            )
            logger.info(
                "Cloud session ended session=%s duration=%ds answers=%d",
                session_id,
                int(orch_ctx.elapsed),
                len(orch_ctx.questions_responses),
            )

    return server, cli


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    server, cli = _create_server()
    logger.info("ARIA Cloud Agent — agent_name=%s stt=%s tts=%s", AGENT_NAME, STT_MODEL, TTS_MODEL)
    cli.run_app(server)


if __name__ == "__main__":
    main()
