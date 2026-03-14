# Sovreign AI

Malaysia moderation dataset pipeline for generating synthetic moderation examples. Produces a 7,000+ example dataset for fine-tuning a Malaysia-aligned judge + rewrite model.

## Project Structure

```
sovreign-ai/
├── src/sovreign/          # Main Python package
│   ├── __init__.py
│   ├── constants.py       # Dataset constants (principles, severities, labels, etc.)
│   ├── schema.py          # Pydantic DatasetExample model with consistency validators
│   ├── validate.py        # Post-generation filtering (9 validation rules)
│   ├── merge.py           # Merge batch JSONL files into a single dataset
│   ├── stats.py           # Compute and report dataset statistics
│   └── split.py           # Stratified train/val/test splitting
├── templates/             # Prompt templates and seed scenarios
│   ├── master_prompt.txt  # LLM prompt template for synthetic data generation
│   └── seeds.json         # 50 seed scenarios across S0-S3 severities
├── data/
│   ├── batches/           # Raw generated JSONL batches (~8,500 raw examples)
│   ├── merged/            # Merged batch output (all.jsonl)
│   ├── filtered/          # Validated/filtered data (clean.jsonl)
│   ├── augmentation/      # Edge case augmentation data (historical)
│   ├── cot/               # Chain-of-thought augmented data
│   │   ├── train_cot_final.jsonl       # Base CoT training set (6,237)
│   │   ├── train_cot_augmented.jsonl   # R1 augmented (6,472) ← PRODUCTION
│   │   ├── contrastive_pairs.jsonl     # Contrastive pairs with reasoning (190)
│   │   └── validation_cot.jsonl        # Validation data with reasoning (726)
│   └── final/             # Final train/validation/test splits
├── scripts/               # Data generation and processing scripts
│   ├── generate_cot_reasoning.py  # Add CoT reasoning to existing data
│   ├── generate_contrastive_pairs.py # Generate contrastive pairs
│   ├── validate_contrastive.py    # Validate contrastive pair integrity
│   ├── assemble_cot_dataset.py    # Assemble final CoT training set
│   ├── generate_augmented_data.py # R1 targeted gap-pattern augmentation
│   └── generate_augmented_r2_fix.py # R2-fix augmentation (experimental)
├── notebooks/             # Kaggle fine-tuning and evaluation notebooks
│   ├── shared_utils.py    # Shared data loading, formatting, and metrics
│   ├── gemma3_sft.ipynb   # FunctionGemma 270M LoRA SFT training
│   ├── lfm2_sft.ipynb     # LFM2 350M LoRA SFT training
│   ├── qwen35_sft.ipynb   # Qwen3.5 0.8B LoRA SFT training
│   ├── qwen35_cot_sft.ipynb # Qwen3.5 0.8B CoT LoRA SFT training
│   └── eval_compare.ipynb # Model comparison and evaluation
├── stress_test/           # 93 handwritten edge-case examples for model evaluation
├── deploy/
│   ├── worker/            # Cloudflare Worker (frontend + API proxy)
│   └── hf-space/          # HuggingFace Space (FastAPI inference server)
├── tests/                 # Test suite
├── docs/plans/            # Design and implementation plan documents
└── pyproject.toml         # Project configuration
```

## Setup

Requires Python >= 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-extras
```

## Verify Installation

```bash
uv run python -c "import sovreign; print('ok')"
```

## Running Tests

```bash
uv run pytest -v
```

## Malaysia Constitution Principles (MY-1 through MY-8)

| ID   | Principle |
|------|-----------|
| MY-1 | Preserve harmony across communities |
| MY-2 | Respect faith and religious sensitivity |
| MY-3 | Respect constitutional order and lawful process |
| MY-4 | Uphold dignity, courtesy, and adab |
| MY-5 | Allow criticism, but not incitement |
| MY-6 | Protect truth in sensitive public matters |
| MY-7 | Protect privacy, confidentiality, and personal safety |
| MY-8 | Prefer constructive, plural, and de-escalatory assistance |

## Severity Levels

| Level | Description | Target Count |
|-------|-------------|-------------|
| S0 | Safe — no moderation concern | 2,000 |
| S1 | Mild concern — needs constructive rewrite | 2,000 |
| S2 | Significant concern — harmful content | 2,000 |
| S3 | Severe — incitement, doxxing, dangerous | 1,000 |

## Risk Labels

9 fixed risk categories validated by Pydantic `Literal` type:

- `communal_hostility` — inter-ethnic or inter-community hostility
- `religious_provocation` — targeting religious beliefs or practices
- `unlawful_incitement` — inciting illegal activity
- `targeted_abuse` — directed harassment at individuals or groups
- `revenge_or_vigilantism` — calls for vigilante justice
- `dangerous_misinformation` — false claims that could cause harm
- `privacy_exposure` — doxxing or exposing private information
- `inflammatory_polarisation` — content designed to divide communities
- `needs_constructive_rewrite` — content that should be reframed constructively

## Dataset Schema

Each example is a JSON object validated by `DatasetExample` (Pydantic v2):

```json
{
  "input_text": "The actual text to be moderated",
  "language": "ms|en|zh|ta|mixed",
  "safe": true|false,
  "severity": "S0|S1|S2|S3",
  "triggered_principles": ["MY-1", "MY-4"],
  "risk_labels": ["communal_hostility"],
  "reason": "Why this content was flagged",
  "rewrite_required": true|false,
  "suggested_rewrite": "A constructive alternative"
}
```

Consistency rules enforced by the schema:
- `safe=True` requires `severity=S0`, empty `triggered_principles` and `risk_labels`
- `safe=False` requires `severity` in S1-S3
- `rewrite_required=True` requires non-empty `suggested_rewrite`
- `input_text` must be at least 10 characters

## Language Distribution

| Language | Code | Target |
|----------|------|--------|
| Bahasa Malaysia | ms | 35% |
| English | en | 25% |
| Chinese (Mandarin) | zh | 15% |
| Tamil | ta | 10% |
| Code-switching mix | mixed | 15% |

## Pipeline Usage

The pipeline processes raw batch files through four stages:

### 1. Merge

Combines all `*.jsonl` batch files into a single file:

```python
from src.sovreign.merge import merge_batches
from pathlib import Path

count = merge_batches(Path("data/batches"), Path("data/merged/all.jsonl"))
```

### 2. Validate & Filter

Applies Pydantic schema validation and 9 quality rules:

```python
import json
from src.sovreign.validate import validate_batch

raw = [json.loads(l) for l in open("data/merged/all.jsonl") if l.strip()]
result = validate_batch(raw)
# result.accepted — list of valid DatasetExample objects
# result.rejected — list of (dict, reason) tuples
# result.flagged — list of (DatasetExample, reason) tuples
```

Quality rules include:
- Pydantic schema validation (types, consistency)
- Near-duplicate detection (Jaccard similarity > 0.85)
- Robotic/generic text detection
- Slang overload filtering (> 25% particles)
- Cartoonish extreme content filtering
- Political criticism over-labeling flags

### 3. Statistics

```python
from src.sovreign.stats import compute_stats, print_stats

stats = compute_stats(result.accepted)
report = print_stats(stats)
print(report)
```

### 4. Stratified Split

80/10/10 train/validation/test split, stratified by severity x language:

```python
from src.sovreign.split import stratified_split

train, val, test = stratified_split(result.accepted)
```

### Full Pipeline (One Shot)

```python
from src.sovreign.merge import merge_batches
from src.sovreign.validate import validate_batch
from src.sovreign.stats import compute_stats, print_stats
from src.sovreign.split import stratified_split
from pathlib import Path
import json

count = merge_batches(Path("data/batches"), Path("data/merged/all.jsonl"))
raw = [json.loads(l) for l in open("data/merged/all.jsonl") if l.strip()]
result = validate_batch(raw)
stats = compute_stats(result.accepted)
print(print_stats(stats))
train, val, test = stratified_split(result.accepted)

for name, data in [("train", train), ("validation", val), ("test", test)]:
    with open(f"data/final/{name}.jsonl", "w") as f:
        for ex in data:
            f.write(json.dumps(ex.model_dump(), ensure_ascii=False) + "\n")
```

## Current Dataset Statistics

| Metric | Value |
|--------|-------|
| Raw examples | 8,567 |
| Accepted (after validation) | 7,267 |
| Rejected | 1,300 |
| Flagged (accepted but noted) | 176 |

**Severity distribution (all targets met):**

| Severity | Count | Target | Status |
|----------|-------|--------|--------|
| S0 | 2,251 | 2,000 | Met |
| S1 | 2,006 | 2,000 | Met |
| S2 | 2,006 | 2,000 | Met |
| S3 | 1,004 | 1,000 | Met |

**Final splits:**

| Split | Count | File |
|-------|-------|------|
| Train (production) | 6,472 | `data/cot/train_cot_augmented.jsonl` |
| Train (base) | 6,237 | `data/cot/train_cot_final.jsonl` |
| Validation | 726 | `data/cot/validation_cot.jsonl` |
| Test | 725 | `data/final/test.jsonl` |

## Data Augmentation

### Stage 1: Edge Case Augmentation (Historical)

231 initial edge case examples were generated to fill gaps in quoted offensive, sarcasm, and communal euphemism patterns. These were merged into the base training split (5,816 → 6,047 examples).

### Stage 2: R1 Targeted Gap-Pattern Augmentation (Production)

After scientific analysis of the CoT model's 69% ceiling, 5 distribution gaps were identified between training data and stress test patterns. 235 targeted examples were generated:

| Pattern | Count | Label | Purpose |
|---------|-------|-------|---------|
| Quote-and-condemn | 50 | Safe | Teach quoting hate to condemn it = safe |
| Pro-social defense | 40 | Safe | Teach defending a group = safe |
| Rumor debunking | 35 | Safe | Teach debunking misinformation = safe |
| Nostalgia/anecdote | 35 | Safe | Teach nostalgic inter-ethnic memories = safe |
| Sarcastic political critique | 60 | Unsafe S1 | Teach sarcastic government critique = S1 |
| Safe everyday anchors | 15 | Safe | Prevent over-correction |

Script: `scripts/generate_augmented_data.py`
Result: 69% → **73%** on stress test (FP: 22→15)

### Stage 3: R2 Experiments (Failed)

Two R2 augmentation attempts were made to push beyond 73%:
- **R2 (contrastive):** Added 138 examples including unsafe ethnic-mentioning patterns → 70% (regression)
- **R2-fix:** Removed colliding patterns, kept non-colliding additions → 70% (no improvement)

**Root cause:** For a 0.8B model, adding unsafe examples in the same semantic space as R1's safe examples creates contrastive confusion. The model uses surface heuristics (presence of ethnic terms → safe/unsafe) and cannot learn fine-grained intent discrimination from small contrastive batches. Further gains require either a larger model or significantly more training data.

## Stress Test Set

`stress_test/handwritten.jsonl` contains 93 handwritten edge-case examples designed to evaluate model performance on ambiguous or tricky inputs:

| Edge Case Type | Count |
|----------------|-------|
| Code-switching (BM-EN, BM-ZH) | 2 |
| Sarcasm and satire | 15 |
| Quoted offensive speech (news/reporting) | 11 |
| Communal euphemisms | 37 |
| Religious edge cases | 11 |
| Forwarded-message style rumors | 17 |

These examples test whether the model can distinguish between:
- Reporting hate speech vs. endorsing it
- Sarcastic political critique vs. actual incitement
- Cultural complaints vs. racial hostility
- Debunking misinformation vs. spreading it
- Religious discussion vs. provocation

## Fine-Tuning

Three models are fine-tuned on this dataset using LoRA SFT:

| Model | HuggingFace ID | Params | Notebook |
|-------|---------------|--------|----------|
| FunctionGemma | `google/functiongemma-270m-it` | 270M | `notebooks/gemma3_sft.ipynb` |
| LFM2 | `LiquidAI/LFM2-350M` | 350M | `notebooks/lfm2_sft.ipynb` |
| Qwen3.5 | `Qwen/Qwen3.5-0.8B` | 800M | `notebooks/qwen35_sft.ipynb` |
| **Qwen3 (production)** | `Qwen/Qwen3-0.6B` | 600M | Kaggle kernel v17 |

### Training Setup

- **Method:** LoRA (r=16, alpha=32) with SFTTrainer from HuggingFace TRL
- **Hardware:** Kaggle P100 GPU (16GB VRAM)
- **Epochs:** 3
- **Effective batch size:** 8 (2 x 4 gradient accumulation)
- **Precision:** fp16
- **Max sequence length:** 1536 (CoT), 1024 (baseline)
- **Training time:** ~5 hours (6,472 examples × 3 epochs on P100)

### Task Format

The model receives input text and outputs a structured JSON verdict:

```json
{
  "safe": false,
  "severity": "S1",
  "triggered_principles": ["MY-5"],
  "risk_labels": ["inflammatory_polarisation"],
  "reason": "...",
  "rewrite_required": true,
  "suggested_rewrite": "..."
}
```

### Running on Kaggle

1. Create a new Kaggle notebook with GPU T4 x2 accelerator
2. Upload `data/final/train.jsonl`, `data/final/validation.jsonl`, and `notebooks/shared_utils.py`
3. Copy cells from `notebooks/gemma3_sft.ipynb` or `notebooks/lfm2_sft.ipynb`
4. Run all cells

### Evaluation

Use `notebooks/eval_compare.ipynb` to compare both models on the test set (725 examples) and stress test (93 edge cases). Upload both adapter directories and the test/stress data files.

### Evaluation Results

**Overall accuracy (safe/unsafe classification on 93-example stress test):**

| Metric | Gemma 270M | LFM2 350M | Qwen3.5 0.8B | Qwen3.5 CoT | CoT + R1 Aug | **Qwen3 0.6B** |
|--------|-----------|-----------|--------------|-------------|-----------------|----------------|
| Safe accuracy (stress) | 58% | 47% | 62% | 69% | 73% | **73%** |
| Valid JSON rate | 100% | 78% | 99% | 100% | 100% | **100%** |
| Reasoning rate | — | — | — | 100% | 100% | **100%** |
| False positives | — | — | — | 22 | 15 | **16** |
| False negatives | — | — | — | 7 | 10 | **9** |

**Stress test breakdown by edge case type (best model = Qwen3 0.6B CoT):**

| Edge Case Type | Count | Gemma 270M | Qwen3.5 CoT | CoT + R1 Aug | **Qwen3 0.6B** |
|----------------|-------|-----------|-------------|-----------------|----------------|
| Code-switching | 2 | 0% | 100% | 100% | **100%** |
| Communal euphemism | 37 | 62% | 70% | 70% | **81%** |
| Forwarded rumor | 17 | 65% | 82% | 82% | **76%** |
| Quoted offensive | 11 | 9% | 45% | 55% | **54%** |
| Religious edge case | 11 | 55% | 73% | 82% | **54%** |
| Sarcasm | 15 | 80% | 60% | 80% | **73%** |
| **TOTAL** | **93** | **58%** | **69%** | **73%** | **73%** |

**Key findings:**
- **Qwen3 0.6B CoT is the production model at 73%** on the 93-example stress test — matches Qwen3.5 0.8B accuracy with ONNX-exportable architecture
- R1 augmentation added 235 targeted examples covering 5 gap patterns, improving from 69% → 73%
- CoT reasoning enables the model to reason about speaker intent — 100% reasoning and valid JSON rate
- Biggest improvements from augmentation: quoted offensive (45%→55%), religious (73%→82%), sarcasm (60%→80%)
- False positives dropped significantly (22→15) — model better at recognizing pro-social speech as safe

**Post-training experiments (GRPO, DPO) failed to improve beyond 69%:**
- Root cause: distribution mismatch between training data and stress test patterns
- RL/preference methods can't teach unseen patterns — only data augmentation works
- Further R2 augmentation attempts (contrastive boundaries) caused regressions due to signal collision in the 0.8B model's surface-level heuristics
- 73% appears to be near the ceiling for this model size + dataset scale
- **Qwen3 0.6B matches Qwen3.5 0.8B at 73%** with a standard softmax attention architecture, enabling ONNX export for browser/edge inference

## Live Demo

**Web demo:** https://sovreign-moderation.swmengappdev.workers.dev

Architecture:
- **Cloudflare Worker** serves the frontend UI and proxies API calls
- **HuggingFace Space** ([wms2537/sovreign-moderation](https://huggingface.co/spaces/wms2537/sovreign-moderation)) runs the FastAPI inference server
- **Model:** [wms2537/qwen3-0.6b-malaysia-moderation-cot](https://huggingface.co/wms2537/qwen3-0.6b-malaysia-moderation-cot) — merged Qwen3 0.6B with LoRA adapter

Run locally:
```bash
python3 scripts/demo_server.py
# Open http://localhost:8080
```

## Chain-of-Thought Fine-Tuning

To address the model's inability to reason about speaker intent (particularly for quoted offensive speech, sarcasm, and communal euphemisms), a chain-of-thought (CoT) training approach was developed.

### Approach

Instead of training the model to output just a JSON verdict, it is trained to **reason first** inside `<reasoning>` tags, then output the verdict:

```
<reasoning>
This text quotes a racial slur in a news report context. The speaker is a journalist
documenting a hate crime, not endorsing the slur. The quoting serves factual reporting.
</reasoning>
{"safe": true, "severity": "S0", ...}
```

This forces the model to explicitly reason about context before deciding, rather than pattern-matching keywords.

### CoT Dataset

| Component | Examples | Description |
|-----------|----------|-------------|
| Original + CoT reasoning | 6,047 | Template-based reasoning added to all existing training examples |
| Contrastive pairs | 190 | Minimal-edit pairs (same topic, different context = different verdict) |
| Base CoT training set | 6,237 | Merged, shuffled, schema-validated |
| R1 gap-pattern augmentation | 235 | Targeted examples for 5 failure modes |
| **Production training set** | **6,472** | `train_cot_augmented.jsonl` |

Contrastive pair categories:
- **Quoted offensive** (56 pairs): News reporting vs endorsement of slurs
- **Sarcasm** (18 pairs): Legitimate political critique (S1) vs communal hostility (S2)
- **Communal euphemism** (21 pairs): Benign cultural reference vs coded ethnic exclusion

### CoT Training Config

| Parameter | Baseline | CoT |
|-----------|----------|-----|
| max_seq_length | 1024 | 1536 |
| max_new_tokens (inference) | 200 | 400 |
| System prompt | "...respond with JSON..." | "...reason inside `<reasoning>` tags, then JSON..." |
| Training examples | 6,047 | 6,237 |

### Scripts

| Script | Purpose |
|--------|---------|
| `scripts/generate_cot_reasoning.py` | Add reasoning field to existing train/val data |
| `scripts/generate_contrastive_pairs.py` | Generate contrastive pairs with reasoning |
| `scripts/validate_contrastive.py` | Validate pair integrity and schema compliance |
| `scripts/assemble_cot_dataset.py` | Merge all data into final CoT training set |
| `scripts/generate_augmented_data.py` | R1 targeted gap-pattern augmentation (production) |
| `scripts/generate_augmented_r2_fix.py` | R2-fix augmentation (experimental, not used in production) |

### CoT Evaluation Results

The production model (CoT + R1 augmentation) achieves **73% accuracy** on the 93-example stress test:

| Stage | Accuracy | Key Change |
|-------|----------|------------|
| Baseline (no CoT) | 62% | JSON-only output |
| CoT training | 69% | Added `<reasoning>` tags, contrastive pairs |
| **CoT + R1 augmentation** | **73%** | +235 targeted gap-pattern examples |

Key improvements from R1 augmentation:
- **Quoted offensive 45% → 55%** — better at distinguishing reporting from endorsement
- **Religious edge case 73% → 82%** — improved interfaith content handling
- **Sarcasm 60% → 80%** — major improvement in political sarcasm classification
- **False positives 22 → 15** — model better recognizes pro-social speech as safe

Remaining weaknesses (25/93 wrong):
- **Communal euphemism at 70%** — coded ethnic exclusion patterns still challenging
- **Forwarded rumor at 82%** — some debunking-vs-spreading confusion persists
- **Quoted offensive at 55%** — quoting-to-condemn vs endorsement remains hardest

JSON parsing: Uses balanced brace extraction (`extract_first_json_object`) + truncation at `<|im_start|>` for 100% valid JSON rate.

## Templates

### Master Prompt (`templates/master_prompt.txt`)

LLM prompt template for generating synthetic moderation examples. Includes the 8 Malaysia-specific principles, generation rules, and output JSON schema. Uses placeholder variables: `{scenario_type}`, `{language}`, `{severity}`, `{topic}`, `{style}`.

### Seeds (`templates/seeds.json`)

50 seed scenarios distributed across all severity levels:
- **S0** (12 seeds): Safe civic discourse, respectful criticism, neutral discussion
- **S1** (14 seeds): Borderline content with rude tone, sarcasm, or mild insensitivity
- **S2** (12 seeds): Harmful generalizations, doxxing-lite, fake rumors, harassment
- **S3** (12 seeds): Explicit incitement, full doxxing, dehumanizing content, panic-inducing falsehoods

Topics covered: `politics_public_issues`, `race_religion_culture`, `personal_conflict_insults`, `rumors_misinformation`, `privacy_doxxing`, `neutral_civic_safe`.

## Pipeline Modules

### Schema (`sovreign.schema`)

Pydantic `DatasetExample` model enforcing field types and consistency rules via `model_validator`.

### Validation (`sovreign.validate`)

Post-generation filtering with quality rules covering robotic text detection, structural duplication (Jaccard similarity > 0.85), slang overload, cartoonish content, and over-labeling flags for political criticism.

### Merge (`sovreign.merge`)

`merge_batches(batch_dir, output_path)` — Merges all `*.jsonl` files from a batch directory into a single JSONL output file. Validates JSON and skips blank lines. Returns count of merged examples.

### Stats (`sovreign.stats`)

- `compute_stats(examples)` — Computes severity, language, principle/risk label distributions, and rewrite coverage.
- `print_stats(stats)` — Formats statistics into a human-readable report with progress toward target counts.

### Split (`sovreign.split`)

`stratified_split(examples, train, val, test, seed)` — Deterministic stratified splitting by severity x language groups. Default ratios: 80/10/10. Returns `(train_list, val_list, test_list)`.
