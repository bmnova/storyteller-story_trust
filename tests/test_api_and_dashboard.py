from __future__ import annotations

import json


def test_health_endpoint(app_client) -> None:
    client = app_client["client"]
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_run_with_source_label_and_no_persist(app_client, sample_payload_dict: dict) -> None:
    client = app_client["client"]
    response = client.post(
        "/qa/run?use_ai=false&persist=false&source_label=api_pytest",
        json=sample_payload_dict,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["source_label"] == "api_pytest"
    assert payload["summary"]["stories_checked"] == len(sample_payload_dict["stories"])
    assert "ai_provider" in payload["stories"][0]


def test_dashboard_run_trigger_with_textarea_payload(app_client, sample_payload_dict: dict) -> None:
    client = app_client["client"]
    main_module = app_client["main"]
    response = client.post(
        "/dashboard/run",
        data={
            "payload_json": json.dumps(sample_payload_dict),
            "source_label": "textarea_pytest",
            "use_ai": "on",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/dashboard/runs/run_")
    latest_run = main_module.db.list_runs(limit=1)[0]
    assert latest_run["source_label"] == "textarea_pytest"


def test_dashboard_run_trigger_with_uploaded_file(app_client) -> None:
    client = app_client["client"]
    main_module = app_client["main"]
    with open("data/sample_response.json", "rb") as upload_file:
        response = client.post(
            "/dashboard/run",
            data={"payload_json": "", "source_label": "data/sample_response.json", "use_ai": "on"},
            files={"payload_file": ("uploaded_payload.json", upload_file, "application/json")},
            follow_redirects=False,
        )

    assert response.status_code == 303
    latest_run = main_module.db.list_runs(limit=1)[0]
    assert latest_run["source_label"] == "uploaded_payload.json"


def test_dashboard_run_trigger_invalid_payload_returns_400(app_client) -> None:
    client = app_client["client"]
    response = client.post(
        "/dashboard/run",
        data={"payload_json": "not-json", "source_label": "bad_payload"},
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "Invalid payload" in response.json()["detail"]

