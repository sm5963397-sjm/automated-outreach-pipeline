from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.routes import pipeline as pipeline_routes
from app.models.enums import CampaignStatus


def test_start_pipeline_endpoint_queues_task(
    api_client: TestClient,
    monkeypatch,
) -> None:
    queued: dict[str, tuple] = {}

    def fake_delay(*args, **kwargs):
        queued["args"] = args
        queued["kwargs"] = kwargs

    monkeypatch.setattr(pipeline_routes.run_pipeline_task, "delay", fake_delay)
    response = api_client.post("/api/v1/pipeline/start", json={"domain": "https://openai.com"})

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == CampaignStatus.PENDING.value
    assert queued["args"][1] == "openai.com"

    status_response = api_client.get(f"/api/v1/pipeline/{body['campaign_id']}")
    assert status_response.status_code == 200
    assert status_response.json()["campaign"]["source_domain"] == "openai.com"


def test_list_endpoints_return_empty_collections(api_client: TestClient) -> None:
    for path in ["/api/v1/companies", "/api/v1/contacts", "/api/v1/campaigns", "/api/v1/emails"]:
        response = api_client.get(path)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
