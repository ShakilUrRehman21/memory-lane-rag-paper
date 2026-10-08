import pytest
from pathlib import Path
from app.core.database import init_db
from app.ingestion.ingestion_service import ingestion_service
from app.storage.repository import Repository
from app.models.schemas import MemoryType, DateSource

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

def test_ingest_text_with_quad_dates():
    sample_text = """
    # Personal Reflections - May 2025
    
    Looking back at my career journey:
    In 2022, I don't think AI is relevant to my career. I was focused purely on Java backend systems.
    
    In March 2023, I started learning machine learning and PyTorch out of curiosity.
    
    By Summer 2024, I decided to build AI applications full time.
    
    Now in 2025, my goal is to work as an AI engineer at a top lab.
    """

    doc = ingestion_service.ingest_text_content(
        content=sample_text,
        title="2025 Reflection Note",
        document_date="2025-05-15"
    )

    assert doc is not None
    assert doc.id.startswith("doc_")
    assert doc.chunk_count > 0
    assert doc.tmu_count > 0

    # Retrieve TMUs
    tmus = Repository.list_tmus(user_id="default_user")
    assert len(tmus) >= 3

    # Check the 2022 statement: doc_date is 2025, but event_date is 2022!
    stmt_2022 = next((t for t in tmus if "2022" in (t.event_date_start or "")), None)
    assert stmt_2022 is not None
    assert stmt_2022.event_date_start.startswith("2022")
    assert stmt_2022.date_source == DateSource.EXPLICIT_IN_TEXT
    assert stmt_2022.stance_polarity < 0  # "don't think AI is relevant" should have negative polarity!
    assert "AI" in stmt_2022.entities or "Java" in stmt_2022.entities

    # Check 2025 goal
    stmt_2025 = next((t for t in tmus if "work as an AI engineer" in t.statement), None)
    assert stmt_2025 is not None
    assert stmt_2025.memory_type == MemoryType.GOAL
    assert stmt_2025.stance_polarity > 0

    # Clean up test doc
    assert Repository.delete_document(doc.id) is True
    assert Repository.get_document(doc.id) is None
