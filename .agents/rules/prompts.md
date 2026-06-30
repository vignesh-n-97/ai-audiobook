# Prompt Rules

Extends AGENTS.md. Do not repeat rules defined there.

---

## Prompt Location

All prompts live in `shared/prompts/`.

```
shared/prompts/
  __init__.py
  registry.py          prompt registry — maps prompt_id to PromptTemplate
  templates/
    normalise_text_v1.py
    detect_dialogue_v1.py
    chapter_detection_v1.py
    prosody_prep_v1.py
    ...
  tests/
    test_normalise_text_v1.py
    ...
```

**Forbidden:**
- Inline prompt strings in pipeline code, workers, or API handlers
- Prompt strings defined in YAML experiment configs (configs reference prompt IDs, not strings)
- Prompt strings in environment variables

---

## Prompt Template Structure

Every prompt template is a Python module exporting a `PromptTemplate` instance.

```python
# shared/prompts/templates/normalise_text_v1.py

from shared.prompts.base import PromptTemplate

PROMPT_ID = "normalise_text"
PROMPT_VERSION = "1.0.0"

SYSTEM = """
You are a text normalisation assistant. Your task is to prepare raw extracted
text from a PDF for text-to-speech synthesis. ...
"""

USER_TEMPLATE = """
Raw text:
{raw_text}

Normalise the text according to the rules provided.
"""

template = PromptTemplate(
    prompt_id=PROMPT_ID,
    version=PROMPT_VERSION,
    system=SYSTEM,
    user_template=USER_TEMPLATE,
    input_variables=["raw_text"],
)
```

---

## Prompt Versioning

Prompt IDs follow the pattern `{slug}`. Versions follow semantic versioning.

When a prompt changes:
- **Patch bump** (`1.0.0` → `1.0.1`): wording fix, typo correction, no
  behavioural change expected
- **Minor bump** (`1.0.0` → `1.1.0`): new instruction, changed output format,
  expected quality change
- **Major bump** (`1.0.0` → `2.0.0`): fundamentally different approach,
  incompatible output structure

Every prompt version change requires a new experiment to evaluate its effect.
Never update a prompt's content without bumping the version.

Old versions must not be deleted — they must remain importable for experiment
reproducibility.

---

## Prompt Execution Tracing

Every prompt invocation must record the following (emit via observability):

```python
from shared.observability import emit_event

emit_event(
    event_type="llm.prompt.invoked",
    run_id=run_id,
    experiment_id=experiment_id,
    payload={
        "prompt_id": template.prompt_id,
        "prompt_version": template.version,
        "model_name": model_name,
        "model_version": model_version,
        "input": rendered_user_prompt,    # the full rendered string
        "output": model_response,
        "input_tokens": token_count_in,
        "output_tokens": token_count_out,
        "duration_ms": elapsed_ms,
    }
)
```

No prompt execution is silent. If a prompt is invoked, it must appear in the
run's trace.

---

## Prompt Registry

The registry maps `prompt_id` → `PromptTemplate`. It is the single lookup
mechanism for prompt resolution at runtime.

```python
# shared/prompts/registry.py
from .templates.normalise_text_v1 import template as normalise_text_v1
from .templates.detect_dialogue_v1 import template as detect_dialogue_v1

REGISTRY: dict[str, PromptTemplate] = {
    f"{t.prompt_id}@{t.version}": t
    for t in [normalise_text_v1, detect_dialogue_v1]
}

def get_prompt(prompt_id: str, version: str) -> PromptTemplate:
    key = f"{prompt_id}@{version}"
    if key not in REGISTRY:
        raise PromptNotFoundError(f"Prompt {key} not registered")
    return REGISTRY[key]
```

Experiment configs reference prompts by ID and version:

```yaml
pipeline:
  llm: qwen2.5_7b
  prompt_id: normalise_text
  prompt_version: "1.0.0"
```

---

## Prompt Changes Must Go Through Experiments

Prompt changes are not cosmetic. Every change to a prompt template must:
1. Bump the version
2. Run a comparison experiment (old prompt version vs. new prompt version)
3. Record evaluation scores for both
4. Document the decision in the experiment run notes

Never deploy a prompt change without measurable evidence of its effect.

---

## LLM Adapter Interface

The LLM adapter wraps the local model and handles prompt rendering and
invocation. It lives in `shared/ai/`.

```python
class LLMAdapter(Protocol):
    def invoke(
        self,
        template: PromptTemplate,
        inputs: dict[str, str],
        *,
        run_context: RunContext,
    ) -> LLMResponse: ...
```

Adapters are responsible for:
- Rendering the prompt template with inputs
- Invoking the model
- Recording the prompt trace event
- Returning a typed `LLMResponse`

Adapters are not responsible for chunking, parsing, or audio.

---

## Forbidden

- Calling an LLM without using a registered `PromptTemplate`
- Modifying a prompt template's content without incrementing its version
- Using cloud-hosted LLM APIs as a core dependency (benchmarking experiments only)
- Storing prompt text in the database
- Hardcoding model endpoint URLs — they come from `shared/config.py`
