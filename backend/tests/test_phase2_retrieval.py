import pytest
from app.core.database import init_db
from app.ingestion.ingestion_service import ingestion_service
from app.retrieval.query_router import QueryRouter
from app.retrieval.hybrid_retriever import hybrid_retriever
from app.models.schemas import QueryIntent

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_query_router_intents():
    r1 = QueryRouter.analyze_query("How has my opinion about AI changed?")
    assert r1["intent"] == QueryIntent.EVOLUTION_ANALYSIS
    assert r1["is_evolution_query"] is True

    r2 = QueryRouter.analyze_query("What did I think about Java in 2023?")
    assert r2["intent"] == QueryIntent.TEMPORAL_LOOKUP
    assert r2["start_year"] == 2023
    assert r2["end_year"] == 2023

    r3 = QueryRouter.analyze_query("Did I ever contradict an earlier opinion?")
    assert r3["intent"] == QueryIntent.CONTRADICTION_ANALYSIS

    r4 = QueryRouter.analyze_query("What changed between 2023 and 2026?")
    assert r4["start_year"] == 2023
    assert r4["end_year"] == 2026

def test_stratified_temporal_retrieval():
    uid = "test_user_phase2_retrieval"
    # Ingest historical milestones across multiple years
    ingestion_service.ingest_text_content(
        content="In 2022, I don't think AI is relevant to my career. Java is what I do.",
        title="Journal 2022",
        document_date="2022-04-10",
        user_id=uid
    )
    ingestion_service.ingest_text_content(
        content="In 2023, I started learning machine learning and neural networks.",
        title="Journal 2023",
        document_date="2023-05-12",
        user_id=uid
    )
    ingestion_service.ingest_text_content(
        content="In 2024, I want to build AI applications and production RAG pipelines.",
        title="Journal 2024",
        document_date="2024-06-15",
        user_id=uid
    )
    ingestion_service.ingest_text_content(
        content="In 2025, my goal is to work as an AI engineer.",
        title="Journal 2025",
        document_date="2025-07-20",
        user_id=uid
    )
    ingestion_service.ingest_text_content(
        content="In 2026, I want to conduct AI research and publish academic papers.",
        title="Journal 2026",
        document_date="2026-08-01",
        user_id=uid
    )

    # Query for longitudinal evolution
    res = hybrid_retriever.retrieve(
        query="How has my thinking about AI changed?",
        user_id=uid,
        top_k=5
    )
    tmus = res["results"]
    assert len(tmus) >= 3

    # Ensure chronological diversity across the retrieved set
    years = [t.event_date_start[:4] for t in tmus if t.event_date_start]
    assert len(set(years)) >= 3, f"Expected coverage across multiple years, got: {years}"
