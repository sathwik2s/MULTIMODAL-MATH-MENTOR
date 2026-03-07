# 🧮 Multimodal Math Mentor

An AI-powered tutoring system that solves JEE-style math problems using multimodal inputs, multi-agent architecture, RAG, human-in-the-loop verification, and persistent memory.

---

## Features

- **Multimodal Input** — Text, image (OCR via EasyOCR), or audio (Whisper ASR)
- **Multi-Agent Pipeline** — Parser → Router → Solver → Verifier → Explainer
- **RAG Knowledge Base** — 10+ JEE math topic documents indexed in ChromaDB
- **Math Tools** — SymPy symbolic solver + sandboxed Python executor
- **Human-in-the-Loop** — Triggers review when confidence is low; accepts corrections
- **Persistent Memory** — SQLite + vector embeddings for learning from past problems
- **Step-by-Step Explanations** — Beginner-friendly, formula-referenced solutions
- **Streamlit UI** — Clean, interactive web interface

---

## Architecture

See [architecture.md](architecture.md) for the full architecture diagram and component details.

```
User Input (Text / Image / Audio)
        │
        ▼
   ┌─────────┐
   │  Parser  │──── HITL (if ambiguous)
   └────┬────┘
        │
   ┌────▼────┐
   │  Router  │
   └────┬────┘
        │
   ┌────▼────┐     ┌──────┐
   │  Solver  │────►│  RAG │
   └────┬────┘     └──────┘
        │           ┌────────┐
        ├──────────►│ SymPy  │
        │           └────────┘
   ┌────▼──────┐
   │  Verifier │──── HITL (if uncertain)
   └────┬──────┘
        │
   ┌────▼──────┐
   │ Explainer │──► UI (Step-by-step solution)
   └───────────┘
        │
   ┌────▼──────┐
   │  Memory   │ (SQLite + ChromaDB)
   └───────────┘
```

---

## Project Structure

```
multimodel_maths_mentor/
├── backend/                     # All server-side / logic code
│   ├── __init__.py
│   ├── config.py                # Configuration & LLM client
│   ├── main.py                  # Orchestration pipeline
│   ├── agents/
│   │   ├── parser_agent.py      # Raw text → structured problem
│   │   ├── router_agent.py      # Classify domain & select tools
│   │   ├── solver_agent.py      # RAG + tools → answer
│   │   ├── verifier_agent.py    # Validate correctness
│   │   └── explainer_agent.py   # Step-by-step explanation
│   ├── multimodal/
│   │   ├── image_ocr.py         # EasyOCR pipeline
│   │   ├── audio_asr.py         # Whisper transcription
│   │   └── text_input.py        # Text normalisation
│   ├── rag/
│   │   ├── ingest.py            # Document chunking & indexing
│   │   ├── retriever.py         # Query → top-K chunks
│   │   └── embeddings.py        # sentence-transformers
│   ├── tools/
│   │   ├── math_solver.py       # SymPy functions
│   │   └── python_executor.py   # Sandboxed code runner
│   ├── memory/
│   │   ├── memory_store.py      # SQLite CRUD
│   │   └── similarity_search.py # Vector similarity
│   ├── hitl/
│   │   └── human_review.py      # Review workflow
│   └── utils/
│       ├── logger.py            # Application logger
│       └── confidence.py        # Confidence scoring
├── frontend/                    # Streamlit UI layer
│   ├── __init__.py
│   ├── app.py                   # Main Streamlit entry point
│   └── components/
│       ├── sidebar.py           # KB ingestion & history
│       ├── input_panel.py       # Text / Image / Audio tabs
│       ├── preview_panel.py     # Extracted text preview & edit
│       ├── result_panel.py      # Solution & explanation display
│       ├── agent_trace.py       # Agent debug trace
│       └── feedback_panel.py    # Correct / Incorrect / Re-check
├── data/
│   ├── knowledge_base/          # RAG source documents
│   └── solved_examples/         # Example problems
├── run.py                       # Convenience entry point
├── requirements.txt
├── .env.example
├── architecture.md
├── Dockerfile
└── README.md
```

---

## Quick Start

### 1. Clone & Install

```bash
git clone <repo-url>
cd multimodel_maths_mentor
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your API keys
```

**Required:** At least one LLM API key (OpenAI recommended).

| Variable | Description |
|---|---|
| `LLM_PROVIDER` | `openai`, `groq`, or `anthropic` |
| `OPENAI_API_KEY` | Your OpenAI API key |
| `OPENAI_MODEL` | Model name (default: `gpt-4o`) |

### 3. Ingest Knowledge Base

```bash
python -m backend.rag.ingest
```

Or use the sidebar button in the UI.

### 4. Run the App

```bash
streamlit run frontend/app.py
# or
python run.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Usage

1. **Enter a question** via text box, image upload, or audio upload.
2. **Preview & edit** — review the extracted text before solving.
3. **Click "Solve Problem"** — the multi-agent pipeline runs.
4. **Review the solution** — see step-by-step explanation, RAG sources, and confidence.
5. **Provide feedback** — mark as correct/incorrect or submit corrections.

---

## Configuration

All settings are in `.env`. Key options:

| Setting | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `openai` | LLM backend |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model |
| `OCR_CONFIDENCE_THRESHOLD` | `0.7` | Below this triggers HITL |
| `VERIFIER_CONFIDENCE_THRESHOLD` | `0.75` | Below this triggers HITL |
| `RAG_TOP_K` | `5` | Number of chunks to retrieve |
| `CHUNK_SIZE` | `500` | Characters per document chunk |

---

## Deployment

### Streamlit Cloud

1. Push to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io).
3. Connect your repo, set main file to `frontend/app.py`.
4. Add secrets (API keys) via Streamlit Cloud dashboard.

### HuggingFace Spaces

1. Create a new Space (SDK: Streamlit).
2. Push the repo.
3. Set secrets in Space settings.

### Docker

```bash
docker build -t math-mentor .
docker run -p 8501:8501 --env-file .env math-mentor
```

---

## Tech Stack

| Component | Technology |
|---|---|
| UI | Streamlit |
| LLM | OpenAI / Groq / Anthropic |
| OCR | EasyOCR |
| ASR | OpenAI Whisper |
| Vector DB | ChromaDB |
| Embeddings | sentence-transformers |
| Math | SymPy |
| Database | SQLite |
| Language | Python 3.10+ |

---

## License

MIT
