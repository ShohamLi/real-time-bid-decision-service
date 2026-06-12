from types import SimpleNamespace

import app.ai_classifier as classifier_module
from app.config import Settings


def _mock_client(content: str):
    completions = SimpleNamespace(
        create=lambda **kwargs: SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )
    )
    return SimpleNamespace(chat=SimpleNamespace(completions=completions))


def test_enrichment_disabled_uses_local_classification(monkeypatch):
    settings = Settings(
        enable_ai_enrichment=False,
        openai_api_key="not-a-real-key",
    )
    monkeypatch.setattr(
        classifier_module,
        "_create_openai_client",
        lambda settings: (_ for _ in ()).throw(AssertionError("OpenAI called")),
    )

    assert classifier_module.classify_context("sports shoes", settings) == "sports"


def test_missing_api_key_uses_local_classification(monkeypatch):
    settings = Settings(enable_ai_enrichment=True, openai_api_key=None)
    monkeypatch.setattr(
        classifier_module,
        "_create_openai_client",
        lambda settings: (_ for _ in ()).throw(AssertionError("OpenAI called")),
    )

    assert classifier_module.classify_context("stock investing", settings) == "finance"


def test_successful_mocked_openai_classification(monkeypatch):
    settings = Settings(
        enable_ai_enrichment=True,
        openai_api_key="not-a-real-key",
    )
    monkeypatch.setattr(
        classifier_module,
        "_create_openai_client",
        lambda settings: _mock_client("travel"),
    )

    assert classifier_module.classify_context("sports shoes", settings) == "travel"


def test_invalid_openai_category_falls_back_locally(monkeypatch):
    settings = Settings(
        enable_ai_enrichment=True,
        openai_api_key="not-a-real-key",
    )
    monkeypatch.setattr(
        classifier_module,
        "_create_openai_client",
        lambda settings: _mock_client("health"),
    )

    assert classifier_module.classify_context("sports shoes", settings) == "sports"


def test_openai_exception_falls_back_locally(monkeypatch):
    settings = Settings(
        enable_ai_enrichment=True,
        openai_api_key="not-a-real-key",
    )

    def raise_timeout(settings):
        raise TimeoutError("OpenAI timed out")

    monkeypatch.setattr(classifier_module, "_create_openai_client", raise_timeout)

    assert classifier_module.classify_context("stock investing", settings) == "finance"
