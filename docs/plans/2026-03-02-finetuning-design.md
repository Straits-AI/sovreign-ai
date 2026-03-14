# Fine-Tuning Design: Gemma 3 270M & LFM2 350M

## Goal

Fine-tune two small language models (Gemma 3 270M, LFM2 350M) on the Malaysia moderation dataset to serve as judge + rewrite models. Compare their performance to select the best candidate for deployment.

## Models

| Model | HuggingFace ID | Params | Architecture |
|-------|---------------|--------|-------------|
| FunctionGemma | `google/functiongemma-270m-it` | 270M | Transformer (function-call fine-tuned) |
| LFM2 | `LiquidAI/LFM2-350M` | 350M | Hybrid (gated short conv + GQA) |

## Dataset

| Split | Count | Source |
|-------|-------|--------|
| Train | 5,816 | `data/final/train.jsonl` |
| Validation | 726 | `data/final/validation.jsonl` |
| Test | 725 | `data/final/test.jsonl` |
| Stress test | 93 | `stress_test/handwritten.jsonl` |

## Task Format: Structured JSON Output

Single model performs both judging and rewriting. Input is the raw text; output is a JSON object with all moderation fields.

**Prompt template:**
```
You are a Malaysia content moderation judge. Analyze the following text and respond with a JSON verdict.

Text: {input_text}
```

**Expected output:**
```json
{
  "safe": false,
  "severity": "S1",
  "triggered_principles": ["MY-5"],
  "risk_labels": ["inflammatory_polarisation"],
  "reason": "Political frustration about subsidies, not incitement",
  "rewrite_required": true,
  "suggested_rewrite": "Subsidy concerns can be raised through democratic channels."
}
```

Each model uses its own chat template for formatting (Gemma uses `<start_of_turn>` tags, LFM2 uses its own format).

## Training Configuration

| Setting | Value |
|---------|-------|
| Method | LoRA SFT (Supervised Fine-Tuning) |
| Framework | HuggingFace TRL + PEFT |
| Hardware | Kaggle T4 GPU (16GB VRAM) |
| LoRA rank (r) | 16 |
| LoRA alpha | 32 |
| LoRA target modules | All linear layers |
| Learning rate | 2e-4 |
| Batch size | 8 (effective, with gradient accumulation 4) |
| Epochs | 3 |
| Optimizer | AdamW 8-bit |
| Precision | fp16 (T4 does not support bf16) |
| Max sequence length | 1024 |
| Warmup ratio | 0.05 |
| Weight decay | 0.01 |
| Eval strategy | Per-epoch on validation set |

### Why LoRA over Full Fine-Tune

With 5,816 training examples and 270M-350M parameters, full fine-tuning risks overfitting (data-to-param ratio too low). LoRA reduces trainable parameters to ~2-5M, giving a much healthier ratio and allowing 3 epochs without memorization.

## Evaluation Metrics

| Metric | Description |
|--------|-------------|
| Safe/unsafe accuracy | Binary classification (safe vs not safe) |
| Severity accuracy | Exact match on S0/S1/S2/S3 |
| Severity within-1 | Correct if off by at most one severity level |
| Principle F1 | Multi-label F1 on triggered_principles (MY-1 through MY-8) |
| Risk label F1 | Multi-label F1 on risk_labels (9 labels) |
| Valid JSON rate | Percentage of outputs that parse as valid JSON |
| Rewrite BLEU | BLEU score on suggested_rewrite vs ground truth |

Evaluation runs on both `data/final/test.jsonl` (725 examples) and `stress_test/handwritten.jsonl` (93 edge cases). Final comparison table: Gemma 3 270M vs LFM2 350M across all metrics.

## Deliverables

```
notebooks/
  gemma3_sft.ipynb       # Gemma 3 270M LoRA SFT training
  lfm2_sft.ipynb         # LFM2 350M LoRA SFT training
  eval_compare.ipynb     # Evaluate and compare both models
```

### Training Notebook Structure (each model)

1. Install dependencies (transformers, peft, trl, datasets, accelerate, bitsandbytes)
2. Load and format training data from JSONL into model-specific chat template
3. Configure LoRA adapters and SFTTrainer
4. Train with per-epoch validation loss logging
5. Save LoRA adapter weights
6. Quick inference sanity check (3-5 examples)

### Eval Notebook Structure

1. Load both fine-tuned models (base + LoRA adapters)
2. Run inference on test set (725) and stress test (93)
3. Parse JSON outputs, handle malformed outputs gracefully
4. Compute all metrics per model
5. Print side-by-side comparison table
6. Analyze stress test performance by edge_case_type

## Dependencies (Kaggle pip install)

```
transformers>=4.46
peft>=0.13
trl>=0.12
datasets>=3.0
accelerate>=1.0
bitsandbytes>=0.44
evaluate
sacrebleu
```
