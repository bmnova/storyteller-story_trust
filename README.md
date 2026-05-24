# Story QA Service — Automated Content Trust Checks

## TL;DR

This prototype is a backend-style Story Trust QA service. It takes structured Story batch data, runs deterministic checks plus optional AI semantic evaluation, and returns a 0–100 Trust Score with `pass` / `review` / `block` verdicts.

For the take-home, it can be run locally via CLI or dashboard. In production, the same pipeline would run as a worker on every synced Story batch.

The prototype does not require an API key to run. Without keys, it falls back to deterministic mock-AI heuristics so reviewers can still inspect the full pipeline.

**Example result:**

```json
{
  "story_id": "story_123",
  "trust_score": 84,
  "verdict": "review",
  "issues": [
    {
      "code": "CTA_DESTINATION_MISMATCH",
      "severity": "high",
      "message": "CTA says 'Buy tickets' but the URL points to /highlights."
    }
  ]
}
```

A backend-style **Content Trust & QA** service for high-volume Stories content: repeatable, automatic checks on every synced batch (not one-off manual review). The prototype runs locally; the same pipeline maps to a production worker or API on continuous ingest.

Reports are generated locally under `output/` (e.g. `qa_report.json`, `qa_report.md`) when you run the CLI below.

## 1) Problem Framing

The core problem is not one-off moderation. It is a **scalable publishing confidence** challenge:

- Story volume is too high for reliable manual review.
- Quality, trust, and professional consistency can drift across pages, metadata, CTA links, and context.
- Teams need repeatable automatic checks that can run on every sync.

## 2) What This Builds

- FastAPI backend with repeatable QA run endpoint.
- Deterministic checks for structural and policy issues.
- AI semantic evaluator layer with real LLM support (OpenAI `OPENAI_API_KEY` and/or Google Gemini `GEMINI_API_KEY` / `GOOGLE_API_KEY`) and mock fallback.
- Scoring engine with:
  - Internal `risk_score`
  - Product-facing `trust_score` where `100 = best`
  - Verdict: `pass` / `review` / `block`
- SQLite persistence of runs and story-level issues.
- Web dashboard to inspect runs, story verdicts, and issue details.
- JSON + Markdown report generation for sharing with operations/product teams.

I intentionally kept the core decision logic small and inspectable. The API/dashboard layer is included only to show how the same pipeline could be used repeatedly by product or operations teams.

## 3) Architecture

```mermaid
flowchart TD
    inputData[Input JSON batch] --> ingestService[TenantBatchInput validation]
    ingestService --> ruleEngine[DeterministicChecks]
    ingestService --> aiEngine[AISemanticEvaluator]
    ruleEngine --> scoreEngine[ScoringAndVerdict]
    aiEngine --> scoreEngine
    scoreEngine --> reports[PersistedQAResults]
    reports --> apiLayer[FastAPIEndpoints]
    reports --> webUi[DashboardViews]
```

## 4) Assumptions

- Input data is continuously synced in a structured batch shape (`tenant_id`, `stories[]`, `pages[]`, `context`).
- V1 acts as advisory trust gating (recommendation), not auto-publishing control.
- AI output must be structured and evidence-backed; deterministic checks remain first-class.
- Tenant-specific policies can be layered in after issue patterns are observed.

## 5) Run Locally

### Quick start with `run_dev.sh` (first-time reviewers)

Recommended path to run the API and dashboard without manual venv/uvicorn steps. The script creates `.venv` if needed, installs dependencies when asked, picks a free port if the default is busy, and prints the dashboard URL.

```bash
cp .env.example .env
# Optional: set OPENAI_API_KEY and/or GEMINI_API_KEY in .env for live LLM checks
chmod +x run_dev.sh
./run_dev.sh --install
```

| Flag | Purpose |
| --- | --- |
| `--install` | Create/update `.venv` and install packages from `requirements.txt` |
| `--port <n>` | Preferred port (default `8000`; script increments if occupied) |
| `-h`, `--help` | Show usage |

Without `--install`, the script still installs dependencies on first run if `uvicorn` is missing in `.venv`.

Examples:

```bash
./run_dev.sh --install              # first run: deps + server
./run_dev.sh                        # later runs (reuses existing .venv)
./run_dev.sh --port 8010            # prefer 8010, auto-fallback if taken
```

After startup, open the URL printed in the terminal (typically `http://127.0.0.1:8000/dashboard`). API docs: `http://127.0.0.1:<port>/docs`. Use **Trigger New Run** to paste JSON or upload a file. The **Use AI semantic evaluator** checkbox is on by default; uncheck it for rules-only runs. With the checkbox on and no API keys in `.env`, the pipeline falls back to `mock-ai` heuristics.

### Manual setup

From the project root (this repo):

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

Commands below assume the virtualenv is **activated** (`source .venv/bin/activate`), or prefix with `.venv/bin/` (e.g. `.venv/bin/python -m app.run_once ...`).

Configure environment (do this before starting the server or enabling `--use-ai`):

```bash
cp .env.example .env
# Optional: set OPENAI_API_KEY and/or GEMINI_API_KEY in .env for live LLM checks
```

Run a single automated QA batch from sample data (rules only; fast, no API key):

```bash
python -m app.run_once --input data/sample_response.json --output output/qa_report.json --markdown output/qa_report.md
```

With semantic AI checks (uses `OPENAI_API_KEY` / `GEMINI_API_KEY` from `.env`, else mock-ai fallback):

```bash
python -m app.run_once --input data/sample_response.json --output output/qa_report.json --markdown output/qa_report.md --use-ai
```

Optional: provide explicit source label shown on dashboard:

```bash
python -m app.run_once --input data/sample_response.json --source-label "data/sample_response.json" --use-ai
```

Start backend + dashboard manually (alternative to `run_dev.sh`):

```bash
python -m uvicorn app.main:app --reload
```

Then open (default port `8000` when using `uvicorn` directly; `run_dev.sh` may choose another port if busy):

- API docs: <http://127.0.0.1:8000/docs>
- Dashboard: <http://127.0.0.1:8000/dashboard>
- Health: <http://127.0.0.1:8000/health>
- Dashboard can trigger new runs directly via the **Trigger New Run** form.
- Trigger form supports both pasted JSON and **Upload JSON file** input.

Run tests:

```bash
python -m pytest -q
```

Live LLM smoke test (runs only if an API key exists in env):

```bash
python -m pytest -q tests/test_live_llm_smoke.py
```

### Sample data notes

- `data/sample_response.json` includes three stories: two typical payloads (`story_123`, `story_124`) and `story_125` with intentional defects (empty title, duplicate `page_id`, bad date, external domain, etc.) so blocked/review outcomes are visible in one run.
- On a rules-only run, `story_123` is typically **review** (e.g. “Buy tickets” CTA pointing at `/highlights`); `story_124` **pass**; `story_125` **block**.

## 6) AI Workflow

1. **Ingest** — `TenantBatchInput` validates the batch JSON (`tenant_id`, `stories`, pages, context).
2. **Deterministic checks** — `app/checks.py` (metadata, media type, duplicate IDs, CTA/URL alignment, domain risk).
3. **Semantic evaluation** — `app/ai_evaluator.py` sends each story to configured LLM providers in order (`STORY_TRUST_AI_PROVIDERS`, default `openai,gemini`).
4. **Score & verdict** — `app/scoring.py` aggregates issue severities into `risk_score` / `trust_score` and `pass` | `review` | `block`.
5. **Persist & report** — SQLite (`output/story_trust.db`), JSON/Markdown reports, dashboard views.

**LLM prompt (summary)** — system: content-trust QA evaluator; return strict JSON only. User payload includes `tenant_name`, full `story` object, evaluation focus (semantic mismatches, context, CTA quality), and `required_schema` for `summary`, `confidence`, and `issues[]`. Implementation: `AISemanticEvaluator._build_prompt_payload()` in `app/ai_evaluator.py`. Provider failures are logged to `output/ai_evaluator.log`; pipeline continues via `mock-ai` heuristics.

## 7) API Endpoints

- `GET /health` — service health check
- `POST /qa/run` — run QA on incoming payload; query params: `use_ai` (default `true`), `persist` (default `true`), `source_label` (default `api_payload`)
- `GET /` — redirects to `/dashboard`
- `GET /qa/runs` - list recent runs
- `GET /qa/runs/{run_id}` - run summary + story results
- `GET /qa/stories/{story_result_id}` - story detail with issues

## 8) Trust Score and Verdict Logic

- `trust_score = max(0, 100 - risk_score)`
- Verdict bands:
  - `85-100`: `pass`
  - `60-84`: `review`
  - `0-59`: `block`
- Overrides:
  - any `critical` issue => force `block` (trust capped at 59)
  - any `high` issue => if trust band would be `pass`, verdict becomes `review` (trust set to 84)

## 9) Included Check Types

Checks run in `app/pipeline.py`: deterministic rules first (`app/checks.py`), then optional AI (`app/ai_evaluator.py`). Issue `code` values below match what appears in reports and the dashboard.

### Deterministic rules (`source: rule`)

Always run; do not require an API key.

| Code | What it flags |
| --- | --- |
| `MISSING_STORY_TITLE` | Empty story title |
| `MISSING_PUBLISH_DATE` | No publish date in context |
| `INVALID_PUBLISH_DATE` | Publish date not ISO-parseable |
| `TENANT_CONTEXT_MISMATCH` | Story `context.tenant` ≠ batch `tenant_name` |
| `DUPLICATE_PAGE_ID` | Same `page_id` used on more than one page |
| `UNSUPPORTED_MEDIA_TYPE` | Page `type` not `image` or `video` |
| `MISSING_ASSET_URL` | Page media URL empty |
| `MISSING_CTA` | Page action CTA text empty |
| `MISSING_ACTION_URL` | Page action URL empty |
| `INVALID_ACTION_URL` | Action URL cannot be parsed (no valid domain) |
| `CTA_DESTINATION_MISMATCH` | CTA implies tickets (`buy` + `ticket`) but path has no `ticket` (e.g. `Buy tickets` → `/highlights`) |
| `CTA_INTENT_WEAK_MATCH` | CTA implies highlights (`watch` + `highlight`) but path lacks `highlight` or `report` |
| `LIVE_CTA_MISMATCH` | CTA implies live content but path has no `live` |
| `EXTERNAL_DOMAIN_RISK` | CTA domain not clearly related to tenant (tenant tokens not in domain; `*.storyteller.com` allowed) |

### AI semantic layer

When `--use-ai` / `use_ai=true`:

1. **Live LLM** (OpenAI or Gemini, if keys are set) — open-ended semantic review; returns structured JSON (`summary`, `confidence`, `issues[]`). Codes are model-defined (e.g. `AI_SEMANTIC_NOTE` default).
2. **`mock-ai` fallback** (no keys or all providers fail) — fixed heuristics in `app/ai_evaluator.py`:

| Code | What it flags |
| --- | --- |
| `WEAK_CONTEXT_COVERAGE` | Title suggests a matchup (`vs`) but fewer than two context categories |
| `SEMANTIC_TENANT_MISMATCH` | Same tenant/context mismatch as `TENANT_CONTEXT_MISMATCH`, surfaced again as a semantic signal |
| `GENERIC_CTA_LANGUAGE` | CTA is `click here`, `learn more`, or `tap now` |

**Note:** `TENANT_CONTEXT_MISMATCH` (rule) and `SEMANTIC_TENANT_MISMATCH` (mock-ai) can both appear on one story when AI is enabled without a live LLM. With a live LLM, mock heuristics are not used for that run.

## 10) LLM Configuration

- Provider failover is supported: evaluator tries providers in `STORY_TRUST_AI_PROVIDERS` order (default: `openai,gemini`).
- OpenAI:
  - `OPENAI_API_KEY`
  - `STORY_TRUST_LLM_MODEL` (default: `gpt-4o-mini`)
- Gemini:
  - `GEMINI_API_KEY` (or `GOOGLE_API_KEY`)
  - `STORY_TRUST_GEMINI_MODEL` (default: `gemini-2.5-flash-lite`)
- If a provider fails, evaluator tries the next provider; if all fail, it falls back to deterministic `mock-ai`.
- AI provider failures and fallback reasons are logged to `output/ai_evaluator.log`.
- `.env` is auto-loaded by both API server and CLI runner.

## 11) What Is Deliberately Not Built Yet

V1 evaluates **structured batch JSON** only (titles, context, CTA text, URLs, page types). It does **not** download or analyze story media pixels. The items below are intentionally out of scope for this prototype; section 12 lists the planned follow-ups.

| Not in V1 | Meaning |
| --- | --- |
| **Visual / media content checks** | No frame-by-frame video review, no image NSFW/logo detection, and no **OCR** (optical character recognition — extracting text from images or video frames). Trust signals come from metadata and links, not from pixels. |
| **Tenant policy builder UI** | Rules live in code (`app/checks.py`); no self-serve editor for per-tenant allowlists or custom checks. |
| **Distributed ingest workers** | No Celery/Kafka (or similar) queue; QA runs are on demand via CLI, API, or dashboard. |
| **Autonomous CMS publish control** | Verdicts are advisory (`pass` / `review` / `block`); upstream CMS is not blocked automatically (see section 4). |

## 12) What To Build Next With Engineering Support

Natural extensions after the V1 prototype, mapped to the gaps in section 11:

| Next step | Addresses (section 11) |
| --- | --- |
| **Event-driven workers** — run QA on each story sync/update via a job queue | Distributed ingest workers |
| **Tenant rule packs and allowlists** — per-`tenant_id` domain lists, CTA patterns, severity overrides (code/config first; UI later) | Tenant policy builder UI |
| **Reviewer feedback loop** — `correct issue`, `false positive`, `ignore`, `new rule` to tune rules and cut false positives | — (quality loop) |
| **Targeted multimodal checks** (optional) — LLM or dedicated services on thumbnails from `asset_url`; not a full frame/OCR moderation pipeline | Visual / media content checks |
| **Operations KPIs** — review rate, false positive rate, prevented trust incidents, time-to-fix for high-severity issues | — (observability) |

CMS integration can later **consume** verdicts (e.g. hold `block` stories for human review) without turning V1 into an autonomous publish gate — that remains a product/integration choice outside this repo.

