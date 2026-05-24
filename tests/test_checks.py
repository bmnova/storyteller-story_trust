from __future__ import annotations

from app.checks import run_deterministic_checks
from app.schemas import StoryInput


def test_deterministic_checks_flag_cta_destination_mismatch() -> None:
    story = StoryInput.model_validate(
        {
            "story_id": "story_x",
            "story_title": "Derby Highlights",
            "pages": [
                {
                    "page_id": "page_1",
                    "type": "image",
                    "asset_url": "https://cdn.storyteller.com/assets/story_x/page_1.jpg",
                    "action": {
                        "cta": "Buy tickets",
                        "url": "https://antarcticfootballleague.com/highlights",
                    },
                }
            ],
            "context": {
                "categories": ["Penguin FC", "Seals United"],
                "tenant": "Antarctic Football League",
                "publish_date": "2026-02-14",
            },
        }
    )

    issues = run_deterministic_checks(story, tenant_name="Antarctic Football League")
    codes = {issue.code for issue in issues}
    assert "CTA_DESTINATION_MISMATCH" in codes


def test_deterministic_checks_flag_missing_structural_fields() -> None:
    story = StoryInput.model_validate(
        {
            "story_id": "story_y",
            "story_title": "",
            "pages": [{"page_id": "page_1", "type": "gif", "asset_url": "", "action": {"cta": "", "url": ""}}],
            "context": {"categories": [], "tenant": "Other Tenant", "publish_date": ""},
        }
    )

    issues = run_deterministic_checks(story, tenant_name="Antarctic Football League")
    codes = {issue.code for issue in issues}
    assert {"MISSING_STORY_TITLE", "UNSUPPORTED_MEDIA_TYPE", "MISSING_ASSET_URL", "MISSING_ACTION_URL"}.issubset(
        codes
    )

