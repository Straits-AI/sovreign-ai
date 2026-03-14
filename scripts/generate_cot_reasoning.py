"""Generate chain-of-thought reasoning for existing training/validation data.

Uses template-based rules to construct reasoning from each example's existing
fields (reason, severity, principles, risk_labels). The reasoning explains
HOW a moderation judge should arrive at the verdict.

Usage:
    # Preview 5 examples:
    python scripts/generate_cot_reasoning.py --dry-run --count 5

    # Generate for all training data:
    python scripts/generate_cot_reasoning.py --input data/final/train.jsonl --output data/cot/train_cot.jsonl

    # Generate for validation data:
    python scripts/generate_cot_reasoning.py --input data/final/validation.jsonl --output data/cot/validation_cot.jsonl
"""
import argparse
import json
import random
from pathlib import Path

random.seed(42)

PRINCIPLES = {
    "MY-1": "preserving harmony across communities",
    "MY-2": "respecting faith and religious sensitivity",
    "MY-3": "respecting constitutional order and lawful process",
    "MY-4": "upholding dignity, courtesy, and adab",
    "MY-5": "allowing criticism but not incitement",
    "MY-6": "protecting truth in sensitive public matters",
    "MY-7": "protecting privacy, confidentiality, and personal safety",
    "MY-8": "preferring constructive and de-escalatory assistance",
}

RISK_LABEL_DESCRIPTIONS = {
    "communal_hostility": "inter-ethnic or inter-community hostility",
    "religious_provocation": "targeting religious beliefs or practices",
    "unlawful_incitement": "inciting illegal activity",
    "targeted_abuse": "directed harassment at individuals or groups",
    "revenge_or_vigilantism": "calls for vigilante justice",
    "dangerous_misinformation": "false claims that could cause harm",
    "privacy_exposure": "exposing private information",
    "inflammatory_polarisation": "content designed to divide communities",
    "needs_constructive_rewrite": "content that should be reframed constructively",
}

# ═══════════════════════════════════════════════════════════════
# REASONING TEMPLATES by severity
# ═══════════════════════════════════════════════════════════════

S0_TEMPLATES = [
    "This text expresses {topic_hint} without triggering any moderation principles. The tone is {tone} and the speaker's intent is {intent}. No intervention needed.",
    "The speaker {intent_verb} in a {tone} manner. No principles are violated — the content is {content_type}. Safe for all audiences.",
    "This is {content_type} content. The speaker's purpose is {intent} and the language used is {tone}. No moderation concern.",
]

S1_TEMPLATES = [
    "The speaker {intent_verb}, which {why_flagged}. This triggers {principle_text} ({label_text}). While not severely harmful, the {tone} framing warrants a constructive rewrite.",
    "This text {why_flagged}. The {tone} tone edges into {label_text} territory, triggering {principle_text}. S1 because the concern is mild but present.",
    "Although the speaker may have legitimate intent, the {tone} language {why_flagged}. This mildly violates {principle_text}, warranting S1.",
]

S2_TEMPLATES = [
    "This text {why_flagged}, constituting {label_text}. It violates {principle_text}. The {tone} framing makes this significantly harmful — S2 severity.",
    "The speaker {intent_verb} in a way that {why_flagged}. This is {label_text}, violating {principle_text}. The content poses significant harm.",
    "This constitutes {label_text} — the text {why_flagged}. Multiple principles are at stake: {principle_text}. S2 due to significant potential for harm.",
]

S3_TEMPLATES = [
    "This text {why_flagged}, representing severe {label_text}. It directly violates {principle_text}. The content poses immediate danger and warrants S3.",
    "Severe content: the speaker {intent_verb}, which {why_flagged}. This is {label_text} at the most dangerous level, violating {principle_text}.",
    "This is {label_text} at S3 severity — the text {why_flagged}. It violates {principle_text} and poses direct, immediate harm.",
]

# ═══════════════════════════════════════════════════════════════
# CONTEXT VOCABULARY for filling templates
# ═══════════════════════════════════════════════════════════════

SAFE_TONES = ["respectful", "neutral", "constructive", "warm", "measured", "thoughtful", "balanced"]
SAFE_INTENTS = [
    "sharing a personal experience", "expressing an opinion constructively",
    "providing factual information", "celebrating cultural diversity",
    "making a neutral observation", "engaging in civic discourse",
    "appreciating community values", "discussing a topic thoughtfully",
]
SAFE_INTENT_VERBS = [
    "shares their perspective respectfully", "discusses the topic constructively",
    "expresses their views within acceptable bounds", "provides context or information",
    "engages in normal social interaction", "comments on the topic neutrally",
]
SAFE_CONTENT_TYPES = [
    "normal social discourse", "constructive civic engagement",
    "respectful personal expression", "factual or educational",
    "cultural appreciation", "neutral commentary",
]
SAFE_TOPIC_HINTS = [
    "a personal view", "everyday observations", "cultural or social matters",
    "civic concerns", "community life", "personal experiences",
]

UNSAFE_TONES = {
    "S1": ["mildly inflammatory", "somewhat dismissive", "borderline disrespectful",
           "sarcastic but pointed", "slightly aggressive", "passively hostile"],
    "S2": ["hostile", "inflammatory", "dehumanizing", "deliberately provocative",
           "aggressively dismissive", "contemptuous"],
    "S3": ["extremely hostile", "violently inciting", "dangerously inflammatory",
           "directly threatening", "severely dehumanizing"],
}

UNSAFE_INTENT_VERBS = {
    "S1": [
        "uses mildly inflammatory language", "expresses frustration in a borderline manner",
        "frames criticism with unnecessary hostility", "employs sarcasm that edges into provocation",
    ],
    "S2": [
        "targets a community with harmful generalizations", "spreads content that could incite hostility",
        "uses language that dehumanizes or stereotypes", "amplifies divisive narratives",
    ],
    "S3": [
        "directly incites violence or hatred", "exposes private information maliciously",
        "makes extremely dangerous false claims", "calls for vigilante action",
    ],
}


def load_jsonl(path: str) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def save_jsonl(examples: list[dict], path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")


def get_principle_text(principles: list[str]) -> str:
    """Convert principle IDs to readable text."""
    if not principles:
        return "no specific principles"
    descs = [PRINCIPLES.get(p, p) for p in principles[:3]]
    return ", ".join(descs)


def get_label_text(labels: list[str]) -> str:
    """Convert risk labels to readable text."""
    if not labels:
        return "no specific risk"
    descs = [RISK_LABEL_DESCRIPTIONS.get(l, l) for l in labels[:2]]
    return " and ".join(descs)


def generate_reasoning(example: dict) -> str:
    """Generate CoT reasoning for a single example using templates."""
    severity = example["severity"]
    safe = example["safe"]
    reason = example.get("reason", "")
    principles = example.get("triggered_principles", [])
    labels = example.get("risk_labels", [])

    principle_text = get_principle_text(principles)
    label_text = get_label_text(labels)

    if safe or severity == "S0":
        template = random.choice(S0_TEMPLATES)
        return template.format(
            topic_hint=random.choice(SAFE_TOPIC_HINTS),
            tone=random.choice(SAFE_TONES),
            intent=random.choice(SAFE_INTENTS),
            intent_verb=random.choice(SAFE_INTENT_VERBS),
            content_type=random.choice(SAFE_CONTENT_TYPES),
        )

    # For unsafe examples, derive "why_flagged" from the reason field
    why_flagged = reason.lower().rstrip(".")
    if not why_flagged or len(why_flagged) < 10:
        why_flagged = f"contains {label_text}"

    tone = random.choice(UNSAFE_TONES.get(severity, UNSAFE_TONES["S2"]))
    intent_verb = random.choice(UNSAFE_INTENT_VERBS.get(severity, UNSAFE_INTENT_VERBS["S2"]))

    if severity == "S1":
        template = random.choice(S1_TEMPLATES)
    elif severity == "S2":
        template = random.choice(S2_TEMPLATES)
    else:  # S3
        template = random.choice(S3_TEMPLATES)

    return template.format(
        topic_hint="",
        tone=tone,
        intent_verb=intent_verb,
        why_flagged=why_flagged,
        principle_text=principle_text,
        label_text=label_text,
        content_type="",
    )


def main():
    parser = argparse.ArgumentParser(description="Generate CoT reasoning for training data")
    parser.add_argument("--input", type=str, default="data/final/train.jsonl",
                        help="Input JSONL file")
    parser.add_argument("--output", type=str, default="data/cot/train_cot.jsonl",
                        help="Output JSONL file with reasoning field")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview reasoning without saving")
    parser.add_argument("--count", type=int, default=0,
                        help="Process only N examples (0 = all)")
    args = parser.parse_args()

    examples = load_jsonl(args.input)
    print(f"Loaded {len(examples)} examples from {args.input}")

    if args.count:
        examples = examples[:args.count]

    processed = []
    for i, ex in enumerate(examples):
        reasoning = generate_reasoning(ex)
        processed.append({**ex, "reasoning": reasoning})

        if args.dry_run and i < (args.count or 10):
            print(f"\n{'='*60}")
            print(f"Example {i+1}: safe={ex['safe']}, severity={ex['severity']}")
            print(f"Text: {ex['input_text'][:100]}...")
            print(f"Reason: {ex.get('reason', '')[:100]}")
            print(f"Reasoning: {reasoning}")

        if (i + 1) % 1000 == 0:
            print(f"  [{i+1}/{len(examples)}] processed")

    if not args.dry_run:
        save_jsonl(processed, args.output)

    # Stats
    total = len(processed)
    avg_len = sum(len(p["reasoning"].split()) for p in processed) / total if total else 0
    by_sev = {}
    for p in processed:
        s = p["severity"]
        if s not in by_sev:
            by_sev[s] = []
        by_sev[s].append(len(p["reasoning"].split()))

    print(f"\nDone! {total} examples processed")
    print(f"Average reasoning length: {avg_len:.0f} words")
    for s in ["S0", "S1", "S2", "S3"]:
        if s in by_sev:
            avg = sum(by_sev[s]) / len(by_sev[s])
            print(f"  {s}: {len(by_sev[s])} examples, avg {avg:.0f} words")
    if not args.dry_run:
        print(f"Output saved to {args.output}")


if __name__ == "__main__":
    main()
