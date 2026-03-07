#!/usr/bin/env python
"""
Multimodal Math Mentor — Entry Point

Convenience script to launch the Streamlit app.

Usage:
    python run.py
"""

import os
import subprocess
import sys

# ── Disable OpenTelemetry SDK (avoids Python 3.13 hang with chromadb) ────────
os.environ.setdefault("OTEL_SDK_DISABLED", "true")


def main() -> None:
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "frontend/app.py",
         "--server.port=8501", "--server.address=0.0.0.0"],
        check=True,
    )


if __name__ == "__main__":
    main()
