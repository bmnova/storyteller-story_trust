from __future__ import annotations

import json
from pathlib import Path

from app.schemas import QARunResult


def write_json_report(run_result: QARunResult, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(run_result.model_dump(mode="json"), indent=2), encoding="utf-8")


def write_markdown_report(run_result: QARunResult, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# Story QA Report")
    lines.append("")
    lines.append(f"- Run ID: `{run_result.run_id}`")
    lines.append(f"- Tenant: `{run_result.tenant_name}` (`{run_result.tenant_id}`)")
    lines.append(f"- Source: `{run_result.source_label}`")
    lines.append(f"- Created at: `{run_result.created_at.isoformat()}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Stories checked: **{run_result.summary.stories_checked}**")
    lines.append(f"- Passed: **{run_result.summary.passed}**")
    lines.append(f"- Needs review: **{run_result.summary.needs_review}**")
    lines.append(f"- Blocked: **{run_result.summary.blocked}**")
    lines.append(f"- Average trust score: **{run_result.summary.average_trust_score}**")
    lines.append("")

    for story in run_result.stories:
        lines.append(f"## {story.story_id} — {story.story_title}")
        lines.append("")
        lines.append(f"- Verdict: **{story.verdict.upper()}**")
        lines.append(f"- Trust score: **{story.trust_score}**")
        lines.append(f"- Risk score: **{story.risk_score}**")
        lines.append(f"- AI provider: `{story.ai_provider}`")
        lines.append(f"- AI summary: {story.ai_summary}")
        lines.append("")
        if not story.issues:
            lines.append("- No issues detected.")
        else:
            for issue in story.issues:
                lines.append(
                    f"- `{issue.severity.upper()}` `{issue.code}` ({issue.source}) - {issue.message}"
                )
                lines.append(f"  - Recommendation: {issue.recommendation}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")

