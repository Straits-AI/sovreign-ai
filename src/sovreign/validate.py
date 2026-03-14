"""Post-generation validation and filtering."""
from __future__ import annotations

from dataclasses import dataclass, field
from sovreign.schema import DatasetExample


@dataclass
class ValidationResult:
    accepted: list[DatasetExample] = field(default_factory=list)
    rejected: list[tuple[dict, str]] = field(default_factory=list)
    flagged: list[tuple[DatasetExample, str]] = field(default_factory=list)


POLITICAL_KEYWORDS = [
    "kerajaan", "government", "policy", "dasar", "minister", "menteri",
    "parliament", "parlimen", "election", "pilihanraya", "taxpayer",
    "cukai", "budget", "bajet", "corruption", "rasuah",
]


def _jaccard_similarity(a: str, b: str) -> float:
    set_a = set(a.lower().split())
    set_b = set(b.lower().split())
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _is_robotic(text: str) -> bool:
    if len(text) < 10:
        return True
    robotic_markers = [
        "as an ai", "i cannot", "here is an example", "sure, here",
        "certainly!", "of course!", "happy to help",
    ]
    text_lower = text.lower()
    return any(m in text_lower for m in robotic_markers)


def _has_slang_overload(text: str) -> bool:
    slang_particles = ["lah", "lor", "meh", "geh", "wor", "mah", "leh", "bah"]
    words = text.lower().split()
    if not words:
        return False
    count = sum(1 for w in words if w.rstrip(".,!?") in slang_particles)
    return count / len(words) > 0.25


def _is_cartoonish(text: str) -> bool:
    extreme_markers = [
        "kill them all", "bunuh semua", "destroy every", "musnahkan semua",
        "exterminate", "hapuskan bangsa", "genocide",
    ]
    text_lower = text.lower()
    return sum(1 for m in extreme_markers if m in text_lower) >= 2


def _is_political_criticism_overlabeled(example: DatasetExample) -> bool:
    if example.safe:
        return False
    text_lower = example.input_text.lower()
    has_political = any(kw in text_lower for kw in POLITICAL_KEYWORDS)
    if not has_political:
        return False
    hostile_labels = {"communal_hostility", "religious_provocation", "targeted_abuse"}
    has_hostile = bool(set(example.risk_labels) & hostile_labels)
    if has_hostile:
        return False
    return example.severity in ("S1", "S2") and not has_hostile


def validate_batch(raw_examples: list[dict]) -> ValidationResult:
    result = ValidationResult()

    parsed: list[tuple[int, DatasetExample]] = []
    for i, raw in enumerate(raw_examples):
        try:
            ex = DatasetExample.model_validate(raw)
            parsed.append((i, ex))
        except Exception as e:
            result.rejected.append((raw, f"Schema validation failed: {e}"))

    # Check duplicates via Jaccard similarity
    texts = [(i, ex.input_text) for i, ex in parsed]
    duplicate_indices: set[int] = set()
    for a_idx in range(len(texts)):
        for b_idx in range(a_idx + 1, len(texts)):
            if _jaccard_similarity(texts[a_idx][1], texts[b_idx][1]) > 0.85:
                duplicate_indices.add(texts[b_idx][0])

    for i, ex in parsed:
        reasons = []

        if i in duplicate_indices:
            reasons.append("Duplicate/near-duplicate structure")

        if _is_robotic(ex.input_text):
            reasons.append("Robotic/generic text")

        if _has_slang_overload(ex.input_text):
            reasons.append("Unrealistic slang overload")

        if _is_cartoonish(ex.input_text):
            reasons.append("Cartoonish extreme content")

        if reasons:
            result.rejected.append((ex.model_dump(), "; ".join(reasons)))
            continue

        # Flags (not rejections)
        if _is_political_criticism_overlabeled(ex):
            result.flagged.append((ex, "Political criticism may be over-labeled as unsafe"))

        result.accepted.append(ex)

    return result
