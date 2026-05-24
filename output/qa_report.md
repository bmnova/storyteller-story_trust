# Story QA Report

- Run ID: `run_40ce3cc66b`
- Tenant: `Antarctic Football League` (`tenant_antarctic_league_001`)
- Source: `data/sample_response.json`
- Created at: `2026-05-24T22:53:26.101256+00:00`

## Summary

- Stories checked: **3**
- Passed: **1**
- Needs review: **1**
- Blocked: **1**
- Average trust score: **56.67**

## story_123 — Last 5 meetings: Penguin FC vs Seals United

- Verdict: **REVIEW**
- Trust score: **70**
- Risk score: **30**
- AI provider: `disabled`
- AI summary: AI evaluation disabled.

- `HIGH` `CTA_DESTINATION_MISMATCH` (rule) - CTA implies ticket purchase but destination path is not ticket-related.
  - Recommendation: Change CTA text or route URL to a ticket purchase destination.

## story_124 — Matchday build-up: PFC v SU

- Verdict: **PASS**
- Trust score: **100**
- Risk score: **0**
- AI provider: `disabled`
- AI summary: AI evaluation disabled.

- No issues detected.

## story_125 — 

- Verdict: **BLOCK**
- Trust score: **0**
- Risk score: **100**
- AI provider: `disabled`
- AI summary: AI evaluation disabled.

- `MEDIUM` `MISSING_STORY_TITLE` (rule) - Story title is empty.
  - Recommendation: Provide a concise descriptive story title.
- `HIGH` `TENANT_CONTEXT_MISMATCH` (rule) - Story context tenant does not match batch tenant.
  - Recommendation: Sync story context tenant with the owning tenant.
- `MEDIUM` `INVALID_PUBLISH_DATE` (rule) - Publish date is not ISO-compatible.
  - Recommendation: Use ISO date format such as YYYY-MM-DD.
- `MEDIUM` `UNSUPPORTED_MEDIA_TYPE` (rule) - Page media type is not supported.
  - Recommendation: Use page type 'image' or 'video'.
- `HIGH` `MISSING_ASSET_URL` (rule) - Page asset URL is missing.
  - Recommendation: Attach a valid media asset URL before publishing.
- `MEDIUM` `EXTERNAL_DOMAIN_RISK` (rule) - CTA URL points to a domain not clearly related to tenant.
  - Recommendation: Verify destination domain or whitelist trusted partner domains.
- `HIGH` `DUPLICATE_PAGE_ID` (rule) - Duplicate page_id detected in story pages.
  - Recommendation: Ensure each page has a unique page_id.
- `MEDIUM` `MISSING_CTA` (rule) - Page action CTA text is missing.
  - Recommendation: Add a CTA text aligned with the intended action.
- `HIGH` `MISSING_ACTION_URL` (rule) - Page action URL is missing.
  - Recommendation: Provide a destination URL for the CTA.
