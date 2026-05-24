from __future__ import annotations

from app.pipeline import run_qa_batch
from app.schemas import TenantBatchInput


def test_pipeline_generates_summary_and_preserves_source(sample_payload: TenantBatchInput) -> None:
    result = run_qa_batch(sample_payload, use_ai=False, source_label="pytest_source")

    assert result.source_label == "pytest_source"
    assert result.summary.stories_checked == len(sample_payload.stories)
    assert result.summary.passed + result.summary.needs_review + result.summary.blocked == len(sample_payload.stories)
    assert len(result.stories) == len(sample_payload.stories)
    assert all(0 <= story.trust_score <= 100 for story in result.stories)

