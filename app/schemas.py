from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ActionInput(BaseModel):
    cta: str = ""
    url: str = ""


class PageInput(BaseModel):
    page_id: str
    type: str
    asset_url: str = ""
    action: ActionInput = Field(default_factory=ActionInput)


class ContextInput(BaseModel):
    categories: list[str] = Field(default_factory=list)
    tenant: str = ""
    publish_date: str = ""


class StoryInput(BaseModel):
    story_id: str
    story_title: str = ""
    pages: list[PageInput] = Field(default_factory=list)
    context: ContextInput = Field(default_factory=ContextInput)


class TenantBatchInput(BaseModel):
    tenant_id: str
    tenant_name: str
    last_synced_at: datetime | None = None
    stories: list[StoryInput] = Field(default_factory=list)


Severity = Literal["low", "medium", "high", "critical"]
Verdict = Literal["pass", "review", "block"]
IssueSource = Literal["rule", "ai", "ai-mock"]


class Issue(BaseModel):
    severity: Severity
    code: str
    story_id: str
    page_id: str | None = None
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    recommendation: str
    source: IssueSource = "rule"


class StoryQAResult(BaseModel):
    story_id: str
    story_title: str
    verdict: Verdict
    risk_score: int
    trust_score: int
    issues: list[Issue] = Field(default_factory=list)
    ai_provider: str = "disabled"
    ai_summary: str = ""
    ai_confidence: float = 0.0


class RunSummary(BaseModel):
    stories_checked: int
    passed: int
    needs_review: int
    blocked: int
    average_trust_score: float


class QARunResult(BaseModel):
    run_id: str
    created_at: datetime
    tenant_id: str
    tenant_name: str
    source_label: str = "api_payload"
    summary: RunSummary
    stories: list[StoryQAResult] = Field(default_factory=list)

