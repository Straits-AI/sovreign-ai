"""Validate generated contrastive pairs against DatasetExample schema.

Checks:
1. Pydantic schema validation (all fields valid)
2. Pair integrity (each pair_id has exactly 2 examples with different verdicts)
3. Reasoning field quality (non-empty, under 100 tokens)
4. Distribution stats (category, language, severity)

Usage:
    python scripts/validate_contrastive.py data/cot/contrastive_pairs.jsonl
    python scripts/validate_contrastive.py data/cot/contrastive_pairs.jsonl --fix-output data/cot/contrastive_pairs_clean.jsonl
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from sovreign.schema import DatasetExample


def load_jsonl(path: str) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def validate_schema(example: dict) -> tuple[bool, str]:
    """Validate against DatasetExample, ignoring extra fields."""
    schema_fields = {
        "input_text", "language", "safe", "severity",
        "triggered_principles", "risk_labels", "reason",
        "rewrite_required", "suggested_rewrite",
    }
    try:
        schema_data = {k: v for k, v in example.items() if k in schema_fields}
        DatasetExample(**schema_data)
        return True, ""
    except Exception as e:
        return False, str(e)


def validate_reasoning(example: dict) -> tuple[bool, str]:
    """Check reasoning field quality."""
    reasoning = example.get("reasoning", "")
    if not reasoning or not reasoning.strip():
        return False, "empty reasoning"
    words = reasoning.split()
    if len(words) > 120:
        return False, f"reasoning too long ({len(words)} words, max 120)"
    if len(words) < 5:
        return False, f"reasoning too short ({len(words)} words, min 5)"
    return True, ""


def validate_pairs(examples: list[dict]) -> list[str]:
    """Check pair integrity."""
    issues = []
    pairs = defaultdict(list)
    for ex in examples:
        pair_id = ex.get("contrastive_pair_id", "")
        if not pair_id:
            continue
        # Extract base pair ID (remove -safe/-unsafe/-s1/-s2 suffix)
        base_id = pair_id.rsplit("-", 1)[0]
        pairs[base_id].append(ex)

    for base_id, pair_exs in pairs.items():
        if len(pair_exs) != 2:
            issues.append(f"Pair {base_id}: expected 2 examples, got {len(pair_exs)}")
            continue

        # Check that verdicts differ (for non-sarcasm pairs)
        safe_vals = [ex["safe"] for ex in pair_exs]
        sev_vals = [ex["severity"] for ex in pair_exs]

        # For sarcasm, both should be unsafe but different severity
        if pair_exs[0].get("edge_case_type") == "sarcasm":
            if any(ex["safe"] for ex in pair_exs):
                issues.append(f"Pair {base_id}: sarcasm pair has safe=True example")
            if sev_vals[0] == sev_vals[1]:
                issues.append(f"Pair {base_id}: sarcasm pair has same severity")
        else:
            if safe_vals[0] == safe_vals[1]:
                issues.append(f"Pair {base_id}: both examples have same safe value")

    return issues


def main():
    parser = argparse.ArgumentParser(description="Validate contrastive pairs")
    parser.add_argument("input", type=str, help="Input JSONL file")
    parser.add_argument("--fix-output", type=str, default="",
                        help="Save valid examples to this file")
    args = parser.parse_args()

    examples = load_jsonl(args.input)
    print(f"Loaded {len(examples)} examples from {args.input}")

    # Schema validation
    schema_valid = []
    schema_invalid = []
    for i, ex in enumerate(examples):
        ok, err = validate_schema(ex)
        if ok:
            schema_valid.append(ex)
        else:
            schema_invalid.append((i, ex, err))

    # Reasoning validation
    reasoning_issues = []
    for i, ex in enumerate(examples):
        ok, err = validate_reasoning(ex)
        if not ok:
            reasoning_issues.append((i, err))

    # Pair integrity
    pair_issues = validate_pairs(examples)

    # Distribution stats
    cat_counts = Counter(ex.get("edge_case_type", "unknown") for ex in schema_valid)
    lang_counts = Counter(ex.get("language", "unknown") for ex in schema_valid)
    sev_counts = Counter(ex.get("severity", "unknown") for ex in schema_valid)
    safe_counts = Counter("safe" if ex.get("safe") else "unsafe" for ex in schema_valid)

    # Report
    print(f"\n{'='*60}")
    print("VALIDATION REPORT")
    print(f"{'='*60}")

    print(f"\nSchema validation: {len(schema_valid)}/{len(examples)} passed")
    if schema_invalid:
        print(f"\n  Failed examples ({len(schema_invalid)}):")
        for i, ex, err in schema_invalid[:10]:
            print(f"    #{i}: {err[:100]}")
        if len(schema_invalid) > 10:
            print(f"    ... and {len(schema_invalid) - 10} more")

    print(f"\nReasoning quality: {len(examples) - len(reasoning_issues)}/{len(examples)} passed")
    if reasoning_issues:
        print(f"\n  Issues ({len(reasoning_issues)}):")
        for i, err in reasoning_issues[:5]:
            print(f"    #{i}: {err}")

    print(f"\nPair integrity: {len(pair_issues)} issues")
    for issue in pair_issues[:5]:
        print(f"  {issue}")

    print(f"\n{'='*60}")
    print("DISTRIBUTION")
    print(f"{'='*60}")

    print(f"\nBy category:")
    for cat, count in cat_counts.most_common():
        print(f"  {cat}: {count}")

    print(f"\nBy language:")
    for lang, count in lang_counts.most_common():
        print(f"  {lang}: {count}")

    print(f"\nBy severity:")
    for sev, count in sorted(sev_counts.items()):
        print(f"  {sev}: {count}")

    print(f"\nBy verdict:")
    for verdict, count in safe_counts.most_common():
        print(f"  {verdict}: {count}")

    # Save clean output
    if args.fix_output:
        valid_indices = set(range(len(examples))) - {i for i, _, _ in schema_invalid}
        clean = [examples[i] for i in sorted(valid_indices)]
        Path(args.fix_output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.fix_output, "w") as f:
            for ex in clean:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")
        print(f"\nSaved {len(clean)} valid examples to {args.fix_output}")

    # Exit code
    total_issues = len(schema_invalid) + len(pair_issues)
    if total_issues > 0:
        print(f"\n{total_issues} total issues found.")
        return 1
    print("\nAll validations passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
