from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency fallback
    OpenAI = None

try:
    from google import genai
except ImportError:  # pragma: no cover - optional dependency fallback
    genai = None

from app.schemas import Issue, StoryInput


@dataclass
class AISemanticOutput:
    issues: list[Issue]
    summary: str
    confidence: float
    provider: str


class AISemanticEvaluator:
    """
    Lightweight AI adapter.

    For take-home reliability, default mode uses deterministic heuristics that emulate
    semantic checks and always return structured output.
    """

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.logger = _build_ai_logger()

    def evaluate(self, story: StoryInput, tenant_name: str) -> AISemanticOutput:
        if not self.enabled:
            return AISemanticOutput(issues=[], summary="AI evaluation disabled.", confidence=0.0, provider="disabled")
        llm_output = self._evaluate_with_providers(story, tenant_name)
        if llm_output is not None:
            return llm_output
        return self._mock_semantic_eval(story, tenant_name)

    def _evaluate_with_providers(self, story: StoryInput, tenant_name: str) -> AISemanticOutput | None:
        provider_order = [
            provider.strip().lower()
            for provider in os.getenv("STORY_TRUST_AI_PROVIDERS", "openai,gemini").split(",")
            if provider.strip()
        ]
        for provider in provider_order:
            if provider == "openai":
                output = self._openai_semantic_eval(story, tenant_name)
            elif provider == "gemini":
                output = self._gemini_semantic_eval(story, tenant_name)
            else:
                self.logger.warning("Skipping unknown provider in STORY_TRUST_AI_PROVIDERS: %s", provider)
                output = None

            if output is not None:
                return output

        self.logger.info("All configured LLM providers failed/unavailable, using mock-ai fallback.")
        return None

    def _openai_semantic_eval(self, story: StoryInput, tenant_name: str) -> AISemanticOutput | None:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("STORY_TRUST_LLM_MODEL", "gpt-4o-mini")
        if not api_key:
            self.logger.info("OpenAI skipped: OPENAI_API_KEY is missing.")
            return None
        if OpenAI is None:
            self.logger.warning("OpenAI skipped: openai package is unavailable.")
            return None

        prompt_payload, system_prompt = self._build_prompt_payload(story, tenant_name)

        try:
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(prompt_payload)},
                ],
            )
            message = response.choices[0].message.content or "{}"
            parsed = json.loads(message)
            self.logger.info("LLM evaluation succeeded with provider=openai:%s story_id=%s", model, story.story_id)
            return self._build_ai_output_from_llm(parsed, story.story_id, model)
        except Exception as exc:
            self.logger.exception(
                "OpenAI provider failed. provider=%s story_id=%s error=%s",
                model,
                story.story_id,
                exc,
            )
            return None

    def _gemini_semantic_eval(self, story: StoryInput, tenant_name: str) -> AISemanticOutput | None:
        api_key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()
        model = os.getenv("STORY_TRUST_GEMINI_MODEL", "gemini-2.5-flash-lite")
        if not api_key:
            self.logger.info("Gemini skipped: GEMINI_API_KEY/GOOGLE_API_KEY is missing.")
            return None
        if genai is None:
            self.logger.warning("Gemini skipped: google.generativeai package is unavailable.")
            return None

        prompt_payload, system_prompt = self._build_prompt_payload(story, tenant_name)
        user_prompt = json.dumps(prompt_payload)

        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model,
                contents=f"{system_prompt}\n\nInput:\n{user_prompt}",
            )
            raw_text = getattr(response, "text", "") or ""
            parsed = self._safe_json_loads(raw_text)
            if parsed is None:
                self.logger.error("Gemini provider returned non-JSON response. story_id=%s", story.story_id)
                return None

            self.logger.info("LLM evaluation succeeded with provider=gemini:%s story_id=%s", model, story.story_id)
            return self._build_ai_output_from_llm(parsed, story.story_id, model)
        except Exception as exc:
            self.logger.exception(
                "Gemini provider failed. provider=%s story_id=%s error=%s",
                model,
                story.story_id,
                exc,
            )
            return None

    def _build_ai_output_from_llm(
        self, llm_data: dict[str, Any], story_id: str, provider: str
    ) -> AISemanticOutput:
        issues: list[Issue] = []
        raw_issues = llm_data.get("issues", [])
        if isinstance(raw_issues, list):
            for raw_issue in raw_issues:
                if not isinstance(raw_issue, dict):
                    continue
                severity = raw_issue.get("severity", "low")
                if severity not in {"low", "medium", "high", "critical"}:
                    severity = "low"
                issues.append(
                    Issue(
                        severity=severity,
                        code=str(raw_issue.get("code", "AI_SEMANTIC_NOTE")),
                        story_id=story_id,
                        page_id=raw_issue.get("page_id"),
                        message=str(raw_issue.get("message", "Semantic concern detected.")),
                        recommendation=str(
                            raw_issue.get("recommendation", "Review the story for semantic consistency.")
                        ),
                        evidence=raw_issue.get("evidence", {}),
                        source="ai",
                    )
                )

        confidence = llm_data.get("confidence", 0.75)
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.75
        confidence = max(0.0, min(1.0, confidence))

        summary = str(llm_data.get("summary", "Semantic analysis completed."))
        return AISemanticOutput(issues=issues, summary=summary, confidence=confidence, provider=provider)

    def _build_prompt_payload(self, story: StoryInput, tenant_name: str) -> tuple[dict[str, Any], str]:
        prompt_payload = {
            "tenant_name": tenant_name,
            "story": story.model_dump(),
            "task": (
                "Evaluate story trust and publishing quality. Focus on semantic mismatches, "
                "context inconsistency, CTA intent quality, and professionalism signals."
            ),
            "required_schema": {
                "summary": "string",
                "confidence": "number 0..1",
                "issues": [
                    {
                        "severity": "low|medium|high|critical",
                        "code": "string",
                        "page_id": "string|null",
                        "message": "string",
                        "recommendation": "string",
                        "evidence": "object",
                    }
                ],
            },
        }
        system_prompt = (
            "You are a content trust QA evaluator for short-form media stories. "
            "Return strict JSON only and do not wrap with markdown."
        )
        return prompt_payload, system_prompt

    @staticmethod
    def _safe_json_loads(raw_text: str) -> dict[str, Any] | None:
        text = raw_text.strip()
        if not text:
            return None

        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        try:
            parsed = json.loads(text[start : end + 1])
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    def _mock_semantic_eval(self, story: StoryInput, tenant_name: str) -> AISemanticOutput:
        issues: list[Issue] = []
        title_lower = story.story_title.lower()

        if "vs" in title_lower and len(story.context.categories) < 2:
            issues.append(
                Issue(
                    severity="medium",
                    code="WEAK_CONTEXT_COVERAGE",
                    story_id=story.story_id,
                    message="Story title suggests a matchup but context has limited category coverage.",
                    recommendation="Add team and event categories to improve discoverability and context quality.",
                    evidence={"story_title": story.story_title, "categories": story.context.categories},
                    source="ai-mock",
                )
            )

        if story.context.tenant and story.context.tenant.strip().lower() != tenant_name.strip().lower():
            issues.append(
                Issue(
                    severity="high",
                    code="SEMANTIC_TENANT_MISMATCH",
                    story_id=story.story_id,
                    message="Tenant context mismatch may reduce trust and editorial consistency.",
                    recommendation="Review tenant mapping and correct story ownership metadata.",
                    evidence={"context_tenant": story.context.tenant, "batch_tenant": tenant_name},
                    source="ai-mock",
                )
            )

        for page in story.pages:
            cta_lower = page.action.cta.lower().strip()
            if cta_lower in {"click here", "learn more", "tap now"}:
                issues.append(
                    Issue(
                        severity="low",
                        code="GENERIC_CTA_LANGUAGE",
                        story_id=story.story_id,
                        page_id=page.page_id,
                        message="CTA language is generic and may reduce professionalism and user clarity.",
                        recommendation="Use an intent-specific CTA such as 'View lineup' or 'Watch highlights'.",
                        evidence={"cta": page.action.cta},
                        source="ai-mock",
                    )
                )

        summary = "No major semantic trust concerns detected."
        confidence = 0.82
        if issues:
            summary = "Semantic checks found context or messaging risks that should be reviewed."
            confidence = 0.76

        return AISemanticOutput(issues=issues, summary=summary, confidence=confidence, provider="mock-ai")


def _build_ai_logger() -> logging.Logger:
    logger = logging.getLogger("story_trust.ai_evaluator")
    if logger.handlers:
        return logger

    log_path = Path(os.getenv("STORY_TRUST_AI_LOG_PATH", "output/ai_evaluator.log"))
    log_path.parent.mkdir(parents=True, exist_ok=True)

    handler = logging.FileHandler(log_path, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger

