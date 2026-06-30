# AI Audiobook Platform — Agent Task File

> **For the agent:** Read the entire `## GLOBAL CONTEXT` section before touching any ticket.
> Each ticket is self-contained but lists explicit dependencies. Check them.
> Framework/model alternatives are embedded in every ticket that uses them — swap via config, never by changing business logic.

---

## GLOBAL CONTEXT

### Hardware Constraints (affects every implementation decision)

| Device    | Specs                    | Role                                      |
|-----------|--------------------------|-------------------------------------------|
| Primary   | 16 GB RAM, CPU only      | All pipeline stages, primary inference    |
| Secondary | 8 GB RAM + GTX 1650 4 GB | Parallel runs; GPU inference for small models |

**GTX 1650 rules:**
- Usable VRAM: ~3.5 GB after OS/CUDA overhead
- Models ≤ 3.5 GB Q4_K_M → full GPU fit
- Models 4–6 GB → partial layer offload via `-ngl N` in llama.cpp
- Models > 6 GB → CPU only on secondary device
- Not suitable for training — inference only

### Model Progression Ladder (via Ollama)

| Tier | Model                      | Quant       | Size    | Primary | Secondary GPU | License    |
|------|----------------------------|-------------|---------|---------|---------------|------------|
| 0    | gemma3:270m                | FP16/BF16   | ~0.5 GB | ✅      | ✅ Full       | Apache 2.0 |
| 1    | qwen2.5:0.5b               | FP16/BF16   | ~1.0 GB | ✅      | ✅ Full       | Apache 2.0 |
| 2    | qwen3.5:0.8b               | Q4_K_M      | ~1.0 GB | ✅      | ✅ Full       | Apache 2.0 |
| 3    | smollm2:1.7b               | Q4_K_M      | ~1.1 GB | ✅      | ✅ Full       | Apache 2.0 |
| 4    | llama3.2:1b                | FP16/BF16   | ~2.0 GB | ✅      | ✅ Full       | Llama 3.2  |
| 5    | qwen2.5:1.5b               | Q4_K_M      | ~1.0 GB | ✅      | ✅ Full       | Apache 2.0 |
| 6    | gemma2:2b                  | Q8_0        | ~2.7 GB | ✅      | ✅ Full       | Gemma ToU  |
| 7    | gemma3n:e2b                | FP16/BF16   | ~2.0 GB | ✅      | ✅ Full       | Gemma ToU  |
| 8    | phi3:mini                  | Q4_K_M      | ~2.3 GB | ✅      | ✅ Full       | MIT        |
| 9    | phi4-mini                  | Q4_K_M      | ~2.5 GB | ✅      | ✅ Full       | MIT        |
| 10   | llama3.2:3b                | Q4_K_M      | ~2.0 GB | ✅      | ✅ Full       | Llama 3.2  |
| 11   | ministral:3b               | Q4_K_M      | ~2.0 GB | ✅      | ✅ Full       | Apache 2.0 |
| 12   | gemma3:4b                  | Q4_K_M      | ~2.5 GB | ✅      | ✅ Full       | Gemma ToU  |
| 13   | mistral:7b-v0.3            | Q4_K_M      | ~4.1 GB | ✅      | ⚠️ Partial   | Apache 2.0 |
| 14   | llama3:8b                  | Q4_K_M      | ~4.7 GB | ✅      | ⚠️ Partial   | Llama 3    |
| 15   | qwen2.5:7b                 | Q4_K_M      | ~4.5 GB | ✅      | ⚠️ Partial   | Apache 2.0 |
| 16   | qwen3:8b                   | Q4_K_M      | ~5.2 GB | ✅      | ❌ CPU only   | Apache 2.0 |
| 17   | granite4.1:8b              | Q4_K_M      | ~5.0 GB | ✅      | ❌ CPU only   | Apache 2.0 |
| 18   | gemma2:9b                  | Q4_K_M      | ~5.8 GB | ✅      | ❌ CPU only   | Gemma ToU  |
| 19   | qwen3.5:9b                 | Q4_K_M      | ~6.6 GB | ✅      | ❌ CPU only   | Apache 2.0 |

**Escalation rule:** Always start at the lowest tier that can attempt the task. Only escalate when benchmarks fail the threshold defined in the ticket. Never hardcode a model name — read it from config.

### Per-Task Model Starting Points

| Task                    | Start Tier | Escalate if…                               |
|-------------------------|------------|--------------------------------------------|
| Punctuation Restoration | Tier 0–1   | Accuracy < 90% on benchmark set            |
| Emotion Classification  | Tier 1–2   | F1 < 0.75 across emotion categories        |
| Dialogue Attribution    | Tier 2–3   | Attribution accuracy < 85%                 |
| Emphasis Detection      | Tier 1     | False positive rate > 15%                  |
| Prosody Markup          | Tier 2–3   | MOS improvement < 0.3 over baseline        |
| Full Narration Prep     | Tier 4–5   | Only after all subtasks have escalated     |

### Repository Structure

```
api/            # FastAPI service
worker/         # Celery workers
llmops/         # Streamlit experiment review UI
shared/         # Pydantic schemas, shared types, config loader
tests/          # All tests
datasets/       # Benchmark corpora, evaluation sets
experiments/    # MLflow experiment configs (YAML)
runs/           # Run outputs (gitignored large files)
artifacts/      # Versioned model/audio artifacts
docker-compose.yml
.env.example
requirements.txt
requirements-dev.txt
```

### Config Loading Pattern

Every swappable component reads its implementation from config. No component should contain an `if provider == "kokoro"` style branch in business logic. Use a factory.

```python
# shared/config.py
from pydantic_settings import BaseSettings

class Config(BaseSettings):
    # Storage (Primary: b2, Secondary: r2)
    storage_backend: str = "b2"           # b2 | r2 | minio | seaweedfs | filesystem
    b2_application_key_id: str = ""       # B2_APPLICATION_KEY_ID
    b2_application_key: str = ""          # B2_APPLICATION_KEY
    b2_bucket_id: str = ""                # B2_BUCKET_ID
    b2_bucket_name: str = ""              # B2_BUCKET_NAME
    b2_region: str = "us-west-004"        # e.g. us-west-004 — from your bucket endpoint

    # Parsers
    pdf_parser: str = "docling"           # docling | pdfplumber | pypdf | pymupdf
    ocr_backend: str = "rapidocr"         # rapidocr | easyocr | paddleocr | tesseract

    # Chunker
    chunker: str = "paragraph"            # paragraph | sentence | semantic | dialogue
    chunk_max_chars: int = 800

    # TTS
    tts_provider: str = "kokoro"          # kokoro | piper | melotts
    tts_voice: str = "af_bella"
    tts_speed: float = 1.0

    # LLM
    llm_runtime: str = "ollama"           # ollama | llamafile
    llm_model: str = "qwen2.5:0.5b"      # follow tier ladder
    llm_orchestration: str = "langgraph"  # langgraph | dspy | haystack
    llm_structured_output: str = "pydantic_ai"  # pydantic_ai | outlines | instructor

    # NLP
    sentence_detector: str = "spacy"      # spacy | nltk | stanza | nnsplit
    g2p_backend: str = "espeak"           # espeak | gruut | g2p_en

    # Experiment tracking
    mlflow_tracking_uri: str = "http://localhost:5000"
    langfuse_host: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
```

### Core ABCs (implement these first — all other tickets depend on them)

```python
# shared/interfaces.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

# --- Document Parsing ---
@dataclass
class ParseResult:
    markdown: str
    metadata: dict[str, Any]
    source_path: str
    parser_name: str

class Parser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> ParseResult: ...
    @property
    @abstractmethod
    def supported_formats(self) -> list[str]: ...

# --- Chunking ---
@dataclass
class Chunk:
    text: str
    index: int
    chunk_type: str          # "narration" | "dialogue" | "heading"
    metadata: dict[str, Any] = field(default_factory=dict)

class Chunker(ABC):
    @abstractmethod
    def chunk(self, text: str) -> list[Chunk]: ...

# --- TTS ---
@dataclass
class AudioSegment:
    audio_bytes: bytes
    sample_rate: int
    duration_seconds: float
    provider_name: str

class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, voice: str, speed: float = 1.0, **kwargs) -> AudioSegment: ...
    @property
    @abstractmethod
    def available_voices(self) -> list[str]: ...

# --- LLM ---
from pydantic import BaseModel
from typing import TypeVar, Type
T = TypeVar("T", bound=BaseModel)

class LLMProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str) -> str: ...
    @abstractmethod
    def complete_structured(self, prompt: str, schema: Type[T]) -> T: ...
```

### License Reference

| Symbol | Meaning |
|--------|---------|
| ✅ | Permissive (MIT / Apache 2.0 / BSD / ISC) — safe for all uses |
| ⚠️ | Copyleft (GPL / AGPL) — free for internal use; do not redistribute |
| 🔶 | Custom open-weight — free but not OSI-certified |

---

## EPIC 1 — Repository Foundation

---

### AUD-001 — Repository Bootstrap

**Status:** TODO
**Priority:** Critical
**Depends on:** —
**Blocks:** Everything

#### Implement

Create the flat directory structure. Set up pre-commit hooks and CI.

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
  interfaces.py    # ABCs from GLOBAL CONTEXT
  config.py        # Config class from GLOBAL CONTEXT
  schemas.py
  storage.py
  logging.py
tests/
  api/
  worker/
  shared/
datasets/
  .gitkeep
experiments/
  .gitkeep
runs/
  .gitignore   # ignore *.wav, *.mp3, *.bin
artifacts/
  .gitkeep
requirements.txt
requirements-dev.txt
.env.example
.pre-commit-config.yaml
.github/workflows/ci.yml
```

#### CI requirements

- `ruff check .` passes
- `mypy api/ worker/ shared/` passes
- `pytest tests/` with at least one smoke test per package passes

#### Acceptance criteria

- [ ] `git clone && python3 -m venv .venv && pip install -r requirements-dev.txt` succeeds
- [ ] CI workflow runs and passes on push
- [ ] `.env.example` contains every key defined in `Config` class

---

### AUD-002 — Docker Development Environment

**Status:** TODO
**Priority:** Critical
**Depends on:** AUD-001
**Blocks:** AUD-003, AUD-010

#### Implement

Create `docker-compose.yml` at repo root with the following services. All data directories must be volume-mounted so state survives container restarts.

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: audiobook
      POSTGRES_USER: audiobook
      POSTGRES_PASSWORD: audiobook
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports: ["5432:5432"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  mlflow:
    image: ghcr.io/mlflow/mlflow:latest
    command: mlflow server --host 0.0.0.0 --port 5000 --backend-store-uri postgresql://audiobook:audiobook@postgres/mlflow --default-artifact-root s3://audiobook-artifacts
    environment:
      MLFLOW_S3_ENDPOINT_URL: https://s3.${B2_REGION}.backblazeb2.com
      AWS_ACCESS_KEY_ID: ${B2_APPLICATION_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${B2_APPLICATION_KEY}
    depends_on: [postgres]
    ports: ["5000:5000"]

  langfuse:
    image: langfuse/langfuse:latest
    environment:
      DATABASE_URL: postgresql://audiobook:audiobook@postgres/langfuse
      NEXTAUTH_SECRET: local-dev-secret
      NEXTAUTH_URL: http://localhost:3000
    depends_on: [postgres]
    ports: ["3000:3000"]

  prometheus:
    image: prom/prometheus:latest
    volumes: ["./infra/prometheus.yml:/etc/prometheus/prometheus.yml"]
    ports: ["9090:9090"]

  grafana:
    image: grafana/grafana:latest
    environment:
      GF_AUTH_ANONYMOUS_ENABLED: "true"
      GF_AUTH_ANONYMOUS_ORG_ROLE: Admin
    volumes: ["grafana_data:/var/lib/grafana"]
    ports: ["3001:3000"]

  loki:
    image: grafana/loki:latest
    ports: ["3100:3100"]

  tempo:
    image: grafana/tempo:latest
    ports: ["3200:3200", "4317:4317"]
```

**Object Storage — Backblaze B2 (primary)**

B2 is used for artifact storage (audio files, parsed markdown, metrics). It exposes an S3-compatible API — use `boto3` with a custom endpoint. The endpoint hostname encodes the region (e.g. `us-west-004`): `s3.<region>.backblazeb2.com`. Read the region from `b2_region` in config so it stays in one place.

```python
# shared/storage.py
import boto3
from botocore.config import Config as BotoConfig
from shared.config import Config

def get_b2_client(cfg: Config):
    return boto3.client(
        "s3",
        endpoint_url=f"https://s3.{cfg.b2_region}.backblazeb2.com",
        aws_access_key_id=cfg.b2_application_key_id,
        aws_secret_access_key=cfg.b2_application_key,
        config=BotoConfig(signature_version="s3v4"),
        region_name=cfg.b2_region,
    )
```

> **Note:** Use `cfg.b2_bucket_name` when addressing bucket operations. `cfg.b2_bucket_id` is needed for B2-native API calls (e.g. `b2sdk`) but not for the S3-compatible path — keep it in config for future use.

**Storage alternatives (swap via `storage_backend` config key):**

| Backend    | When to use |
|------------|-------------|
| MinIO      | Air-gapped / fully offline deployment (AGPL — internal only) |
| SeaweedFS  | Self-hosted, OSI-licensed alternative to MinIO |
| LocalStack | Local dev/CI only — `AWS_ENDPOINT_URL=http://localhost:4566` |
| Filesystem | Earliest experiment runs before B2 is configured |

#### Acceptance criteria

- [ ] `docker compose up -d` completes without errors
- [ ] `postgres` reachable at `localhost:5432`
- [ ] `redis` reachable at `localhost:6379`
- [ ] MLflow UI accessible at `http://localhost:5000`
- [ ] Langfuse UI accessible at `http://localhost:3000`
- [ ] Grafana accessible at `http://localhost:3001`

---

### AUD-003 — FastAPI Service Bootstrap

**Status:** TODO
**Priority:** Critical
**Depends on:** AUD-002
**Blocks:** AUD-020, AUD-010

#### Implement

```
api/
  main.py            # FastAPI app factory
  config.py          # re-exports shared Config; adds API-specific fields
  routers/
    health.py        # GET /health
    documents.py     # stub, filled by AUD-020
    experiments.py   # stub, filled by AUD-010
  middleware/
    logging.py       # structlog JSON logging
    tracing.py       # OpenTelemetry OTLP exporter to Tempo
  db/
    session.py       # SQLAlchemy async engine + session factory
    base.py          # declarative Base
```

`GET /health` must return:

```json
{
  "status": "healthy",
  "db": "connected",
  "redis": "connected",
  "version": "<git-sha>"
}
```

Include `git_sha` by reading `GIT_SHA` env var (set in docker build / CI).

#### Logging

Use `structlog` with JSON output. Every request must log: `method`, `path`, `status_code`, `duration_ms`, `request_id`.

#### Tracing

Use `opentelemetry-sdk` + `opentelemetry-exporter-otlp-proto-grpc`. Export to Tempo at `OTEL_EXPORTER_OTLP_ENDPOINT` (default: `http://localhost:4317`).

#### Acceptance criteria

- [ ] `GET /health` returns `200` with `{"status": "healthy"}`
- [ ] Logs appear as JSON in stdout
- [ ] Traces appear in Tempo/Grafana after a request

---

## EPIC 2 — Experiment Framework

---

### AUD-010 — Experiment Domain Models

**Status:** TODO
**Priority:** High
**Depends on:** AUD-003
**Blocks:** AUD-011, AUD-012

#### Implement

SQLAlchemy 2 async models + Pydantic schemas + Alembic migration.

```python
# api/db/models.py
import uuid
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import JSON, String, DateTime
from api.db.base import Base

class Experiment(Base):
    __tablename__ = "experiments"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str | None]
    pipeline_config: Mapped[dict] = mapped_column(JSON)   # full PipelineConfig dict
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

class Run(Base):
    __tablename__ = "runs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("experiments.id"))
    run_id: Mapped[str]           # MLflow run_id
    git_sha: Mapped[str]
    branch: Mapped[str]
    timestamp: Mapped[datetime]
    status: Mapped[str]           # "running" | "completed" | "failed"
    config_snapshot: Mapped[dict] = mapped_column(JSON)
```

```python
# shared/schemas.py
from pydantic import BaseModel

class PipelineConfig(BaseModel):
    pdf_parser: str = "docling"
    ocr_backend: str = "rapidocr"
    chunker: str = "paragraph"
    chunk_max_chars: int = 800
    tts_provider: str = "kokoro"
    tts_voice: str = "af_bella"
    tts_speed: float = 1.0
    llm_model: str = "qwen2.5:0.5b"
    llm_orchestration: str = "langgraph"
    sentence_detector: str = "spacy"
    g2p_backend: str = "espeak"
    dsp_preset: str = "default"
    extra: dict = {}
```

**Experiment YAML format** (stored in `experiments/`):

```yaml
# experiments/baseline-kokoro-v1.yaml
name: baseline-kokoro-v1
description: Paragraph chunker + Kokoro default voice
pipeline_config:
  pdf_parser: docling
  chunker: paragraph
  tts_provider: kokoro
  tts_voice: af_bella
  tts_speed: 1.0
  llm_model: qwen2.5:0.5b
```

#### Acceptance criteria

- [ ] Alembic migration `alembic upgrade head` creates `experiments` and `runs` tables
- [ ] A YAML file in `experiments/` can be loaded into `PipelineConfig` without error
- [ ] `POST /experiments` creates a DB record with the config stored as JSON

---

### AUD-011 — Run Tracking

**Status:** TODO
**Priority:** High
**Depends on:** AUD-010
**Blocks:** AUD-012, AUD-054

#### Implement

```python
# api/services/run_service.py
import subprocess
from shared.schemas import PipelineConfig
import mlflow

class RunTracker:
    def start_run(self, experiment_name: str, config: PipelineConfig) -> str:
        git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
        branch = subprocess.check_output(["git", "branch", "--show-current"]).decode().strip()

        mlflow.set_experiment(experiment_name)
        with mlflow.start_run() as run:
            mlflow.log_params(config.model_dump())
            mlflow.set_tags({"git_sha": git_sha, "branch": branch})
            return run.info.run_id

    def log_metric(self, run_id: str, key: str, value: float, step: int | None = None):
        with mlflow.start_run(run_id=run_id):
            mlflow.log_metric(key, value, step=step)

    def end_run(self, run_id: str, status: str = "FINISHED"):
        mlflow.end_run(status=status)
```

Every pipeline execution must call `RunTracker.start_run()` before processing begins and `end_run()` when done or on exception.

#### Acceptance criteria

- [ ] Every pipeline run creates an MLflow run with `git_sha`, `branch`, `timestamp`, and full `PipelineConfig` as params
- [ ] Failed runs are marked `FAILED` in MLflow, not left as `RUNNING`
- [ ] Run ID is stored in the `runs` DB table and linked to its `experiment_id`

---

### AUD-012 — Artifact Registry

**Status:** TODO
**Priority:** High
**Depends on:** AUD-011
**Blocks:** AUD-054

#### Implement

```python
# api/services/artifact_service.py
from enum import StrEnum
import mlflow

class ArtifactType(StrEnum):
    MARKDOWN = "markdown"
    AUDIO = "audio"
    METRICS = "metrics"
    TRACES = "traces"

class ArtifactRegistry:
    def log(self, run_id: str, local_path: str, artifact_type: ArtifactType):
        """Logs file to MLflow (which uses B2 as artifact store)."""
        with mlflow.start_run(run_id=run_id):
            mlflow.log_artifact(local_path, artifact_path=artifact_type.value)

    def get_uri(self, run_id: str, artifact_type: ArtifactType, filename: str) -> str:
        return f"runs:/{run_id}/{artifact_type.value}/{filename}"
```

**Artifact types and their storage paths:**

| Type     | Extension | Path pattern |
|----------|-----------|--------------|
| markdown | `.md`     | `{run_id}/markdown/{document_id}.md` |
| audio    | `.mp3`    | `{run_id}/audio/{chapter_id}.mp3` |
| metrics  | `.json`   | `{run_id}/metrics/summary.json` |
| traces   | `.jsonl`  | `{run_id}/traces/pipeline.jsonl` |

#### Acceptance criteria

- [ ] Artifact uploaded during a run is retrievable via MLflow UI
- [ ] Each artifact record links back to its `run_id` in the DB
- [ ] Artifacts land in B2 bucket (verify via B2 dashboard or `b2 ls`)

---

## EPIC 3 — Document Ingestion

---

### AUD-020 — Document Upload API

**Status:** TODO
**Priority:** High
**Depends on:** AUD-003, AUD-012
**Blocks:** AUD-021

#### Implement

```python
# api/routers/documents.py
from fastapi import APIRouter, UploadFile, File, Depends

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".epub"}

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    storage: StorageService = Depends(get_storage),
) -> dict:
    # Validate extension
    # Stream to B2 at key: uploads/{uuid}/{original_filename}
    # Return: {"document_id": uuid, "storage_key": key, "size_bytes": n}
```

**B2 upload** — use multipart upload for files > 10 MB:

```python
# shared/storage.py
class StorageService:
    def upload(self, key: str, data: bytes | IO, content_type: str) -> str:
        self.client.put_object(Bucket=self.bucket_name, Key=key, Body=data, ContentType=content_type)
        return f"https://s3.{self.region}.backblazeb2.com/{self.bucket_name}/{key}"
```

#### Acceptance criteria

- [ ] `POST /documents/upload` with a PDF returns `201` and a `document_id`
- [ ] File is visible in B2 bucket under `uploads/{document_id}/`
- [ ] Unsupported formats (`.txt`, `.png`) return `422`
- [ ] Files > 100 MB use multipart upload without memory errors

---

### AUD-021 — Parser Abstraction Layer

**Status:** TODO
**Priority:** High
**Depends on:** AUD-020
**Blocks:** AUD-022, AUD-023

#### Implement

```python
# api/parsers/factory.py
from shared.config import Config
from shared.interfaces import Parser

def get_parser(cfg: Config, file_format: str) -> Parser:
    if file_format == ".pdf":
        match cfg.pdf_parser:
            case "docling":   from .docling_parser import DoclingParser; return DoclingParser()
            case "pdfplumber": from .pdfplumber_parser import PDFPlumberParser; return PDFPlumberParser()
            case "pypdf":     from .pypdf_parser import PyPDFParser; return PyPDFParser()
            case "pymupdf":   from .pymupdf_parser import PyMuPDFParser; return PyMuPDFParser()
    elif file_format == ".docx":
        from .docx_parser import DocxParser; return DocxParser()
    elif file_format == ".epub":
        from .epub_parser import EpubParser; return EpubParser()
    raise ValueError(f"No parser for format: {file_format}")
```

**Parser alternatives per format:**

PDF:
| Implementation | Package | When to prefer |
|---------------|---------|----------------|
| `DoclingParser` (default) | `docling` (MIT) | Structured markdown with headings, tables |
| `PDFPlumberParser` | `pdfplumber` (MIT) | Text + table extraction without LLM |
| `PyPDFParser` | `pypdf` (MIT) | Lightweight; basic text only |
| `PyMuPDFParser` | `pymupdf` (AGPL) | Fastest; richest; internal use only |

OCR (used by DoclingParser internally, also injectable):
| Implementation | Package | When to prefer |
|---------------|---------|----------------|
| `RapidOCRBackend` (default) | `rapidocr-onnxruntime` (Apache 2.0) | CPU-optimised ONNX |
| `EasyOCRBackend` | `easyocr` (Apache 2.0) | Better on degraded/skewed scans |
| `PaddleOCRBackend` | `paddleocr` (Apache 2.0) | Best accuracy; heavier |
| `TesseractBackend` | `pytesseract` (Apache 2.0) | Lightest; weakest on complex layouts |

DOCX:
| Implementation | Package | When to prefer |
|---------------|---------|----------------|
| `DocxParser` (default) | `python-docx` (MIT) | Full style/structure access |
| `MammothParser` | `mammoth` (MIT) | Better semantic HTML output |

EPUB:
| Implementation | Package | When to prefer |
|---------------|---------|----------------|
| `EpubParser` (default) | `ebooklib` (AGPL — internal only) | Mature EPUB2/EPUB3 |
| `BSEpubParser` | `beautifulsoup4` (MIT) | Raw HTML parsing; more control |

#### Acceptance criteria

- [ ] Changing `pdf_parser` in `.env` switches implementation without code changes
- [ ] All parser implementations return a `ParseResult` with valid markdown
- [ ] `ParseResult.parser_name` is logged as an MLflow param on every run

---

### AUD-022 — Docling Integration

**Status:** TODO
**Priority:** High
**Depends on:** AUD-021
**Blocks:** AUD-030

#### Implement

```python
# api/parsers/docling_parser.py
from docling.document_converter import DocumentConverter
from shared.interfaces import Parser, ParseResult

class DoclingParser(Parser):
    def __init__(self):
        self._converter = DocumentConverter()

    @property
    def supported_formats(self) -> list[str]:
        return [".pdf"]

    def parse(self, file_path: str) -> ParseResult:
        result = self._converter.convert(file_path)
        markdown = result.document.export_to_markdown()
        return ParseResult(
            markdown=markdown,
            metadata={"page_count": result.document.page_count},
            source_path=file_path,
            parser_name="docling",
        )
```

**Install:** `pip install docling` — pulls in `docling-core`, `docling-ibm-models`. First run downloads models (~500 MB); cache at `~/.cache/docling`.

**CPU note:** Docling's layout model runs on CPU. On primary device (16 GB), a 300-page PDF takes ~2–4 min. This is acceptable for an experiment platform.

#### Acceptance criteria

- [ ] A 10-page PDF with headings produces markdown with `#`, `##` headings preserved
- [ ] A PDF with tables produces markdown tables
- [ ] `ParseResult.metadata["page_count"]` matches the source PDF

---

### AUD-023 — RapidOCR Integration

**Status:** TODO
**Priority:** Medium
**Depends on:** AUD-021
**Blocks:** AUD-030

#### Implement

```python
# api/parsers/rapidocr_backend.py
from rapidocr_onnxruntime import RapidOCR
from shared.interfaces import Parser, ParseResult

class RapidOCRParser(Parser):
    def __init__(self):
        self._engine = RapidOCR()

    @property
    def supported_formats(self) -> list[str]:
        return [".pdf"]   # scanned PDFs only; rasterize pages first

    def parse(self, file_path: str) -> ParseResult:
        # 1. Rasterize each page to numpy array via pypdf + Pillow
        # 2. Run self._engine(page_array) → (boxes, texts, scores)
        # 3. Join texts in reading order
        # 4. Return as plain markdown (no structure detection)
        ...
```

**Rasterisation helper:**
```python
import fitz  # pymupdf — only for rasterisation, not parsing
def rasterize_pdf(path: str, dpi: int = 150) -> list:
    doc = fitz.open(path)
    return [page.get_pixmap(dpi=dpi).tobytes("png") for page in doc]
```

**OCR backend alternatives:**

| Backend | Notes |
|---------|-------|
| `EasyOCRBackend` | Better recall on low-quality scans; slower |
| `PaddleOCRBackend` | Best accuracy; requires PaddlePaddle (heavy) |
| `TesseractBackend` | `pytesseract.image_to_string(img)` — lightest |

#### Acceptance criteria

- [ ] A scanned PDF (image-only, no text layer) produces non-empty text output
- [ ] WER of output vs ground truth < 10% on a clean scan test document
- [ ] OCR backend is swappable via `ocr_backend` config key

---

## EPIC 4 — Structural Understanding

---

### AUD-030 — Chapter Detection Engine

**Status:** TODO
**Priority:** High
**Depends on:** AUD-022
**Blocks:** AUD-031, AUD-032

#### Implement

```python
# api/structure/chapter_detector.py
from dataclasses import dataclass
import re

@dataclass
class Chapter:
    index: int
    title: str
    start_char: int
    end_char: int
    text: str

class ChapterDetector:
    # Detect markdown headings: # Title, ## Title, or "Chapter N" / "CHAPTER N"
    HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
    CHAPTER_WORD_RE = re.compile(r"^(chapter\s+\d+|part\s+\d+)", re.IGNORECASE | re.MULTILINE)

    def detect(self, markdown: str) -> list[Chapter]:
        # Returns chapters with text slices
        ...
```

Chapter metadata must be stored in the DB and logged as MLflow artifacts per run.

#### Acceptance criteria

- [ ] A markdown document with `# Chapter 1` headings produces one `Chapter` per heading
- [ ] A document without headings but with "Chapter N" text patterns still detects chapters
- [ ] `chapter_count` logged as an MLflow metric per run

---

### AUD-031 — Paragraph Detection

**Status:** TODO
**Priority:** Medium
**Depends on:** AUD-030
**Blocks:** AUD-040

#### Implement

Preserve paragraph boundaries from markdown (double-newline separated blocks). Do not merge paragraphs unless they are shorter than `min_paragraph_chars` (configurable, default 50).

```python
# api/structure/paragraph_detector.py
class ParagraphDetector:
    def detect(self, text: str, min_chars: int = 50) -> list[str]:
        # Split on double newlines, strip, filter blanks and very short fragments
        ...
```

#### Acceptance criteria

- [ ] Paragraphs from a novel chapter are correctly split at double-newline boundaries
- [ ] Paragraph count is logged as MLflow metric

---

### AUD-032 — Dialogue Detection

**Status:** TODO
**Priority:** High
**Depends on:** AUD-031
**Blocks:** AUD-044, AUD-083

#### Implement

```python
# api/structure/dialogue_detector.py
from enum import StrEnum
from dataclasses import dataclass
import spacy

class TextType(StrEnum):
    NARRATION = "narration"
    DIALOGUE = "dialogue"

@dataclass
class TaggedSpan:
    text: str
    text_type: TextType
    start: int
    end: int

class DialogueDetector:
    # Patterns: "quoted text", 'quoted text', — em-dash dialogue (French/Spanish style)
    QUOTE_RE = re.compile(r'(["""\'])(.*?)\1', re.DOTALL)

    def __init__(self):
        self._nlp = spacy.load("en_core_web_sm")

    def tag(self, text: str) -> list[TaggedSpan]:
        # 1. Find all quoted spans → DIALOGUE
        # 2. Everything between quotes → NARRATION
        # 3. Use spaCy Matcher for custom edge cases (em-dash dialogue)
        ...
```

**NLP backend alternatives:**

| Backend | Package | Notes |
|---------|---------|-------|
| `spaCy` (default) | `spacy` (MIT) | Fast, strong Matcher rules |
| `NLTK` | `nltk` (Apache 2.0) | Good Punkt sentence tokenizer; no Matcher |
| `Stanza` | `stanza` (Apache 2.0) | Stanford NLP; multilingual |
| `nnsplit` | `nnsplit` (MIT) | Neural sentence splitter; fast |

Backend is swappable via `sentence_detector` config key.

#### Acceptance criteria

- [ ] A passage with 5 dialogue lines and narration is correctly split into `DIALOGUE` and `NARRATION` spans
- [ ] Dialogue detection accuracy benchmark created: logs `dialogue_precision` and `dialogue_recall` to MLflow

---

## EPIC 5 — Chunking Framework

---

### AUD-040 — Chunking Framework

**Status:** TODO
**Priority:** High
**Depends on:** AUD-031, AUD-032
**Blocks:** AUD-041–AUD-044, AUD-050

#### Implement

```python
# api/chunkers/factory.py
from shared.config import Config
from shared.interfaces import Chunker

def get_chunker(cfg: Config) -> Chunker:
    match cfg.chunker:
        case "paragraph": from .paragraph_chunker import ParagraphChunker; return ParagraphChunker(cfg)
        case "sentence":  from .sentence_chunker import SentenceChunker; return SentenceChunker(cfg)
        case "semantic":  from .semantic_chunker import SemanticChunker; return SemanticChunker(cfg)
        case "dialogue":  from .dialogue_chunker import DialogueChunker; return DialogueChunker(cfg)
    raise ValueError(f"Unknown chunker: {cfg.chunker}")
```

Chunker is selected at pipeline start via `Config.chunker`. The config value is logged as an MLflow param on every run.

#### Acceptance criteria

- [ ] Changing `chunker=sentence` in `.env` switches implementation without touching pipeline code
- [ ] `chunk_count` and `avg_chunk_chars` logged as MLflow metrics per run

---

### AUD-041 — Paragraph Chunker

**Status:** TODO
**Priority:** High
**Depends on:** AUD-040

#### Implement

Split on double-newline paragraph boundaries. If a paragraph exceeds `chunk_max_chars`, split at the nearest sentence boundary using spaCy.

```python
class ParagraphChunker(Chunker):
    def chunk(self, text: str) -> list[Chunk]:
        # Split on \n\n, assign chunk_type based on DialogueDetector
        ...
```

---

### AUD-042 — Sentence Chunker

**Status:** TODO
**Priority:** Medium
**Depends on:** AUD-040

#### Implement

Use configured `sentence_detector` (spaCy default) to split. Merge short sentences up to `chunk_max_chars`. Respect paragraph boundaries — do not merge sentences across paragraphs.

---

### AUD-043 — Semantic Chunker

**Status:** TODO
**Priority:** Medium
**Depends on:** AUD-040

#### Implement

Use sentence embeddings to find natural topic shift boundaries. Use `sentence-transformers/all-MiniLM-L6-v2` (Apache 2.0, ~80 MB, CPU-friendly). Split where cosine similarity between adjacent sentence embeddings drops below threshold (default 0.75, configurable).

**Hardware note:** MiniLM-L6-v2 at 80 MB runs comfortably on primary device CPU. Embedding 100 sentences takes ~2–5 seconds.

#### Acceptance criteria

- [ ] Semantic chunker produces fewer but larger chunks than sentence chunker on the same text
- [ ] Similarity threshold is configurable and logged as MLflow param

---

### AUD-044 — Dialogue Chunker

**Status:** TODO
**Priority:** Medium
**Depends on:** AUD-040, AUD-032

#### Implement

Preserve complete dialogue exchanges as single chunks. A "dialogue exchange" is a sequence of consecutive `DIALOGUE` spans (from AUD-032) optionally surrounded by attribution narration (e.g. `"he said"`). Do not split mid-exchange.

---

## EPIC 6 — Baseline Audiobook Generation

---

### AUD-050 — TTS Provider Abstraction

**Status:** TODO
**Priority:** Critical
**Depends on:** AUD-040
**Blocks:** AUD-051, AUD-051b, AUD-054

#### Implement

```python
# api/tts/factory.py
from shared.config import Config
from shared.interfaces import TTSProvider

def get_tts_provider(cfg: Config) -> TTSProvider:
    match cfg.tts_provider:
        case "kokoro":  from .kokoro_provider import KokoroProvider; return KokoroProvider(cfg)
        case "piper":   from .piper_provider import PiperProvider; return PiperProvider(cfg)
        case "melotts": from .melotts_provider import MeloTTSProvider; return MeloTTSProvider(cfg)
    raise ValueError(f"Unknown TTS provider: {cfg.tts_provider}")
```

**TTS engine alternatives:**

| Engine | Package | CPU Suitability | Notes |
|--------|---------|-----------------|-------|
| Kokoro (default) | `kokoro` (Apache 2.0) | ✅ Excellent | 82M params; fast; ~54 voices |
| Piper | `piper-tts` (MIT) | ✅ Excellent | ONNX; fastest CPU option; models 60–200 MB |
| MeloTTS | `melo-tts` (MIT) | ✅ Good | Multi-lingual; good quality |
| StyleTTS2 | `styletts2` (MIT) | ⚠️ Moderate | Higher quality; GPU helpful |
| F5-TTS | `f5-tts` (MIT) | ⚠️ Moderate | Zero-shot cloning; experimental |
| Bark | `bark` (MIT) | ❌ Heavy | 1.1B params; too slow for CPU batch |

#### Acceptance criteria

- [ ] Changing `tts_provider=piper` in `.env` switches TTS engine without code changes
- [ ] `tts_provider`, `tts_voice`, `tts_speed` logged as MLflow params per run

---

### AUD-051 — Kokoro Provider

**Status:** TODO
**Priority:** Critical
**Depends on:** AUD-050

#### Implement

```python
# api/tts/kokoro_provider.py
import soundfile as sf
import numpy as np
from kokoro import KPipeline
from shared.interfaces import TTSProvider, AudioSegment

class KokoroProvider(TTSProvider):
    def __init__(self, cfg):
        self._pipeline = KPipeline(lang_code="a")  # "a" = American English
        self._voice = cfg.tts_voice
        self._speed = cfg.tts_speed

    @property
    def available_voices(self) -> list[str]:
        # Return list of all voice IDs from kokoro voice registry
        ...

    def synthesize(self, text: str, voice: str | None = None, speed: float | None = None, **kwargs) -> AudioSegment:
        v = voice or self._voice
        s = speed or self._speed
        generator = self._pipeline(text, voice=v, speed=s, split_pattern=r"\n+")
        audio_chunks = [audio for _, _, audio in generator]
        audio = np.concatenate(audio_chunks)
        # Write to bytes buffer at 24000 Hz
        import io
        buf = io.BytesIO()
        sf.write(buf, audio, 24000, format="WAV")
        return AudioSegment(
            audio_bytes=buf.getvalue(),
            sample_rate=24000,
            duration_seconds=len(audio) / 24000,
            provider_name="kokoro",
        )
```

**Voice blending support (needed for AUD-KE-003):**

```python
    def synthesize_blended(self, text: str, voice_a: str, voice_b: str, alpha: float) -> AudioSegment:
        # Load voice tensors and interpolate: voice = alpha * v_a + (1 - alpha) * v_b
        # Then synthesize with blended voice
        ...
```

#### Acceptance criteria

- [ ] `synthesize("Hello world", voice="af_bella")` returns a non-empty `AudioSegment`
- [ ] Output WAV is playable with correct duration
- [ ] Blended voice synthesis works for any `alpha` in [0.0, 1.0]

---

### AUD-051b — Piper Provider

**Status:** TODO
**Priority:** Medium
**Depends on:** AUD-050
**Note:** Parallel to AUD-051; enables early Kokoro vs Piper comparison

#### Implement

```python
# api/tts/piper_provider.py
import subprocess, io
from shared.interfaces import TTSProvider, AudioSegment

class PiperProvider(TTSProvider):
    """
    Piper TTS — MIT License — https://github.com/rhasspy/piper
    ONNX-based; models 60–200 MB each; no Python runtime overhead.
    Install: pip install piper-tts
    Models: downloaded to ~/.local/share/piper/voices/
    """
    def __init__(self, cfg):
        self._model = cfg.tts_voice   # e.g. "en_US-lessac-medium"
        self._speed = cfg.tts_speed

    @property
    def available_voices(self) -> list[str]:
        # List .onnx files in voice cache directory
        ...

    def synthesize(self, text: str, voice: str | None = None, speed: float | None = None, **kwargs) -> AudioSegment:
        # Use piper Python API or subprocess:
        # echo "text" | piper --model {model}.onnx --output_raw | ...
        ...
```

**Piper voice download:**

```bash
python -m piper.download --voice en_US-lessac-medium --data-dir ~/.local/share/piper
```

#### Acceptance criteria

- [ ] `synthesize("Hello world")` returns valid WAV via Piper
- [ ] Speed is meaningfully different at 0.75 vs 1.25

---

### AUD-052 — Voice Registry

**Status:** TODO
**Priority:** Medium
**Depends on:** AUD-051, AUD-051b

#### Implement

```python
# api/tts/voice_registry.py
from dataclasses import dataclass

@dataclass
class VoiceInfo:
    voice_id: str
    provider: str
    language: str
    gender: str
    description: str

class VoiceRegistry:
    def list_voices(self, provider: str | None = None) -> list[VoiceInfo]: ...
    def get_voice(self, voice_id: str) -> VoiceInfo: ...
```

Voice selection in `PipelineConfig` must reference a `voice_id` from the registry, not a raw string.

---

### AUD-053 — Audio Stitching

**Status:** TODO
**Priority:** High
**Depends on:** AUD-051
**Blocks:** AUD-054

#### Implement

```python
# api/audio/stitcher.py
from pydub import AudioSegment as PydubSegment
from shared.interfaces import AudioSegment

class AudioStitcher:
    def stitch(
        self,
        segments: list[AudioSegment],
        silence_between_ms: int = 200,
        crossfade_ms: int = 0,
    ) -> bytes:
        """
        Concatenates AudioSegment list into a single MP3.
        silence_between_ms: silence inserted between each chunk
        crossfade_ms: if > 0, crossfade at junctions instead of silence
        """
        ...

    def export_mp3(self, audio_bytes: bytes, bitrate: str = "192k") -> bytes:
        ...
```

**DSP alternatives:**

| Library | Package | Notes |
|---------|---------|-------|
| Pydub (default) | `pydub` (MIT) | Simple, widely compatible |
| pedalboard | `pedalboard` (GPL-3.0) | Spotify; richer DSP effects |
| scipy.signal | `scipy` (BSD) | Low-level; maximum control |
| soundfile | `soundfile` (BSD) | Read/write only; combine with librosa |

#### Acceptance criteria

- [ ] 10 `AudioSegment` objects stitch into a single MP3 without audible gaps
- [ ] `silence_between_ms=0` and `crossfade_ms=50` both work correctly
- [ ] Output MP3 duration ≈ sum of input durations + silence

---

### AUD-054 — Audiobook Generation Pipeline

**Status:** TODO
**Priority:** Critical
**Depends on:** AUD-011, AUD-012, AUD-040, AUD-053
**Blocks:** AUD-060

#### Implement

```python
# worker/tasks/pipeline_task.py
from celery import shared_task
from shared.schemas import PipelineConfig

@shared_task(bind=True, max_retries=1)
def generate_audiobook(self, document_id: str, config_dict: dict):
    cfg = PipelineConfig(**config_dict)
    run_id = run_tracker.start_run(experiment_name="audiobook-generation", config=cfg)
    try:
        # 1. Download source file from B2
        # 2. parser = get_parser(cfg, file_ext)
        # 3. result = parser.parse(local_path)
        # 4. chapters = chapter_detector.detect(result.markdown)
        # 5. For each chapter:
        #    a. chunks = get_chunker(cfg).chunk(chapter.text)
        #    b. For each chunk:
        #       - segments = tts.synthesize(chunk.text, cfg.tts_voice, cfg.tts_speed)
        #    c. chapter_audio = stitcher.stitch(segments)
        #    d. artifact_registry.log(run_id, chapter_mp3_path, ArtifactType.AUDIO)
        # 6. run_tracker.end_run(run_id, "FINISHED")
    except Exception as e:
        run_tracker.end_run(run_id, "FAILED")
        raise self.retry(exc=e)
```

**Pipeline:** Document → Parser → Chapter Detection → Chunker → TTS Provider → Stitcher → MP3

#### Acceptance criteria

- [ ] A full PDF generates one MP3 per chapter in B2
- [ ] Run is logged in MLflow with all config params
- [ ] Failed run is marked `FAILED` in MLflow and DB
- [ ] Re-running with a different `PipelineConfig` creates a new MLflow run (not overwriting)

---

## EPIC 7 — Evaluation Framework

---

### AUD-060 — Runtime Metrics Collection

**Status:** TODO
**Priority:** High
**Depends on:** AUD-054

#### Implement

Wrap each pipeline stage with timing and resource collection. Use `psutil` for memory/CPU.

```python
# shared/metrics.py
import time, psutil
from contextlib import contextmanager

@contextmanager
def measure(run_id: str, stage: str, run_tracker):
    proc = psutil.Process()
    mem_before = proc.memory_info().rss / 1e6
    t0 = time.perf_counter()
    yield
    elapsed = time.perf_counter() - t0
    mem_after = proc.memory_info().rss / 1e6
    run_tracker.log_metric(run_id, f"{stage}.duration_s", elapsed)
    run_tracker.log_metric(run_id, f"{stage}.memory_delta_mb", mem_after - mem_before)
```

**Metrics to collect:**

| Metric | Unit | Stage |
|--------|------|-------|
| `parse.duration_s` | seconds | Parser |
| `chunk.count` | integer | Chunker |
| `chunk.avg_chars` | characters | Chunker |
| `tts.rtf` | ratio | TTS (real-time factor = gen_time / audio_duration) |
| `tts.duration_s` | seconds | TTS per chunk |
| `pipeline.total_s` | seconds | Full pipeline |
| `pipeline.memory_peak_mb` | MB | Full pipeline |
| `pipeline.cpu_pct` | percent | Full pipeline |

RTF is the most important TTS metric: RTF < 1.0 means faster than real-time.

---

### AUD-061 — Chunk Metrics

**Status:** TODO
**Priority:** Medium
**Depends on:** AUD-054

Log per-chunk metrics to MLflow. Store chunk-level data as a `metrics/chunks.jsonl` artifact.

**Metrics per chunk:**

| Metric | Description |
|--------|-------------|
| `char_count` | Character length |
| `word_count` | Word count |
| `chunk_type` | narration / dialogue |
| `tts_duration_s` | Time to synthesize |
| `audio_duration_s` | Length of resulting audio |
| `rtf` | Per-chunk real-time factor |

---

### AUD-062 — Audio Metrics

**Status:** TODO
**Priority:** Medium
**Depends on:** AUD-054

```python
# shared/audio_metrics.py
import librosa
import numpy as np

def compute_audio_metrics(audio_path: str) -> dict:
    y, sr = librosa.load(audio_path, sr=None)
    silence_pct = (np.abs(y) < 0.01).sum() / len(y) * 100
    spectral_flatness = librosa.feature.spectral_flatness(y=y).mean()
    duration = librosa.get_duration(y=y, sr=sr)
    size_mb = os.path.getsize(audio_path) / 1e6
    return {
        "duration_s": duration,
        "silence_pct": silence_pct,
        "spectral_flatness": float(spectral_flatness),
        "size_mb": size_mb,
    }
```

---

### AUD-063 — Evaluation Reports

**Status:** TODO
**Priority:** Medium
**Depends on:** AUD-060, AUD-061, AUD-062

```python
# shared/evaluation.py
import mlflow

def compare_experiments(run_id_a: str, run_id_b: str) -> dict:
    """
    Returns a side-by-side comparison of two MLflow runs.
    Output is logged as metrics/comparison.json artifact on run_id_a.
    """
    client = mlflow.tracking.MlflowClient()
    a = client.get_run(run_id_a)
    b = client.get_run(run_id_b)
    ...
```

Report must include: config diff, metric diff (with Δ and % change), artifact sizes.

#### Acceptance criteria

- [ ] `compare_experiments(run_a, run_b)` produces a JSON diff of all metrics
- [ ] Report is stored as an artifact linked to both runs
- [ ] Report is accessible from the MLflow UI

---

## EPIC 8 — Prosody Preparation

---

### AUD-070 — Prosody Processor Framework

**Status:** TODO
**Priority:** High
**Depends on:** AUD-040
**Blocks:** AUD-071–AUD-073, AUD-KE-005

#### Implement

```python
# api/prosody/base.py
from abc import ABC, abstractmethod
from shared.interfaces import Chunk

class ProsodyProcessor(ABC):
    @abstractmethod
    def process(self, chunk: Chunk) -> Chunk:
        """Returns the chunk with text modified for prosody."""
        ...

class ProsodyPipeline:
    def __init__(self, processors: list[ProsodyProcessor]):
        self._processors = processors

    def run(self, chunk: Chunk) -> Chunk:
        for p in self._processors:
            chunk = p.process(chunk)
        return chunk
```

Processors are composed in order and configured via a list in `PipelineConfig.prosody_processors`.

---

### AUD-071 — Pause Injection Engine

**Status:** TODO
**Priority:** Medium
**Depends on:** AUD-070

```python
class PauseInjector(ProsodyProcessor):
    """
    Replaces or supplements punctuation with explicit pause markers
    that Kokoro responds to.
    Configurable: pause style, dialogue pause ms, paragraph pause ms.
    """
    def process(self, chunk: Chunk) -> Chunk:
        # Replace — with ,  (or …, configurable)
        # Add ... after sentence-ending . if next sentence starts a dialogue
        ...
```

All pause parameters are experiment axes in AUD-KE-005.

---

### AUD-072 — Emphasis Detection

**Status:** TODO
**Priority:** Medium
**Depends on:** AUD-070

Detect words that should receive prosodic stress. Use one of:
- ALL-CAPS words (reliable signal in source text)
- Italic markers (`*word*` in markdown)
- spaCy dependency parse to identify syntactic focus

```python
class EmphasisDetector(ProsodyProcessor):
    def process(self, chunk: Chunk) -> Chunk:
        # Mark detected emphasis words for downstream TTS handling
        # Store in chunk.metadata["emphasis_tokens"]
        ...
```

**LLM model for this task:** Start at Tier 1 (SmolLM2 1.7B). Escalate if false positive rate > 15%.

---

### AUD-073 — Emotional Markup

**Status:** TODO
**Priority:** Medium
**Depends on:** AUD-070, AUD-082

```python
class EmotionalMarkup(ProsodyProcessor):
    """
    Adds emotion metadata to each chunk based on LLM emotion classification (AUD-082).
    Emotion is stored in chunk.metadata["emotion"] and used by TTS voice selection.
    """
```

---

## EPIC 9 — Local LLM Augmentation

---

### AUD-080 — LLM Provider Abstraction

**Status:** TODO
**Priority:** High
**Depends on:** AUD-003
**Blocks:** AUD-081–AUD-083

#### Implement

```python
# api/llm/factory.py
from shared.config import Config
from shared.interfaces import LLMProvider

def get_llm_provider(cfg: Config) -> LLMProvider:
    match cfg.llm_runtime:
        case "ollama":    from .ollama_provider import OllamaProvider; return OllamaProvider(cfg)
        case "llamafile": from .llamafile_provider import LlamafileProvider; return LlamafileProvider(cfg)
    raise ValueError(f"Unknown LLM runtime: {cfg.llm_runtime}")
```

```python
# api/llm/ollama_provider.py
import ollama
from pydantic import BaseModel
from typing import TypeVar, Type
from shared.interfaces import LLMProvider
T = TypeVar("T", bound=BaseModel)

class OllamaProvider(LLMProvider):
    def __init__(self, cfg):
        self._model = cfg.llm_model   # always from config; start at Tier 0

    def complete(self, prompt: str) -> str:
        response = ollama.chat(model=self._model, messages=[{"role": "user", "content": prompt}])
        return response["message"]["content"]

    def complete_structured(self, prompt: str, schema: Type[T]) -> T:
        # Use pydantic_ai / outlines / instructor depending on cfg.llm_structured_output
        ...
```

**LLM orchestration alternatives:**

| Framework | Package | Notes |
|-----------|---------|-------|
| LangGraph (default) | `langgraph` (MIT) | Graph-based; good for multi-step pipelines |
| DSPy | `dspy-ai` (MIT) | Declarative; excellent for prompt tuning experiments |
| Haystack | `haystack-ai` (Apache 2.0) | Modular; easiest for simple pipelines |

**Structured output alternatives:**

| Framework | Package | Notes |
|-----------|---------|-------|
| Pydantic AI (default) | `pydantic-ai` (MIT) | Native Pydantic integration |
| Outlines | `outlines` (Apache 2.0) | Grammar-constrained; works with llama.cpp directly |
| instructor | `instructor` (MIT) | Thinnest wrapper; easiest to add |

**LLM runtime alternatives:**

| Runtime | Notes |
|---------|-------|
| Ollama (default) | REST API; easy model management |
| llamafile | MIT; single-file executable; zero infra |
| vLLM | Apache 2.0; GPU-focused; secondary device only |

#### Acceptance criteria

- [ ] `complete("Say hello")` returns a non-empty string using `llm_model` from config
- [ ] `complete_structured(prompt, MySchema)` returns a validated Pydantic instance
- [ ] Model name logged as MLflow param on every run

---

### AUD-081 — Punctuation Restoration

**Status:** TODO
**Priority:** Medium
**Depends on:** AUD-080
**Start model tier:** Tier 0 (qwen2.5:0.5b)
**Escalate if:** Accuracy < 90% on benchmark set

#### Implement

```python
# api/llm/tasks/punctuation_restoration.py
from pydantic import BaseModel

class RestoredText(BaseModel):
    text: str
    changes_made: int

SYSTEM_PROMPT = """You are a punctuation restoration assistant.
Given text that may be missing commas, periods, or quotation marks, restore them.
Preserve all original words exactly. Only add or fix punctuation.
Respond with JSON: {"text": "...", "changes_made": N}"""

def restore_punctuation(text: str, llm: LLMProvider) -> str:
    result = llm.complete_structured(
        f"{SYSTEM_PROMPT}\n\nText: {text}",
        schema=RestoredText
    )
    return result.text
```

---

### AUD-082 — Emotion Classification

**Status:** TODO
**Priority:** Medium
**Depends on:** AUD-080
**Start model tier:** Tier 1–2 (smollm2:1.7b → qwen2.5:1.5b)
**Escalate if:** F1 < 0.75

#### Implement

```python
from pydantic import BaseModel
from enum import StrEnum

class Emotion(StrEnum):
    NEUTRAL = "neutral"
    TENSE = "tense"
    SAD = "sad"
    JOYFUL = "joyful"
    ANGRY = "angry"
    FEARFUL = "fearful"

class EmotionResult(BaseModel):
    emotion: Emotion
    confidence: float
    reasoning: str

SYSTEM_PROMPT = """Classify the emotional tone of this text passage.
Choose from: neutral, tense, sad, joyful, angry, fearful.
Respond with JSON: {"emotion": "...", "confidence": 0.0-1.0, "reasoning": "..."}"""
```

Emotion result stored in `chunk.metadata["emotion"]` for use by prosody and voice selection.

---

### AUD-083 — Dialogue Attribution

**Status:** TODO
**Priority:** Medium
**Depends on:** AUD-080, AUD-032
**Start model tier:** Tier 2–3 (qwen2.5:1.5b → phi3:mini)
**Escalate if:** Attribution accuracy < 85%

#### Implement

Given a dialogue span and its surrounding narration context, identify the likely speaker.

```python
from pydantic import BaseModel

class AttributionResult(BaseModel):
    speaker: str        # character name or "unknown"
    confidence: float
    attribution_cue: str   # the text fragment that reveals the speaker ("he said", "Mary replied")
```

Output stored in `chunk.metadata["speaker"]` for per-character voice assignment (AUD-KE-009).

---

## EPIC 10 — LLMOps Platform

---

### AUD-090 — Run Explorer

**Status:** TODO
**Priority:** Medium
**Depends on:** AUD-011
**Note:** Build as a Streamlit app in `llmops/`

#### Implement

```python
# llmops/pages/runs.py
import streamlit as st
import mlflow

# Display: experiment selector, run table with params + metrics
# Filter by: date range, status, model, chunker, tts_provider
# Sort by: any metric column
```

#### Acceptance criteria

- [ ] Runs from MLflow are listed with config params and key metrics
- [ ] Clicking a run shows its full config and artifact list

---

### AUD-091 — Chunk Review UI

**Status:** TODO
**Priority:** Medium
**Depends on:** AUD-061

Display chunks from a selected run: show text, chunk type, character count, and any LLM-generated metadata (emotion, speaker).

---

### AUD-092 — Audio Review UI

**Status:** TODO
**Priority:** Medium
**Depends on:** AUD-062

Display generated audio artifacts from a run. Embed an HTML5 audio player. Allow A/B comparison: load two runs and switch between their chapter audio.

---

### AUD-093 — Experiment Comparison Dashboard

**Status:** TODO
**Priority:** Medium
**Depends on:** AUD-063

Render the comparison report from `AUD-063` in the UI. Show metric deltas as coloured cells (green = better, red = worse). Allow selecting any two runs from the Run Explorer.

---

## EPIC 11 — Advanced Research

> **Do not start any ticket in this epic until Epics 1–10 are fully complete.**

---

### AUD-100 — (Replaced) → See AUD-KE-000 through AUD-KE-010

The original single voice blending ticket has been expanded into a full Kokoro Hyperparameter Experiment series. See the `KOKORO EXPERIMENTS` section below.

---

### AUD-101 — DSP Pipeline

**Status:** TODO
**Priority:** Low
**Depends on:** AUD-053, AUD-KE-007
**Note:** AUD-KE-007 defines the optimal DSP config. This ticket implements it as a reusable module.

#### Implement

Fixed DSP chain order: normalize → EQ → compress → noise gate → de-ess

```python
# api/audio/dsp.py
from dataclasses import dataclass

@dataclass
class DSPPreset:
    name: str
    lufs_target: float = -16.0
    eq_presence_boost_db: float = 2.0
    eq_presence_freq_hz: int = 3000
    eq_low_cut_hz: int = 80
    compression_ratio: float = 3.0
    compression_threshold_db: float = -18.0
    compression_attack_ms: float = 5.0
    gate_threshold_db: float = -60.0
    de_ess: bool = True
    output_bitrate: str = "192k"

class DSPChain:
    def __init__(self, preset: DSPPreset):
        self._preset = preset

    def process(self, audio_bytes: bytes, sample_rate: int) -> bytes:
        # Apply in order: normalize → EQ → compress → gate → de-ess
        # Use pedalboard (GPL-3.0) or librosa + scipy.signal
        ...
```

**Breathing and silence injection:**
```python
    def inject_breath(self, audio_bytes: bytes, interval_sentences: int = 3) -> bytes: ...
    def inject_silence(self, audio_bytes: bytes, duration_ms: int = 200) -> bytes: ...
    def time_stretch(self, audio_bytes: bytes, rate: float = 1.0) -> bytes: ...
```

---

### AUD-102 — Adaptive Pacing

**Status:** TODO
**Priority:** Low
**Depends on:** AUD-082, AUD-101

Modulate `tts_speed` per chunk based on emotion classification output:

| Emotion | Speed modifier |
|---------|---------------|
| tense | × 1.1 |
| fearful | × 1.15 |
| sad | × 0.88 |
| joyful | × 1.05 |
| neutral | × 1.0 |
| dialogue | × 0.95 |
| chapter break | inject 3s silence |

Speed modifiers and silence durations must be configurable, not hardcoded.

---

### AUD-103 — Kokoro Fine-Tuning

**Status:** BLOCKED
**Priority:** Low
**Depends on:** AUD-KE-010 (exhaustion gate — all items must be checked)

#### Prerequisites (all must be satisfied before starting)

- [ ] AUD-KE-010 exhaustion gate fully passed
- [ ] Training corpus assembled: minimum 10 hours of clean audiobook reference audio with aligned transcripts
- [ ] `kokoro-best-v1` MOS and WER are documented
- [ ] GTX 1650 assessed for fine-tuning feasibility (82M params, small batch size)
- [ ] Fine-tuning framework selected: Kokoro official training scripts or StyleTTS2 trainer adapted

#### Implement

Only after all prerequisites are met:

1. Prepare dataset: aligned `(text, audio)` pairs in Kokoro training format
2. Fine-tune from `kokoro-best-v1` checkpoint (not from base weights)
3. Register fine-tuned model as `kokoro-finetuned-v1` in MLflow Model Registry
4. Re-run full benchmark corpus with fine-tuned model

#### Acceptance criteria

- [ ] Fine-tuned model MOS exceeds `kokoro-best-v1` MOS by **≥ +0.3 points**
- [ ] Fine-tuned model WER ≤ `kokoro-best-v1` WER
- [ ] Training run is fully reproducible from MLflow run record
- [ ] Fine-tuned model is versioned as `kokoro-finetuned-v1` in MLflow Model Registry

---

## KOKORO EXPERIMENTS (AUD-KE)

> **Purpose:** Exhaustively search Kokoro's configuration space before any fine-tuning.
> Every experiment must be logged as an MLflow run with the full config as params.
> AUD-103 is blocked until AUD-KE-010 passes.

---

### AUD-KE-000 — Kokoro Evaluation Baseline Setup

**Status:** TODO
**Priority:** Critical (blocks all AUD-KE-xxx)
**Depends on:** AUD-062, AUD-063

#### Implement

**Benchmark corpus** (store in `datasets/kokoro-benchmark/`):

```
datasets/kokoro-benchmark/
  genre-literary/       # dialogue-heavy prose (e.g. public domain novel)
    source.pdf
    chunks.jsonl        # 30 representative chunks
  genre-technical/      # technical non-fiction
    source.pdf
    chunks.jsonl
  genre-narrative/      # children's or narrative fiction
    source.pdf
    chunks.jsonl
  ground_truth.jsonl    # reference transcripts for WER calculation
```

**Scoring rubric (implement all five):**

```python
# shared/kokoro_eval.py
import whisper
import librosa
import numpy as np

def compute_wer(reference: str, audio_path: str) -> float:
    """Transcribe audio with Whisper, compute WER vs reference."""
    model = whisper.load_model("base")   # ~140 MB, CPU-friendly
    result = model.transcribe(audio_path)
    # compute WER: (S + D + I) / N
    ...

def compute_silence_pct(audio_path: str) -> float:
    y, sr = librosa.load(audio_path, sr=None)
    return (np.abs(y) < 0.01).sum() / len(y) * 100

def compute_spectral_flatness(audio_path: str) -> float:
    y, sr = librosa.load(audio_path, sr=None)
    return float(librosa.feature.spectral_flatness(y=y).mean())

def compute_rtf(gen_time_s: float, audio_duration_s: float) -> float:
    return gen_time_s / audio_duration_s
```

**MOS:** Internal panel of 3 listeners, scale 1–5. Log as `mos_mean` and `mos_std`.

**Baseline run:** Default Kokoro config (`voice=af_bella`, `speed=1.0`, no prosody injection). Log all five metrics. This is the reference all subsequent experiments compare against.

#### Acceptance criteria

- [ ] `datasets/kokoro-benchmark/` contains 3 genres × 30 chunks = 90 chunks
- [ ] All five metrics implemented and returning valid values
- [ ] Baseline MLflow run exists with tag `kokoro_experiment=baseline`

---

### AUD-KE-001 — Voice Selection Sweep

**Status:** TODO
**Depends on:** AUD-KE-000

#### Implement

```python
# experiments/ke-001-voice-sweep.py
import mlflow
from api.tts.kokoro_provider import KokoroProvider

VOICES = KokoroProvider.list_all_voice_ids()   # ~54 voices

for voice_id in VOICES:
    for genre in ["literary", "technical", "narrative"]:
        with mlflow.start_run(run_name=f"voice-sweep-{voice_id}-{genre}"):
            mlflow.set_tags({"kokoro_experiment": "voice-sweep", "genre": genre})
            mlflow.log_param("voice", voice_id)
            # Synthesize all 30 chunks for this genre
            # Compute and log: wer, silence_pct, spectral_flatness, rtf, mos (manual)
```

**Expected outputs (log to MLflow):**
- `voice_genre_affinity_matrix.csv` artifact — voice × genre composite score
- Top 5 voices per genre tagged with `top5_{genre}=true` in MLflow

---

### AUD-KE-002 — Speed Parameter Sweep

**Status:** TODO
**Depends on:** AUD-KE-001

#### Implement

```python
SPEED_RANGE = [round(x * 0.1, 1) for x in range(5, 21)]  # 0.5 to 2.0, step 0.1 = 16 values
TOP_VOICES_PER_GENRE = load_top5_from_mlflow()  # from AUD-KE-001

for genre, voices in TOP_VOICES_PER_GENRE.items():
    for voice in voices:
        for speed in SPEED_RANGE:
            with mlflow.start_run(run_name=f"speed-sweep-{voice}-{speed}-{genre}"):
                mlflow.log_params({"voice": voice, "speed": speed, "genre": genre})
                # Synthesize 30 chunks, compute metrics
```

**Expected outputs:**
- Speed vs WER curve per genre (artifact: `speed_wer_curve_{genre}.json`)
- Speed vs MOS curve per genre
- Optimal speed per voice × genre combination tagged in MLflow

---

### AUD-KE-003 — Voice Blending Experiments

**Status:** TODO
**Depends on:** AUD-KE-002

#### Implement

```python
BLEND_RATIOS = [round(i * 0.1, 1) for i in range(1, 10)]  # 0.1 to 0.9
TOP_3_VOICES = load_top3_from_mlflow()  # from AUD-KE-001
NEXT_3_VOICES = load_next3_from_mlflow()

for voice_a in TOP_3_VOICES:
    for voice_b in NEXT_3_VOICES:
        for alpha in BLEND_RATIOS:
            # voice_tensor = alpha * v_a + (1 - alpha) * v_b
            with mlflow.start_run(run_name=f"blend-{voice_a}-{voice_b}-a{alpha}"):
                mlflow.log_params({"voice_a": voice_a, "voice_b": voice_b, "alpha": alpha})
                # 81 total combinations
```

**Expected outputs:**
- Best blend ratio per voice pair
- Comparison: best blend vs best single voice MOS

---

### AUD-KE-004 — Text Preprocessing Impact

**Status:** TODO
**Depends on:** AUD-KE-000

#### Implement

Test each variable independently (isolation), then combine the winning options.

```python
PREPROCESSING_AXES = {
    "pause_marker": [",", "…", "—", "[pause]", "<break>", "none"],
    "abbrev_expansion": ["expanded", "raw"],
    "number_rendering": ["digit", "words"],
    "sentence_boundary": ["single_space", "newline", "double_newline"],
    "quote_normalization": ["curly", "straight"],
    "ellipsis_treatment": ["three_dots", "unicode_ellipsis", "spaced"],
    "emphasis_caps": ["all_caps", "stripped", "unchanged"],
}

# Phase 1: test each axis with all others at default
for axis, values in PREPROCESSING_AXES.items():
    for val in values:
        config = {**DEFAULT_PREPROCESSING, axis: val}
        with mlflow.start_run(run_name=f"preproc-{axis}-{val}"):
            mlflow.log_params(config)
            # synthesize, score

# Phase 2: combine best value per axis
best_config = load_best_per_axis_from_mlflow()
with mlflow.start_run(run_name="preproc-combined-best"):
    mlflow.log_params(best_config)
    # synthesize full benchmark corpus
```

**Expected outputs:**
- Ranked impact table: which axis moves WER the most
- Optimal text prep config for narrative prose
- Optimal text prep config for technical content

---

### AUD-KE-005 — Prosody Injection Strategy Experiments

**Status:** TODO
**Depends on:** AUD-070, AUD-KE-000

#### Variables (test via AUD-070 PauseInjector config)

| Variable | Values |
|----------|--------|
| Pre-dialogue pause | 0 ms, 200 ms, 500 ms, 800 ms |
| Post-dialogue pause | 0 ms, 100 ms, 300 ms |
| Chapter break silence | 1 s, 2 s, 3 s, 5 s |
| Paragraph break silence | 0 ms, 200 ms, 500 ms |
| Breath marker | none / every sentence / every 3 sentences |
| Em-dash treatment | pause / comma / strip |

Use the fixed best config from AUD-KE-004 as the text preprocessing baseline.

**Expected outputs:**
- MOS per prosody config (automated + human)
- Silence % per config
- Listener fatigue score (subjective, 1–5 after 10 min listening)

---

### AUD-KE-006 — Chunk Boundary Strategy Impact

**Status:** TODO
**Depends on:** AUD-040, AUD-KE-002

#### Variables

| Variable | Values |
|----------|--------|
| Chunker | paragraph, sentence, semantic, dialogue |
| Chunk max chars | 50, 100, 200, 400, 800 |
| Junction handling | hard cut, 100 ms crossfade, 300 ms crossfade, silence gap |

Fix: best voice + speed from AUD-KE-002.

**Measure:**
- WER at boundary regions only (first and last 2 words of each chunk)
- Boundary artifact rate (manual review: 0 = clean, 1 = minor, 2 = audible)
- Whether crossfade reduces artifacts enough to justify DSP cost (RTF impact)

---

### AUD-KE-007 — DSP Post-Processing Chain Optimization

**Status:** TODO
**Depends on:** AUD-053, AUD-KE-000

#### Variables (fixed chain order: normalize → EQ → compress → gate → de-ess)

| Stage | Values |
|-------|--------|
| Normalization LUFS | -6, -9, -12, -16, -23 |
| EQ presence boost | +2 dB at 3 kHz, +4 dB at 3 kHz, none |
| EQ low cut | 80 Hz, 120 Hz |
| Compression ratio | 2:1, 3:1, 4:1 |
| Compression threshold | -18 dB, -24 dB |
| Compression attack | 5 ms, 20 ms |
| Noise gate | -50 dB, -60 dB, off |
| De-essing | on, off |
| Output bitrate | MP3 128k, MP3 192k, MP3 320k, M4B AAC 128k |

Implement DSP via `pedalboard` (Spotify, GPL-3.0, internal use OK) or `librosa` + `scipy.signal`.

**Expected outputs:**
- Optimal DSP preset saved as `dsp-best-v1` in MLflow Model Registry
- Listener preference score per bitrate option

---

### AUD-KE-008 — espeak-ng Phoneme Override Experiments

**Status:** TODO
**Depends on:** AUD-KE-000

#### Implement

```python
# experiments/ke-008-phoneme-overrides.py
import whisper

# Step 1: Transcribe all baseline audio, compute WER per word
# Step 2: Rank words by frequency of mispronunciation
# Step 3: Generate IPA overrides via espeak-ng
# Step 4: Resynthesize with override dictionary active
# Step 5: Compare WER

DICT_SIZES = [10, 50, 100, 500]
IPA_STRATEGIES = ["espeak_default", "manual_correction", "gruut_fallback"]
NOUN_CATEGORIES = ["titles", "character_names", "place_names"]
```

**G2P backend alternatives:**

| Backend | Package | Notes |
|---------|---------|-------|
| espeak-ng (default) | system package (GPL-3.0) | Best coverage; IPA output |
| gruut | `gruut` (MIT) | Python-native; cleanly embeddable |
| g2p-en | `g2p-en` (Apache 2.0) | English-only; very lightweight |

---

### AUD-KE-009 — Per-Section Voice Strategy

**Status:** TODO
**Depends on:** AUD-083, AUD-KE-001

#### Strategies to implement and benchmark

| Strategy | Description |
|----------|-------------|
| Single voice (control) | Same voice across full document |
| Narrator + character | One voice narration, second voice all dialogue |
| Per-character | Distinct voice per speaking character (requires AUD-083 attribution) |
| Chapter-level switch | Voice rotates at chapter boundaries |
| Emotional speed shift | Speed modulated by emotion (AUD-082 output) |

**Measure:**
- Narrative coherence score (subjective, 1–5)
- Listener A/B preference vs single-voice control
- MOS per strategy

---

### AUD-KE-010 — Exhaustion Gate (Blocks AUD-103)

**Status:** TODO
**Priority:** Critical gate
**Depends on:** AUD-KE-001 through AUD-KE-009

This ticket is a review and documentation task, not an implementation task.

#### Deliverable

Produce `artifacts/kokoro-hyperparameter-exhaustion-report.md` containing:

1. Summary of every AUD-KE-xxx experiment
2. Best configuration identified across all axes (tag as `kokoro-best-v1` in MLflow)
3. MOS score of `kokoro-best-v1` vs baseline (from AUD-KE-000)
4. WER of `kokoro-best-v1` vs baseline
5. Assessment of whether the MOS plateau has been reached
6. Specific failure cases that remain after best config (if any)

#### Gate checklist (all must be ✅ before AUD-103 is started)

- [ ] All AUD-KE-001 through AUD-KE-009 MLflow runs exist with complete params and metrics
- [ ] `kokoro-best-v1` tagged in MLflow Model Registry
- [ ] MOS of `kokoro-best-v1` documented vs baseline
- [ ] WER of `kokoro-best-v1` documented vs baseline
- [ ] Internal panel has listened to at least 3 full chapter-length samples from `kokoro-best-v1`
- [ ] Exhaustion report written and stored as artifact
- [ ] MOS improvement from hyperparameter search has plateaued (Δ < 0.3 between last 3 experiments)
- [ ] Remaining failure cases are identified and confirmed to be unreachable via text/config changes

**If all items are checked → AUD-103 is unblocked.**
**If MOS plateau has not been reached → continue experimentation before checking this gate.**
