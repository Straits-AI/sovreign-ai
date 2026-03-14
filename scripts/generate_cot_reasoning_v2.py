"""Generate content-aware chain-of-thought reasoning (v2).

Unlike v1 (template-based), this version analyzes the actual input text to produce
reasoning that references specific words, phrases, and context signals. No API needed.

Key improvements over v1:
- Detects quoting/reporting patterns and generates reporting-aware reasoning
- Detects sarcasm markers and generates sarcasm-specific reasoning
- References actual words from the text
- Distinguishes endorsement vs condemnation signals
- Produces unique reasoning per example (not fill-in-the-blank)

Usage:
    python scripts/generate_cot_reasoning_v2.py --input data/final/train.jsonl --output data/cot/train_cot.jsonl
    python scripts/generate_cot_reasoning_v2.py --input data/final/validation.jsonl --output data/cot/validation_cot.jsonl
"""
import argparse
import json
import random
import re
from pathlib import Path

random.seed(42)

PRINCIPLES = {
    "MY-1": "preserving harmony across communities",
    "MY-2": "respecting faith and religious sensitivity",
    "MY-3": "respecting constitutional order and lawful process",
    "MY-4": "upholding dignity, courtesy, and adab",
    "MY-5": "allowing criticism but not incitement",
    "MY-6": "protecting truth in sensitive public matters",
    "MY-7": "protecting privacy and personal safety",
    "MY-8": "preferring constructive and de-escalatory assistance",
}

# ═══════════════════════════════════════════════════════════════
# TEXT ANALYSIS FUNCTIONS
# ═══════════════════════════════════════════════════════════════

QUOTING_SIGNALS = [
    "reported", "menurut", "according to", "newspaper", "berita", "surat khabar",
    "bernama", "headline", "tajuk", "overheard", "terdengar", "dengar",
    "told me", "cerita", "he said", "she said", "dia cakap", "orang cakap",
    "laporan", "report", "documented", "investigation", "siasatan",
    "court", "mahkamah", "testimony", "keterangan", "polis", "police",
    "confession", "viral video", "screenshot", "whatsapp", "telegram",
    "forward", "share", "someone posted",
]

CONDEMNATION_SIGNALS = [
    "sad", "sedih", "unacceptable", "tak boleh terima", "condemned",
    "dikecam", "should not", "tak patut", "disgusting", "menjijikkan",
    "need to stop", "kena berhenti", "dangerous", "bahaya", "report",
    "laporkan", "this is wrong", "ini salah", "shameful", "memalukan",
    "ridiculous", "anti-", "call out", "not okay", "tak okay", "kena ubah",
    "we need to", "kita perlu", "respect", "hormati",
]

ENDORSEMENT_SIGNALS = [
    "betul", "right", "correct", "setuju", "agree", "finally",
    "akhirnya", "share kalau", "viral kan", "spread", "sebarkan",
    "memang fakta", "the truth", "kebenaran", "berani", "brave",
    "respect", "tahniah", "well said", "exactly", "tepat sekali",
    "love it", "suka", "everyone knows", "semua tahu", "wake up",
]

SARCASM_MARKERS = [
    "konon", "apparently", "bravo", "lawak", "funny",
    "sure la", "of course", "memang la", "how lucky",
    "world-class", "pandai", "hebat",
    "what a surprise", "tak sangka", "lol", "haha", "😂", "🤣",
    "priorities", "brillian",
]

CODED_ETHNIC_SIGNALS = [
    "orang kita", "orang luar", "mereka", "certain people", "you know who",
    "kaum tertentu", "golongan", "those people", "their kind", "bangsa dia",
    "darah daging", "dna", "budaya mereka", "know your place",
    "tahu tempat", "balik", "keluar", "go back", "pendatang",
]

RELIGIOUS_SIGNALS = [
    "masjid", "surau", "mosque", "gereja", "church", "kuil", "temple",
    "agama", "religion", "islam", "kristian", "hindu", "buddha",
    "halal", "haram", "kafir", "solat", "prayer", "sembahyang",
    "raya", "deepavali", "christmas", "thaipusam", "allah",
    "interfaith", "antara agama", "semua agama",
]

PRO_SOCIAL_SIGNALS = [
    "respect", "hormati", "appreciate", "hargai", "beautiful",
    "indah", "celebrate", "raikan", "together", "bersama",
    "diverse", "pelbagai", "unity", "perpaduan", "contribute",
    "sumbang", "protect", "lindungi", "support", "sokong",
    "all races", "semua kaum", "semua agama", "all faiths",
]

MISINFORMATION_SIGNALS = [
    "viral", "forward", "whatsapp", "telegram", "heard that",
    "dengar kata", "someone said", "orang cakap", "rumor", "khabar angin",
    "urgent", "breaking", "share this", "share sebelum", "confirm",
    "sebarkan", "boikot", "boycott", "beware", "awas", "amaran",
    "warning", "breaking news", "confirmed", "!!!",
]


def count_signals(text: str, signals: list[str]) -> tuple[int, list[str]]:
    """Count how many signal words appear in text, return count and matched words."""
    text_lower = text.lower()
    matched = [s for s in signals if s.lower() in text_lower]
    return len(matched), matched


def extract_quoted_text(text: str) -> list[str]:
    """Extract text within quotes."""
    quotes = re.findall(r"['\"]([^'\"]{3,})['\"]", text)
    quotes += re.findall(r"'([^']{3,})'", text)
    return quotes[:3]  # Max 3


def get_first_n_words(text: str, n: int = 5) -> str:
    """Get first N significant words from text."""
    words = text.split()[:n]
    return " ".join(words)


# ═══════════════════════════════════════════════════════════════
# REASONING GENERATORS by content pattern
# ═══════════════════════════════════════════════════════════════

def generate_quoting_safe_reasoning(text: str, signals: list[str], quoted: list[str], ex: dict) -> str:
    """Reasoning for safe quoting/reporting contexts."""
    quote_text = f"'{quoted[0][:50]}'" if quoted else "offensive language"
    signal_word = signals[0] if signals else "quoting context"

    templates = [
        f"The speaker quotes {quote_text} within a {signal_word} context. Key signals: the framing expresses disapproval rather than endorsement. The slur is mentioned to document or condemn it, not to amplify it.",
        f"This text uses {signal_word} framing to reference {quote_text}. The speaker's intent is to report or critique, as shown by the condemning tone. Quoting harmful language for documentation purposes is safe.",
        f"Despite containing {quote_text}, the {signal_word} framing makes clear the speaker is reporting, not endorsing. The context signals — attribution and factual framing — indicate journalistic or testimonial intent.",
    ]
    return random.choice(templates)


def generate_quoting_unsafe_reasoning(text: str, signals: list[str], ex: dict) -> str:
    """Reasoning for unsafe quoting that endorses."""
    endorse_words = [s for s in ENDORSEMENT_SIGNALS if s.lower() in text.lower()][:2]
    endorse_text = f"'{endorse_words[0]}'" if endorse_words else "agreement signals"

    templates = [
        f"While the text appears to quote offensive language, {endorse_text} signals explicit endorsement. The speaker validates the harmful content rather than condemning it. This transforms quoting into amplification.",
        f"The speaker frames the quoted content approvingly with {endorse_text}. Unlike reporting or testimony, this endorses the harmful language and calls for wider distribution, constituting active amplification.",
    ]
    return random.choice(templates)


def generate_sarcasm_reasoning(text: str, markers: list[str], ex: dict) -> str:
    """Reasoning for sarcastic content."""
    marker_text = f"'{markers[0]}'" if markers else "sarcastic tone"
    severity = ex["severity"]

    if ex["safe"]:
        templates = [
            f"The {marker_text} sarcasm is directed at policies or public figures, not ethnic/religious groups. The speaker criticizes governance through irony, which is legitimate political expression under MY-5.",
            f"Sarcastic markers like {marker_text} indicate political frustration, not communal hostility. The target is government policy, and the critique stays within legitimate discourse boundaries.",
        ]
    elif severity == "S1":
        templates = [
            f"The sarcasm ({marker_text}) expresses legitimate political frustration but uses inflammatory framing that could polarize. Under MY-5, criticism is allowed but the mocking tone warrants a constructive rewrite.",
            f"While the {marker_text} sarcasm targets policy failures (legitimate under MY-5), the inflammatory framing risks polarizing discourse. The critique has merit but needs more constructive expression — S1.",
        ]
    else:  # S2+
        coded_count, coded = count_signals(text, CODED_ETHNIC_SIGNALS)
        coded_text = f"'{coded[0]}'" if coded else "ethnic framing"
        templates = [
            f"The sarcasm escalates beyond policy critique into communal hostility via {coded_text}. Attributing policy failures to ethnic favoritism transforms legitimate frustration into inter-ethnic blame.",
            f"Starting as sarcastic critique, the text pivots to communal hostility through {coded_text}. This crosses from MY-5 (legitimate criticism) into MY-1 violation (communal harmony), warranting S2.",
        ]
    return random.choice(templates)


def generate_euphemism_reasoning(text: str, coded: list[str], ex: dict) -> str:
    """Reasoning for communal euphemism content."""
    code_text = f"'{coded[0]}'" if coded else "coded language"

    if ex["safe"]:
        pro_count, pro_signals = count_signals(text, PRO_SOCIAL_SIGNALS)
        if pro_signals:
            pro_text = f"'{pro_signals[0]}'"
            templates = [
                f"While the text references ethnic or community topics, the {pro_text} framing indicates positive intent. The speaker celebrates diversity or advocates for inclusivity rather than exclusion.",
                f"The mention of ethnic/community matters is framed with {pro_text} signals, indicating appreciation rather than hostility. The speaker's intent is constructive — celebrating shared community life.",
            ]
        else:
            templates = [
                f"The text discusses community matters without coded exclusionary language. The speaker shares a personal observation or cultural reference in a neutral, non-divisive manner.",
                f"Despite touching on ethnic or cultural topics, the framing is neutral and observational. No 'us vs them' rhetoric or coded dog whistles are present. The speaker's intent is descriptive, not divisive.",
            ]
    else:
        severity = ex["severity"]
        templates = [
            f"The phrase {code_text} is a coded ethnic dog whistle, creating an 'us vs them' divide. The speaker uses euphemistic language to avoid direct ethnic targeting while clearly communicating communal hostility.",
            f"{code_text} serves as veiled communal hostility — the speaker avoids naming specific groups but the exclusionary intent is clear. This coded language is designed to divide communities while maintaining plausible deniability.",
            f"Using {code_text} as a coded reference, the speaker frames demographic or social changes as ethnic threats. This euphemistic framing makes the communal hostility harder to detect but equally harmful.",
        ]
    return random.choice(templates)


def generate_religious_reasoning(text: str, signals: list[str], ex: dict) -> str:
    """Reasoning for religious content."""
    rel_text = f"'{signals[0]}'" if signals else "religious references"

    if ex["safe"]:
        pro_count, pro = count_signals(text, PRO_SOCIAL_SIGNALS)
        if pro:
            templates = [
                f"The text discusses {rel_text} in an interfaith or appreciative context. Key signals like '{pro[0]}' indicate the speaker is celebrating religious harmony, not provoking division.",
                f"References to {rel_text} are framed positively — the speaker promotes interfaith understanding or shares a constructive religious observation. No provocation or exclusionary rhetoric present.",
            ]
        else:
            templates = [
                f"The mention of {rel_text} is factual or descriptive, without provocation. The speaker discusses religion in a neutral, informational context that respects MY-2 (religious sensitivity).",
                f"Religious references ({rel_text}) appear in a constructive context — the speaker engages with faith matters respectfully without targeting any religious group or promoting supremacism.",
            ]
    else:
        templates = [
            f"The text weaponizes {rel_text} to target or exclude other faiths. The speaker frames religious differences as threats, violating MY-2 (religious sensitivity) and potentially MY-1 (communal harmony).",
            f"Using {rel_text} as a basis for exclusion or supremacism, the speaker promotes religious intolerance. Phrases that delegitimize other faiths or demand their subordination violate MY-2.",
        ]
    return random.choice(templates)


def generate_misinfo_reasoning(text: str, signals: list[str], ex: dict) -> str:
    """Reasoning for misinformation/rumor content."""
    misinfo_text = f"'{signals[0]}'" if signals else "viral sharing patterns"

    if ex["safe"]:
        condemn_count, condemn = count_signals(text, CONDEMNATION_SIGNALS)
        if condemn:
            templates = [
                f"While the text shares viral content ({misinfo_text}), the speaker frames it with '{condemn[0]}' — debunking rather than spreading. Sharing misinformation to counter it is media literacy, not amplification.",
                f"The {misinfo_text} framing appears alongside clear debunking signals ('{condemn[0]}'). The speaker's intent is to expose and counter false information, not to spread it.",
            ]
        else:
            templates = [
                f"The text references {misinfo_text} content in a factual or analytical context. The speaker discusses the spread of misinformation without endorsing or amplifying it.",
            ]
    else:
        urgency_words = [w for w in ["!!!", "URGENT", "BREAKING", "sebarkan", "share", "boikot", "boycott", "NOW"]
                        if w.lower() in text.lower()]
        if urgency_words:
            urg_text = f"'{urgency_words[0]}'"
            templates = [
                f"The {misinfo_text} content uses urgency markers ({urg_text}) to pressure immediate action without verification. This false urgency is a hallmark of dangerous misinformation designed to cause real-world harm.",
                f"Unverified claims spread via {misinfo_text} with pressure tactics ({urg_text}). The speaker doesn't cite credible sources and uses panic-inducing language. This violates MY-6 (truth in sensitive matters).",
            ]
        else:
            templates = [
                f"The text spreads unverified claims through {misinfo_text} without attribution or evidence. The confident framing of false information as fact violates MY-6 and could cause real-world harm.",
                f"Using {misinfo_text} patterns to distribute unverified information. The speaker presents rumors as established facts, undermining public trust and potentially inciting harmful actions.",
            ]
    return random.choice(templates)


def generate_prosocial_safe_reasoning(text: str, ex: dict) -> str:
    """Reasoning for clearly pro-social safe content."""
    words = text.split()
    text_snippet = " ".join(words[:6])
    reason = ex.get("reason", "")
    reason_lower = reason.lower().rstrip(".") if reason else ""

    # Detect tone: is this a complaint, appreciation, factual, advocacy?
    complaint_words = ["nightmare", "frustrated", "problem", "issue", "susah", "kesian", "membimbangkan",
                       "exploited", "unfair", "inequality", "should be", "perlu", "kena"]
    advocacy_words = ["should", "must", "need to", "perlu", "kena", "protect", "lindungi", "rights", "hak"]
    appreciation_words = ["beautiful", "amazing", "love", "best", "cantik", "indah", "bagus", "respect"]

    complaint_count = sum(1 for w in complaint_words if w.lower() in text.lower())
    advocacy_count = sum(1 for w in advocacy_words if w.lower() in text.lower())
    appreciation_count = sum(1 for w in appreciation_words if w.lower() in text.lower())

    if complaint_count >= 2:
        # Legitimate complaint/criticism — explain why it's safe despite critical tone
        templates = [
            f"Despite the critical tone, '{text_snippet}...' expresses legitimate civic frustration. The speaker targets policies or systems, not ethnic/religious groups. {reason_lower.capitalize() + '.' if reason_lower else ''} Criticism of governance is protected under MY-5.",
            f"The text voices genuine concern about {reason_lower or 'a public issue'}. While the tone is frustrated, the criticism is directed at institutions or policies, not communities. This is legitimate civic discourse.",
        ]
    elif advocacy_count >= 2:
        templates = [
            f"'{text_snippet}...' is advocacy speech — the speaker calls for positive change regarding {reason_lower or 'a social issue'}. The constructive intent and non-targeting framing make this safe.",
            f"The speaker advocates for {reason_lower or 'social improvement'} in a constructive manner. No ethnic targeting or divisive framing — this is legitimate civic engagement.",
        ]
    elif appreciation_count >= 1 or (reason_lower and any(w in reason_lower for w in ["positive", "appreciation", "celebrating", "personal"])):
        templates = [
            f"'{text_snippet}...' is personal appreciation content — {reason_lower or 'sharing a positive experience'}. The warm, inclusive tone has no moderation concern.",
            f"The speaker shares {reason_lower or 'a positive personal experience'}. Starting with '{text_snippet}...', the content is warm and inclusive with no harmful framing.",
        ]
    else:
        if reason_lower:
            templates = [
                f"This text — '{text_snippet}...' — describes {reason_lower}. The language is factual and non-inflammatory, with no coded ethnic references or divisive framing.",
                f"'{text_snippet}...' presents {reason_lower}. The speaker's tone is neutral and informational, without targeting any group or promoting division.",
            ]
        else:
            templates = [
                f"The text beginning '{text_snippet}...' is everyday discourse. The speaker's language is neutral to positive, with no harmful targeting or divisive framing.",
                f"Starting with '{text_snippet}...', this is non-controversial content. No coded language, hostility signals, or inflammatory framing detected.",
            ]
    return random.choice(templates)


def generate_general_unsafe_reasoning(text: str, ex: dict) -> str:
    """Reasoning for general unsafe content without specific pattern."""
    severity = ex["severity"]
    principles = ex.get("triggered_principles", [])
    labels = ex.get("risk_labels", [])
    reason = ex.get("reason", "")

    # Build principle text
    p_text = ", ".join(PRINCIPLES.get(p, p) for p in principles[:2]) if principles else "multiple principles"
    l_text = ", ".join(labels[:2]) if labels else "harmful content"

    # Find specific concerning words
    words = text.split()
    text_start = " ".join(words[:5])

    if reason:
        # Use reason to build specific reasoning
        reason_lower = reason.lower().rstrip(".")
        if severity == "S1":
            templates = [
                f"The text ('{text_start}...') {reason_lower}. While the concern is mild, the framing could polarize discourse. This triggers {p_text} at S1 severity — warranting a constructive rewrite.",
                f"'{text_start}...' — {reason_lower}. The speaker's frustration may be legitimate but the inflammatory expression crosses into {l_text}. S1: mild concern, needs reframing.",
            ]
        elif severity == "S2":
            templates = [
                f"'{text_start}...' constitutes {l_text} — {reason_lower}. This violates {p_text} with significant potential for harm. The content targets communities or spreads harmful generalizations.",
                f"The text {reason_lower}, amounting to {l_text}. Multiple principles are violated: {p_text}. The severity is S2 due to the potential for real-world communal harm.",
            ]
        else:  # S3
            templates = [
                f"Severe content: '{text_start}...' {reason_lower}. This represents the most dangerous form of {l_text}, directly violating {p_text}. Immediate intervention required — S3.",
                f"'{text_start}...' is severely harmful — {reason_lower}. This is {l_text} at S3 level, posing direct and immediate danger. Violates {p_text}.",
            ]
    else:
        templates = [
            f"The text starting '{text_start}...' contains {l_text}. This triggers {p_text}, classified as {severity} severity based on the potential for harm.",
        ]
    return random.choice(templates)


# ═══════════════════════════════════════════════════════════════
# MAIN REASONING ROUTER
# ═══════════════════════════════════════════════════════════════

def generate_reasoning(ex: dict) -> str:
    """Generate content-aware reasoning by analyzing the actual text."""
    text = ex["input_text"]
    safe = ex["safe"]
    severity = ex["severity"]

    # Analyze text for patterns
    quote_count, quote_signals = count_signals(text, QUOTING_SIGNALS)
    quoted_text = extract_quoted_text(text)
    sarcasm_count, sarcasm_signals = count_signals(text, SARCASM_MARKERS)
    coded_count, coded_signals = count_signals(text, CODED_ETHNIC_SIGNALS)
    religious_count, religious_signals = count_signals(text, RELIGIOUS_SIGNALS)
    misinfo_count, misinfo_signals = count_signals(text, MISINFORMATION_SIGNALS)
    condemn_count, condemn_signals = count_signals(text, CONDEMNATION_SIGNALS)
    endorse_count, endorse_signals = count_signals(text, ENDORSEMENT_SIGNALS)
    prosocial_count, prosocial_signals = count_signals(text, PRO_SOCIAL_SIGNALS)

    # Route to specialized generator based on dominant pattern
    # Priority: quoting > sarcasm > misinfo > euphemism > religious > general

    # 1. Quoting/reporting pattern
    if (quote_count >= 2 or quoted_text) and (quote_count > sarcasm_count):
        if safe:
            return generate_quoting_safe_reasoning(text, quote_signals, quoted_text, ex)
        elif endorse_count > condemn_count:
            return generate_quoting_unsafe_reasoning(text, endorse_signals, ex)

    # 2. Sarcasm pattern (threshold 1 for safe, 2 for unsafe)
    # Guard: skip sarcasm routing if pro-social signals dominate (genuine positivity)
    if sarcasm_count >= 1 and (safe or sarcasm_count >= 2):
        if not (safe and prosocial_count > sarcasm_count):
            return generate_sarcasm_reasoning(text, sarcasm_signals, ex)

    # 3. Misinformation pattern
    if misinfo_count >= 2:
        return generate_misinfo_reasoning(text, misinfo_signals, ex)

    # 4. Coded ethnic euphemism pattern
    if coded_count >= 1:
        return generate_euphemism_reasoning(text, coded_signals, ex)

    # 5. Religious content pattern
    if religious_count >= 2:
        return generate_religious_reasoning(text, religious_signals, ex)

    # 6. General safe (pro-social or benign)
    if safe:
        return generate_prosocial_safe_reasoning(text, ex)

    # 7. General unsafe
    return generate_general_unsafe_reasoning(text, ex)


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def load_jsonl(path: str) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def save_jsonl(examples: list[dict], path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Generate content-aware CoT reasoning (v2)")
    parser.add_argument("--input", type=str, default="data/final/train.jsonl")
    parser.add_argument("--output", type=str, default="data/cot/train_cot.jsonl")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--count", type=int, default=0)
    args = parser.parse_args()

    examples = load_jsonl(args.input)
    print(f"Loaded {len(examples)} examples from {args.input}")

    if args.count:
        examples = examples[:args.count]

    processed = []
    pattern_counts = {}

    for i, ex in enumerate(examples):
        reasoning = generate_reasoning(ex)
        processed.append({**ex, "reasoning": reasoning})

        # Track which pattern was used (for stats)
        # Simple heuristic: check first word of reasoning
        if "quote" in reasoning.lower()[:50] or "quoting" in reasoning.lower()[:50]:
            pattern = "quoting"
        elif "sarcas" in reasoning.lower()[:50]:
            pattern = "sarcasm"
        elif "coded" in reasoning.lower()[:80] or "euphemis" in reasoning.lower()[:80] or "dog whistle" in reasoning.lower()[:80]:
            pattern = "euphemism"
        elif "viral" in reasoning.lower()[:50] or "misinfo" in reasoning.lower()[:50] or "unverified" in reasoning.lower()[:80]:
            pattern = "misinfo"
        elif "interfaith" in reasoning.lower()[:80] or "religious" in reasoning.lower()[:50] or "faith" in reasoning.lower()[:50]:
            pattern = "religious"
        else:
            pattern = "general"
        pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

        if args.dry_run and i < (args.count or 20):
            print(f"\n{'='*60}")
            print(f"[{pattern}] safe={ex['safe']}, severity={ex['severity']}")
            print(f"Text: {ex['input_text'][:120]}...")
            print(f"Reasoning: {reasoning}")

        if (i + 1) % 1000 == 0:
            print(f"  [{i+1}/{len(examples)}] processed")

    if not args.dry_run:
        save_jsonl(processed, args.output)

    # Stats
    total = len(processed)
    avg_len = sum(len(p["reasoning"].split()) for p in processed) / total if total else 0

    # Check uniqueness
    unique_reasonings = len(set(p["reasoning"] for p in processed))

    print(f"\nDone! {total} examples processed")
    print(f"Average reasoning length: {avg_len:.0f} words")
    print(f"Unique reasonings: {unique_reasonings}/{total} ({unique_reasonings/total:.0%})")
    print(f"\nPattern breakdown:")
    for pattern, count in sorted(pattern_counts.items(), key=lambda x: -x[1]):
        print(f"  {pattern}: {count} ({count/total:.0%})")
    if not args.dry_run:
        print(f"Output saved to {args.output}")


if __name__ == "__main__":
    main()
