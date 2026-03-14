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
