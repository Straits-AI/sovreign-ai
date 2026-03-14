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
