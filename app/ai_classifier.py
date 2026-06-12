from collections import Counter
from typing import Any

from app.config import Settings, get_settings


CATEGORY_KEYWORDS: dict[str, set[str]] = {
    "sports": {"sports", "football", "basketball", "running", "shoes", "gym", "fitness"},
    "finance": {"finance", "stock", "stocks", "bank", "loan", "investing", "crypto"},
    "fashion": {"fashion", "dress", "clothes", "shirt", "shoes", "style", "beauty"},
    "gaming": {"gaming", "game", "games", "console", "pc", "xbox", "playstation"},
    "travel": {"travel", "flight", "hotel", "vacation", "trip", "booking"},
}

SUPPORTED_CATEGORIES = frozenset(
    {"sports", "finance", "fashion", "gaming", "travel", "generic", "unknown"}
)

OPENAI_SYSTEM_PROMPT = (
    "Classify the context. Reply with exactly one category: sports, finance, "
    "fashion, gaming, travel, generic, or unknown."
)


def classify_context_locally(context: str | None) -> str:
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


def _create_openai_client(settings: Settings) -> Any:
    from openai import OpenAI

    return OpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.ai_timeout_seconds,
    )


def _classify_context_with_openai(context: str, settings: Settings) -> str | None:
    client = _create_openai_client(settings)
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": OPENAI_SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ],
        temperature=0,
        max_tokens=5,
        timeout=settings.ai_timeout_seconds,
    )
    content = response.choices[0].message.content
    if not isinstance(content, str):
        return None

    category = content.strip().lower()
    return category if category in SUPPORTED_CATEGORIES else None


def classify_context(
    context: str | None,
    settings: Settings | None = None,
) -> str:
    local_category = classify_context_locally(context)
    effective_settings = settings or get_settings()

    if (
        not context
        or not effective_settings.enable_ai_enrichment
        or not effective_settings.openai_api_key
    ):
        return local_category

    try:
        ai_category = _classify_context_with_openai(context, effective_settings)
    except Exception:
        return local_category

    return ai_category or local_category
