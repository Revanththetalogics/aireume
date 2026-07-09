"""Low-latency speech playback helpers (sentence streaming + barge-in)."""
from __future__ import annotations

import asyncio
import logging
import random
import re
import time
from typing import TYPE_CHECKING, Awaitable, Callable, Optional

if TYPE_CHECKING:
    from app.voice_agent.turn_telemetry import TurnTelemetryCollector

logger = logging.getLogger("voice_agent.speech_pipeline")

PublishFn = Callable[..., Awaitable[None]]

IMMEDIATE_ACKS = [
    "Got it.",
    "Thanks.",
    "Okay.",
    "I see.",
    "Right.",
    "Makes sense.",
    "Understood.",
]


class PlaybackGate:
    """Cooperative cancellation for in-progress TTS playback (barge-in)."""

    def __init__(self) -> None:
        self.is_playing = False
        self._cancelled = False

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def reset(self) -> None:
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True


def pick_immediate_ack() -> str:
    """Short phrase to play while the LLM is thinking."""
    return random.choice(IMMEDIATE_ACKS)


def clean_tts_text(text: str) -> str:
    """Strip markdown and URLs so TTS sounds natural on phone calls."""
    text = (text or "").strip()
    if not text:
        return ""
    text = re.sub(r"\*+([^*]+)\*+", r"\1", text)
    text = re.sub(r"#+\s*", "", text)
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def split_sentences(text: str) -> list[str]:
    """Split bot text into speakable sentence chunks."""
    text = (text or "").strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [part.strip() for part in parts if part.strip()]


async def speak_text(
    text: str,
    speech,
    room,
    audio_source,
    publish_fn: PublishFn,
    playback_gate: PlaybackGate,
    *,
    sample_rate: int = 16000,
    voice: str = "female",
    telemetry: Optional["TurnTelemetryCollector"] = None,
) -> None:
    """Synthesize and publish text sentence-by-sentence with TTS prefetch."""
    text = clean_tts_text(text)
    sentences = split_sentences(text)
    if not sentences:
        return

    playback_gate.reset()
    playback_gate.is_playing = True
    total_tts_ms = 0.0
    total_playback_ms = 0.0
    try:
        prefetch_task: asyncio.Task | None = None
        prefetched_audio: bytes | None = None

        for index, sentence in enumerate(sentences):
            if playback_gate.cancelled:
                logger.debug("Playback cancelled before sentence TTS")
                break

            if prefetch_task is not None:
                prefetched_audio = await prefetch_task
                prefetch_task = None
                audio = prefetched_audio
            else:
                tts_start = time.monotonic()
                audio = await speech.synthesize(sentence, voice=voice)
                total_tts_ms += (time.monotonic() - tts_start) * 1000

            next_index = index + 1
            if next_index < len(sentences) and not playback_gate.cancelled:
                next_sentence = sentences[next_index]
                prefetch_task = asyncio.create_task(
                    speech.synthesize(next_sentence, voice=voice)
                )

            if not audio or playback_gate.cancelled:
                if prefetch_task:
                    prefetch_task.cancel()
                continue

            playback_start = time.monotonic()
            await publish_fn(
                room,
                audio_source,
                audio,
                sample_rate,
                playback_gate,
            )
            total_playback_ms += (time.monotonic() - playback_start) * 1000

        if prefetch_task and not prefetch_task.done():
            prefetch_task.cancel()
    finally:
        playback_gate.is_playing = False
        if telemetry is not None:
            if total_tts_ms:
                telemetry.record("tts_ms", round(total_tts_ms, 1))
            if total_playback_ms:
                telemetry.record("playback_ms", round(total_playback_ms, 1))


async def speak_with_filler(
    *,
    filler: str,
    response_coro,
    speech,
    room,
    audio_source,
    publish_fn: PublishFn,
    playback_gate: PlaybackGate,
    sample_rate: int = 16000,
    voice: str = "female",
) -> Optional[str]:
    """
    Play a short acknowledgment while the LLM runs, then speak the full response.

    Returns the response text (or None).
    """
    filler_task: asyncio.Task | None = None
    if filler:
        filler_task = asyncio.create_task(
            speak_text(
                filler,
                speech,
                room,
                audio_source,
                publish_fn,
                playback_gate,
                sample_rate=sample_rate,
                voice=voice,
            )
        )

    response_text = await response_coro

    if filler_task:
        await filler_task

    if response_text:
        await speak_text(
            response_text,
            speech,
            room,
            audio_source,
            publish_fn,
            playback_gate,
            sample_rate=sample_rate,
            voice=voice,
        )

    return response_text


async def barge_in(playback_gate: PlaybackGate, *, settle_ms: int = 50) -> None:
    """Stop current agent playback when the candidate starts speaking."""
    if playback_gate.is_playing:
        playback_gate.cancel()
        await asyncio.sleep(settle_ms / 1000.0)
