from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_analyze_with_demo_dataset_finds_seeded_anomalies(client: TestClient):
    resp = client.post("/analyze", params={"use_demo": "true"})
    assert resp.status_code == 200

    body = resp.json()
    assert body["source"] == "demo"
    runs_by_id = {run["run_id"]: run for run in body["runs"]}
    assert set(runs_by_id) == {"RUN-2026-014", "RUN-2026-015", "RUN-2026-016"}

    good_run = runs_by_id["RUN-2026-014"]
    assert good_run["electrode_trend"]["trend"] == "stable"
    assert good_run["anomalies"] == []
    assert all(c["degradation_efficiency_pct"] >= 95.0 for c in good_run["compounds"])

    degraded_run = runs_by_id["RUN-2026-015"]
    assert degraded_run["electrode_trend"]["trend"] == "degrading"
    assert any(a["type"] == "voltage_spike" for a in degraded_run["anomalies"])

    interrupted_run = runs_by_id["RUN-2026-016"]
    assert any(a["type"] == "flow_interruption" for a in interrupted_run["anomalies"])


def test_analyze_rejects_csv_with_missing_columns(client: TestClient):
    bad_csv = b"run_id,timestamp\nRUN-1,2026-01-01T09:00:00\n"
    resp = client.post("/analyze", files={"file": ("bad.csv", bad_csv, "text/csv")})
    assert resp.status_code == 422
    assert "Missing required columns" in resp.json()["detail"]


def test_analyze_requires_file_or_demo_flag(client: TestClient):
    resp = client.post("/analyze")
    assert resp.status_code == 422


def test_report_endpoint_generates_from_analyze_output(client: TestClient):
    analyze_resp = client.post("/analyze", params={"use_demo": "true"})
    metrics = analyze_resp.json()

    report_resp = client.post("/report", json=metrics)
    assert report_resp.status_code == 200

    body = report_resp.json()
    assert body["source"] in ("llm", "template_fallback")
    assert "RUN-2026-014" in body["markdown"]
    assert "Generated with AI assistance" in body["markdown"]


def test_report_endpoint_rejects_empty_runs(client: TestClient):
    resp = client.post("/report", json={"source": "demo", "generated_at": "2026-01-01T00:00:00", "runs": []})
    assert resp.status_code == 422


def test_feed_endpoint_returns_seeded_snapshot(client: TestClient):
    resp = client.get("/feed")
    assert resp.status_code == 200

    body = resp.json()
    assert body["source"] == "snapshot"
    assert 6 <= len(body["items"]) <= 8

    categories = {item["category"] for item in body["items"]}
    assert categories == {"Regulation", "Litigation", "Science", "Industry"}
    assert all(1 <= item["relevance_score"] <= 5 for item in body["items"])

    published_dates = [item["published_at"] for item in body["items"]]
    assert published_dates == sorted(published_dates, reverse=True)
