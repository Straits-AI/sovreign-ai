"""Pydantic schema for Malaysia moderation dataset."""
from __future__ import annotations

from pydantic import BaseModel, model_validator
from typing import Literal

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
