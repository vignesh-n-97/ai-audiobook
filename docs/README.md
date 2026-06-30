# Documentation Index

> Implementation notes and ticket documentation for the AI Audiobook Platform.

---

## Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Fully implemented and functional |
| 🔲 | Stub or scaffold — wired but not complete |
| ⏳ | Not yet started |

---

## EPIC 1 — Repository Foundation

| Ticket | Title | Status | Doc |
|--------|-------|--------|-----|
| AUD-001 | Repository Bootstrap | ✅ | [AUD-001-repository-bootstrap.md](./AUD-001-repository-bootstrap.md) |
| AUD-002 | Docker Development Environment | ✅ | [AUD-002-docker-environment.md](./AUD-002-docker-environment.md) |
| AUD-003 | FastAPI Service Bootstrap | ✅ | [AUD-003-fastapi-bootstrap.md](./AUD-003-fastapi-bootstrap.md) |

---

## EPIC 2 — Experiment Framework

| Ticket | Title | Status | Doc |
|--------|-------|--------|-----|
| AUD-010 | Experiment Domain Models | ✅ | [AUD-010-experiment-domain-models.md](./AUD-010-experiment-domain-models.md) |
| AUD-011 | Run Tracking | ✅ | [AUD-011-run-tracking.md](./AUD-011-run-tracking.md) |
| AUD-012 | Artifact Registry | ✅ | [AUD-012-artifact-registry.md](./AUD-012-artifact-registry.md) |

---

## EPIC 3 — Document Ingestion

| Ticket | Title | Status | Doc |
|--------|-------|--------|-----|
| AUD-020 | Document Upload API | ✅ | [AUD-020-document-upload-api.md](./AUD-020-document-upload-api.md) |
| AUD-021 | Parser Abstraction Layer | ✅ | [AUD-021-parser-abstraction.md](./AUD-021-parser-abstraction.md) |
| AUD-022 | Docling Integration | ✅ | — |
| AUD-023 | RapidOCR Integration | ✅ | — |

---

## EPIC 4 — Structural Understanding

| Ticket | Title | Status | Doc |
|--------|-------|--------|-----|
| AUD-030 | Chapter Detection Engine | ⏳ | — |
| AUD-031 | Paragraph Detection | ⏳ | — |
| AUD-032 | Dialogue Detection | ⏳ | — |

---

## EPIC 5 — Chunking Framework

| Ticket | Title | Status | Doc |
|--------|-------|--------|-----|
| AUD-040 | Chunking Framework | ⏳ | — |
| AUD-041 | Paragraph Chunker | ⏳ | — |
| AUD-042 | Sentence Chunker | ⏳ | — |
| AUD-043 | Semantic Chunker | ⏳ | — |
| AUD-044 | Dialogue Chunker | ⏳ | — |

---

## EPIC 6 — Baseline Audiobook Generation

| Ticket | Title | Status | Doc |
|--------|-------|--------|-----|
| AUD-050 | TTS Provider Abstraction | ⏳ | — |
| AUD-051 | Kokoro Provider | ⏳ | — |
| AUD-051b | Piper Provider | ⏳ | — |
| AUD-052 | Voice Registry | ⏳ | — |
| AUD-053 | Audio Stitching | ⏳ | — |
| AUD-054 | Audiobook Generation Pipeline | 🔲 Scaffolded | [AUD-054-pipeline.md](./AUD-054-pipeline.md) |

---

## EPIC 7 — Evaluation Framework

| Ticket | Title | Status | Doc |
|--------|-------|--------|-----|
| AUD-060 | Runtime Metrics Collection | ⏳ | — |
| AUD-061 | Chunk Metrics | ⏳ | — |
| AUD-062 | Audio Metrics | ⏳ | — |
| AUD-063 | Evaluation Reports | ⏳ | — |

---

## EPIC 8 — Prosody Preparation

| Ticket | Title | Status | Doc |
|--------|-------|--------|-----|
| AUD-070 | Prosody Processor Framework | ⏳ | — |
| AUD-071 | Pause Injection Engine | ⏳ | — |
| AUD-072 | Emphasis Detection | ⏳ | — |
| AUD-073 | Emotional Markup | ⏳ | — |

---

## EPIC 9 — Local LLM Augmentation

| Ticket | Title | Status | Doc |
|--------|-------|--------|-----|
| AUD-080 | LLM Provider Abstraction | ⏳ | — |
| AUD-081 | Punctuation Restoration | ⏳ | — |
| AUD-082 | Emotion Classification | ⏳ | — |
| AUD-083 | Dialogue Attribution | ⏳ | — |

---

## EPIC 10 — LLMOps Platform

| Ticket | Title | Status | Doc |
|--------|-------|--------|-----|
| AUD-090 | Run Explorer | ⏳ | — |
| AUD-091 | Chunk Review UI | ⏳ | — |
| AUD-092 | Audio Review UI | ⏳ | — |
| AUD-093 | Experiment Comparison Dashboard | ⏳ | — |

---

## EPIC 11 — Advanced Research

| Ticket | Title | Status | Doc |
|--------|-------|--------|-----|
| AUD-101 | DSP Pipeline | ⏳ (blocked on AUD-KE-007) | — |
| AUD-102 | Adaptive Pacing | ⏳ | — |
| AUD-103 | Kokoro Fine-Tuning | ⏳ (blocked on AUD-KE-010) | — |

---

## Kokoro Experiments (AUD-KE)

> All AUD-KE tickets are blocked until Epics 1–10 are complete.

| Ticket | Title | Status |
|--------|-------|--------|
| AUD-KE-000 | Kokoro Evaluation Baseline Setup | ⏳ |
| AUD-KE-001 | Voice Selection Sweep | ⏳ |
| AUD-KE-002 | Speed Parameter Sweep | ⏳ |
| AUD-KE-003 | Voice Blending Experiments | ⏳ |
| AUD-KE-004 | Text Preprocessing Impact | ⏳ |
| AUD-KE-005 | Prosody Injection Strategy | ⏳ |
| AUD-KE-006 | Chunk Boundary Strategy Impact | ⏳ |
| AUD-KE-007 | DSP Post-Processing Chain Optimization | ⏳ |
| AUD-KE-008 | espeak-ng Phoneme Override Experiments | ⏳ |
| AUD-KE-009 | Per-Section Voice Strategy | ⏳ |
| AUD-KE-010 | Exhaustion Gate (blocks AUD-103) | ⏳ |

---

## Related Files

- [TASKS.md](../TASKS.md) — Full ticket specifications with acceptance criteria
- [AGENTS.md](../AGENTS.md) — Architectural rules and agent decision guidelines
- [COMMANDS.md](../COMMANDS.md) — Command reference for running all services
- [.env.example](../.env.example) — Environment variable template
