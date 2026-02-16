"""Self-contained sensitivity scorer — embeds Silver algorithm, no file I/O."""

import re

# Weighted keywords from config.yaml
KEYWORDS_WEIGHTED: dict[str, float] = {
    "invoice": 0.8,
    "payment": 0.9,
    "email": 0.6,
    "client": 0.5,
    "delete": 0.9,
    "password": 1.0,
    "refund": 0.8,
    "credential": 0.9,
    "permission": 0.7,
    "access": 0.6,
}

DEFAULT_THRESHOLD = 0.6

CONTEXT_BOOST: dict[tuple[str, str], float] = {
    ("email", "client"): 0.3,
    ("email", "external"): 0.2,
    ("payment", "invoice"): 0.2,
    ("delete", "database"): 0.3,
    ("delete", "production"): 0.3,
    ("access", "admin"): 0.3,
    ("password", "reset"): 0.2,
    ("credential", "share"): 0.3,
}

CONTEXT_REDUCE: dict[tuple[str, str], float] = {
    ("email", "internal"): -0.2,
    ("email", "notification"): -0.15,
    ("delete", "draft"): -0.2,
    ("delete", "temp"): -0.2,
    ("access", "read"): -0.1,
}

KEYWORD_CATEGORIES: dict[str, str] = {
    "invoice": "financial",
    "payment": "financial",
    "refund": "financial",
    "email": "external_communication",
    "client": "external_communication",
    "delete": "data_deletion",
    "password": "access_change",
    "credential": "access_change",
    "permission": "access_change",
    "access": "access_change",
}


def score_sensitivity(
    text: str, threshold: float = DEFAULT_THRESHOLD
) -> dict:
    """Score text for sensitivity. Returns score, category, signals, requires_approval."""
    text_lower = text.lower()
    words = set(re.findall(r"\w+", text_lower))

    signals: list[str] = []
    category_scores: dict[str, float] = {}
    total_score = 0.0

    for keyword, weight in KEYWORDS_WEIGHTED.items():
        if keyword in text_lower:
            signals.append(f"{keyword} (+{weight})")
            total_score += weight
            cat = KEYWORD_CATEGORIES.get(keyword, "unknown")
            category_scores[cat] = category_scores.get(cat, 0) + weight

    for (w1, w2), modifier in CONTEXT_BOOST.items():
        if w1 in words and w2 in words:
            total_score += modifier
            signals.append(f"context({w1}+{w2}) (+{modifier})")

    for (w1, w2), modifier in CONTEXT_REDUCE.items():
        if w1 in words and w2 in words:
            total_score += modifier
            signals.append(f"context({w1}+{w2}) ({modifier})")

    score = min(1.0, max(0.0, total_score))
    top_category = max(category_scores, key=category_scores.get) if category_scores else "none"

    return {
        "score": round(score, 2),
        "category": top_category,
        "signals": signals,
        "requires_approval": score >= threshold,
    }
