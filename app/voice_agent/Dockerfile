FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY app/voice_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy voice agent code
COPY app/voice_agent/ ./app/voice_agent/

# Create non-root user
RUN useradd -m -u 1000 agentuser
RUN chown -R agentuser:agentuser /app
USER agentuser

ENV PYTHONPATH=/app
EXPOSE 8002

CMD ["python", "-m", "app.voice_agent.agent"]
