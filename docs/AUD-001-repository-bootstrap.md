# AUD-001 — Repository Bootstrap

**Epic:** EPIC 1 — Repository Foundation  
**Status:** ✅ Implemented  
**Priority:** Critical  
**Blocks:** Everything  

---

## Summary

Establishes the flat directory structure, configures a single venv for all packages, sets up pre-commit hooks, and provides CI scaffolding.

---

## What Was Implemented

### Directory Structure

```
api/
  __init__.py
  main.py
  config.py
  db/
  middleware/
  routers/
worker/
  __init__.py
  app.py
  tasks/
llmops/
  __init__.py
  main.py
shared/
  __init__.py
  interfaces.py   ← Core ABCs
  config.py       ← Centralised Config
  schemas.py
  storage.py
  logging.py
tests/
  api/
  worker/
  shared/
datasets/.gitkeep
experiments/.gitkeep
runs/.gitignore                ← ignores *.wav, *.mp3, *.bin
artifacts/.gitkeep
requirements.txt
requirements-dev.txt
.env.example
.pre-commit-config.yaml
.github/workflows/ci.yml
```

### Core ABCs (`shared/interfaces.py`)

All swappable pipeline components implement one of the following abstract base classes:

| ABC | Implementations (planned) |
|-----|--------------------------|
| `Parser` | DoclingParser, PDFPlumberParser, PyPDFParser, PyMuPDFParser, DocxParser, EpubParser |
| `Chunker` | ParagraphChunker, SentenceChunker, SemanticChunker, DialogueChunker |
| `TTSProvider` | KokoroProvider, PiperProvider, MeloTTSProvider |
| `LLMProvider` | OllamaProvider, LlamafileProvider |

**Data classes defined:**
- `ParseResult` — output of any parser
- `Chunk` — single text chunk with type and metadata
- `AudioSegment` — output of any TTS synthesis call

### Centralised Config (`shared/config.py`)

`pydantic-settings` `BaseSettings` subclass. Loads from `.env` file and environment variables. All swappable components read their implementation choice from this config — no `if provider == "..."` branches in business logic.

**Config keys defined:**

| Key | Default | Options |
|-----|---------|---------|
| `storage_backend` | `b2` | `b2 \| r2 \| minio \| seaweedfs \| filesystem` |
| `pdf_parser` | `docling` | `docling \| pdfplumber \| pypdf \| pymupdf` |
| `ocr_backend` | `rapidocr` | `rapidocr \| easyocr \| paddleocr \| tesseract` |
| `chunker` | `paragraph` | `paragraph \| sentence \| semantic \| dialogue` |
| `chunk_max_chars` | `800` | integer |
| `tts_provider` | `kokoro` | `kokoro \| piper \| melotts` |
| `tts_voice` | `af_bella` | voice ID string |
| `llm_runtime` | `ollama` | `ollama \| llamafile` |
| `llm_model` | `qwen2.5:0.5b` | model name (follow tier ladder) |

### Pre-commit Hooks (`.pre-commit-config.yaml`)

- `ruff` — linting and formatting
- `mypy` — static type checking

### CI Workflow (`.github/workflows/ci.yml`)

Runs on push/PR:
1. `ruff check .`
2. `mypy api/ worker/ shared/`
3. `pytest tests/` (smoke tests)

---

## Files Changed

| File | Purpose |
|------|---------|
| `shared/__init__.py` | Package init |
| `shared/interfaces.py` | All pipeline ABCs and data classes |
| `shared/config.py` | Centralised `Config` class |
| `requirements.txt` | Runtime dependencies |
| `requirements-dev.txt` | Dev + test dependencies |
| `.env.example` | Template for all required env vars |
| `.pre-commit-config.yaml` | Pre-commit hook configuration |
| `.github/workflows/ci.yml` | CI pipeline |

---

## Acceptance Criteria Status

- [x] `git clone && python3 -m venv .venv && pip install -r requirements-dev.txt` succeeds
- [x] CI workflow defined and runs on push
- [x] `.env.example` contains every key defined in `Config` class
