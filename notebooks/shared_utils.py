"""Shared utilities for Malaysia moderation fine-tuning notebooks."""
import json
import re

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

SYSTEM_PROMPT_COT = (
    "You are a Malaysia content moderation judge. "
    "First, briefly reason about the speaker's intent, context, and relevant signals "
    "inside <reasoning> tags. Then respond with a JSON verdict containing: "
    "safe (bool), severity (S0-S3), triggered_principles (list of MY-1..MY-8), "
    "risk_labels (list), reason (string), rewrite_required (bool), suggested_rewrite (string)."
)

SEVERITY_ORDER = {"S0": 0, "S1": 1, "S2": 2, "S3": 3}


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


def format_gemma(example: dict) -> str:
    """Format a single example into Gemma 3 chat template."""
    user_msg = f"{SYSTEM_PROMPT}\n\nText: {example['input_text']}"
    target = make_target_json(example)
    return (
        f"<start_of_turn>user\n{user_msg}<end_of_turn>\n"
        f"<start_of_turn>model\n{target}<end_of_turn>"
    )


def format_lfm2(example: dict) -> str:
    """Format a single example into LFM2 ChatML template."""
    user_msg = f"{SYSTEM_PROMPT}\n\nText: {example['input_text']}"
    target = make_target_json(example)
    return (
        f"<|im_start|>user\n{user_msg}<|im_end|>\n"
        f"<|im_start|>assistant\n{target}<|im_end|>"
    )


def format_qwen(example: dict) -> str:
    """Format a single example into Qwen3.5 ChatML template."""
    user_msg = f"{SYSTEM_PROMPT}\n\nText: {example['input_text']}"
    target = make_target_json(example)
    return (
        f"<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n"
        f"<|im_start|>user\n{user_msg}<|im_end|>\n"
        f"<|im_start|>assistant\n{target}<|im_end|>"
    )


def make_cot_target(example: dict) -> str:
    """Build CoT reasoning + JSON target string."""
    reasoning = example.get("reasoning", "")
    target_json = make_target_json(example)
    if reasoning:
        return f"<reasoning>\n{reasoning}\n</reasoning>\n{target_json}"
    return target_json


def format_qwen_cot(example: dict) -> str:
    """Format example with CoT reasoning for Qwen3.5 training."""
    user_msg = f"{SYSTEM_PROMPT_COT}\n\nText: {example['input_text']}"
    target = make_cot_target(example)
    return (
        f"<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n"
        f"<|im_start|>user\n{user_msg}<|im_end|>\n"
        f"<|im_start|>assistant\n{target}<|im_end|>"
    )


def inference_prompt_qwen_cot(input_text: str) -> str:
    """Build Qwen3.5 CoT inference prompt (no target)."""
    user_msg = f"{SYSTEM_PROMPT_COT}\n\nText: {input_text}"
    return (
        f"<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n"
        f"<|im_start|>user\n{user_msg}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )


def extract_reasoning(text: str) -> str | None:
    """Extract reasoning text from model output."""
    match = re.search(r"<reasoning>\s*(.*?)\s*</reasoning>", text, re.DOTALL)
    return match.group(1) if match else None


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


def inference_prompt_qwen(input_text: str) -> str:
    """Build Qwen3.5 inference prompt (no target)."""
    user_msg = f"{SYSTEM_PROMPT}\n\nText: {input_text}"
    return (
        f"<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n"
        f"<|im_start|>user\n{user_msg}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )


def parse_model_output(text: str) -> dict | None:
    """Try to parse JSON from model output. Returns None if invalid."""
    for token in ["<end_of_turn>", "<|im_end|>", "</s>", "<eos>"]:
        text = text.replace(token, "")
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def safe_accuracy(preds: list[dict | None], golds: list[dict]) -> float:
    correct = sum(
        1 for p, g in zip(preds, golds)
        if p is not None and p.get("safe") == g["safe"]
    )
    return correct / len(golds) if golds else 0.0


def severity_accuracy(preds: list[dict | None], golds: list[dict]) -> float:
    correct = sum(
        1 for p, g in zip(preds, golds)
        if p is not None and p.get("severity") == g["severity"]
    )
    return correct / len(golds) if golds else 0.0


def severity_within_one(preds: list[dict | None], golds: list[dict]) -> float:
    correct = 0
    for p, g in zip(preds, golds):
        if p is None:
            continue
        p_ord = SEVERITY_ORDER.get(p.get("severity"), -1)
        g_ord = SEVERITY_ORDER.get(g.get("severity"), -1)
        if p_ord >= 0 and g_ord >= 0 and abs(p_ord - g_ord) <= 1:
            correct += 1
    return correct / len(golds) if golds else 0.0


def multilabel_f1(preds: list[dict | None], golds: list[dict], key: str) -> float:
    tp = fp = fn = 0
    for p, g in zip(preds, golds):
        if p is None:
            fn += len(set(g[key]))
            continue
        pred_set = set(p.get(key, []))
        gold_set = set(g[key])
        tp += len(pred_set & gold_set)
        fp += len(pred_set - gold_set)
        fn += len(gold_set - pred_set)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0


def valid_json_rate(outputs: list[dict | None]) -> float:
    valid = sum(1 for o in outputs if o is not None)
    return valid / len(outputs) if outputs else 0.0


def compute_all_metrics(
    parsed_preds: list[dict],
    golds: list[dict],
    raw_outputs: list[dict | None],
) -> dict:
    return {
        "valid_json_rate": valid_json_rate(raw_outputs),
        "safe_accuracy": safe_accuracy(parsed_preds, golds),
        "severity_accuracy": severity_accuracy(parsed_preds, golds),
        "severity_within_1": severity_within_one(parsed_preds, golds),
        "principle_f1": multilabel_f1(parsed_preds, golds, "triggered_principles"),
        "risk_label_f1": multilabel_f1(parsed_preds, golds, "risk_labels"),
    }


def print_comparison(gemma_metrics: dict, lfm2_metrics: dict) -> None:
    print(f"{'Metric':<25} {'Gemma 270M':>14} {'LFM2 350M':>14}")
    print("-" * 55)
    for key in gemma_metrics:
        g = gemma_metrics[key]
        l = lfm2_metrics[key]
        print(f"{key:<25} {g:>13.1%} {l:>13.1%}")
