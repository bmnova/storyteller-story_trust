from __future__ import annotations

from app.schemas import Issue, Verdict

SEVERITY_WEIGHTS = {
    "low": 5,
    "medium": 15,
    "high": 30,
    "critical": 50,
}


def score_story(issues: list[Issue]) -> tuple[int, int, Verdict]:
    risk_score = sum(SEVERITY_WEIGHTS.get(issue.severity, 0) for issue in issues)
    risk_score = max(0, min(100, risk_score))
    trust_score = max(0, 100 - risk_score)

    has_critical = any(issue.severity == "critical" for issue in issues)
    has_high = any(issue.severity == "high" for issue in issues)

    if has_critical:
        return risk_score, min(trust_score, 59), "block"

    verdict = _map_trust_to_verdict(trust_score)
    if has_high and verdict == "pass":
        return risk_score, 84, "review"

    return risk_score, trust_score, verdict


def _map_trust_to_verdict(trust_score: int) -> Verdict:
    if trust_score >= 85:
        return "pass"
    if trust_score >= 60:
        return "review"
    return "block"

