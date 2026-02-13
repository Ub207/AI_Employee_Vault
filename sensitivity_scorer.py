"""
AI Employee Vault — Sensitivity Scorer (Silver Tier)
Smart weighted sensitivity detection. Replaces simple keyword matching
with scored, context-aware classification.
"""

import re
from config_loader import load_config

# Context modifiers: pairs of words that boost or reduce score
CONTEXT_BOOST = {
    ("email", "client"): 0.3,
    ("email", "external"): 0.2,
    ("payment", "invoice"): 0.2,
    ("delete", "database"): 0.3,
    ("delete", "production"): 0.3,
    ("access", "admin"): 0.3,
    ("password", "reset"): 0.2,
    ("credential", "share"): 0.3,
}

CONTEXT_REDUCE = {
    ("email", "internal"): -0.2,
    ("email", "notification"): -0.15,
    ("delete", "draft"): -0.2,
    ("delete", "temp"): -0.2,
    ("access", "read"): -0.1,
}

# Map keywords to sensitivity categories
KEYWORD_CATEGORIES = {
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


def score_sensitivity(text: str, config: dict | None = None) -> dict:
    """
    Score text for sensitivity using weighted keywords and context.

    Returns:
        {
            "score": float 0.0-1.0,
            "category": str (top category or "none"),
            "signals": list[str] (matched keywords with weights),
            "requires_approval": bool
        }
    """
    if config is None:
        config = load_config()

    sens_cfg = config.get("sensitivity", {})
    weights = sens_cfg.get("keywords_weighted", {})
    threshold = sens_cfg.get("threshold", 0.6)

    text_lower = text.lower()
    words = set(re.findall(r"\w+", text_lower))

    signals = []
    category_scores: dict[str, float] = {}
    total_score = 0.0
    matched_keywords = []

    # Score each weighted keyword
    for keyword, weight in weights.items():
        if keyword in text_lower:
            signals.append(f"{keyword} (+{weight})")
            total_score += weight
            matched_keywords.append(keyword)

            cat = KEYWORD_CATEGORIES.get(keyword, "unknown")
            category_scores[cat] = category_scores.get(cat, 0) + weight

    # Apply context boosters
    for (w1, w2), modifier in CONTEXT_BOOST.items():
        if w1 in words and w2 in words:
            total_score += modifier
            signals.append(f"context({w1}+{w2}) (+{modifier})")

    # Apply context reducers
    for (w1, w2), modifier in CONTEXT_REDUCE.items():
        if w1 in words and w2 in words:
            total_score += modifier
            signals.append(f"context({w1}+{w2}) ({modifier})")

    # Normalize score to 0.0-1.0 range
    score = min(1.0, max(0.0, total_score))

    # Determine top category
    if category_scores:
        top_category = max(category_scores, key=category_scores.get)
    else:
        top_category = "none"

    return {
        "score": round(score, 2),
        "category": top_category,
        "signals": signals,
        "requires_approval": score >= threshold,
    }


if __name__ == "__main__":
    tests = [
        "Send an invoice to the client for $500 payment",
        "Prepare weekly internal report for the team",
        "Delete user credentials from the production database",
        "Email the client about the project update",
        "Draft internal notification about office hours",
    ]
    for t in tests:
        result = score_sensitivity(t)
        print(f"\nText: {t}")
        print(f"  Score: {result['score']}")
        print(f"  Category: {result['category']}")
        print(f"  Signals: {result['signals']}")
        print(f"  Requires approval: {result['requires_approval']}")
