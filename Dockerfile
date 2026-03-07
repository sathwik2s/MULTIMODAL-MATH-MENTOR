FROM python:3.11-slim

WORKDIR /app

# System dependencies for OCR, audio processing, and Manim rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    ffmpeg \
    libcairo2-dev \
    libpango1.0-dev \
    texlive-latex-base \
    texlive-fonts-recommended \
    texlive-latex-extra \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create output directories
RUN mkdir -p outputs/videos outputs/manim_scripts

# Ingest knowledge base at build time
RUN python -m backend.rag.ingest || true

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "frontend/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
