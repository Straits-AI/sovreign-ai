# Fine-Tuning Gemma 3 270M & LFM2 350M — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create three Kaggle-ready notebooks that LoRA fine-tune Gemma 3 270M and LFM2 350M on the Malaysia moderation dataset, then evaluate and compare both models.

**Architecture:** Each training notebook loads JSONL data, formats it into model-specific chat templates (Gemma uses `<start_of_turn>` tokens, LFM2 uses ChatML `<|im_start|>` tokens), trains LoRA adapters via HuggingFace TRL SFTTrainer, and saves adapter weights. A shared eval notebook loads both models and computes metrics on test + stress test sets.

**Tech Stack:** Python, transformers, peft, trl, datasets, accelerate, bitsandbytes, sacrebleu

---

### Task 1: Create shared data utilities module

**Files:**
- Create: `notebooks/shared_utils.py`

This utility file will be uploaded to Kaggle alongside the notebooks. It contains all shared logic: data loading, prompt formatting, JSON parsing, and evaluation metrics. Both training notebooks and the eval notebook import from it.

**Step 1: Create the notebooks directory**

```bash
mkdir -p notebooks
```

**Step 2: Write `notebooks/shared_utils.py`**

```python
"""Shared utilities for Malaysia moderation fine-tuning notebooks."""
import json
import re
from pathlib import Path
from collections import Counter

# ── Prompt template ──────────────────────────────────────────────
SYSTEM_PROMPT = (
    "You are a Malaysia content moderation judge. "
    "Analyze the following text and respond with a JSON object containing: "
    "safe (bool), severity (S0-S3), triggered_principles (list of MY-1..MY-8), "
    "risk_labels (list), reason (string), rewrite_required (bool), suggested_rewrite (string)."
)

OUTPUT_KEYS = [
    "safe", "severity", "triggered_principles", "risk_labels",
    "reason", "rewrite_required", "suggested_rewrite",
]

SEVERITY_ORDER = {"S0": 0, "S1": 1, "S2": 2, "S3": 3}

VALID_PRINCIPLES = {f"MY-{i}" for i in range(1, 9)}
VALID_RISK_LABELS = {
    "communal_hostility", "religious_provocation", "unlawful_incitement",
    "targeted_abuse", "revenge_or_vigilantism", "dangerous_misinformation",
    "privacy_exposure", "inflammatory_polarisation", "needs_constructive_rewrite",
}


# ── Data loading ─────────────────────────────────────────────────
def load_jsonl(path: str) -> list[dict]:
    """Load JSONL file and return list of dicts."""
    examples = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


def make_target_json(example: dict) -> str:
    """Build the target JSON string from a dataset example."""
    target = {k: example[k] for k in OUTPUT_KEYS}
    return json.dumps(target, ensure_ascii=False)


# ── Chat formatting (Gemma 3) ───────────────────────────────────
def format_gemma(example: dict) -> str:
    """Format a single example into Gemma 3 chat template."""
    user_msg = f"{SYSTEM_PROMPT}\n\nText: {example['input_text']}"
    target = make_target_json(example)
    return (
        f"<start_of_turn>user\n{user_msg}<end_of_turn>\n"
        f"<start_of_turn>model\n{target}<end_of_turn>"
    )


# ── Chat formatting (LFM2 ChatML) ───────────────────────────────
def format_lfm2(example: dict) -> str:
    """Format a single example into LFM2 ChatML template."""
    user_msg = f"{SYSTEM_PROMPT}\n\nText: {example['input_text']}"
    target = make_target_json(example)
    return (
        f"<|im_start|>user\n{user_msg}<|im_end|>\n"
        f"<|im_start|>assistant\n{target}<|im_end|>"
    )


# ── Inference prompt (no target) ────────────────────────────────
def inference_prompt_gemma(input_text: str) -> str:
    """Build Gemma inference prompt (no target)."""
    user_msg = f"{SYSTEM_PROMPT}\n\nText: {input_text}"
    return (
        f"<start_of_turn>user\n{user_msg}<end_of_turn>\n"
        f"<start_of_turn>model\n"
    )


def inference_prompt_lfm2(input_text: str) -> str:
    """Build LFM2 inference prompt (no target)."""
    user_msg = f"{SYSTEM_PROMPT}\n\nText: {input_text}"
    return (
        f"<|im_start|>user\n{user_msg}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )


# ── JSON parsing ────────────────────────────────────────────────
def parse_model_output(text: str) -> dict | None:
    """Try to parse JSON from model output. Returns None if invalid."""
    # Strip any trailing special tokens
    for token in ["<end_of_turn>", "<|im_end|>", "</s>", "<eos>"]:
        text = text.replace(token, "")
    text = text.strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in text
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None


# ── Evaluation metrics ──────────────────────────────────────────
def safe_accuracy(preds: list[dict], golds: list[dict]) -> float:
    """Binary safe/unsafe accuracy."""
    correct = sum(1 for p, g in zip(preds, golds) if p.get("safe") == g["safe"])
    return correct / len(golds) if golds else 0.0


def severity_accuracy(preds: list[dict], golds: list[dict]) -> float:
    """Exact severity match."""
    correct = sum(1 for p, g in zip(preds, golds) if p.get("severity") == g["severity"])
    return correct / len(golds) if golds else 0.0


def severity_within_one(preds: list[dict], golds: list[dict]) -> float:
    """Severity within one level."""
    correct = 0
    for p, g in zip(preds, golds):
        p_ord = SEVERITY_ORDER.get(p.get("severity"), -1)
        g_ord = SEVERITY_ORDER.get(g["severity"], -1)
        if p_ord >= 0 and abs(p_ord - g_ord) <= 1:
            correct += 1
    return correct / len(golds) if golds else 0.0


def multilabel_f1(preds: list[dict], golds: list[dict], key: str) -> float:
    """Micro F1 for a multi-label list field."""
    tp = fp = fn = 0
    for p, g in zip(preds, golds):
        pred_set = set(p.get(key, []))
        gold_set = set(g[key])
        tp += len(pred_set & gold_set)
        fp += len(pred_set - gold_set)
        fn += len(gold_set - pred_set)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0


def valid_json_rate(outputs: list[dict | None]) -> float:
    """Percentage of outputs that parsed as valid JSON."""
    valid = sum(1 for o in outputs if o is not None)
    return valid / len(outputs) if outputs else 0.0


def compute_all_metrics(
    parsed_preds: list[dict],
    golds: list[dict],
    raw_outputs: list[dict | None],
) -> dict:
    """Compute all evaluation metrics. parsed_preds has Nones replaced with empty dicts."""
    return {
        "valid_json_rate": valid_json_rate(raw_outputs),
        "safe_accuracy": safe_accuracy(parsed_preds, golds),
        "severity_accuracy": severity_accuracy(parsed_preds, golds),
        "severity_within_1": severity_within_one(parsed_preds, golds),
        "principle_f1": multilabel_f1(parsed_preds, golds, "triggered_principles"),
        "risk_label_f1": multilabel_f1(parsed_preds, golds, "risk_labels"),
    }


def print_comparison(gemma_metrics: dict, lfm2_metrics: dict) -> None:
    """Print side-by-side comparison table."""
    print(f"{'Metric':<25} {'Gemma 3 270M':>14} {'LFM2 350M':>14}")
    print("-" * 55)
    for key in gemma_metrics:
        g = gemma_metrics[key]
        l = lfm2_metrics[key]
        print(f"{key:<25} {g:>13.1%} {l:>13.1%}")
```

**Step 3: Commit**

```bash
git add notebooks/shared_utils.py
git commit -m "feat: add shared utilities for fine-tuning notebooks"
```

---

### Task 2: Create Gemma 3 270M training notebook

**Files:**
- Create: `notebooks/gemma3_sft.ipynb`

**Step 1: Write the notebook**

The notebook has these cells (each is a separate code or markdown cell):

**Cell 1 (markdown):**
```markdown
# FunctionGemma 270M — LoRA SFT for Malaysia Moderation

Fine-tune `google/functiongemma-270m-it` with LoRA adapters on the Malaysia moderation dataset.
Structured JSON output: the model judges content safety and generates rewrites.

**Hardware:** Kaggle T4 GPU (16GB VRAM)
**Dataset:** 5,816 train / 726 validation examples
**Method:** LoRA (r=16, alpha=32) with SFTTrainer
```

**Cell 2 (code) — Install dependencies:**
```python
!pip install -q transformers>=4.46 peft>=0.13 trl>=0.12 datasets>=3.0 accelerate>=1.0 bitsandbytes>=0.44
```

**Cell 3 (code) — Imports and setup:**
```python
import json
import torch
from pathlib import Path
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments
from peft import LoraConfig, get_peft_model, TaskType
from trl import SFTTrainer, SFTConfig

# Import shared utilities (upload shared_utils.py to Kaggle working directory)
import shared_utils as utils

print(f"CUDA available: {torch.cuda.is_available()}")
print(f"Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
```

**Cell 4 (code) — Load and format data:**
```python
# Upload train.jsonl and validation.jsonl to Kaggle, adjust paths as needed
TRAIN_PATH = "train.jsonl"
VAL_PATH = "validation.jsonl"

train_raw = utils.load_jsonl(TRAIN_PATH)
val_raw = utils.load_jsonl(VAL_PATH)

print(f"Train: {len(train_raw)} examples")
print(f"Validation: {len(val_raw)} examples")

# Format into Gemma chat template
train_texts = [utils.format_gemma(ex) for ex in train_raw]
val_texts = [utils.format_gemma(ex) for ex in val_raw]

train_dataset = Dataset.from_dict({"text": train_texts})
val_dataset = Dataset.from_dict({"text": val_texts})

# Preview one example
print("\n--- Example formatted text ---")
print(train_texts[0][:500])
```

**Cell 5 (code) — Load model and tokenizer:**
```python
MODEL_ID = "google/functiongemma-270m-it"

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

# Gemma PT model may not have a pad token; set it
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float16,
    device_map="auto",
)

print(f"Model parameters: {model.num_parameters():,}")
```

**Cell 6 (code) — Configure LoRA:**
```python
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    bias="none",
    task_type=TaskType.CAUSAL_LM,
    target_modules="all-linear",
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
```

**Cell 7 (code) — Training configuration:**
```python
OUTPUT_DIR = "gemma3-malaysia-mod"

sft_config = SFTConfig(
    output_dir=OUTPUT_DIR,
    num_train_epochs=3,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    weight_decay=0.01,
    warmup_ratio=0.05,
    fp16=True,
    logging_steps=50,
    eval_strategy="epoch",
    save_strategy="epoch",
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    max_seq_length=1024,
    dataset_text_field="text",
    report_to="none",
)
```

**Cell 8 (code) — Train:**
```python
trainer = SFTTrainer(
    model=model,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    processing_class=tokenizer,
    args=sft_config,
)

trainer.train()
```

**Cell 9 (code) — Save adapter weights:**
```python
# Save LoRA adapter
model.save_pretrained(f"{OUTPUT_DIR}/final_adapter")
tokenizer.save_pretrained(f"{OUTPUT_DIR}/final_adapter")
print(f"Adapter saved to {OUTPUT_DIR}/final_adapter")

# Show training logs
for log in trainer.state.log_history:
    if "eval_loss" in log:
        print(f"Epoch {log.get('epoch', '?')}: eval_loss={log['eval_loss']:.4f}")
```

**Cell 10 (markdown):**
```markdown
## Quick Sanity Check
Run inference on a few examples to verify the model produces valid JSON.
```

**Cell 11 (code) — Sanity check inference:**
```python
model.eval()

test_inputs = [
    "Hari ini cuaca sangat panas. Jom minum air kelapa kat pantai!",
    "Semua orang kaum X memang pemalas dan suka curi.",
    "Government should consider raising minimum wage to match inflation rates.",
]

for text in test_inputs:
    prompt = utils.inference_prompt_gemma(text)
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=300,
            do_sample=False,
            temperature=1.0,
        )

    response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=False)
    parsed = utils.parse_model_output(response)

    print(f"\nInput: {text[:80]}...")
    print(f"Valid JSON: {parsed is not None}")
    if parsed:
        print(f"  safe={parsed.get('safe')}, severity={parsed.get('severity')}")
    print()
```

**Step 2: Commit**

```bash
git add notebooks/gemma3_sft.ipynb
git commit -m "feat: add Gemma 3 270M LoRA SFT training notebook"
```

---

### Task 3: Create LFM2 350M training notebook

**Files:**
- Create: `notebooks/lfm2_sft.ipynb`

**Step 1: Write the notebook**

**Cell 1 (markdown):**
```markdown
# LFM2 350M — LoRA SFT for Malaysia Moderation

Fine-tune `LiquidAI/LFM2-350M` with LoRA adapters on the Malaysia moderation dataset.
Structured JSON output: the model judges content safety and generates rewrites.

**Hardware:** Kaggle T4 GPU (16GB VRAM)
**Dataset:** 5,816 train / 726 validation examples
**Method:** LoRA (r=16, alpha=32) with SFTTrainer
```

**Cell 2 (code) — Install dependencies:**
```python
!pip install -q transformers>=4.46 peft>=0.13 trl>=0.12 datasets>=3.0 accelerate>=1.0 bitsandbytes>=0.44
```

**Cell 3 (code) — Imports and setup:**
```python
import json
import torch
from pathlib import Path
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig, get_peft_model, TaskType
from trl import SFTTrainer, SFTConfig

import shared_utils as utils

print(f"CUDA available: {torch.cuda.is_available()}")
print(f"Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
```

**Cell 4 (code) — Load and format data:**
```python
TRAIN_PATH = "train.jsonl"
VAL_PATH = "validation.jsonl"

train_raw = utils.load_jsonl(TRAIN_PATH)
val_raw = utils.load_jsonl(VAL_PATH)

print(f"Train: {len(train_raw)} examples")
print(f"Validation: {len(val_raw)} examples")

# Format into LFM2 ChatML template
train_texts = [utils.format_lfm2(ex) for ex in train_raw]
val_texts = [utils.format_lfm2(ex) for ex in val_raw]

train_dataset = Dataset.from_dict({"text": train_texts})
val_dataset = Dataset.from_dict({"text": val_texts})

print("\n--- Example formatted text ---")
print(train_texts[0][:500])
```

**Cell 5 (code) — Load model and tokenizer:**
```python
MODEL_ID = "LiquidAI/LFM2-350M"

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)

if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True,
)

print(f"Model parameters: {model.num_parameters():,}")
```

**Cell 6 (code) — Configure LoRA:**
```python
# LFM2 uses a hybrid architecture; target all linear layers
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    bias="none",
    task_type=TaskType.CAUSAL_LM,
    target_modules="all-linear",
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
```

**Cell 7 (code) — Training configuration:**
```python
OUTPUT_DIR = "lfm2-malaysia-mod"

sft_config = SFTConfig(
    output_dir=OUTPUT_DIR,
    num_train_epochs=3,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    weight_decay=0.01,
    warmup_ratio=0.05,
    fp16=True,
    logging_steps=50,
    eval_strategy="epoch",
    save_strategy="epoch",
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    max_seq_length=1024,
    dataset_text_field="text",
    report_to="none",
)
```

**Cell 8 (code) — Train:**
```python
trainer = SFTTrainer(
    model=model,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    processing_class=tokenizer,
    args=sft_config,
)

trainer.train()
```

**Cell 9 (code) — Save adapter weights:**
```python
model.save_pretrained(f"{OUTPUT_DIR}/final_adapter")
tokenizer.save_pretrained(f"{OUTPUT_DIR}/final_adapter")
print(f"Adapter saved to {OUTPUT_DIR}/final_adapter")

for log in trainer.state.log_history:
    if "eval_loss" in log:
        print(f"Epoch {log.get('epoch', '?')}: eval_loss={log['eval_loss']:.4f}")
```

**Cell 10 (markdown):**
```markdown
## Quick Sanity Check
```

**Cell 11 (code) — Sanity check inference:**
```python
model.eval()

test_inputs = [
    "Hari ini cuaca sangat panas. Jom minum air kelapa kat pantai!",
    "Semua orang kaum X memang pemalas dan suka curi.",
    "Government should consider raising minimum wage to match inflation rates.",
]

for text in test_inputs:
    prompt = utils.inference_prompt_lfm2(text)
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=300,
            do_sample=False,
            temperature=1.0,
        )

    response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=False)
    parsed = utils.parse_model_output(response)

    print(f"\nInput: {text[:80]}...")
    print(f"Valid JSON: {parsed is not None}")
    if parsed:
        print(f"  safe={parsed.get('safe')}, severity={parsed.get('severity')}")
    print()
```

**Step 2: Commit**

```bash
git add notebooks/lfm2_sft.ipynb
git commit -m "feat: add LFM2 350M LoRA SFT training notebook"
```

---

### Task 4: Create evaluation comparison notebook

**Files:**
- Create: `notebooks/eval_compare.ipynb`

**Step 1: Write the notebook**

**Cell 1 (markdown):**
```markdown
# Model Comparison: Gemma 3 270M vs LFM2 350M

Evaluate both fine-tuned models on:
- **Test set** (725 examples from `data/final/test.jsonl`)
- **Stress test** (93 handwritten edge cases from `stress_test/handwritten.jsonl`)

Metrics: safe accuracy, severity accuracy, severity within-1, principle F1, risk label F1, valid JSON rate.
```

**Cell 2 (code) — Install and import:**
```python
!pip install -q transformers>=4.46 peft>=0.13 datasets>=3.0 accelerate>=1.0 bitsandbytes>=0.44 sacrebleu

import json
import torch
from tqdm import tqdm
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import shared_utils as utils
```

**Cell 3 (code) — Load test data:**
```python
TEST_PATH = "test.jsonl"
STRESS_PATH = "handwritten.jsonl"

test_data = utils.load_jsonl(TEST_PATH)
stress_data = utils.load_jsonl(STRESS_PATH)

print(f"Test set: {len(test_data)} examples")
print(f"Stress test: {len(stress_data)} examples")
```

**Cell 4 (code) — Inference helper:**
```python
def run_inference(model, tokenizer, examples, prompt_fn, batch_desc="Inferring"):
    """Run inference on a list of examples. Returns (raw_outputs, parsed_outputs)."""
    model.eval()
    raw_outputs = []
    parsed_outputs = []

    for ex in tqdm(examples, desc=batch_desc):
        prompt = prompt_fn(ex["input_text"])
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=768).to(model.device)

        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=300,
                do_sample=False,
                temperature=1.0,
            )

        response = tokenizer.decode(output_ids[0][inputs["input_ids"].shape[1]:], skip_special_tokens=False)
        parsed = utils.parse_model_output(response)

        raw_outputs.append(parsed)
        parsed_outputs.append(parsed if parsed else {})

    return raw_outputs, parsed_outputs
```

**Cell 5 (markdown):**
```markdown
## Load Gemma 3 270M (fine-tuned)
```

**Cell 6 (code) — Load Gemma:**
```python
GEMMA_BASE = "google/functiongemma-270m-it"
GEMMA_ADAPTER = "gemma3-malaysia-mod/final_adapter"

gemma_tokenizer = AutoTokenizer.from_pretrained(GEMMA_ADAPTER)
gemma_base = AutoModelForCausalLM.from_pretrained(
    GEMMA_BASE, torch_dtype=torch.float16, device_map="auto"
)
gemma_model = PeftModel.from_pretrained(gemma_base, GEMMA_ADAPTER)
gemma_model.eval()
print("Gemma 3 loaded.")
```

**Cell 7 (code) — Gemma inference on test + stress:**
```python
gemma_test_raw, gemma_test_parsed = run_inference(
    gemma_model, gemma_tokenizer, test_data, utils.inference_prompt_gemma, "Gemma test"
)
gemma_stress_raw, gemma_stress_parsed = run_inference(
    gemma_model, gemma_tokenizer, stress_data, utils.inference_prompt_gemma, "Gemma stress"
)
```

**Cell 8 (code) — Free Gemma from GPU:**
```python
del gemma_model, gemma_base
torch.cuda.empty_cache()
print("Gemma freed from GPU.")
```

**Cell 9 (markdown):**
```markdown
## Load LFM2 350M (fine-tuned)
```

**Cell 10 (code) — Load LFM2:**
```python
LFM2_BASE = "LiquidAI/LFM2-350M"
LFM2_ADAPTER = "lfm2-malaysia-mod/final_adapter"

lfm2_tokenizer = AutoTokenizer.from_pretrained(LFM2_ADAPTER, trust_remote_code=True)
lfm2_base = AutoModelForCausalLM.from_pretrained(
    LFM2_BASE, torch_dtype=torch.float16, device_map="auto", trust_remote_code=True
)
lfm2_model = PeftModel.from_pretrained(lfm2_base, LFM2_ADAPTER)
lfm2_model.eval()
print("LFM2 loaded.")
```

**Cell 11 (code) — LFM2 inference on test + stress:**
```python
lfm2_test_raw, lfm2_test_parsed = run_inference(
    lfm2_model, lfm2_tokenizer, test_data, utils.inference_prompt_lfm2, "LFM2 test"
)
lfm2_stress_raw, lfm2_stress_parsed = run_inference(
    lfm2_model, lfm2_tokenizer, stress_data, utils.inference_prompt_lfm2, "LFM2 stress"
)
```

**Cell 12 (code) — Free LFM2:**
```python
del lfm2_model, lfm2_base
torch.cuda.empty_cache()
```

**Cell 13 (markdown):**
```markdown
## Results: Test Set (725 examples)
```

**Cell 14 (code) — Test set metrics:**
```python
gemma_test_metrics = utils.compute_all_metrics(gemma_test_parsed, test_data, gemma_test_raw)
lfm2_test_metrics = utils.compute_all_metrics(lfm2_test_parsed, test_data, lfm2_test_raw)

print("=== Test Set Results ===\n")
utils.print_comparison(gemma_test_metrics, lfm2_test_metrics)
```

**Cell 15 (markdown):**
```markdown
## Results: Stress Test (93 edge cases)
```

**Cell 16 (code) — Stress test metrics:**
```python
gemma_stress_metrics = utils.compute_all_metrics(gemma_stress_parsed, stress_data, gemma_stress_raw)
lfm2_stress_metrics = utils.compute_all_metrics(lfm2_stress_parsed, stress_data, lfm2_stress_raw)

print("=== Stress Test Results ===\n")
utils.print_comparison(gemma_stress_metrics, lfm2_stress_metrics)
```

**Cell 17 (markdown):**
```markdown
## Stress Test Breakdown by Edge Case Type
```

**Cell 18 (code) — Breakdown by edge case type:**
```python
from collections import defaultdict

def breakdown_by_type(parsed_preds, golds):
    """Group by edge_case_type and compute severity accuracy per group."""
    groups = defaultdict(lambda: ([], []))
    for pred, gold in zip(parsed_preds, golds):
        etype = gold.get("edge_case_type", "unknown")
        groups[etype][0].append(pred)
        groups[etype][1].append(gold)

    print(f"{'Edge Case Type':<25} {'Count':>6} {'Safe Acc':>10} {'Sev Acc':>10}")
    print("-" * 55)
    for etype in sorted(groups.keys()):
        preds, gs = groups[etype]
        sa = utils.safe_accuracy(preds, gs)
        sev = utils.severity_accuracy(preds, gs)
        print(f"{etype:<25} {len(gs):>6} {sa:>9.1%} {sev:>9.1%}")

print("=== Gemma 3 270M ===")
breakdown_by_type(gemma_stress_parsed, stress_data)

print("\n=== LFM2 350M ===")
breakdown_by_type(lfm2_stress_parsed, stress_data)
```

**Cell 19 (markdown):**
```markdown
## Error Analysis: Failed JSON Outputs
```

**Cell 20 (code) — Error analysis:**
```python
def show_failures(raw_outputs, examples, model_name, max_show=5):
    """Show examples where model failed to produce valid JSON."""
    failures = [(i, ex) for i, (out, ex) in enumerate(zip(raw_outputs, examples)) if out is None]
    print(f"\n{model_name}: {len(failures)} / {len(examples)} failed to produce valid JSON")
    for i, (idx, ex) in enumerate(failures[:max_show]):
        print(f"  [{idx}] {ex['input_text'][:80]}...")

show_failures(gemma_test_raw, test_data, "Gemma 3 (test)")
show_failures(gemma_stress_raw, stress_data, "Gemma 3 (stress)")
show_failures(lfm2_test_raw, test_data, "LFM2 (test)")
show_failures(lfm2_stress_raw, stress_data, "LFM2 (stress)")
```

**Cell 21 (markdown):**
```markdown
## Summary

| Metric | Gemma 3 270M | LFM2 350M | Winner |
|--------|-------------|-----------|--------|
| ... results filled from above ... |

**Recommendation:** Based on the metrics above, the recommended model for deployment is **[TBD after results]**.
```

**Step 2: Commit**

```bash
git add notebooks/eval_compare.ipynb
git commit -m "feat: add evaluation comparison notebook"
```

---

### Task 5: Update README with fine-tuning documentation

**Files:**
- Modify: `README.md`

**Step 1: Add fine-tuning section to README**

Append after the existing "Stress Test Set" section:

```markdown
## Fine-Tuning

Two models are fine-tuned on this dataset using LoRA SFT:

| Model | HuggingFace ID | Params | Notebook |
|-------|---------------|--------|----------|
| FunctionGemma | `google/functiongemma-270m-it` | 270M | `notebooks/gemma3_sft.ipynb` |
| LFM2 | `LiquidAI/LFM2-350M` | 350M | `notebooks/lfm2_sft.ipynb` |

### Training Setup

- **Method:** LoRA (r=16, alpha=32) with SFTTrainer from HuggingFace TRL
- **Hardware:** Kaggle T4 GPU (16GB VRAM)
- **Epochs:** 3
- **Effective batch size:** 8 (2 x 4 gradient accumulation)
- **Precision:** fp16
- **Max sequence length:** 1024

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
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add fine-tuning section to README"
```

---

Plan complete and saved to `docs/plans/2026-03-02-finetuning-plan.md`. Two execution options:

**1. Subagent-Driven (this session)** — I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** — Open new session with executing-plans, batch execution with checkpoints

Which approach?
