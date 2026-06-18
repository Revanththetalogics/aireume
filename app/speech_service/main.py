"""
Speech Service — CPU-optimized inference for STT, TTS, and VAD.

Endpoints:
  POST /stt/transcribe       — Audio bytes → text (Parakeet TDT 1.1B)
  POST /tts/synthesize       — Text → audio bytes (Kokoro 82M)
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

stt_model = None
stt_processor = None
tts_model = None
tts_pipeline = None
vad_model = None
vad_utils = None

SAMPLE_RATE = 16000  # All models use 16 kHz


# ─── Model loading ────────────────────────────────────────────────────────────

def load_stt():
    """Load Parakeet TDT 1.1B — fastest open-source streaming STT."""
    global stt_model, stt_processor
    try:
        from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
        model_id = "nvidia/parakeet-tdt-1.1b"
        logger.info("Loading STT model: %s", model_id)

        stt_processor = AutoProcessor.from_pretrained(model_id)
        stt_model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id,
            torch_dtype=torch.float32,  # CPU-only
            low_cpu_mem_usage=True,
        )
        stt_model.to("cpu")

        stt_pipeline = pipeline(
            "automatic-speech-recognition",
            model=stt_model,
            tokenizer=stt_processor.tokenizer,
            feature_extractor=stt_processor.feature_extractor,
            chunk_length_s=30,
            return_timestamps=True,
        )
        # Store pipeline for easy access
        stt_model._pipeline = stt_pipeline
        logger.info("STT model loaded successfully")
        return True
    except Exception as e:
        logger.error("Failed to load STT model: %s", e)
        return False


def load_tts():
    """Load Kokoro 82M — fast, lightweight TTS for CPU."""
    global tts_model, tts_pipeline
    try:
        # Kokoro uses a custom pipeline — load via transformers
        from transformers import AutoModel, AutoTokenizer
        model_id = "hexgrad/Kokoro-82M"
        logger.info("Loading TTS model: %s", model_id)

        tts_model = AutoModel.from_pretrained(
            model_id,
            torch_dtype=torch.float32,
            low_cpu_mem_usage=True,
        )
        tts_model.to("cpu")
        tts_tokenizer = AutoTokenizer.from_pretrained(model_id)

        # Store tokenizer alongside model
        tts_model._tokenizer = tts_tokenizer
        logger.info("TTS model loaded successfully")
        return True
    except Exception as e:
        logger.error("Failed to load TTS model: %s", e)
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
    """Load all models on startup."""
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
            "stt": stt_model is not None,
            "tts": tts_model is not None,
            "vad": vad_model is not None,
        },
    }


# ─── STT Endpoint ─────────────────────────────────────────────────────────────

@app.post("/stt/transcribe")
async def transcribe_audio(request: Request):
    """
    Transcribe audio bytes to text.
    Accepts: raw PCM (16kHz, 16-bit, mono) or WAV/MP3/OGG bytes.
    Content-Type header should match the audio format.
    """
    if stt_model is None or not hasattr(stt_model, "_pipeline"):
        raise HTTPException(status_code=503, detail="STT model not loaded")

    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty audio body")

    content_type = request.headers.get("content-type", "audio/wav")

    try:
        # Load audio via torchaudio
        audio_buffer = io.BytesIO(body)

        if "raw" in content_type or "pcm" in content_type:
            # Raw PCM: 16kHz, 16-bit, mono
            audio_np = np.frombuffer(body, dtype=np.int16).astype(np.float32) / 32768.0
            audio_tensor = torch.from_numpy(audio_np).unsqueeze(0)
            sample_rate = SAMPLE_RATE
        else:
            # WAV/MP3/OGG — let torchaudio handle it
            waveform, sample_rate = torchaudio.load(audio_buffer)
            # Resample to 16kHz if needed
            if sample_rate != SAMPLE_RATE:
                resampler = torchaudio.transforms.Resample(sample_rate, SAMPLE_RATE)
                waveform = resampler(waveform)
            # Convert stereo to mono
            if waveform.shape[0] > 1:
                waveform = waveform.mean(dim=0, keepdim=True)
            audio_tensor = waveform

        audio_np = audio_tensor.squeeze().numpy()

        # Run inference
        start = time.time()
        result = stt_model._pipeline(audio_np)
        elapsed = time.time() - start

        text = result.get("text", "").strip()
        chunks = result.get("chunks", [])

        logger.info("STT: %d chars in %.2fs", len(text), elapsed)

        return {
            "text": text,
            "duration_audio": len(audio_np) / SAMPLE_RATE,
            "duration_inference": round(elapsed, 3),
            "chunks": [
                {"text": c.get("text", ""), "timestamp": c.get("timestamp", None)}
                for c in chunks
            ] if chunks else [],
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
    Synthesize text to audio.
    Body JSON: {"text": "...", "voice": "female"|"male", "speed": 1.0}
    Returns: WAV audio bytes.
    """
    if tts_model is None:
        raise HTTPException(status_code=503, detail="TTS model not loaded")

    body = await request.json()
    text = body.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    voice = body.get("voice", "female")
    speed = body.get("speed", 1.0)

    try:
        start = time.time()

        # Kokoro TTS inference
        # Generate audio from text using the loaded model
        tokenizer = tts_model._tokenizer
        inputs = tokenizer(text, return_tensors="pt", padding=True)

        with torch.no_grad():
            outputs = tts_model.generate(
                **inputs,
                max_length=4096,
                do_sample=True,
                temperature=speed,
            )

        # Decode audio tokens to waveform
        audio_tensor = outputs.squeeze(0).float()

        # Convert to WAV bytes
        audio_buffer = io.BytesIO()
        torchaudio.save(
            audio_buffer,
            audio_tensor.unsqueeze(0) if audio_tensor.dim() == 1 else audio_tensor,
            SAMPLE_RATE,
            format="wav",
        )
        audio_buffer.seek(0)

        elapsed = time.time() - start
        logger.info("TTS: %d chars → %.1fs audio in %.2fs", len(text), len(audio_tensor) / SAMPLE_RATE, elapsed)

        return StreamingResponse(
            audio_buffer,
            media_type="audio/wav",
            headers={
                "X-Inference-Time": f"{elapsed:.3f}",
                "X-Audio-Duration": f"{len(audio_tensor) / SAMPLE_RATE:.2f}",
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
