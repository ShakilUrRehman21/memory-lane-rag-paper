"""Regression tests for the v1.1 fixes (one test per audit finding where applicable)."""
import uuid

import numpy as np
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.evaluation.metrics import EvaluationMetrics as M
from app.ingestion.ingestion_service import ingestion_service
from app.models.schemas import ChangePointResponse, GroundedClaim, MemoryType, QueryRequest, TMUResponse
from app.reasoning.contradiction_detector import ContradictionDetector
from app.retrieval.stratified_sampler import StratifiedTemporalSampler
from app.storage.embeddings import HashEmbedder, get_embedder
from app.storage.vector_store import VectorStore, tmu_vector_store
from app.synthesis import grounded_synthesizer as gs_mod
from app.synthesis.grounded_synthesizer import grounded_synthesizer


def _uid():
    return f"u_{uuid.uuid4().hex[:8]}"


def _tmu(i, date, pol=0.0, stmt=None, ents=None, topics=None, mtype=MemoryType.BELIEF):
    return TMUResponse(id=f"t{i}", document_id="d", chunk_id="c", user_id="u", memory_type=mtype,
                       statement=stmt or f"statement {i}", event_date_start=date, event_date_end=date,
                       date_granularity="day", date_confidence=0.9, date_source="doc_metadata",
                       stance_polarity=pol, entities=ents or [], topics=topics or [], created_at=date)


# ---------------------------------------------------------------- embeddings (A1, A2)
def test_default_embedder_is_not_word_hashing():
    emb = get_embedder()
    assert emb.name != "hash"
    a, b, c = emb.embed(["I love programming in Python", "Python coding is my favourite", "I went hiking"])
    assert float(a @ b) > float(a @ c)


def test_hash_backend_preserved_for_ablation():
    v = HashEmbedder().embed(["java python"])
    assert v.shape == (1, 384) and abs(np.linalg.norm(v[0]) - 1) < 1e-5


# ---------------------------------------------------------------- vector store (A16, A19)
def test_vector_store_user_isolation_persistence_and_delete():
    u1, u2 = _uid(), _uid()
    vs = VectorStore("unit_test_index")
    vs.add_many([("a", "apples and pears", {"user_id": u1, "document_id": "doc1"}),
                 ("b", "bananas", {"user_id": u2, "document_id": "doc2"})])
    assert [r["id"] for r in vs.search("fruit", top_k=5, filter_meta={"user_id": u1})] == ["a"]
    fresh = VectorStore("unit_test_index")  # new instance reads from SQLite
    assert [r["id"] for r in fresh.search("fruit", 5, {"user_id": u2})] == ["b"]
    fresh.delete_by_document("doc1")
    assert fresh.search("fruit", 5, {"user_id": u1}) == []


def test_search_requires_user():
    import pytest
    with pytest.raises(ValueError):
        tmu_vector_store.search("x", 5, {})


def test_chunk_vectors_carry_user_id_and_upload_names_unique():
    u1, u2 = _uid(), _uid()
    d1 = ingestion_service.ingest_text_content("Same title text for user one, long enough.", "Shared Title", u1, "2021-01-01")
    d2 = ingestion_service.ingest_text_content("Different text written by user two, long enough.", "Shared Title", u2, "2021-01-01")
    assert d1.file_path != d2.file_path
    with get_db() as c:
        users = {r[0] for r in c.execute("SELECT user_id FROM vectors WHERE index_name='chunks' AND document_id IN (?,?)",
                                          (d1.id, d2.id))}
    assert users == {u1, u2}


# ---------------------------------------------------------------- stratification (A6, A7)
def test_adaptive_epochs_stratify_within_one_year():
    items = [{"tmu": _tmu(i, f"2023-{m:02d}-15"), "score": 1.0 - i * 0.01} for i, m in enumerate([12] * 8 + [1, 6])]
    year = StratifiedTemporalSampler.sample(items, target_k=3, epoch_mode="year")
    adaptive = StratifiedTemporalSampler.sample(items, target_k=3, epoch_mode="adaptive")
    months = lambda xs: {x["tmu"].event_date_start[5:7] for x in xs}
    assert months(year) == {"12"}               # one calendar year -> no stratification
    assert {"01", "06", "12"} <= months(adaptive)


def test_stratification_no_longer_depends_on_query_wording():
    uid = _uid()
    for y in range(2018, 2024):
        ingestion_service.ingest_text_content(f"In this period I kept writing notes about Elixir and other things {y}.",
                                              f"note {y}", uid, f"{y}-05-01")
    for i in range(10):
        ingestion_service.ingest_text_content(f"Elixir again, yet another Elixir note number {i}.", f"late {i}", uid,
                                              "2024-03-01")
    plain = grounded_synthesizer.synthesize(QueryRequest(query="What do I think about Elixir?", user_id=uid, top_k=6,
                                                         stratification_mode="always"))
    assert plain.stratified
    years = {p.event_date[:4] for p in plain.timeline}
    assert len(years) >= 5


# ---------------------------------------------------------------- pipelines (A5)
def test_temporal_pipeline_differs_from_memory_lane():
    uid = _uid()
    ingestion_service.ingest_text_content("I don't think Rust is worth my time.", "a", uid, "2019-01-01")
    ingestion_service.ingest_text_content("I started learning Rust and I am excited about it.", "b", uid, "2022-01-01")
    t = grounded_synthesizer.synthesize(QueryRequest(query="How has my view on Rust changed?", user_id=uid,
                                                     pipeline_mode="temporal", top_k=4))
    m = grounded_synthesizer.synthesize(QueryRequest(query="How has my view on Rust changed?", user_id=uid,
                                                     pipeline_mode="memory_lane", top_k=4))
    assert t.pipeline_used == "temporal" and t.detected_changes == [] and not t.stratified
    assert m.pipeline_used == "memory_lane" and len(m.detected_changes) >= 1


# ---------------------------------------------------------------- change detection (A8, A18)
def test_query_focused_change_detection_handles_unlisted_topic_and_is_read_only():
    uid = _uid()
    ingestion_service.ingest_text_content("I honestly don't think Haskell is relevant to my work.", "a", uid, "2019-03-01")
    ingestion_service.ingest_text_content("I started learning Haskell and I am excited about it.", "b", uid, "2022-03-01")
    with get_db() as c:
        before = c.execute("SELECT COUNT(*) FROM change_points").fetchone()[0]
    r = grounded_synthesizer.synthesize(QueryRequest(query="How has my view on Haskell changed over the years?",
                                                     user_id=uid, top_k=5))
    assert any(c.change_type == "reversal" and "haskell" in c.topic_or_entity.lower() for c in r.detected_changes)
    assert any("haskell" in x.evidence_rationale.lower() for x in r.potential_contradictions)
    with get_db() as c:
        assert c.execute("SELECT COUNT(*) FROM change_points").fetchone()[0] == before


def test_contradiction_message_reports_true_direction():
    a = _tmu(1, "2020-01-01", 0.9, "I love Java.", ents=["Java"])
    b = _tmu(2, "2022-01-01", -0.9, "I abandoned Java.", ents=["Java"])
    rel = ContradictionDetector.detect_contradictions("u", [a, b], persist=False)[0]
    assert "polarity was positive" in rel.evidence_rationale and "became negative" in rel.evidence_rationale


# ---------------------------------------------------------------- metrics (A10-A12)
def test_metrics_no_longer_fixed_by_construction():
    claims = [GroundedClaim(claim_id="1", claim_text="x", claim_type="explicit", confidence=1, evidence_tmu_ids=["t2"], source_citations=[]),
              GroundedClaim(claim_id="2", claim_text="y", claim_type="explicit", confidence=1, evidence_tmu_ids=["t1"], source_citations=[])]
    tm = [_tmu(1, "2019-01-01"), _tmu(2, "2022-01-01")]
    assert M.chronological_ordering_accuracy(claims, tm, backend="llm") == 0.0
    assert M.chronological_ordering_accuracy(claims, tm, backend="deterministic") is None
    assert M.unsupported_claim_rate(claims, backend="deterministic") is None
    assert M.change_point_f1([], []) is None  # v1.0 returned 1.0 (free credit)


def test_change_f1_requires_topic_and_supports_tolerance():
    cp = ChangePointResponse(id="x", user_id="u", topic_or_entity="Java", from_period="2021-01-01",
                             to_period="2023-01-01", change_type="reversal", magnitude=0.5, earlier_memory_id="a",
                             later_memory_id="b", earlier_statement="java", later_statement="java",
                             created_at="2024-01-01")
    gt = [("2021", "2022", "reversal")]
    assert M.change_point_f1([cp], gt, topic="Java") == 0.0
    assert M.change_point_f1([cp], gt, topic="Java", year_tolerance=1) == 1.0
    assert M.change_point_f1([cp], gt, topic="Python", year_tolerance=1) == 0.0


# ---------------------------------------------------------------- LLM provenance (A21)
def test_llm_prompt_contains_evidence_and_bogus_citations_are_stripped(monkeypatch):
    from app.synthesis import llm_provider
    uid = _uid()
    ingestion_service.ingest_text_content("I started learning Go and I am excited about it.", "go", uid, "2021-01-01")
    seen = {}

    def fake_llm(api_key, prompt, system_instruction, model):
        seen["prompt"] = prompt
        return {"answer": "You like Go.", "claims": [
            {"claim_id": "c1", "claim_text": "You like Go.", "evidence_tmu_ids": ["does_not_exist"]}]}
    monkeypatch.setenv("ML_LLM_BACKEND", "openai")
    monkeypatch.setattr(llm_provider.LLMProvider, "_call_openai", staticmethod(fake_llm))
    r = grounded_synthesizer.synthesize(QueryRequest(query="Do I like Go?", user_id=uid, top_k=3))
    assert "EVIDENCE" in seen["prompt"] and "learning Go" in seen["prompt"]
    assert r.synthesis_backend == "openai"
    assert r.grounded_claims[0].evidence_tmu_ids == []
    assert M.unsupported_claim_rate(r.grounded_claims, backend="openai") == 1.0


# ---------------------------------------------------------------- API (A20)
def test_documented_benchmark_endpoint_exists():
    from app.main import app
    with TestClient(app) as c:
        assert c.post("/api/research/run-benchmark", json={"pipelines": ["baseline"]}).status_code == 200


def test_default_stratification_is_router_and_selectable_per_request():
    from app.core.config import settings
    assert settings.STRATIFICATION_MODE == "router"
    uid = _uid()
    ingestion_service.ingest_text_content("Notes about Clojure from long ago.", "a", uid, "2018-01-01")
    ingestion_service.ingest_text_content("More notes about Clojure today.", "b", uid, "2024-01-01")
    assert not grounded_synthesizer.synthesize(QueryRequest(query="What do I think about Clojure?", user_id=uid)).stratified
    assert grounded_synthesizer.synthesize(QueryRequest(query="How has my view on Clojure changed over the years?",
                                                        user_id=uid)).stratified
