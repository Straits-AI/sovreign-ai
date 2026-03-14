# Malaysia Moderation Dataset Pipeline — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Python pipeline and generate 7,000+ synthetic moderation examples for fine-tuning a small Malaysia-aligned judge+rewrite model.

**Architecture:** Python package (`src/sovreign/`) with Pydantic schema validation, post-generation filtering, merge, stats, and stratified splitting. Data generated via parallel Claude Code agents writing JSONL batch files, then processed through the pipeline.

**Tech Stack:** Python 3.12+, uv, Pydantic v2, pytest

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/sovreign/__init__.py`
- Create: all data directories

**Step 1: Initialize uv project**

```bash
cd /Users/sohweimeng/Documents/projects/sovreign-ai
uv init --lib --name sovreign
```

**Step 2: Edit pyproject.toml for dependencies**

Ensure `pyproject.toml` has:
```toml
[project]
name = "sovreign"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Step 3: Create directory structure**

```bash
mkdir -p src/sovreign templates data/{batches,merged,filtered,final} stress_test tests
```

**Step 4: Install dependencies**

```bash
uv sync --all-extras
```

**Step 5: Verify**

```bash
uv run python -c "import sovreign; print('ok')"
```

Expected: `ok`

---

### Task 2: Constants Module

**Files:**
- Create: `src/sovreign/constants.py`

**Step 1: Write constants**

```python
"""Malaysia moderation dataset constants."""

from enum import Enum

PRINCIPLES = {
    "MY-1": "Preserve harmony across communities",
    "MY-2": "Respect faith and religious sensitivity",
    "MY-3": "Respect constitutional order and lawful process",
    "MY-4": "Uphold dignity, courtesy, and adab",
    "MY-5": "Allow criticism, but not incitement",
    "MY-6": "Protect truth in sensitive public matters",
    "MY-7": "Protect privacy, confidentiality, and personal safety",
    "MY-8": "Prefer constructive, plural, and de-escalatory assistance",
}

PRINCIPLE_IDS = list(PRINCIPLES.keys())

SEVERITIES = ["S0", "S1", "S2", "S3"]

LANGUAGES = ["ms", "en", "zh", "ta", "mixed"]

RISK_LABELS = [
    "communal_hostility",
    "religious_provocation",
    "unlawful_incitement",
    "targeted_abuse",
    "revenge_or_vigilantism",
    "dangerous_misinformation",
    "privacy_exposure",
    "inflammatory_polarisation",
    "needs_constructive_rewrite",
]

TOPICS = [
    "politics_public_issues",
    "race_religion_culture",
    "personal_conflict_insults",
    "rumors_misinformation",
    "privacy_doxxing",
    "neutral_civic_safe",
]

# Target distribution
TARGET_COUNTS = {"S0": 2000, "S1": 2000, "S2": 2000, "S3": 1000}

LANGUAGE_MIX = {"ms": 0.35, "en": 0.25, "zh": 0.15, "ta": 0.10, "mixed": 0.15}

TOPIC_MIX = {
    "politics_public_issues": 0.25,
    "race_religion_culture": 0.20,
    "personal_conflict_insults": 0.15,
    "rumors_misinformation": 0.15,
    "privacy_doxxing": 0.10,
    "neutral_civic_safe": 0.15,
}
```

**Step 2: Verify import**

```bash
uv run python -c "from sovreign.constants import PRINCIPLES; print(len(PRINCIPLES))"
```

Expected: `8`

---

### Task 3: Schema Module

**Files:**
- Create: `src/sovreign/schema.py`
- Create: `tests/test_schema.py`

**Step 1: Write test**

```python
"""Tests for schema validation."""
import json
import pytest
from sovreign.schema import DatasetExample


def test_valid_s0_example():
    ex = DatasetExample(
        input_text="Saya tak setuju dengan dasar ni. Kerajaan patut jelaskan data.",
        language="ms",
        safe=True,
        severity="S0",
        triggered_principles=[],
        risk_labels=[],
        reason="Lawful policy criticism without abuse.",
        rewrite_required=False,
        suggested_rewrite="",
    )
    assert ex.safe is True
    assert ex.severity == "S0"


def test_valid_s2_example():
    ex = DatasetExample(
        input_text="Orang macam tu memang rosakkan negara.",
        language="ms",
        safe=False,
        severity="S2",
        triggered_principles=["MY-1", "MY-5"],
        risk_labels=["communal_hostility", "inflammatory_polarisation"],
        reason="Hostile language toward a group.",
        rewrite_required=True,
        suggested_rewrite="Saya bimbang tentang kesan isu ini.",
    )
    assert ex.safe is False
    assert "MY-1" in ex.triggered_principles


def test_safe_must_be_s0():
    with pytest.raises(ValueError):
        DatasetExample(
            input_text="Some text here that is long enough.",
            language="en",
            safe=True,
            severity="S2",
            triggered_principles=[],
            risk_labels=[],
            reason="Test",
            rewrite_required=False,
            suggested_rewrite="",
        )


def test_unsafe_cannot_be_s0():
    with pytest.raises(ValueError):
        DatasetExample(
            input_text="Some text here that is long enough.",
            language="en",
            safe=False,
            severity="S0",
            triggered_principles=["MY-1"],
            risk_labels=["communal_hostility"],
            reason="Test",
            rewrite_required=False,
            suggested_rewrite="",
        )


def test_rewrite_required_needs_content():
    with pytest.raises(ValueError):
        DatasetExample(
            input_text="Some text here that is long enough.",
            language="en",
            safe=False,
            severity="S2",
            triggered_principles=["MY-1"],
            risk_labels=["communal_hostility"],
            reason="Test",
            rewrite_required=True,
            suggested_rewrite="",
        )


def test_invalid_language():
    with pytest.raises(ValueError):
        DatasetExample(
            input_text="Some text here that is long enough.",
            language="jp",
            safe=True,
            severity="S0",
            triggered_principles=[],
            risk_labels=[],
            reason="Test",
            rewrite_required=False,
            suggested_rewrite="",
        )


def test_invalid_principle():
    with pytest.raises(ValueError):
        DatasetExample(
            input_text="Some text here that is long enough.",
            language="en",
            safe=False,
            severity="S2",
            triggered_principles=["MY-99"],
            risk_labels=["communal_hostility"],
            reason="Test",
            rewrite_required=False,
            suggested_rewrite="",
        )


def test_json_roundtrip():
    ex = DatasetExample(
        input_text="Test message for roundtrip.",
        language="en",
        safe=True,
        severity="S0",
        triggered_principles=[],
        risk_labels=[],
        reason="Safe.",
        rewrite_required=False,
        suggested_rewrite="",
    )
    json_str = ex.model_dump_json()
    parsed = DatasetExample.model_validate_json(json_str)
    assert parsed == ex
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_schema.py -v
```

Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write schema implementation**

```python
"""Pydantic schema for Malaysia moderation dataset."""
from __future__ import annotations

from pydantic import BaseModel, model_validator
from typing import Literal

from sovreign.constants import PRINCIPLE_IDS, RISK_LABELS

PrincipleID = Literal["MY-1", "MY-2", "MY-3", "MY-4", "MY-5", "MY-6", "MY-7", "MY-8"]
Language = Literal["ms", "en", "zh", "ta", "mixed"]
Severity = Literal["S0", "S1", "S2", "S3"]
RiskLabel = Literal[
    "communal_hostility",
    "religious_provocation",
    "unlawful_incitement",
    "targeted_abuse",
    "revenge_or_vigilantism",
    "dangerous_misinformation",
    "privacy_exposure",
    "inflammatory_polarisation",
    "needs_constructive_rewrite",
]


class DatasetExample(BaseModel):
    input_text: str
    language: Language
    safe: bool
    severity: Severity
    triggered_principles: list[PrincipleID]
    risk_labels: list[RiskLabel]
    reason: str
    rewrite_required: bool
    suggested_rewrite: str

    @model_validator(mode="after")
    def check_consistency(self) -> DatasetExample:
        if self.safe and self.severity != "S0":
            raise ValueError("safe=True requires severity=S0")
        if not self.safe and self.severity == "S0":
            raise ValueError("safe=False cannot have severity=S0")
        if self.rewrite_required and not self.suggested_rewrite.strip():
            raise ValueError("rewrite_required=True needs non-empty suggested_rewrite")
        if self.safe and (self.triggered_principles or self.risk_labels):
            raise ValueError("safe=True should have empty triggered_principles and risk_labels")
        if len(self.input_text) < 10:
            raise ValueError("input_text too short (min 10 chars)")
        return self
```

**Step 4: Run tests**

```bash
uv run pytest tests/test_schema.py -v
```

Expected: all PASS

---

### Task 4: Validation Module

**Files:**
- Create: `src/sovreign/validate.py`
- Create: `tests/test_validate.py`

**Step 1: Write tests**

```python
"""Tests for post-generation validation/filtering."""
import pytest
from sovreign.schema import DatasetExample
from sovreign.validate import validate_batch, ValidationResult


def _make_example(**overrides) -> dict:
    base = {
        "input_text": "Saya tak setuju dengan dasar pengangkutan awam ini.",
        "language": "ms",
        "safe": True,
        "severity": "S0",
        "triggered_principles": [],
        "risk_labels": [],
        "reason": "Lawful policy criticism without abuse or hostility.",
        "rewrite_required": False,
        "suggested_rewrite": "",
    }
    base.update(overrides)
    return base


def test_valid_batch_passes():
    batch = [_make_example(input_text=f"Unique message number {i} about policy.") for i in range(5)]
    result = validate_batch(batch)
    assert len(result.accepted) == 5
    assert len(result.rejected) == 0


def test_rejects_duplicate_structure():
    batch = [_make_example() for _ in range(5)]  # all identical
    result = validate_batch(batch)
    assert len(result.rejected) > 0


def test_rejects_short_robotic_text():
    batch = [_make_example(input_text="Bad.")]  # too short
    result = validate_batch(batch)
    assert len(result.rejected) == 1


def test_rejects_missing_rewrite():
    batch = [_make_example(
        input_text="This group is destroying everything in this country lah.",
        safe=False,
        severity="S2",
        triggered_principles=["MY-1"],
        risk_labels=["communal_hostility"],
        reason="Hostile generalization.",
        rewrite_required=True,
        suggested_rewrite="",
    )]
    result = validate_batch(batch)
    assert len(result.rejected) == 1


def test_flags_political_criticism_overlabeled():
    batch = [_make_example(
        input_text="The government should be more transparent about how they spend taxpayer money.",
        safe=False,
        severity="S1",
        triggered_principles=["MY-5"],
        risk_labels=["inflammatory_polarisation"],
        reason="Critical of government.",
        rewrite_required=True,
        suggested_rewrite="The government should be transparent.",
    )]
    result = validate_batch(batch)
    assert len(result.flagged) > 0
```

**Step 2: Run to verify failure**

```bash
uv run pytest tests/test_validate.py -v
```

**Step 3: Write validation implementation**

```python
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
    # Political criticism without hostile labels but marked unsafe — flag it
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
```

**Step 4: Run tests**

```bash
uv run pytest tests/test_validate.py -v
```

Expected: all PASS

---

### Task 5: Merge Module

**Files:**
- Create: `src/sovreign/merge.py`
- Create: `tests/test_merge.py`

**Step 1: Write test**

```python
"""Tests for batch merging."""
import json
import tempfile
from pathlib import Path
from sovreign.merge import merge_batches


def _write_batch(path: Path, examples: list[dict]):
    with open(path, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")


def test_merge_multiple_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        batch_dir = Path(tmpdir) / "batches"
        batch_dir.mkdir()
        out_path = Path(tmpdir) / "merged.jsonl"

        ex1 = {"input_text": "Message one about policy reform.", "language": "ms", "safe": True, "severity": "S0",
               "triggered_principles": [], "risk_labels": [], "reason": "Safe.", "rewrite_required": False, "suggested_rewrite": ""}
        ex2 = {"input_text": "Message two about different topic.", "language": "en", "safe": True, "severity": "S0",
               "triggered_principles": [], "risk_labels": [], "reason": "Safe.", "rewrite_required": False, "suggested_rewrite": ""}

        _write_batch(batch_dir / "batch_001.jsonl", [ex1])
        _write_batch(batch_dir / "batch_002.jsonl", [ex2])

        count = merge_batches(batch_dir, out_path)
        assert count == 2

        with open(out_path) as f:
            lines = f.readlines()
        assert len(lines) == 2
```

**Step 2: Write implementation**

```python
"""Merge batch JSONL files into a single dataset."""
from __future__ import annotations

import json
from pathlib import Path


def merge_batches(batch_dir: Path, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(output_path, "w") as out:
        for batch_file in sorted(batch_dir.glob("*.jsonl")):
            with open(batch_file) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    # Validate it's valid JSON
                    json.loads(line)
                    out.write(line + "\n")
                    count += 1
    return count
```

**Step 3: Run tests**

```bash
uv run pytest tests/test_merge.py -v
```

---

### Task 6: Stats Module

**Files:**
- Create: `src/sovreign/stats.py`
- Create: `tests/test_stats.py`

**Step 1: Write test**

```python
"""Tests for stats reporting."""
from sovreign.schema import DatasetExample
from sovreign.stats import compute_stats


def _make(severity="S0", language="ms", safe=True, principles=None, risk_labels=None):
    return DatasetExample(
        input_text=f"Test message in {language} with severity {severity} unique.",
        language=language,
        safe=safe,
        severity=severity,
        triggered_principles=principles or [],
        risk_labels=risk_labels or [],
        reason="Test reason.",
        rewrite_required=not safe,
        suggested_rewrite="" if safe else "Rewritten version of the message.",
    )


def test_severity_counts():
    examples = [_make("S0"), _make("S0"), _make("S1", safe=False, principles=["MY-4"], risk_labels=["targeted_abuse"])]
    stats = compute_stats(examples)
    assert stats["severity"]["S0"] == 2
    assert stats["severity"]["S1"] == 1


def test_language_counts():
    examples = [_make(language="ms"), _make(language="en"), _make(language="ms")]
    stats = compute_stats(examples)
    assert stats["language"]["ms"] == 2
    assert stats["language"]["en"] == 1


def test_principle_frequency():
    examples = [
        _make("S2", safe=False, language="en", principles=["MY-1", "MY-2"], risk_labels=["communal_hostility"]),
        _make("S2", safe=False, language="ms", principles=["MY-1"], risk_labels=["communal_hostility"]),
    ]
    stats = compute_stats(examples)
    assert stats["principles"]["MY-1"] == 2
    assert stats["principles"]["MY-2"] == 1
```

**Step 2: Write implementation**

```python
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
    lines = [f"=== Dataset Statistics ===", f"Total examples: {stats['total']}", ""]

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

    report = "\n".join(lines)
    return report
```

**Step 3: Run tests**

```bash
uv run pytest tests/test_stats.py -v
```

---

### Task 7: Split Module

**Files:**
- Create: `src/sovreign/split.py`
- Create: `tests/test_split.py`

**Step 1: Write test**

```python
"""Tests for stratified dataset splitting."""
from sovreign.schema import DatasetExample
from sovreign.split import stratified_split


def _make(severity="S0", language="ms", safe=True, principles=None, risk_labels=None, idx=0):
    return DatasetExample(
        input_text=f"Unique test message number {idx} in {language}.",
        language=language,
        safe=safe,
        severity=severity,
        triggered_principles=principles or [],
        risk_labels=risk_labels or [],
        reason="Test.",
        rewrite_required=not safe,
        suggested_rewrite="" if safe else "Safe rewrite of the message.",
    )


def test_split_sizes():
    examples = [_make(idx=i) for i in range(100)]
    train, val, test = stratified_split(examples, train=0.8, val=0.1, test=0.1, seed=42)
    assert len(train) == 80
    assert len(val) == 10
    assert len(test) == 10


def test_no_overlap():
    examples = [_make(idx=i) for i in range(100)]
    train, val, test = stratified_split(examples, train=0.8, val=0.1, test=0.1, seed=42)
    train_texts = {e.input_text for e in train}
    val_texts = {e.input_text for e in val}
    test_texts = {e.input_text for e in test}
    assert not (train_texts & val_texts)
    assert not (train_texts & test_texts)
    assert not (val_texts & test_texts)


def test_deterministic():
    examples = [_make(idx=i) for i in range(100)]
    t1, v1, te1 = stratified_split(examples, train=0.8, val=0.1, test=0.1, seed=42)
    t2, v2, te2 = stratified_split(examples, train=0.8, val=0.1, test=0.1, seed=42)
    assert [e.input_text for e in t1] == [e.input_text for e in t2]
```

**Step 2: Write implementation**

```python
"""Stratified train/val/test splitting."""
from __future__ import annotations

import random
from collections import defaultdict
from sovreign.schema import DatasetExample


def stratified_split(
    examples: list[DatasetExample],
    train: float = 0.8,
    val: float = 0.1,
    test: float = 0.1,
    seed: int = 42,
) -> tuple[list[DatasetExample], list[DatasetExample], list[DatasetExample]]:
    rng = random.Random(seed)

    # Group by severity x language
    groups: dict[str, list[DatasetExample]] = defaultdict(list)
    for ex in examples:
        key = f"{ex.severity}_{ex.language}"
        groups[key].append(ex)

    train_set: list[DatasetExample] = []
    val_set: list[DatasetExample] = []
    test_set: list[DatasetExample] = []

    for key in sorted(groups.keys()):
        group = groups[key]
        rng.shuffle(group)
        n = len(group)
        n_train = round(n * train)
        n_val = round(n * val)
        # Rest goes to test
        train_set.extend(group[:n_train])
        val_set.extend(group[n_train:n_train + n_val])
        test_set.extend(group[n_train + n_val:])

    return train_set, val_set, test_set
```

**Step 3: Run tests**

```bash
uv run pytest tests/test_split.py -v
```

---

### Task 8: Templates and Seeds

**Files:**
- Create: `templates/master_prompt.txt`
- Create: `templates/seeds.json`

**Step 1: Write master prompt**

Save the master teacher prompt from the spec (Section 8) to `templates/master_prompt.txt`.

**Step 2: Write seeds**

Save all 50 seed scenarios as a structured JSON file:

```json
{
  "seeds": [
    {"id": 1, "severity": "S0", "topic": "politics_public_issues", "description": "Criticize a transport policy without insulting any group"},
    {"id": 2, "severity": "S0", "topic": "politics_public_issues", "description": "Complain about rising prices respectfully"},
    ...all 50 seeds...
  ]
}
```

Each seed includes: id, target severity, topic category, and description text.

---

### Task 9: Generate Dataset — Parallel Agent Dispatch

This is the main generation task. Use parallel Claude Code agents to generate examples in batches.

**Strategy:**
- Dispatch agents in waves of up to 10 concurrent agents
- Each agent generates 25 examples for a specific (severity, language, topic) slice
- Each agent writes its output to `data/batches/batch_NNN.jsonl`
- Total waves needed: ~14 waves of 10 agents = ~140 batches → ~8,000+ raw examples

**Per-agent prompt template:**

Each agent receives:
1. The master teacher prompt with Malaysia principles
2. A specific severity, language, topic, and count assignment
3. Instructions to write strict JSONL to a specific batch file path
4. The seed scenarios relevant to that slice
5. Instructions for variety (different styles, lengths, platforms)

**Wave execution order:**
1. Waves 1-4: S0 examples (2,300 target, ~40 batches)
2. Waves 5-8: S1 examples (2,300 target, ~40 batches)
3. Waves 9-12: S2 examples (2,300 target, ~40 batches)
4. Waves 13-14: S3 examples (1,150 target, ~20 batches)

After each wave group, run merge + stats to check progress.

---

### Task 10: Post-Processing Pipeline

**After all batches are generated:**

**Step 1: Merge all batches**

```bash
uv run python -c "
from pathlib import Path
from sovreign.merge import merge_batches
count = merge_batches(Path('data/batches'), Path('data/merged/all.jsonl'))
print(f'Merged {count} examples')
"
```

**Step 2: Validate and filter**

```bash
uv run python -c "
import json
from pathlib import Path
from sovreign.validate import validate_batch

with open('data/merged/all.jsonl') as f:
    raw = [json.loads(line) for line in f if line.strip()]

result = validate_batch(raw)
print(f'Accepted: {len(result.accepted)}')
print(f'Rejected: {len(result.rejected)}')
print(f'Flagged: {len(result.flagged)}')

with open('data/filtered/clean.jsonl', 'w') as f:
    for ex in result.accepted:
        f.write(ex.model_dump_json() + '\n')
"
```

**Step 3: Check stats**

```bash
uv run python -c "
import json
from pathlib import Path
from sovreign.schema import DatasetExample
from sovreign.stats import compute_stats, print_stats

with open('data/filtered/clean.jsonl') as f:
    examples = [DatasetExample.model_validate_json(line) for line in f if line.strip()]

stats = compute_stats(examples)
print(print_stats(stats))
"
```

**Step 4: If distribution gaps exist, do targeted regeneration for weak slices**

**Step 5: Split**

```bash
uv run python -c "
import json
from pathlib import Path
from sovreign.schema import DatasetExample
from sovreign.split import stratified_split

with open('data/filtered/clean.jsonl') as f:
    examples = [DatasetExample.model_validate_json(line) for line in f if line.strip()]

train, val, test = stratified_split(examples)

for name, data in [('train', train), ('validation', val), ('test', test)]:
    path = Path(f'data/final/{name}.jsonl')
    with open(path, 'w') as f:
        for ex in data:
            f.write(ex.model_dump_json() + '\n')
    print(f'{name}: {len(data)} examples')
"
```

---

### Task 11: Stress Test Set

**Files:**
- Create: `stress_test/handwritten.jsonl`

Generate 100-200 handwritten edge-case examples covering:
- Code-switching (BM-EN, BM-ZH mixes)
- Sarcasm and satire
- Quoted offensive speech from news
- Communal euphemisms
- Political complaints that MUST NOT be flagged
- Religious edge cases
- Forwarded-message style rumors

These are generated with extra care for ambiguity and used to evaluate the fine-tuned model.

---

### Task 12: README

**Files:**
- Create: `README.md`

Document:
- Project purpose
- Setup instructions (`uv sync`)
- Pipeline usage (merge → validate → stats → split)
- Dataset schema
- Constitution principles (MY-1 through MY-8)
- Target distributions
