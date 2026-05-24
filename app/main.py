from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi import File, Form, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.models import Database
from app.pipeline import run_qa_batch
from app.schemas import QARunResult, TenantBatchInput
from app.settings import load_environment

load_environment()
app = FastAPI(title="Story QA Service", version="0.1.0")
templates = Jinja2Templates(directory="app/templates")
db = Database("output/story_trust.db")


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/qa/run", response_model=QARunResult)
def run_qa(
    payload: TenantBatchInput,
    use_ai: bool = Query(default=True),
    persist: bool = Query(default=True),
    source_label: str = Query(default="api_payload"),
) -> QARunResult:
    run_result = run_qa_batch(payload, use_ai=use_ai, source_label=source_label)
    if persist:
        db.save_run(run_result)
    return run_result


@app.get("/qa/runs")
def list_runs(limit: int = Query(default=20, ge=1, le=100)) -> list[dict]:
    return db.list_runs(limit=limit)


@app.get("/qa/runs/{run_id}")
def get_run_stories(run_id: str) -> dict:
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    stories = db.list_story_results(run_id)
    return {"run": run, "stories": stories}


@app.get("/qa/stories/{story_result_id}")
def get_story(story_result_id: int) -> dict:
    story = db.get_story_result(story_result_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story result not found")
    return story


@app.get("/dashboard")
def dashboard(request: Request):
    runs = db.list_runs(limit=25)
    sample_payload = _read_default_payload()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "runs": runs,
            "sample_payload": sample_payload,
        },
    )


@app.post("/dashboard/run")
async def dashboard_trigger_run(
    payload_json: str = Form(default=""),
    payload_file: UploadFile | None = File(default=None),
    source_label: str = Form(default="data/sample_response.json"),
    use_ai: str | None = Form(default=None),
):
    try:
        payload_text = payload_json.strip()
        resolved_source_label = source_label.strip() or "data/sample_response.json"

        if payload_file and payload_file.filename:
            file_bytes = await payload_file.read()
            payload_text = file_bytes.decode("utf-8")
            if not source_label.strip() or source_label.strip() == "data/sample_response.json":
                resolved_source_label = payload_file.filename

        if not payload_text:
            raise ValueError("Provide payload JSON in textarea or upload a JSON file.")

        payload = TenantBatchInput.model_validate(json.loads(payload_text))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {exc}") from exc
    run_result = run_qa_batch(payload, use_ai=bool(use_ai), source_label=resolved_source_label)
    db.save_run(run_result)
    return RedirectResponse(url=f"/dashboard/runs/{run_result.run_id}", status_code=303)


@app.get("/dashboard/runs/{run_id}")
def dashboard_run(request: Request, run_id: str):
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    stories = db.list_story_results(run_id)
    top_issues: dict[str, int] = {}
    for story in stories:
        for issue in story["issues"]:
            code = issue["code"]
            top_issues[code] = top_issues.get(code, 0) + 1

    sorted_issue_counts = sorted(top_issues.items(), key=lambda item: item[1], reverse=True)
    return templates.TemplateResponse(
        request=request,
        name="run.html",
        context={
            "run": run,
            "stories": stories,
            "issue_counts": sorted_issue_counts[:10],
            "ai_log_tail": _read_ai_log_tail(limit=60),
        },
    )


@app.get("/dashboard/stories/{story_result_id}")
def dashboard_story(request: Request, story_result_id: int):
    story = db.get_story_result(story_result_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story result not found")
    return templates.TemplateResponse(
        request=request,
        name="story.html",
        context={"story": story},
    )


def _read_default_payload() -> str:
    sample_path = Path("data/sample_response.json")
    if sample_path.exists():
        return sample_path.read_text(encoding="utf-8")
    return "{}"


def _read_ai_log_tail(limit: int = 60) -> list[str]:
    log_path = Path("output/ai_evaluator.log")
    if not log_path.exists():
        return []

    lines = log_path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return []

    filtered: list[str] = []
    include_trace = False
    for line in lines:
        if "| ERROR |" in line:
            filtered.append(line)
            include_trace = True
            continue
        if include_trace:
            if line.startswith("Traceback") or line.startswith("  ") or line.strip() == "":
                filtered.append(line)
                continue
            include_trace = False

    if limit <= 0:
        return filtered
    return filtered[-limit:]

