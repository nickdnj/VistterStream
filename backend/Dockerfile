# Raspberry Pi (ARM64) ready Dockerfile for VistterStream backend

FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       ffmpeg \
       v4l-utils \
       curl \
       ca-certificates \
       build-essential \
       libxml2-dev \
       libxslt1-dev \
       libffi-dev \
       libssl-dev \
       pkg-config \
       # VA-API libs for Intel GPU hardware encoding
       libva-drm2 \
       libva2 \
       intel-media-va-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

# Copy requirements and install
COPY requirements.txt /app/backend/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy application code
COPY . /app/backend

# Default environment (overridden by compose/.env)
ENV DATABASE_URL=sqlite:////data/vistterstream.db \
    UPLOADS_DIR=/data/uploads \
    RTMP_RELAY_HOST=rtmp-relay \
    RTMP_RELAY_PORT=1935

# Create non-root user and data directories with correct ownership
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash appuser \
    && mkdir -p /data/uploads \
    && chown -R appuser:appuser /data /app

EXPOSE 8000

USER appuser

# Healthcheck via API
HEALTHCHECK --interval=10s --timeout=5s --retries=5 CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

CMD ["python", "start.py"]


