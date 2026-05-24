from __future__ import annotations

from app.ai_evaluator import AISemanticEvaluator, AISemanticOutput
from app.schemas import Issue, StoryInput


def _build_story() -> StoryInput:
    return StoryInput.model_validate(
        {
            "story_id": "story_ai",
            "story_title": "Penguin FC vs Seals United",
            "pages": [
                {
                    "page_id": "page_1",
                    "type": "image",
                    "asset_url": "https://cdn.storyteller.com/assets/story_ai/page_1.jpg",
                    "action": {"cta": "View lineup", "url": "https://antarcticfootballleague.com/lineup"},
                }
            ],
            "context": {
                "categories": ["Penguin FC", "Seals United"],
                "tenant": "Antarctic Football League",
                "publish_date": "2026-02-14",
            },
        }
    )


def test_ai_evaluator_disabled_returns_disabled_provider() -> None:
    evaluator = AISemanticEvaluator(enabled=False)
    output = evaluator.evaluate(_build_story(), "Antarctic Football League")
    assert output.provider == "disabled"
    assert output.issues == []


def test_ai_evaluator_prefers_llm_output_when_available(monkeypatch) -> None:
    evaluator = AISemanticEvaluator(enabled=True)
    mocked = AISemanticOutput(
        issues=[
            Issue(
                severity="low",
                code="LLM_NOTE",
                story_id="story_ai",
                message="Minor semantic note.",
                recommendation="No action needed.",
                source="ai",
            )
        ],
        summary="LLM summary",
        confidence=0.9,
        provider="gpt-test",
    )
    monkeypatch.setattr(evaluator, "_evaluate_with_providers", lambda _story, _tenant: mocked)
    output = evaluator.evaluate(_build_story(), "Antarctic Football League")
    assert output.provider == "gpt-test"
    assert output.summary == "LLM summary"


def test_ai_evaluator_falls_back_to_mock_when_llm_unavailable(monkeypatch) -> None:
    evaluator = AISemanticEvaluator(enabled=True)
    monkeypatch.setattr(evaluator, "_evaluate_with_providers", lambda _story, _tenant: None)
    output = evaluator.evaluate(_build_story(), "Antarctic Football League")
    assert output.provider == "mock-ai"


def test_ai_evaluator_tries_next_provider_on_failure(monkeypatch) -> None:
    evaluator = AISemanticEvaluator(enabled=True)
    monkeypatch.setenv("STORY_TRUST_AI_PROVIDERS", "openai,gemini")
    monkeypatch.setattr(evaluator, "_openai_semantic_eval", lambda _story, _tenant: None)
    mocked_gemini = AISemanticOutput(
        issues=[],
        summary="Gemini summary",
        confidence=0.8,
        provider="gemini-test",
    )
    monkeypatch.setattr(evaluator, "_gemini_semantic_eval", lambda _story, _tenant: mocked_gemini)

    output = evaluator._evaluate_with_providers(_build_story(), "Antarctic Football League")
    assert output is not None
    assert output.provider == "gemini-test"

