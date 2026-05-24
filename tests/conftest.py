from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.models import Database
from app.schemas import TenantBatchInput


@pytest.fixture
def sample_payload_dict() -> dict:
    sample_path = Path("data/sample_response.json")
    return json.loads(sample_path.read_text(encoding="utf-8"))


@pytest.fixture
def sample_payload(sample_payload_dict: dict) -> TenantBatchInput:
    return TenantBatchInput.model_validate(sample_payload_dict)


@pytest.fixture
def app_client(tmp_path: Path):
    main_module = importlib.import_module("app.main")
    main_module.db = Database(str(tmp_path / "test_story_trust.db"))
    client = TestClient(main_module.app)
    return {"client": client, "main": main_module}

