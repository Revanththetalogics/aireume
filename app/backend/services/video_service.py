"""
Video interview analysis:
  • Transcription via faster-whisper (with segment timestamps)
  • Communication quality analysis via Ollama
  • Malpractice detection: suspicious pauses, scripted speech,
    background coaching, inconsistent fluency
"""
import os
import json
import asyncio
import tempfile
import httpx
import logging
from pathlib import Path

from app.backend.services.llm_service import get_ollama_semaphore, get_ollama_headers, is_ollama_cloud

logger = logging.getLogger(__name__)


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


def _is_ollama_cloud_local(base_url: str) -> bool:
    """Check if the base URL points to Ollama Cloud (ollama.com)."""
    return "ollama.com" in base_url.lower()

# Pause longer than this (seconds between speech segments) is flagged
SUSPICIOUS_PAUSE_THRESHOLD = 12.0
CRITICAL_PAUSE_THRESHOLD   = 25.0


# ─── Transcription ────────────────────────────────────────────────────────────

def transcribe_video(video_path: str) -> dict:
    """
    Transcribe audio from video using faster-whisper.
    Returns full transcript, segment-level timestamps, language, duration.
    """
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("base", device="cpu", compute_type="int8")
        raw_segments, info = model.transcribe(video_path, beam_size=5)

        segments = []
        texts = []
        for seg in raw_segments:
            text = seg.text.strip()
            if not text:
                continue
            segments.append({
                "start":         round(seg.start, 2),
                "end":           round(seg.end, 2),
                "text":          text,
                "avg_logprob":   round(seg.avg_logprob, 3),
                "no_speech_prob": round(seg.no_speech_prob, 3),
            })
            texts.append(text)

        return {
            "transcript": " ".join(texts),
            "segments":   segments,
            "language":   info.language,
            "duration_s": info.duration,
        }
    except ImportError:
        return _empty_transcription("faster-whisper not installed")
    except Exception as e:
        return _empty_transcription(str(e))


def _empty_transcription(error: str = "") -> dict:
    return {"transcript": "", "segments": [], "language": "unknown", "duration_s": 0, "error": error}


# ─── Malpractice signal extraction ───────────────────────────────────────────

def extract_pause_signals(segments: list) -> list[dict]:
    """
    Detect suspiciously long gaps between speech segments.
    Returns list of pause events with timestamp, duration, severity.
    """
    pauses = []
    for i in range(1, len(segments)):
        gap = segments[i]["start"] - segments[i - 1]["end"]
        if gap >= SUSPICIOUS_PAUSE_THRESHOLD:
            pauses.append({
                "at_seconds":   round(segments[i - 1]["end"], 1),
                "duration_s":   round(gap, 1),
                "before_text":  segments[i - 1]["text"][:80],
                "after_text":   segments[i]["text"][:80],
                "severity":     "high" if gap >= CRITICAL_PAUSE_THRESHOLD else "medium",
                "formatted_at": _fmt_time(segments[i - 1]["end"]),
            })
    return pauses


def extract_audio_anomalies(segments: list) -> dict:
    """
    Derive anomaly signals from Whisper segment metadata.
    """
    if not segments:
        return {"low_confidence_count": 0, "high_no_speech_count": 0,
                "speech_rate_variance": 0.0, "total_segments": 0}

    low_conf    = sum(1 for s in segments if s.get("avg_logprob", 0) < -1.0)
    no_speech   = sum(1 for s in segments if s.get("no_speech_prob", 0) > 0.6)

    # Speech rate variance (words/second per segment)
    rates = []
    for seg in segments:
        dur = seg["end"] - seg["start"]
        if dur > 0.5:
            rates.append(len(seg["text"].split()) / dur)

    variance = 0.0
    if len(rates) > 2:
        mean = sum(rates) / len(rates)
        variance = round(sum((r - mean) ** 2 for r in rates) / len(rates), 3)

    return {
        "low_confidence_count":  low_conf,
        "high_no_speech_count":  no_speech,
        "speech_rate_variance":  variance,
        "total_segments":        len(segments),
    }


def _fmt_time(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}:{s:02d}"


# ─── Ollama: communication analysis ──────────────────────────────────────────

async def analyze_communication(transcript: str, duration_s: float) -> dict:
    if not transcript or len(transcript) < 20:
        return _default_communication(0)

    wpm = round(len(transcript.split()) / max(duration_s / 60, 1)) if duration_s > 0 else 0

    prompt = (
        "You are an expert communication coach evaluating a recorded interview.\n"
        "Analyze the transcript and return JSON only.\n\n"
        f"Transcript ({wpm} words/min, {int(duration_s)}s):\n{transcript[:2500]}\n\n"
        'Return: {"communication_score":0-100,"confidence_level":"low|medium|high",'
        '"clarity_score":0-100,"articulation_score":0-100,'
        '"key_phrases":["notable phrases (max 5)"],'
        '"strengths":["communication strengths (max 3)"],'
        '"red_flags":["communication concerns (max 3)"],'
        '"summary":"2-sentence recruiter-friendly assessment"}'
    )

    try:
        sem = get_ollama_semaphore()
        if sem.locked():
            logger.info("Waiting for Ollama slot (another request in progress)...")
        async with sem:
            headers = get_ollama_headers(OLLAMA_BASE_URL)
            # Cloud models need more tokens for verbose output
            _is_cloud = _is_ollama_cloud_local(OLLAMA_BASE_URL)
            _num_predict = 800 if _is_cloud else 350
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    headers=headers,
                    json={
                        "model":   os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud"),
                        "prompt":  prompt,
                        "stream":  False,
                        "format":  "json",
                        "options": {"num_predict": _num_predict, "temperature": 0.2},
                    },
                )
                resp.raise_for_status()
                parsed = json.loads(resp.json().get("response", "{}"))
                return {
                    "communication_score":  int(parsed.get("communication_score", 50)),
                    "confidence_level":     parsed.get("confidence_level", "medium"),
                    "clarity_score":        int(parsed.get("clarity_score", 50)),
                    "articulation_score":   int(parsed.get("articulation_score", 50)),
                    "key_phrases":          parsed.get("key_phrases", []),
                    "strengths":            parsed.get("strengths", []),
                    "red_flags":            parsed.get("red_flags", []),
                    "summary":              parsed.get("summary", ""),
                    "words_per_minute":     wpm,
                }
    except Exception:
        return _default_communication(wpm)


def _default_communication(wpm: int = 0) -> dict:
    return {
        "communication_score": 50, "confidence_level": "medium",
        "clarity_score": 50, "articulation_score": 50,
        "key_phrases": [], "strengths": [], "red_flags": [],
        "summary": "Communication analysis unavailable.", "words_per_minute": wpm,
    }


# ─── Ollama: malpractice analysis ─────────────────────────────────────────────

async def analyze_malpractice(
    transcript: str,
    pauses: list,
    anomalies: dict,
    duration_s: float,
) -> dict:
    """
    Analyse the transcript for interview malpractice signals using an LLM.
    Also incorporates pause and audio anomaly data.
    """
    if not transcript or len(transcript) < 30:
        return _default_malpractice(pauses)

    wpm = round(len(transcript.split()) / max(duration_s / 60, 1)) if duration_s > 0 else 0

    pause_ctx = ""
    if pauses:
        pause_ctx = (
            f"\nSuspicious pauses ({len(pauses)} detected):\n"
            + "\n".join(
                f"  • {p['duration_s']}s at {p['formatted_at']} — "
                f"after: \"{p['before_text']}\" → before: \"{p['after_text']}\""
                for p in pauses[:4]
            )
        )

    anomaly_ctx = ""
    if anomalies["low_confidence_count"] > 2:
        anomaly_ctx = (
            f"\nAudio anomalies: {anomalies['low_confidence_count']} segments with "
            "low speech confidence (possible background voice or whispering)."
        )

    prompt = f"""You are an interview integrity expert. Analyze this transcript for malpractice signals.

Transcript ({wpm} wpm, {int(duration_s)}s total):
{transcript[:3000]}
{pause_ctx}
{anomaly_ctx}

Evaluate for these specific malpractice types:
1. SCRIPTED_READING — No filler words (um/uh/well), overly formal/textbook, no self-corrections, perfect grammar throughout
2. BACKGROUND_COACHING — Sudden polished answers after pauses, whispered prompts visible in transcript, inconsistent vocabulary
3. INCONSISTENT_FLUENCY — Some answers very smooth, others very hesitant on similar topics
4. SUSPICIOUS_PAUSE — Pauses >12s mid-answer (looking up information)
5. EVASIVE_PATTERN — Repeatedly deflecting, not answering directly, excessive generalities
6. THIRD_PARTY_ANSWERING — Sudden change in speaking style, vocabulary level inconsistency between questions

Return JSON only:
{{
  "malpractice_score": 0-100,
  "malpractice_risk": "low|medium|high",
  "reliability_rating": "trustworthy|questionable|unreliable",
  "flags": [
    {{
      "type": "scripted_reading|background_coaching|inconsistent_fluency|suspicious_pause|evasive_pattern|third_party_answering",
      "severity": "low|medium|high",
      "evidence": "specific quote or observation (max 120 chars)",
      "recommendation": "one actionable suggestion for the recruiter"
    }}
  ],
  "positive_signals": ["genuine signals (naturalness, self-corrections, appropriate hesitation) — max 3"],
  "overall_assessment": "3-sentence recruiter-facing summary of integrity assessment",
  "follow_up_questions": ["1-2 targeted questions to verify authenticity in next round"]
}}"""

    try:
        sem = get_ollama_semaphore()
        if sem.locked():
            logger.info("Waiting for Ollama slot (another request in progress)...")
        async with sem:
            headers = get_ollama_headers(OLLAMA_BASE_URL)
            # Cloud models need more tokens for verbose output
            _is_cloud = _is_ollama_cloud_local(OLLAMA_BASE_URL)
            _num_predict = 1200 if _is_cloud else 600
            async with httpx.AsyncClient(timeout=75.0) as client:
                resp = await client.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    headers=headers,
                    json={
                        "model":   os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud"),
                        "prompt":  prompt,
                        "stream":  False,
                        "format":  "json",
                        "options": {"num_predict": _num_predict, "temperature": 0.1},
                    },
                )
                resp.raise_for_status()
                parsed = json.loads(resp.json().get("response", "{}"))

                # Merge pause signals into flags
                flags = parsed.get("flags", [])
                for p in pauses:
                    flags.append({
                        "type":           "suspicious_pause",
                        "severity":       p["severity"],
                        "evidence":       f"{p['duration_s']}s pause at {p['formatted_at']} — after \"{p['before_text'][:60]}\"",
                        "recommendation": "Ask the candidate directly what happened during this pause in the next interview.",
                    })

                score = int(parsed.get("malpractice_score", 0))
                risk  = parsed.get("malpractice_risk", "low")

                # Clamp risk to match score if LLM is inconsistent
                if score >= 65 and risk == "low":
                    risk = "medium"
                if score >= 80:
                    risk = "high"

                return {
                    "malpractice_score":    score,
                    "malpractice_risk":     risk,
                    "reliability_rating":   parsed.get("reliability_rating", "trustworthy"),
                    "flags":                flags,
                    "positive_signals":     parsed.get("positive_signals", []),
                    "overall_assessment":   parsed.get("overall_assessment", ""),
                    "follow_up_questions":  parsed.get("follow_up_questions", []),
                    "pause_count":          len(pauses),
                    "pauses":               pauses,
                }
    except Exception:
        return _default_malpractice(pauses)


def _default_malpractice(pauses: list) -> dict:
    flags = []
    score = 0
    risk  = "low"

    if len(pauses) >= 2:
        score = 35
        risk  = "medium"
        for p in pauses:
            flags.append({
                "type":           "suspicious_pause",
                "severity":       p["severity"],
                "evidence":       f"{p['duration_s']}s silence at {p['formatted_at']}",
                "recommendation": "Ask the candidate what happened during this pause.",
            })

    return {
        "malpractice_score":   score,
        "malpractice_risk":    risk,
        "reliability_rating":  "questionable" if flags else "trustworthy",
        "flags":               flags,
        "positive_signals":    [],
        "overall_assessment":  "LLM malpractice analysis unavailable. Review recording manually.",
        "follow_up_questions": [],
        "pause_count":         len(pauses),
        "pauses":              pauses,
    }


# ─── Main entry points ────────────────────────────────────────────────────────

async def _run_full_analysis(tmp_path: str, source_label: str) -> dict:
    """Shared pipeline: transcribe → communication + malpractice in parallel."""
    transcription = await asyncio.get_event_loop().run_in_executor(
        None, transcribe_video, tmp_path
    )

    transcript = transcription.get("transcript", "")
    duration_s = transcription.get("duration_s", 0)
    segments   = transcription.get("segments", [])

    pauses    = extract_pause_signals(segments)
    anomalies = extract_audio_anomalies(segments)

    communication, malpractice = await asyncio.gather(
        analyze_communication(transcript, duration_s),
        analyze_malpractice(transcript, pauses, anomalies, duration_s),
    )

    return {
        "source":      source_label,
        "transcript":  transcript,
        "language":    transcription.get("language", ""),
        "duration_s":  duration_s,
        "segments":    segments,
        **communication,
        "malpractice": malpractice,
    }


async def analyze_video_file(video_bytes: bytes, filename: str) -> dict:
    """Analyse a video uploaded as raw bytes."""
    suffix = Path(filename).suffix.lower() or ".mp4"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(video_bytes)
        tmp_path = tmp.name

    try:
        return await _run_full_analysis(tmp_path, filename)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


async def analyze_video_from_url(url: str) -> dict:
    """Download a video from a public URL then run full analysis."""
    from app.backend.services.video_downloader import download_video_from_url

    video_bytes, filename, platform = await download_video_from_url(url)

    suffix = Path(filename).suffix.lower() or ".mp4"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(video_bytes)
        tmp_path = tmp.name

    try:
        result = await _run_full_analysis(tmp_path, f"{platform} — {filename}")
        result["source_url"]  = url
        result["platform"]    = platform
        result["filename"]    = filename
        return result
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
