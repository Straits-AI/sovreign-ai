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
