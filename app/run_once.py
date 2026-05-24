from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.models import Database
from app.pipeline import run_qa_batch
from app.reporter import write_json_report, write_markdown_report
from app.schemas import TenantBatchInput
from app.settings import load_environment

load_environment()

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Story QA once from input JSON.")
    parser.add_argument("--input", required=True, help="Path to input JSON payload.")
    parser.add_argument("--output", default="output/qa_report.json", help="Path for JSON report.")
    parser.add_argument("--markdown", default="output/qa_report.md", help="Path for markdown report.")
    parser.add_argument("--db", default="output/story_trust.db", help="SQLite database path.")
    parser.add_argument("--source-label", default="", help="Source label shown in dashboard.")
    parser.add_argument("--use-ai", action="store_true", help="Enable semantic AI evaluator.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with open(args.input, "r", encoding="utf-8") as file:
        payload = TenantBatchInput.model_validate(json.load(file))

    source_label = args.source_label or Path(args.input).as_posix()
    result = run_qa_batch(payload, use_ai=args.use_ai, source_label=source_label)
    write_json_report(result, args.output)
    write_markdown_report(result, args.markdown)

    db = Database(args.db)
    db.save_run(result)

    print(f"Run complete: {result.run_id}")
    print(f"Stories checked: {result.summary.stories_checked}")
    print(f"Passed: {result.summary.passed}, Review: {result.summary.needs_review}, Blocked: {result.summary.blocked}")
    print(f"Average trust score: {result.summary.average_trust_score}")
    print(f"JSON report: {args.output}")
    print(f"Markdown report: {args.markdown}")


if __name__ == "__main__":
    main()

