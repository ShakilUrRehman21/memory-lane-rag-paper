import pytest
from app.core.database import init_db
from app.ingestion.ingestion_service import ingestion_service
from app.reasoning.change_detector import ChangePointDetector
from app.reasoning.contradiction_detector import ContradictionDetector
from app.reasoning.version_diff import VersionDiffEngine
from app.reasoning.memory_graph import MemoryGraphBuilder

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_change_and_contradiction_detection():
    uid = "test_user_phase3"
    # Ingest historical trajectory with a clear reversal and gradual evolution
    ingestion_service.ingest_text_content(
        content="In 2022, I don't think AI is relevant to my career. I prefer Java backend work.",
        title="Journal 2022",
        document_date="2022-04-01",
        user_id=uid
    )
    ingestion_service.ingest_text_content(
        content="In 2025, I want to work as an AI engineer. AI is my primary focus now.",
        title="Journal 2025",
        document_date="2025-05-01",
        user_id=uid
    )

    # 1. Test Contradiction Detector scoped to this user
    contradictions = ContradictionDetector.detect_contradictions(user_id=uid)
    assert len(contradictions) >= 1
    reversal = contradictions[0]
    rationale_lower = reversal.evidence_rationale.lower()
    assert "artificial intelligence" in rationale_lower or "ai" in rationale_lower
    assert reversal.confidence >= 0.7

    # 2. Test Change-Point Detector scoped to this user
    changes = ChangePointDetector.detect_all_changes(user_id=uid)
    assert len(changes) >= 1
    cp = next((c for c in changes if "AI" in c.topic_or_entity or "Artificial" in c.topic_or_entity), changes[0])
    assert cp.from_period.startswith("2022")
    assert cp.to_period.startswith("2025")
    assert cp.change_type in ["reversal", "sudden_shift", "gradual_evolution"]
    assert cp.uncertainty_bounds is not None

def test_version_diff_and_memory_graph():
    uid = "test_user_version_diff"
    # Ingest two resume versions
    ingestion_service.ingest_text_content(
        content="Skills: Java, Spring Boot, MySQL, Docker. Goal: Backend Engineering.",
        title="Resume 2022",
        document_date="2022-01-15",
        user_id=uid
    )
    ingestion_service.ingest_text_content(
        content="Skills: Python, PyTorch, Transformers, LLMs, Docker. Goal: AI Engineer.",
        title="Resume 2025",
        document_date="2025-01-15",
        user_id=uid
    )

    # Test Version Diff
    diff = VersionDiffEngine.compare_versions(
        series_name="Resume",
        earlier_label="2022",
        later_label="2025"
    )
    assert diff is not None
    assert any("AI" in s or "Python" in s or "PyTorch" in s for s in diff.added_skills_or_topics)
    assert any("Java" in s for s in diff.removed_skills_or_topics)
    assert "Docker" in diff.retained_skills_or_topics

    # Test Memory Graph
    graph = MemoryGraphBuilder.build_graph(user_id=uid)
    assert len(graph["nodes"]) > 0
    assert len(graph["edges"]) > 0
