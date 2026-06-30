# Experimentation Rules

Extends AGENTS.md. Do not repeat rules defined there.

---

## Experiment Configuration

Every experiment is defined by a YAML configuration file stored in
`experiments/configs/`. Configuration files are the single source of truth
for what an experiment does.

### Required YAML fields

```yaml
experiment:
  name: <slug>                    # unique, lowercase, underscore-separated
  description: >                  # what this experiment is testing
    ...

pipeline:
  parser: <parser_id>             # e.g. dockling, pypdf, marker
  ocr: <ocr_id | none>            # e.g. rapidocr, tesseract, none
  chunker: <chunker_id>           # e.g. paragraph, sentence, semantic, adaptive
  llm: <model_id | none>          # e.g. qwen2.5_7b, none
  tts: <tts_id>                   # e.g. kokoro_fp32, kokoro_q8

chunker_config:
  strategy: <strategy>            # must match chunker id
  max_tokens: <int>               # must be explicit — never use a default
  overlap_tokens: <int>

dataset:
  version: <dataset_version>      # see AGENTS.md Dataset Versioning

tts_config:
  voice: <voice_id>
  speed: <float>
```

**Forbidden:**
- Hardcoded parameters in pipeline code — they belong in YAML
- Experiments without a `dataset.version` field
- Experiments with `max_tokens` or other chunking parameters omitted (must be explicit)

---

## Experiment IDs and Run IDs

- `experiment_id` is derived from the config file name + a content hash
- `run_id` is a UUID4 generated fresh for every execution
- Both must be propagated through every log, trace, and artifact produced
  during the run
- Never reuse a `run_id`

---

## Experiment Runner

The runner lives in `shared/experiment/runner.py`.

The runner is responsible for:
1. Loading and validating the YAML config
2. Resolving pipeline components by ID
3. Executing pipeline stages in order
4. Collecting and emitting metrics at each stage
5. Writing all artifacts to `runs/{run_id}/`
6. Recording final run metadata to the experiment store

The runner must not contain pipeline-stage logic. It orchestrates; packages
implement.

---

## Pipeline Stage Contracts

Each pipeline stage is a callable with a typed input and output. Stages are
composable and independently testable.

```python
class ParserStage(Protocol):
    def execute(self, input: ParseInput) -> ParseOutput: ...

class ChunkerStage(Protocol):
    def execute(self, input: ChunkInput) -> ChunkOutput: ...

class TTSStage(Protocol):
    def execute(self, input: TTSInput) -> TTSOutput: ...
```

Stages emit observability events before and after execution (see `observability.md`).

---

## Artifact Storage

All artifacts produced by a run are stored under:

```
runs/{run_id}/
  metadata.json        run-level metadata (see AGENTS.md)
  config.yaml          copy of the experiment config used
  chunks/              one .json per chunk
  audio/               one .wav per chunk, plus assembled audiobook.wav
  traces/              stage-level trace data
  metrics/             stage-level metrics
  evaluation/          evaluation scores (if an evaluation was run)
```

Artifact paths must never be hardcoded. They are resolved from `run_id` at
runtime.

---

## Reproducibility Implementation

To satisfy AGENTS.md reproducibility requirements:

```python
# Every run must capture this at startup
run_metadata = RunMetadata(
    experiment_id=...,
    run_id=str(uuid4()),
    git_commit_sha=subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip(),
    git_branch=subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode().strip(),
    execution_environment=platform.platform(),
    python_version=sys.version,
    timestamp=datetime.utcnow().isoformat(),
    dataset_version=config.dataset.version,
    pipeline_version=config.pipeline_version,
)
```

This metadata is written to `runs/{run_id}/metadata.json` immediately at run
start — before any pipeline stage executes.

---

## Dataset Versioning Implementation

Dataset versions follow semantic versioning: `v{major}.{minor}.{patch}`.

When any benchmark book, evaluation dataset, test manuscript, or scoring dataset
changes:
- Increment the patch version for additions or corrections
- Increment the minor version for restructuring
- Increment the major version for complete replacement

The version is recorded in `datasets/versions.json` and referenced by experiment
configs via `dataset.version`.

Experiments run against different dataset versions are **not directly comparable**.

---

## Comparing Experiments

Experiments are comparable only when:
1. They share the same `dataset.version`
2. They were run against the same input document(s)
3. Their `git_commit_sha` values are known

Comparisons happen in `llmops/`. Never write comparison logic in pipeline code.

---

## Component Registry

Pipeline components (parsers, OCR engines, chunkers, LLMs, TTS) are registered
in `shared/experiment/registry.py`.

```python
PARSERS = {
    "dockling": DocklingParser,
    "pypdf": PyPDFParser,
    "marker": MarkerParser,
}

CHUNKERS = {
    "paragraph": ParagraphChunker,
    "sentence": SentenceChunker,
    "semantic": SemanticChunker,
    "adaptive": AdaptiveChunker,
}
```

Every registered component must:
- Accept a config dict or Pydantic model for configuration
- Expose a typed `execute()` method
- Be independently unit-testable without running a full pipeline

---

## Forbidden in Experiments

- Hardcoded model paths — paths are resolved from `shared/config.py`
- Experiments that cannot run on CPU — GPU is optional
- Experiment YAML files committed without a `dataset.version`
- Pipeline stages that mutate global state
- Using `time.sleep()` or other delays to "fix" timing issues in a pipeline
