"""
Root entry point for Hugging Face Spaces and Streamlit Community Cloud.
Both platforms require the main app file to be at the repo root.
This simply delegates to the actual app in frontend/app.py.
"""
import os
import runpy

# Disable OpenTelemetry SDK (prevents Python 3.13 hang with chromadb)
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

# Force cloud-based engines when running on hosted platforms to avoid
# downloading heavy local ML models (pix2tex / EasyOCR / Whisper).
# These are overridden by user's .env on local dev.
os.environ.setdefault("OCR_ENGINE", "llm_vision")
os.environ.setdefault("ASR_ENGINE", "groq")

runpy.run_path("frontend/app.py", run_name="__main__")
