"""
Multimodal Math Mentor — FastAPI REST Backend

Exposes the full multi-agent pipeline as a REST API.
Deploy this on Render as the 'math-mentor-api' web service (Dockerfile.api).
The Streamlit frontend can call this API, or it can be used independently.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.main import run_pipeline
from backend.rag.ingest import ingest_knowledge_base
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Multimodal Math Mentor API",
    version="1.0.0",
    description=(
        "REST API for the Multimodal Math Mentor — a multi-agent system "
        "for solving, explaining, and visualizing math problems."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# Allow cross-origin requests so the Vercel frontend / external clients can call this
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response schemas ───────────────────────────────────────────────

class SolveRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000, description="Math problem text")
    input_type: str = Field("text", description="Input source: text | image | audio")
    input_confidence: float = Field(1.0, ge=0.0, le=1.0, description="OCR/ASR confidence score")


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check():
    """Liveness check used by Render health monitor."""
    return {"status": "ok", "service": "math-mentor-api", "version": "1.0.0"}


@app.post("/api/v1/solve", tags=["Pipeline"])
def solve(req: SolveRequest) -> Dict[str, Any]:
    """
    Run the full multi-agent math pipeline.

    Returns parsed problem, routing decision, solution, verification,
    step-by-step explanation, and HITL review status.
    """
    logger.info("API /solve — input_type=%s len=%d", req.input_type, len(req.text))
    try:
        result = run_pipeline(
            text=req.text,
            input_type=req.input_type,
            input_confidence=req.input_confidence,
        )
        return result.to_dict()
    except Exception as exc:
        logger.exception("Pipeline error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/ingest", tags=["Admin"])
def trigger_ingest(background_tasks: BackgroundTasks):
    """Re-ingest the knowledge base into ChromaDB (admin endpoint)."""
    background_tasks.add_task(ingest_knowledge_base)
    return {"status": "queued", "message": "Knowledge base ingestion started in background."}


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "backend.api:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
    )
