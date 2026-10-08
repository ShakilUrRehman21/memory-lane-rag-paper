import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_health_check():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "Memory Lane RAG" in data["service"]

def test_document_ingestion_and_query_api():
    # 1. Ingest text document via API
    ingest_payload = {
        "title": "API Test Journal 2024",
        "content": "In 2024, I decided to transition my work towards AI engineering and LLMs. I am excited.",
        "user_id": "api_test_user",
        "document_date": "2024-03-01",
        "file_type": "txt"
    }
    resp = client.post("/api/documents/text", json=ingest_payload)
    assert resp.status_code == 200
    doc_data = resp.json()
    assert doc_data["title"] == "API Test Journal 2024"
    doc_id = doc_data["id"]

    # 2. Query via Ask Memory Lane API
    query_payload = {
        "query": "What did I decide in 2024?",
        "user_id": "api_test_user",
        "pipeline_mode": "memory_lane",
        "top_k": 5
    }
    q_resp = client.post("/api/query", json=query_payload)
    assert q_resp.status_code == 200
    q_data = q_resp.json()
    assert len(q_data["timeline"]) >= 1
    assert len(q_data["grounded_claims"]) >= 1
    assert "answer" in q_data

    # 3. Timeline API
    t_resp = client.get("/api/timeline?user_id=api_test_user")
    assert t_resp.status_code == 200
    t_data = t_resp.json()
    assert len(t_data) >= 1

    # 4. Graph API
    g_resp = client.get("/api/graph?user_id=api_test_user")
    assert g_resp.status_code == 200
    g_data = g_resp.json()
    assert "nodes" in g_data

    # Cleanup
    del_resp = client.delete(f"/api/documents/{doc_id}")
    assert del_resp.status_code == 200

def test_research_benchmark_suite():
    bench_payload = {
        "run_name": "Automated CI Evaluation Run",
        "test_suite": "temporal_longitudinal_v1",
        "pipelines": ["baseline", "temporal", "memory_lane"]
    }
    resp = client.post("/api/research/benchmark", json=bench_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "metrics" in data
    assert "baseline" in data["metrics"]
    assert "temporal" in data["metrics"]
    assert "memory_lane" in data["metrics"]

    # Verify that Memory Lane has higher or equal Temporal Coverage Recall compared to Baseline
    base_tcr = data["metrics"]["baseline"]["temporal_coverage_recall"]
    ml_tcr = data["metrics"]["memory_lane"]["temporal_coverage_recall"]
    assert ml_tcr >= base_tcr

    # Verify run list endpoint
    runs_resp = client.get("/api/research/runs")
    assert runs_resp.status_code == 200
    runs = runs_resp.json()
    assert len(runs) >= 1
