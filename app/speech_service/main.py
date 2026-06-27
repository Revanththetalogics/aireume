"""
Speech Service — CPU-optimized inference for STT, TTS, and VAD.

Endpoints:
  POST /stt/transcribe       — Audio bytes → text (OpenAI Whisper base)
  POST /tts/synthesize       — Text → audio bytes (Kokoro TTS, Edge TTS fallback)
  POST /vad/detect           — Audio bytes → speech/silence segments (Silero VAD v5)
  GET  /health               — Model readiness probe
"""
import io
import logging
import time
from contextlib import asynccontextmanager

import numpy as np
import torch
import torchaudio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger("speech_service")

# ─── Global model holders ─────────────────────────────────────────────────────

whisper_model = None
vad_model = None
vad_utils = None
kokoro_pipeline = None

SAMPLE_RATE = 16000  # All models use 16 kHz
KOKORO_SAMPLE_RATE = 24000  # Kokoro outputs at 24 kHz

# Kokoro voice mapping (American English voices)
KOKORO_VOICES = {
    "female": "af_heart",
    "male": "am_michael",
}

# Edge TTS voice mapping (fallback)
EDGE_TTS_VOICES = {
    "female": "en-US-JennyNeural",
    "male": "en-US-GuyNeural",
}

# ─── Model loading ────────────────────────────────────────────────────────────

def load_stt():
    """Load OpenAI Whisper tiny model — fast on CPU (~0.5s for 3s audio)."""
    global whisper_model
    try:
        import whisper
        model_name = "tiny"  # 39M params, ~0.5s inference for 3s audio on CPU
        logger.info("Loading Whisper model: %s", model_name)
        whisper_model = whisper.load_model(model_name, device="cpu")
        logger.info("Whisper model loaded successfully")
        return True
    except Exception as e:
        logger.error("Failed to load Whisper model: %s", e)
        return False


def load_tts():
    """Load Kokoro TTS pipeline — CPU-based, professional voice."""
    global kokoro_pipeline
    try:
        from kokoro import KPipeline
        logger.info("Loading Kokoro TTS pipeline (lang_code='a')")
        kokoro_pipeline = KPipeline(lang_code='a')
        logger.info("Kokoro TTS pipeline loaded successfully")
        return True
    except Exception as e:
        logger.error("Failed to load Kokoro TTS: %s", e)
        return False


def load_vad():
    """Load Silero VAD v5 — 2 MB, industry standard."""
    global vad_model, vad_utils
    try:
        logger.info("Loading Silero VAD v5")
        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            trust_repo=True,
        )
        vad_model = model
        vad_utils = utils
        logger.info("Silero VAD loaded successfully")
        return True
    except Exception as e:
        logger.error("Failed to load VAD model: %s", e)
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models on startup. Kokoro TTS loads locally, Edge TTS is cloud fallback."""
    logger.info("════════════════════════════════════════════")
    logger.info("  Speech Service — Starting model warmup")
    logger.info("════════════════════════════════════════════")

    start = time.time()
    results = {}

    results["stt"] = load_stt()
    results["tts"] = load_tts()
    results["vad"] = load_vad()

    elapsed = time.time() - start
    ready = sum(1 for v in results.values() if v)
    total = len(results)

    logger.info("════════════════════════════════════════════")
    logger.info("  Speech Service — Warmup complete (%.1fs)", elapsed)
    logger.info("  Models ready: %d/%d", ready, total)
    for name, ok in results.items():
        status = "READY" if ok else "FAILED"
        logger.info("    %s: %s", name.upper(), status)
    logger.info("════════════════════════════════════════════")

    if ready == 0:
        raise RuntimeError("No speech models loaded — cannot start service")

    yield

    logger.info("Speech Service shutting down")


app = FastAPI(
    title="ARIA Speech Service",
    version="1.0.0",
    lifespan=lifespan,
)


# ─── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Model readiness probe."""
    return {
        "status": "healthy",
        "models": {
            "stt": whisper_model is not None,
            "tts": kokoro_pipeline is not None,
            "tts_fallback": True,  # edge-tts is always ready (cloud)
            "vad": vad_model is not None,
        },
    }


# ─── STT Endpoint ─────────────────────────────────────────────────────────────

@app.post("/stt/transcribe")
async def transcribe_audio(request: Request):
    """
    Transcribe audio bytes to text using OpenAI Whisper.
    Accepts: raw PCM (16kHz, 16-bit, mono) or WAV bytes.
    """
    if whisper_model is None:
        raise HTTPException(status_code=503, detail="STT model not loaded")

    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty audio body")

    content_type = request.headers.get("content-type", "audio/wav")

    try:
        # Convert audio to the format Whisper expects
        if "raw" in content_type or "pcm" in content_type:
            # Raw PCM: 16kHz, 16-bit, mono → float32 numpy array
            audio_np = np.frombuffer(body, dtype=np.int16).astype(np.float32) / 32768.0
        else:
            # WAV — load via torchaudio and convert to float32 numpy
            audio_buffer = io.BytesIO(body)
            waveform, sample_rate = torchaudio.load(audio_buffer)
            if sample_rate != SAMPLE_RATE:
                resampler = torchaudio.transforms.Resample(sample_rate, SAMPLE_RATE)
                waveform = resampler(waveform)
            if waveform.shape[0] > 1:
                waveform = waveform.mean(dim=0, keepdim=True)
            audio_np = waveform.squeeze().numpy()

        # Whisper expects float32 numpy array at 16kHz
        start = time.time()
        result = whisper_model.transcribe(
            audio_np,
            language="en",
            fp16=False,  # CPU — use float32
        )
        elapsed = time.time() - start

        text = result.get("text", "").strip()
        segments = result.get("segments", [])

        logger.info("STT: %d chars in %.2fs", len(text), elapsed)

        return {
            "text": text,
            "duration_audio": len(audio_np) / SAMPLE_RATE,
            "duration_inference": round(elapsed, 3),
            "chunks": [
                {"text": s.get("text", "").strip(), "timestamp": (s.get("start"), s.get("end"))}
                for s in segments
            ] if segments else [],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("STT transcription error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


# ─── TTS Endpoint ─────────────────────────────────────────────────────────────

@app.post("/tts/synthesize")
async def synthesize_speech(request: Request):
    """
    Synthesize text to audio using Kokoro TTS (primary) or Edge TTS (fallback).
    Body JSON: {"text": "...", "voice": "female"|"male", "speed": 1.0}
    Returns: WAV audio bytes at 16kHz mono.
    """
    body = await request.json()
    text = body.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    voice_key = body.get("voice", "female")
    speed = body.get("speed", 1.0)

    # Try Kokoro TTS first (local, CPU-based, professional voice)
    if kokoro_pipeline is not None:
        try:
            return await _synthesize_kokoro(text, voice_key, speed)
        except Exception as e:
            logger.warning("Kokoro TTS failed, falling back to Edge TTS: %s", e)

    # Fallback: Edge TTS (cloud-based)
    return await _synthesize_edge(text, voice_key, speed)


async def _synthesize_kokoro(text: str, voice_key: str, speed: float) -> StreamingResponse:
    """Synthesize speech using Kokoro TTS pipeline."""
    import soundfile as sf

    voice_name = KOKORO_VOICES.get(voice_key, KOKORO_VOICES["female"])
    start = time.time()

    # Kokoro pipeline yields (graphemes, phonemes, audio) chunks
    audio_chunks = []
    for _gs, _ps, audio in kokoro_pipeline(text, voice=voice_name):
        audio_chunks.append(audio)

    if not audio_chunks:
        raise HTTPException(status_code=500, detail="Kokoro generated no audio")

    # Concatenate audio chunks (numpy arrays at 24kHz)
    import numpy as np
    full_audio = np.concatenate(audio_chunks)

    # Resample from 24kHz to 16kHz using torchaudio
    audio_tensor = torch.from_numpy(full_audio).float().unsqueeze(0)
    resampler = torchaudio.transforms.Resample(KOKORO_SAMPLE_RATE, SAMPLE_RATE)
    audio_16k = resampler(audio_tensor).squeeze().numpy()

    # Convert to 16-bit PCM
    audio_int16 = (audio_16k * 32768).clip(-32768, 32767).astype(np.int16)

    # Write WAV to buffer
    wav_buffer = io.BytesIO()
    sf.write(wav_buffer, audio_int16, SAMPLE_RATE, format='WAV', subtype='PCM_16')
    wav_buffer.seek(0)

    elapsed = time.time() - start
    audio_duration = len(audio_16k) / SAMPLE_RATE
    logger.info("Kokoro TTS: %d chars → %.1fs audio in %.2fs", len(text), audio_duration, elapsed)

    return StreamingResponse(
        wav_buffer,
        media_type="audio/wav",
        headers={
            "X-Inference-Time": f"{elapsed:.3f}",
            "X-Audio-Duration": f"{audio_duration:.2f}",
            "X-TTS-Engine": "kokoro",
        },
    )


async def _synthesize_edge(text: str, voice_key: str, speed: float) -> StreamingResponse:
    """Synthesize speech using Edge TTS (cloud fallback)."""
    import edge_tts

    voice_name = EDGE_TTS_VOICES.get(voice_key, EDGE_TTS_VOICES["female"])
    rate_pct = int((1.0 / max(speed, 0.5) - 1.0) * 100)
    rate_str = f"+{rate_pct}%" if rate_pct >= 0 else f"{rate_pct}%"

    start = time.time()

    communicate = edge_tts.Communicate(text, voice_name, rate=rate_str)
    audio_chunks = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])

    if not audio_chunks:
        raise HTTPException(status_code=500, detail="Edge TTS generated no audio")

    # edge-tts returns MP3 — convert to WAV at 16kHz mono using pydub
    mp3_bytes = b"".join(audio_chunks)
    mp3_buffer = io.BytesIO(mp3_bytes)

    from pydub import AudioSegment
    audio_seg = AudioSegment.from_mp3(mp3_buffer)
    audio_seg = audio_seg.set_frame_rate(SAMPLE_RATE).set_channels(1).set_sample_width(2)

    wav_buffer = io.BytesIO()
    audio_seg.export(wav_buffer, format="wav")
    wav_buffer.seek(0)

    elapsed = time.time() - start
    audio_duration = len(audio_seg) / 1000.0
    logger.info("Edge TTS: %d chars → %.1fs audio in %.2fs", len(text), audio_duration, elapsed)

    return StreamingResponse(
        wav_buffer,
        media_type="audio/wav",
        headers={
            "X-Inference-Time": f"{elapsed:.3f}",
            "X-Audio-Duration": f"{audio_duration:.2f}",
            "X-TTS-Engine": "edge",
        },
    )


# ─── VAD Endpoint ──────────────────────────────────────────────────────────────

@app.post("/vad/detect")
async def detect_speech(request: Request):
    """
    Detect speech segments in audio.
    Accepts: raw PCM (16kHz, 16-bit, mono) or WAV bytes.
    Returns: list of speech segments with start/end times.
    """
    if vad_model is None:
        raise HTTPException(status_code=503, detail="VAD model not loaded")

    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty audio body")

    content_type = request.headers.get("content-type", "audio/wav")

    try:
        if "raw" in content_type or "pcm" in content_type:
            audio_np = np.frombuffer(body, dtype=np.int16).astype(np.float32) / 32768.0
            audio_tensor = torch.from_numpy(audio_np)
        else:
            audio_buffer = io.BytesIO(body)
            waveform, sample_rate = torchaudio.load(audio_buffer)
            if sample_rate != SAMPLE_RATE:
                resampler = torchaudio.transforms.Resample(sample_rate, SAMPLE_RATE)
                waveform = resampler(waveform)
            if waveform.shape[0] > 1:
                waveform = waveform.mean(dim=0)
            audio_tensor = waveform.squeeze()

        # Silero VAD expects 512-sample chunks (32ms at 16kHz)
        start = time.time()
        speech_timestamps = vad_utils[0](
            vad_model, audio_tensor, SAMPLE_RATE,
            threshold=0.5,
            min_speech_duration_ms=250,
            min_silence_duration_ms=100,
        )
        elapsed = time.time() - start

        segments = []
        for ts in speech_timestamps:
            segments.append({
                "start": round(ts["start"].item(), 3),
                "end": round(ts["end"].item(), 3),
                "duration": round(ts["end"].item() - ts["start"].item(), 3),
            })

        has_speech = len(segments) > 0
        total_speech = sum(s["duration"] for s in segments)

        logger.info("VAD: %d segments, %.2fs speech in %.2fs", len(segments), total_speech, elapsed)

        return {
            "has_speech": has_speech,
            "segments": segments,
            "total_speech_duration": round(total_speech, 3),
            "audio_duration": round(len(audio_tensor) / SAMPLE_RATE, 3),
            "inference_time": round(elapsed, 3),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("VAD detection error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"VAD detection failed: {str(e)}")


# ─── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.speech_service.main:app",
        host="0.0.0.0",
        port=8001,
        log_level="info",
    )
