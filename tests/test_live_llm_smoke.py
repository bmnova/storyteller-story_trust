from __future__ import annotations

import os

import pytest

from app.ai_evaluator import AISemanticEvaluator
from app.schemas import StoryInput
from app.settings import load_environment

load_environment()


def _has_any_llm_key() -> bool:
    return bool(
        os.getenv("OPENAI_API_KEY", "").strip()
        or os.getenv("GEMINI_API_KEY", "").strip()
        or os.getenv("GOOGLE_API_KEY", "").strip()
    )


@pytest.mark.skipif(
    not _has_any_llm_key(),
    reason="No LLM key found (OPENAI_API_KEY or GEMINI_API_KEY/GOOGLE_API_KEY).",
)
def test_live_llm_smoke_provider_is_not_mock() -> None:
    story = StoryInput.model_validate(
        {
            "story_id": "live_smoke_story",
            "story_title": "Matchday build-up: PFC vs SU",
            "pages": [
                {
                    "page_id": "page_1",
                    "type": "image",
                    "asset_url": "https://cdn.storyteller.com/assets/live_smoke/page_1.jpg",
                    "action": {"cta": "View lineup", "url": "https://antarcticfootballleague.com/lineup"},
                }
            ],
            "context": {
                "categories": ["Penguin FC", "Seals United", "Matchday"],
                "tenant": "Antarctic Football League",
                "publish_date": "2026-02-14",
            },
        }
    )

    evaluator = AISemanticEvaluator(enabled=True)
    output = evaluator.evaluate(story, "Antarctic Football League")

    assert output.provider not in {"disabled", "mock-ai"}
    assert output.summary.strip()
    assert 0.0 <= output.confidence <= 1.0

