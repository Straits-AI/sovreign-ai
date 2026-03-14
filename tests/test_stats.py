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
