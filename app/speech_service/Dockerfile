FROM python:3.11-slim

WORKDIR /app

# System deps for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY app/speech_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy speech service code
COPY app/speech_service/ ./app/speech_service/

# Create non-root user
RUN useradd -m -u 1000 speechuser
RUN chown -R speechuser:speechuser /app
USER speechuser

ENV PYTHONPATH=/app
EXPOSE 8001

# Health check — wait for models to load
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "app.speech_service.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
