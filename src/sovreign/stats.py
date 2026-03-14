"""Compute and report dataset statistics."""
from __future__ import annotations

from collections import Counter
from sovreign.schema import DatasetExample
from sovreign.constants import TARGET_COUNTS, LANGUAGE_MIX


def compute_stats(examples: list[DatasetExample]) -> dict:
    severity_counter = Counter(ex.severity for ex in examples)
    language_counter = Counter(ex.language for ex in examples)
    principle_counter: Counter = Counter()
    risk_counter: Counter = Counter()
    rewrite_required = 0
    rewrite_provided = 0

    for ex in examples:
        for p in ex.triggered_principles:
            principle_counter[p] += 1
        for r in ex.risk_labels:
            risk_counter[r] += 1
        if ex.rewrite_required:
            rewrite_required += 1
            if ex.suggested_rewrite.strip():
                rewrite_provided += 1

    return {
        "total": len(examples),
        "severity": dict(severity_counter),
        "language": dict(language_counter),
        "principles": dict(principle_counter),
        "risk_labels": dict(risk_counter),
        "rewrite_required": rewrite_required,
        "rewrite_provided": rewrite_provided,
    }


def print_stats(stats: dict) -> str:
    lines = ["=== Dataset Statistics ===", f"Total examples: {stats['total']}", ""]

    lines.append("Severity distribution:")
    for sev in ["S0", "S1", "S2", "S3"]:
        count = stats["severity"].get(sev, 0)
        target = TARGET_COUNTS.get(sev, 0)
        pct = (count / stats["total"] * 100) if stats["total"] else 0
        check = "✓" if count >= target else f"need {target - count} more"
        lines.append(f"  {sev}: {count} ({pct:.1f}%)  target: {target} {check}")

    lines.append("")
    lines.append("Language distribution:")
    for lang in ["ms", "en", "zh", "ta", "mixed"]:
        count = stats["language"].get(lang, 0)
        pct = (count / stats["total"] * 100) if stats["total"] else 0
        target_pct = LANGUAGE_MIX.get(lang, 0) * 100
        lines.append(f"  {lang}: {count} ({pct:.1f}%)  target: {target_pct:.0f}%")

    lines.append("")
    lines.append("Principle trigger frequency:")
    for p, c in sorted(stats["principles"].items()):
        lines.append(f"  {p}: {c}")

    lines.append("")
    lines.append("Risk label frequency:")
    for r, c in sorted(stats["risk_labels"].items()):
        lines.append(f"  {r}: {c}")

    lines.append("")
    lines.append(f"Rewrites required: {stats['rewrite_required']}")
    lines.append(f"Rewrites provided: {stats['rewrite_provided']}")

    return "\n".join(lines)
