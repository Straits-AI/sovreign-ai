"""Assemble final CoT training dataset.

Merges CoT-annotated original data with contrastive pairs into a single
training file. Validates schema, shuffles, and reports stats.

Usage:
    python scripts/assemble_cot_dataset.py

    # Custom paths:
    python scripts/assemble_cot_dataset.py \
        --train-cot data/cot/train_cot.jsonl \
        --contrastive data/cot/contrastive_pairs.jsonl \
        --output data/cot/train_cot_final.jsonl
"""
import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from sovreign.schema import DatasetExample

SCHEMA_FIELDS = {
    "input_text", "language", "safe", "severity",
    "triggered_principles", "risk_labels", "reason",
    "rewrite_required", "suggested_rewrite",
}

EXTRA_FIELDS = {"reasoning", "contrastive_pair_id", "edge_case_type"}


def load_jsonl(path: str) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def validate_example(example: dict) -> tuple[bool, str]:
    """Validate schema fields only."""
    try:
        schema_data = {k: v for k, v in example.items() if k in SCHEMA_FIELDS}
        DatasetExample(**schema_data)
        return True, ""
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description="Assemble final CoT dataset")
    parser.add_argument("--train-cot", type=str, default="data/cot/train_cot.jsonl",
                        help="CoT-annotated training data")
    parser.add_argument("--contrastive", type=str, default="data/cot/contrastive_pairs.jsonl",
                        help="Contrastive pairs data")
    parser.add_argument("--output", type=str, default="data/cot/train_cot_final.jsonl",
                        help="Output path for assembled dataset")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for shuffle")
    args = parser.parse_args()

    # Load data
    train_cot = load_jsonl(args.train_cot)
    print(f"Loaded {len(train_cot)} CoT-annotated training examples")

    contrastive = []
    if Path(args.contrastive).exists():
        contrastive = load_jsonl(args.contrastive)
        print(f"Loaded {len(contrastive)} contrastive pair examples")
    else:
        print(f"No contrastive pairs file at {args.contrastive}, skipping")

    # Merge
    all_examples = train_cot + contrastive
    print(f"\nTotal before validation: {len(all_examples)}")

    # Validate
    valid = []
    invalid = 0
    for ex in all_examples:
        ok, err = validate_example(ex)
        if ok:
            valid.append(ex)
        else:
            invalid += 1

    print(f"Schema validation: {len(valid)} passed, {invalid} rejected")

    # Shuffle
    random.seed(args.seed)
    random.shuffle(valid)

    # Save — keep all fields (schema + extra)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        for ex in valid:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    # Stats
    sev_counts = Counter(ex["severity"] for ex in valid)
    lang_counts = Counter(ex["language"] for ex in valid)
    safe_counts = Counter("safe" if ex["safe"] else "unsafe" for ex in valid)
    has_reasoning = sum(1 for ex in valid if ex.get("reasoning"))
    has_pair_id = sum(1 for ex in valid if ex.get("contrastive_pair_id"))
    cat_counts = Counter(ex.get("edge_case_type", "original") for ex in valid)

    reasoning_lengths = [len(ex.get("reasoning", "").split()) for ex in valid if ex.get("reasoning")]
    avg_reasoning = sum(reasoning_lengths) / len(reasoning_lengths) if reasoning_lengths else 0

    print(f"\n{'='*60}")
    print("FINAL DATASET STATS")
    print(f"{'='*60}")
    print(f"\nTotal examples: {len(valid)}")
    print(f"  Original (with CoT): {len(valid) - has_pair_id}")
    print(f"  Contrastive pairs: {has_pair_id}")
    print(f"  With reasoning: {has_reasoning} ({has_reasoning/len(valid)*100:.0f}%)")
    print(f"  Avg reasoning length: {avg_reasoning:.0f} words")

    print(f"\nBy severity:")
    for sev in ["S0", "S1", "S2", "S3"]:
        print(f"  {sev}: {sev_counts.get(sev, 0)}")

    print(f"\nBy language:")
    for lang, count in lang_counts.most_common():
        print(f"  {lang}: {count}")

    print(f"\nBy verdict: safe={safe_counts.get('safe', 0)}, unsafe={safe_counts.get('unsafe', 0)}")

    print(f"\nBy source:")
    for cat, count in cat_counts.most_common():
        print(f"  {cat}: {count}")

    print(f"\nOutput: {args.output}")


if __name__ == "__main__":
    main()
