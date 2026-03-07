FROM python:3.11-slim

# Production Python settings
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System dependencies for OCR, audio processing, and Manim rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libgl1 \
    libglib2.0-0 \
    ffmpeg \
    libcairo2-dev \
    libpango1.0-dev \
    texlive-latex-base \
    texlive-fonts-recommended \
    texlive-latex-extra \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user for security
RUN useradd -m -u 1000 appuser

COPY . .

# Create output directories and set ownership
RUN mkdir -p outputs/videos outputs/manim_scripts outputs/media data \
    && chown -R appuser:appuser /app

USER appuser

# Ingest knowledge base at build time
RUN python -m backend.rag.ingest || true

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "frontend/app.py", \
    "--server.port=8501", \
    "--server.address=0.0.0.0", \
    "--server.headless=true", \
    "--server.fileWatcherType=none", \
    "--server.maxUploadSize=50"]
