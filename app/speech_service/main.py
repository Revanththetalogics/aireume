"""
Speech Service — CPU-optimized inference for STT, TTS, and VAD.

Endpoints:
  POST /stt/transcribe       — Audio bytes → text (OpenAI Whisper base)
  POST /tts/synthesize       — Text → audio bytes (Microsoft Edge TTS)
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

SAMPLE_RATE = 16000  # All models use 16 kHz

# Edge TTS voice mapping
EDGE_TTS_VOICES = {
    "female": "en-US-JennyNeural",
    "male": "en-US-GuyNeural",
}


# ─── Model loading ────────────────────────────────────────────────────────────

def load_stt():
    """Load OpenAI Whisper base model — fast and reliable on CPU."""
    global whisper_model
    try:
        import whisper
        model_name = "base"  # 74M params, ~2-5s inference for 3s audio on CPU
        logger.info("Loading Whisper model: %s", model_name)
        whisper_model = whisper.load_model(model_name, device="cpu")
        logger.info("Whisper model loaded successfully")
        return True
    except Exception as e:
        logger.error("Failed to load Whisper model: %s", e)
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
    """Load models on startup. TTS uses edge-tts (cloud, no local model)."""
    logger.info("════════════════════════════════════════════")
    logger.info("  Speech Service — Starting model warmup")
    logger.info("════════════════════════════════════════════")

    start = time.time()
    results = {}

    results["stt"] = load_stt()
    results["tts"] = True  # edge-tts is cloud-based, no model to load
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
            "tts": True,  # edge-tts is always ready (cloud)
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
    Synthesize text to audio using Microsoft Edge TTS (neural voices).
    Body JSON: {"text": "...", "voice": "female"|"male", "speed": 1.0}
    Returns: WAV audio bytes.
    """
    import edge_tts

    body = await request.json()
    text = body.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    voice_key = body.get("voice", "female")
    speed = body.get("speed", 1.0)
    voice_name = EDGE_TTS_VOICES.get(voice_key, EDGE_TTS_VOICES["female"])

    # Convert speed to rate percentage for edge-tts (e.g., 1.0 → "+0%", 0.8 → "+20%")
    # edge-tts uses rate like "+20%" for faster, "-20%" for slower
    rate_pct = int((1.0 / max(speed, 0.5) - 1.0) * 100)
    rate_str = f"+{rate_pct}%" if rate_pct > 0 else f"{rate_pct}%"

    try:
        start = time.time()

        # Use edge-tts to generate audio
        communicate = edge_tts.Communicate(text, voice_name, rate=rate_str)
        audio_chunks = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])

        if not audio_chunks:
            raise HTTPException(status_code=500, detail="No audio generated")

        # edge-tts returns MP3 — convert to WAV at 16kHz mono
        mp3_bytes = b"".join(audio_chunks)
        mp3_buffer = io.BytesIO(mp3_bytes)
        waveform, sample_rate = torchaudio.load(mp3_buffer, format="mp3")

        # Resample to 16kHz mono
        if sample_rate != SAMPLE_RATE:
            resampler = torchaudio.transforms.Resample(sample_rate, SAMPLE_RATE)
            waveform = resampler(waveform)
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)

        # Save as WAV
        wav_buffer = io.BytesIO()
        torchaudio.save(wav_buffer, waveform, SAMPLE_RATE, format="wav")
        wav_buffer.seek(0)

        elapsed = time.time() - start
        audio_duration = waveform.shape[1] / SAMPLE_RATE
        logger.info("TTS: %d chars → %.1fs audio in %.2fs", len(text), audio_duration, elapsed)

        return StreamingResponse(
            wav_buffer,
            media_type="audio/wav",
            headers={
                "X-Inference-Time": f"{elapsed:.3f}",
                "X-Audio-Duration": f"{audio_duration:.2f}",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("TTS synthesis error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")


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
