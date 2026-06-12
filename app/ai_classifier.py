from collections import Counter


CATEGORY_KEYWORDS: dict[str, set[str]] = {
    "sports": {"sports", "football", "basketball", "running", "shoes", "gym", "fitness"},
    "finance": {"finance", "stock", "stocks", "bank", "loan", "investing", "crypto"},
    "fashion": {"fashion", "dress", "clothes", "shirt", "shoes", "style", "beauty"},
    "gaming": {"gaming", "game", "games", "console", "pc", "xbox", "playstation"},
    "travel": {"travel", "flight", "hotel", "vacation", "trip", "booking"},
}


def classify_context(context: str | None) -> str:
    """
    Rule-based fallback for optional AI enrichment.

    In a production system this could call an AI model or a low-latency
    text classifier, but the service must keep working without an API key.
    """
    if not context:
        return "unknown"

    words = context.lower().replace(",", " ").replace(".", " ").split()
    word_counts = Counter(words)

    best_category = "unknown"
    best_score = 0

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(word_counts[word] for word in keywords)
        if score > best_score:
            best_score = score
            best_category = category

    return best_category