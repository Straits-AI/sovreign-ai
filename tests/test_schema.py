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
