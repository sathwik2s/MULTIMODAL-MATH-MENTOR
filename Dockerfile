FROM python:3.11-slim-bookworm

# Production Python settings
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Force cloud-based OCR and ASR — avoids downloading heavy local ML models
    # (pix2tex ~600 MB, EasyOCR ~500 MB, Whisper ~600 MB) on Render's 512 MB RAM tier
    OCR_ENGINE=llm_vision \
    ASR_ENGINE=groq \
    OTEL_SDK_DISABLED=true

WORKDIR /app

# System dependencies for OCR, audio processing, and Manim rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
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

COPY requirements-render.txt ./requirements-render.txt
COPY requirements.txt .
# Use slim render requirements (excludes pix2tex, easyocr, openai-whisper)
# to keep image under Render's memory limits
RUN pip install --upgrade pip wheel setuptools \
    && pip install --no-cache-dir --prefer-binary -r requirements-render.txt

# Create non-root user for security
RUN useradd -m -u 1000 appuser

COPY . .

# Create output directories and set ownership
RUN mkdir -p outputs/videos outputs/manim_scripts outputs/media data \
    && chown -R appuser:appuser /app

USER appuser

# Ingest knowledge base at build time
RUN python -m backend.rag.ingest || true

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl --fail http://localhost:${PORT:-7860}/_stcore/health || exit 1

# PORT=7860 is required by Hugging Face Spaces.
# Render overrides this with PORT=10000 via its environment.
CMD streamlit run frontend/app.py \
    --server.port=${PORT:-7860} \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.fileWatcherType=none \
    --server.maxUploadSize=200 \
    --server.enableXsrfProtection=false
