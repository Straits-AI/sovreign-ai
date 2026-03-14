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
                    json.loads(line)
                    out.write(line + "\n")
                    count += 1
    return count
