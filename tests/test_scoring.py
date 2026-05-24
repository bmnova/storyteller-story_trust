from __future__ import annotations

from app.schemas import Issue
from app.scoring import score_story


def test_scoring_no_issues_passes_with_full_trust() -> None:
    risk, trust, verdict = score_story([])
    assert risk == 0
    assert trust == 100
    assert verdict == "pass"


def test_scoring_critical_issue_forces_block() -> None:
    critical_issue = Issue(
        severity="critical",
        code="SUSPICIOUS_DESTINATION",
        story_id="story_1",
        message="Suspicious destination URL.",
        recommendation="Block until manually reviewed.",
        source="rule",
    )

    risk, trust, verdict = score_story([critical_issue])
    assert risk == 50
    assert trust <= 59
    assert verdict == "block"

