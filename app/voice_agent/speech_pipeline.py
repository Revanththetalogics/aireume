"""Low-latency speech playback helpers (sentence streaming + barge-in)."""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Awaitable, Callable, Optional

logger = logging.getLogger("voice_agent.speech_pipeline")

PublishFn = Callable[..., Awaitable[None]]


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
) -> None:
    """Synthesize and publish text sentence-by-sentence for lower time-to-first-audio."""
    sentences = split_sentences(text)
    if not sentences:
        return

    playback_gate.reset()
    playback_gate.is_playing = True
    try:
        for sentence in sentences:
            if playback_gate.cancelled:
                logger.debug("Playback cancelled before sentence TTS")
                break
            audio = await speech.synthesize(sentence, voice=voice)
            if not audio or playback_gate.cancelled:
                continue
            await publish_fn(
                room,
                audio_source,
                audio,
                sample_rate,
                playback_gate,
            )
    finally:
        playback_gate.is_playing = False


async def barge_in(playback_gate: PlaybackGate, *, settle_ms: int = 50) -> None:
    """Stop current agent playback when the candidate starts speaking."""
    if playback_gate.is_playing:
        playback_gate.cancel()
        await asyncio.sleep(settle_ms / 1000.0)
