from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.ai_evaluator import AISemanticEvaluator
from app.checks import run_deterministic_checks
from app.scoring import score_story
from app.schemas import QARunResult, RunSummary, StoryQAResult, TenantBatchInput


def run_qa_batch(payload: TenantBatchInput, use_ai: bool = True, source_label: str = "api_payload") -> QARunResult:
    evaluator = AISemanticEvaluator(enabled=use_ai)
    story_results: list[StoryQAResult] = []

    for story in payload.stories:
        rule_issues = run_deterministic_checks(story, payload.tenant_name)
        ai_output = evaluator.evaluate(story, payload.tenant_name)
        all_issues = [*rule_issues, *ai_output.issues]

        risk_score, trust_score, verdict = score_story(all_issues)
        story_results.append(
            StoryQAResult(
                story_id=story.story_id,
                story_title=story.story_title,
                verdict=verdict,
                risk_score=risk_score,
                trust_score=trust_score,
                issues=all_issues,
                ai_provider=ai_output.provider,
                ai_summary=ai_output.summary,
                ai_confidence=ai_output.confidence,
            )
        )

    passed = sum(1 for story in story_results if story.verdict == "pass")
    needs_review = sum(1 for story in story_results if story.verdict == "review")
    blocked = sum(1 for story in story_results if story.verdict == "block")
    average_trust = round(sum(story.trust_score for story in story_results) / max(1, len(story_results)), 2)

    summary = RunSummary(
        stories_checked=len(story_results),
        passed=passed,
        needs_review=needs_review,
        blocked=blocked,
        average_trust_score=average_trust,
    )

    return QARunResult(
        run_id=f"run_{uuid4().hex[:10]}",
        created_at=datetime.now(timezone.utc),
        tenant_id=payload.tenant_id,
        tenant_name=payload.tenant_name,
        source_label=source_label,
        summary=summary,
        stories=story_results,
    )

