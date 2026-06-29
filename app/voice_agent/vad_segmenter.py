"""
Speech Segmenter — energy-based VAD for real-time speech detection.

Replaces the fixed 3-second audio buffer with adaptive speech segmentation.
Detects when a candidate starts and stops speaking, then yields complete
speech segments for STT transcription. This cuts ~3s latency and enables
natural turn-taking.

Usage:
    segmenter = SpeechSegmenter(sample_rate=48000)
    segmenter.add_audio(frame_data_bytes)
    for segment in segmenter.get_speech_segments():
        # segment is raw PCM bytes ready for STT
        ...
"""

import logging
import struct
from collections import deque
from typing import Optional

logger = logging.getLogger("voice_agent.vad")


class SpeechSegmenter:
    """
    Energy-based speech segmenter for real-time audio processing.

    Accumulates incoming audio frames, detects speech using RMS energy,
    and yields complete speech segments when the candidate pauses.

    Parameters:
        sample_rate: Audio sample rate (e.g., 48000 from LiveKit Opus)
        energy_threshold: RMS threshold for speech detection (0-32768 for 16-bit)
        min_speech_duration_ms: Minimum speech duration before activating (avoid noise bursts)
        silence_duration_ms: Silence duration after speech to trigger end-of-segment
        max_speech_duration_s: Maximum speech segment length (safety cap)
    """

    def __init__(
        self,
        sample_rate: int = 48000,
        energy_threshold: float = 300.0,
        min_speech_duration_ms: int = 250,
        silence_duration_ms: int = 1200,
        max_speech_duration_s: int = 30,
    ):
        self.sample_rate = sample_rate
        self.energy_threshold = energy_threshold
        self.min_speech_duration_ms = min_speech_duration_ms
        self.silence_duration_ms = silence_duration_ms
        self.max_speech_duration_s = max_speech_duration_s

        # State
        self._audio_buffer = bytearray()
        self._speech_buffer = bytearray()
        self._is_speaking = False
        self._speech_start_samples = 0
        self._silence_samples = 0
        self._total_samples = 0
        self._completed_segments: deque = deque()

        # Derived constants
        self._min_speech_samples = int(sample_rate * min_speech_duration_ms / 1000)
        self._silence_end_samples = int(sample_rate * silence_duration_ms / 1000)
        self._max_speech_samples = int(sample_rate * max_speech_duration_s)

    def add_audio(self, pcm_data: bytes) -> None:
        """
        Add a chunk of raw 16-bit PCM audio data.
        The segmenter will detect speech and queue completed segments.
        """
        self._audio_buffer.extend(pcm_data)

        # Process in 20ms frames for consistent VAD analysis
        frame_samples = int(self.sample_rate * 0.02)  # 20ms
        frame_bytes = frame_samples * 2  # 16-bit = 2 bytes per sample

        while len(self._audio_buffer) >= frame_bytes:
            frame = bytes(self._audio_buffer[:frame_bytes])
            del self._audio_buffer[:frame_bytes]
            self._process_frame(frame, frame_samples)

    def _process_frame(self, frame: bytes, frame_samples: int) -> None:
        """Process a single 20ms audio frame for speech detection."""
        # Calculate RMS energy
        samples = struct.unpack(f'<{frame_samples}h', frame)
        sum_sq = sum(s * s for s in samples)
        rms = (sum_sq / frame_samples) ** 0.5

        self._total_samples += frame_samples

        if rms >= self.energy_threshold:
            # Speech detected
            if not self._is_speaking:
                self._is_speaking = True
                self._speech_start_samples = self._total_samples
                logger.debug("Speech started at %.2fs", self._total_samples / self.sample_rate)

            self._speech_buffer.extend(frame)
            self._silence_samples = 0

            # Safety cap: if speech is too long, force a segment
            if len(self._speech_buffer) // 2 >= self._max_speech_samples:
                self._emit_segment()
        else:
            # Silence detected
            if self._is_speaking:
                self._speech_buffer.extend(frame)
                self._silence_samples += frame_samples

                # Check if silence duration exceeds threshold
                if self._silence_samples >= self._silence_end_samples:
                    # Check if speech was long enough (not just noise)
                    speech_samples = len(self._speech_buffer) // 2 - self._silence_samples
                    if speech_samples >= self._min_speech_samples:
                        self._emit_segment()
                    else:
                        # Too short, discard
                        logger.debug("Speech too short (%dms), discarding",
                                     speech_samples * 1000 // self.sample_rate)
                        self._speech_buffer.clear()

                    self._is_speaking = False
                    self._silence_samples = 0

    def _emit_segment(self) -> None:
        """Emit the current speech buffer as a completed segment."""
        if not self._speech_buffer:
            return

        # Trim trailing silence from the segment
        silence_bytes = self._silence_samples * 2
        if silence_bytes > 0 and silence_bytes < len(self._speech_buffer):
            segment = bytes(self._speech_buffer[:-silence_bytes])
        else:
            segment = bytes(self._speech_buffer)

        if segment:
            duration = len(segment) // 2 / self.sample_rate
            logger.info(
                "Speech segment: %.1fs (%d bytes, %dHz)",
                duration, len(segment), self.sample_rate,
            )
            self._completed_segments.append(segment)

        self._speech_buffer.clear()

    def get_speech_segments(self) -> list:
        """
        Return all completed speech segments (raw PCM bytes).
        Clears the internal queue.
        """
        segments = list(self._completed_segments)
        self._completed_segments.clear()
        return segments

    def has_pending_speech(self) -> bool:
        """Check if there's an active speech segment being accumulated."""
        return self._is_speaking

    def flush(self) -> Optional[bytes]:
        """
        Force-emit any in-progress speech segment.
        Called when the call is ending or after a long timeout.
        """
        if self._speech_buffer:
            speech_samples = len(self._speech_buffer) // 2 - self._silence_samples
            if speech_samples >= self._min_speech_samples:
                self._emit_segment()
                segments = self.get_speech_segments()
                return segments[0] if segments else None
            else:
                self._speech_buffer.clear()
        return None

    def reset(self) -> None:
        """Reset all state for a new call."""
        self._audio_buffer.clear()
        self._speech_buffer.clear()
        self._is_speaking = False
        self._speech_start_samples = 0
        self._silence_samples = 0
        self._total_samples = 0
        self._completed_segments.clear()
