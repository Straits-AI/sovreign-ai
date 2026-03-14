# Malaysia-Flavoured Moderation & Rewrite Model — Synthetic Dataset Design

**Date:** 2026-03-01
**Status:** Approved

## Goal

Build a synthetic dataset of 7,000 examples to train a small model (Gemma 3 270M or LFM 350M) to:
1. Classify text as safe or risky
2. Assign severity (S0–S3)
3. Identify triggered Malaysia principles (MY-1 through MY-8)
4. Give a short reason
5. Optionally rewrite into safer wording

NOT: legal analysis, theology, or political interpretation.

## Decisions

| Decision | Choice |
|----------|--------|
| Teacher model | Claude Code (this session) |
| Target model | Gemma 3 270M or LFM 350M |
| Package manager | uv |
| Generation scope | Full 7,000 examples |
| Realism level | Realistic Malaysian language |
| Approach | Parallel Agent Generation + Python Validation Pipeline |

## Architecture

### Project Structure

```
sovreign-ai/
├── pyproject.toml
├── README.md
├── src/sovreign/
│   ├── __init__.py
│   ├── schema.py          # Pydantic models
│   ├── constants.py       # Principles, severities, risk labels, languages
│   ├── validate.py        # Post-generation filtering (9 rules)
│   ├── merge.py           # Merge batch files
│   ├── split.py           # Train/val/test splitter
│   └── stats.py           # Distribution reporting
├── templates/
│   ├── master_prompt.txt  # Master teacher prompt
│   └── seeds.json         # 50 seed scenarios
├── data/
│   ├── batches/           # Raw batch JSONL files
│   ├── merged/            # Post-merge
│   ├── filtered/          # Post-filter
│   └── final/             # Train/val/test splits
└── stress_test/
    └── handwritten.jsonl  # 100-200 stress examples
```

### Pipeline Flow

batches → merge → validate/filter → stats check → split

### Constitution IDs

- MY-1: Preserve harmony across communities
- MY-2: Respect faith and religious sensitivity
- MY-3: Respect constitutional order and lawful process
- MY-4: Uphold dignity, courtesy, and adab
- MY-5: Allow criticism, but not incitement
- MY-6: Protect truth in sensitive public matters
- MY-7: Protect privacy, confidentiality, and personal safety
- MY-8: Prefer constructive, plural, and de-escalatory assistance (rewrite behavior)

### Schema

Pydantic-enforced JSONL with fields: input_text, language, safe, severity, triggered_principles, risk_labels, reason, rewrite_required, suggested_rewrite.

### Validation Rules

1. Reject too generic/robotic text
2. Reject copied structure (Jaccard similarity)
3. Reject safe=true with severity != S0
4. Reject reason contradicting triggered_principles
5. Reject unrealistic slang overload
6. Reject cartoonish extreme hatred
7. Reject rewrite_required=true with empty suggested_rewrite
8. Flag rewrite that still violates same principle
9. Flag political criticism over-labeled as unsafe

### Target Distribution

| Severity | Count |
|----------|-------|
| S0 | 2,000 |
| S1 | 2,000 |
| S2 | 2,000 |
| S3 | 1,000 |

Language: 35% BM, 25% EN, 15% ZH, 10% TA, 15% mixed.

Topics: 25% politics, 20% race/religion, 15% personal conflict, 15% rumors, 10% privacy, 15% neutral civic.

### Splits

- Train: 5,600 (80%)
- Validation: 700 (10%)
- Test: 700 (10%)

Stratified by severity x language.

### Generation Strategy

- Parallel sub-agents generating ~50 examples per batch
- ~140 batches total, run in waves
- Overgenerate ~8,000 to account for ~12-15% filtering loss
- Targeted regeneration for distribution gaps
