FROM python:3.11-slim

WORKDIR /app

# System deps for audio processing + espeak-ng (required by Kokoro TTS)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    libsndfile1 \
    ffmpeg \
    espeak-ng \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY app/speech_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install spaCy model required by Kokoro / misaki
RUN python -m spacy download en_core_web_sm

# Copy speech service code
COPY app/speech_service/ ./app/speech_service/

# Pre-download Kokoro model so runtime starts don't depend on HuggingFace
# Cache under /app so the non-root runtime user can read it
ENV HF_HOME=/app/.cache/huggingface
ENV TORCH_HOME=/app/.cache/torch
RUN mkdir -p /app/.cache && \
    python - <<'PY'
from kokoro import KPipeline
KPipeline(lang_code='a')
PY

# Create non-root user
RUN useradd -m -u 1000 speechuser
RUN chown -R speechuser:speechuser /app
USER speechuser

ENV PYTHONPATH=/app
ENV HF_HOME=/app/.cache/huggingface
ENV TORCH_HOME=/app/.cache/torch
EXPOSE 8001

# Health check — wait for models to load
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "app.speech_service.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
