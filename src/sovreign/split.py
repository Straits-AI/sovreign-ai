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
        train_set.extend(group[:n_train])
        val_set.extend(group[n_train:n_train + n_val])
        test_set.extend(group[n_train + n_val:])

    return train_set, val_set, test_set
