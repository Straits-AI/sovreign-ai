"""Malaysia moderation dataset constants."""

PRINCIPLES = {
    "MY-1": "Preserve harmony across communities",
    "MY-2": "Respect faith and religious sensitivity",
    "MY-3": "Respect constitutional order and lawful process",
    "MY-4": "Uphold dignity, courtesy, and adab",
    "MY-5": "Allow criticism, but not incitement",
    "MY-6": "Protect truth in sensitive public matters",
    "MY-7": "Protect privacy, confidentiality, and personal safety",
    "MY-8": "Prefer constructive, plural, and de-escalatory assistance",
}

PRINCIPLE_IDS = list(PRINCIPLES.keys())

SEVERITIES = ["S0", "S1", "S2", "S3"]

LANGUAGES = ["ms", "en", "zh", "ta", "mixed"]

RISK_LABELS = [
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

TOPICS = [
    "politics_public_issues",
    "race_religion_culture",
    "personal_conflict_insults",
    "rumors_misinformation",
    "privacy_doxxing",
    "neutral_civic_safe",
]

TARGET_COUNTS = {"S0": 2000, "S1": 2000, "S2": 2000, "S3": 1000}

LANGUAGE_MIX = {"ms": 0.35, "en": 0.25, "zh": 0.15, "ta": 0.10, "mixed": 0.15}

TOPIC_MIX = {
    "politics_public_issues": 0.25,
    "race_religion_culture": 0.20,
    "personal_conflict_insults": 0.15,
    "rumors_misinformation": 0.15,
    "privacy_doxxing": 0.10,
    "neutral_civic_safe": 0.15,
}
