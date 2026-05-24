from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.schemas import QARunResult


class Database:
    def __init__(self, db_path: str = "story_trust.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS qa_runs (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    tenant_name TEXT NOT NULL,
                    source_label TEXT NOT NULL DEFAULT 'api_payload',
                    stories_checked INTEGER NOT NULL,
                    passed INTEGER NOT NULL,
                    needs_review INTEGER NOT NULL,
                    blocked INTEGER NOT NULL,
                    average_trust_score REAL NOT NULL
                )
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(qa_runs)").fetchall()
            }
            if "source_label" not in columns:
                connection.execute(
                    "ALTER TABLE qa_runs ADD COLUMN source_label TEXT NOT NULL DEFAULT 'api_payload'"
                )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS story_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    story_id TEXT NOT NULL,
                    story_title TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    risk_score INTEGER NOT NULL,
                    trust_score INTEGER NOT NULL,
                    ai_provider TEXT NOT NULL DEFAULT 'disabled',
                    ai_summary TEXT,
                    ai_confidence REAL NOT NULL,
                    issues_json TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES qa_runs(id)
                )
                """
            )
            story_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(story_results)").fetchall()
            }
            if "ai_provider" not in story_columns:
                connection.execute(
                    "ALTER TABLE story_results ADD COLUMN ai_provider TEXT NOT NULL DEFAULT 'disabled'"
                )

    def save_run(self, run_result: QARunResult) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO qa_runs (
                    id, created_at, tenant_id, tenant_name, source_label, stories_checked,
                    passed, needs_review, blocked, average_trust_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_result.run_id,
                    run_result.created_at.isoformat(),
                    run_result.tenant_id,
                    run_result.tenant_name,
                    run_result.source_label,
                    run_result.summary.stories_checked,
                    run_result.summary.passed,
                    run_result.summary.needs_review,
                    run_result.summary.blocked,
                    run_result.summary.average_trust_score,
                ),
            )

            for story in run_result.stories:
                connection.execute(
                    """
                    INSERT INTO story_results (
                        run_id, story_id, story_title, verdict, risk_score,
                        trust_score, ai_provider, ai_summary, ai_confidence, issues_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_result.run_id,
                        story.story_id,
                        story.story_title,
                        story.verdict,
                        story.risk_score,
                        story.trust_score,
                        story.ai_provider,
                        story.ai_summary,
                        story.ai_confidence,
                        json.dumps([issue.model_dump() for issue in story.issues]),
                    ),
                )

    def list_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, created_at, tenant_id, tenant_name, source_label, stories_checked,
                       passed, needs_review, blocked, average_trust_score
                FROM qa_runs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, created_at, tenant_id, tenant_name, source_label, stories_checked,
                       passed, needs_review, blocked, average_trust_score
                FROM qa_runs
                WHERE id = ?
                """,
                (run_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_story_results(self, run_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, run_id, story_id, story_title, verdict, risk_score,
                       trust_score, ai_provider, ai_summary, ai_confidence, issues_json
                FROM story_results
                WHERE run_id = ?
                ORDER BY id ASC
                """,
                (run_id,),
            ).fetchall()
        return [self._decode_story_row(dict(row)) for row in rows]

    def get_story_result(self, story_result_id: int) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, run_id, story_id, story_title, verdict, risk_score,
                       trust_score, ai_provider, ai_summary, ai_confidence, issues_json
                FROM story_results
                WHERE id = ?
                """,
                (story_result_id,),
            ).fetchone()
        return self._decode_story_row(dict(row)) if row else None

    @staticmethod
    def _decode_story_row(row: dict[str, Any]) -> dict[str, Any]:
        row["issues"] = json.loads(row.pop("issues_json"))
        return row

