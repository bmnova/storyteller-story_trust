from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

from app.schemas import Issue, StoryInput

SUPPORTED_PAGE_TYPES = {"image", "video"}


def run_deterministic_checks(story: StoryInput, tenant_name: str) -> list[Issue]:
    issues: list[Issue] = []

    if not story.story_title.strip():
        issues.append(
            Issue(
                severity="medium",
                code="MISSING_STORY_TITLE",
                story_id=story.story_id,
                message="Story title is empty.",
                recommendation="Provide a concise descriptive story title.",
                evidence={"story_title": story.story_title},
                source="rule",
            )
        )

    if story.context.tenant and story.context.tenant.strip().lower() != tenant_name.strip().lower():
        issues.append(
            Issue(
                severity="high",
                code="TENANT_CONTEXT_MISMATCH",
                story_id=story.story_id,
                message="Story context tenant does not match batch tenant.",
                recommendation="Sync story context tenant with the owning tenant.",
                evidence={"context_tenant": story.context.tenant, "batch_tenant": tenant_name},
                source="rule",
            )
        )

    if not story.context.publish_date:
        issues.append(
            Issue(
                severity="medium",
                code="MISSING_PUBLISH_DATE",
                story_id=story.story_id,
                message="Publish date is missing in story context.",
                recommendation="Set publish date so scheduling and audit trails remain reliable.",
                evidence={"publish_date": story.context.publish_date},
                source="rule",
            )
        )
    else:
        try:
            datetime.fromisoformat(story.context.publish_date)
        except ValueError:
            issues.append(
                Issue(
                    severity="medium",
                    code="INVALID_PUBLISH_DATE",
                    story_id=story.story_id,
                    message="Publish date is not ISO-compatible.",
                    recommendation="Use ISO date format such as YYYY-MM-DD.",
                    evidence={"publish_date": story.context.publish_date},
                    source="rule",
                )
            )

    seen_page_ids: set[str] = set()
    for page in story.pages:
        if page.page_id in seen_page_ids:
            issues.append(
                Issue(
                    severity="high",
                    code="DUPLICATE_PAGE_ID",
                    story_id=story.story_id,
                    page_id=page.page_id,
                    message="Duplicate page_id detected in story pages.",
                    recommendation="Ensure each page has a unique page_id.",
                    evidence={"page_id": page.page_id},
                    source="rule",
                )
            )
        seen_page_ids.add(page.page_id)

        if page.type not in SUPPORTED_PAGE_TYPES:
            issues.append(
                Issue(
                    severity="medium",
                    code="UNSUPPORTED_MEDIA_TYPE",
                    story_id=story.story_id,
                    page_id=page.page_id,
                    message="Page media type is not supported.",
                    recommendation="Use page type 'image' or 'video'.",
                    evidence={"page_type": page.type},
                    source="rule",
                )
            )

        if not page.asset_url:
            issues.append(
                Issue(
                    severity="high",
                    code="MISSING_ASSET_URL",
                    story_id=story.story_id,
                    page_id=page.page_id,
                    message="Page asset URL is missing.",
                    recommendation="Attach a valid media asset URL before publishing.",
                    evidence={"asset_url": page.asset_url},
                    source="rule",
                )
            )

        if not page.action.cta.strip():
            issues.append(
                Issue(
                    severity="medium",
                    code="MISSING_CTA",
                    story_id=story.story_id,
                    page_id=page.page_id,
                    message="Page action CTA text is missing.",
                    recommendation="Add a CTA text aligned with the intended action.",
                    evidence={"cta": page.action.cta},
                    source="rule",
                )
            )

        if not page.action.url.strip():
            issues.append(
                Issue(
                    severity="high",
                    code="MISSING_ACTION_URL",
                    story_id=story.story_id,
                    page_id=page.page_id,
                    message="Page action URL is missing.",
                    recommendation="Provide a destination URL for the CTA.",
                    evidence={"url": page.action.url},
                    source="rule",
                )
            )
        else:
            issues.extend(_check_url_and_cta_alignment(story.story_id, page.page_id, page.action.cta, page.action.url))
            issues.extend(_check_domain_risk(story.story_id, page.page_id, page.action.url, tenant_name))

    return issues


def _check_domain_risk(story_id: str, page_id: str, url: str, tenant_name: str) -> list[Issue]:
    issues: list[Issue] = []
    domain = urlparse(url).netloc.lower()
    normalized_tenant = tenant_name.lower().replace(" ", "")
    tenant_tokens = {token for token in normalized_tenant.split("-") if token}

    if not domain:
        issues.append(
            Issue(
                severity="high",
                code="INVALID_ACTION_URL",
                story_id=story_id,
                page_id=page_id,
                message="CTA URL cannot be parsed as a valid URL.",
                recommendation="Provide a fully qualified URL with a valid domain.",
                evidence={"url": url},
                source="rule",
            )
        )
        return issues

    domain_is_related = normalized_tenant in domain or any(token in domain for token in tenant_tokens)
    if not domain_is_related and not domain.endswith("storyteller.com"):
        issues.append(
            Issue(
                severity="medium",
                code="EXTERNAL_DOMAIN_RISK",
                story_id=story_id,
                page_id=page_id,
                message="CTA URL points to a domain not clearly related to tenant.",
                recommendation="Verify destination domain or whitelist trusted partner domains.",
                evidence={"url": url, "domain": domain},
                source="rule",
            )
        )

    return issues


def _check_url_and_cta_alignment(story_id: str, page_id: str, cta: str, url: str) -> list[Issue]:
    issues: list[Issue] = []
    cta_lower = cta.lower().strip()
    path = urlparse(url).path.lower()

    if "buy" in cta_lower and "ticket" in cta_lower and "ticket" not in path:
        issues.append(
            Issue(
                severity="high",
                code="CTA_DESTINATION_MISMATCH",
                story_id=story_id,
                page_id=page_id,
                message="CTA implies ticket purchase but destination path is not ticket-related.",
                recommendation="Change CTA text or route URL to a ticket purchase destination.",
                evidence={"cta": cta, "url": url, "path": path},
                source="rule",
            )
        )

    if "watch" in cta_lower and "highlight" in cta_lower and "highlight" not in path and "report" not in path:
        issues.append(
            Issue(
                severity="medium",
                code="CTA_INTENT_WEAK_MATCH",
                story_id=story_id,
                page_id=page_id,
                message="CTA asks to watch highlights but destination path may not match that intent.",
                recommendation="Align CTA wording and destination URL intent.",
                evidence={"cta": cta, "url": url, "path": path},
                source="rule",
            )
        )

    if "live" in cta_lower and "live" not in path:
        issues.append(
            Issue(
                severity="medium",
                code="LIVE_CTA_MISMATCH",
                story_id=story_id,
                page_id=page_id,
                message="CTA implies live content but destination path does not indicate live coverage.",
                recommendation="Point CTA to a live destination or revise CTA text.",
                evidence={"cta": cta, "url": url, "path": path},
                source="rule",
            )
        )

    return issues

