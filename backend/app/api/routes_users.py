import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from app.models.schemas import UserCreate, UserResponse, LodgeThoughtRequest, TMUResponse, TMUCreate, DateSource, DateGranularity
from app.storage.repository import Repository
from app.ingestion.tmu_extractor import TMUExtractor
from app.ingestion.date_extractor import DateExtractor
from app.reasoning.change_detector import ChangePointDetector
from app.reasoning.contradiction_detector import ContradictionDetector
from app.reasoning.memory_graph import MemoryGraphBuilder

router = APIRouter(prefix="/users", tags=["users"])

@router.get("", response_model=List[UserResponse])
def list_users():
    users = Repository.list_users()
    if not users:
        # Seed default demo user if empty
        default_u = Repository.create_user(
            user_id="default_user",
            username="alex_chen",
            display_name="Alex Chen",
            avatar_color="#38bdf8",
            bio="Software Engineer -> AI Researcher (2019-2026 Archive)"
        )
        return [default_u]
    return users

@router.post("", response_model=UserResponse)
def create_user(u_in: UserCreate):
    existing = Repository.get_user_by_username(u_in.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists.")
    user_id = f"user_{uuid.uuid4().hex[:10]}"
    return Repository.create_user(
        user_id=user_id,
        username=u_in.username,
        display_name=u_in.display_name,
        avatar_color=u_in.avatar_color,
        bio=u_in.bio
    )

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: str):
    u = Repository.get_user(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return u

@router.post("/{user_id}/lodge", response_model=TMUResponse)
def lodge_thought(user_id: str, req: LodgeThoughtRequest):
    """
    Directly lodges a user thought, belief, goal, decision, or time capsule.
    Supports lodging current thoughts today, or backfilling past historical thoughts (e.g. 5 or 7 years ago).
    """
    user = Repository.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    event_dt = req.event_date or today_str
    
    # Create lightweight container document for this lodged memory
    doc_id = f"doc_lodge_{uuid.uuid4().hex[:10]}"
    doc_title = f"Memory Capsule ({event_dt[:7]})"
    doc_record = Repository.create_document(
        doc_id=doc_id,
        user_id=user_id,
        title=doc_title,
        file_path="memory_lane://lodged",
        file_type="lodge",
        file_size=len(req.statement),
        hash_sha256=f"lodge_{uuid.uuid4().hex[:12]}",
        document_date=today_str,
        metadata={"lodged": True, "context_note": req.context_note}
    )

    # Insert single chunk
    chk_id = f"{doc_id}_chk_0"
    Repository.insert_chunks([{
        "id": chk_id,
        "document_id": doc_id,
        "chunk_index": 0,
        "content": req.statement,
        "token_count": max(1, len(req.statement) // 4),
        "page_number": 1,
        "start_char": 0,
        "end_char": len(req.statement)
    }], user_id=user_id)

    # Resolve stance polarity
    polarity = req.stance_polarity if req.stance_polarity is not None else TMUExtractor._compute_stance_polarity(req.statement)
    entities = req.entities if req.entities is not None else TMUExtractor._extract_entities(req.statement)
    topics = req.topics if req.topics is not None else TMUExtractor._extract_topics(req.statement, entities)

    tmu = TMUCreate(
        document_id=doc_id,
        chunk_id=chk_id,
        user_id=user_id,
        memory_type=req.memory_type,
        statement=req.statement,
        event_date_start=event_dt,
        event_date_end=event_dt,
        date_granularity=DateGranularity.DAY if len(event_dt) >= 10 else DateGranularity.YEAR,
        date_confidence=1.0,
        date_source=DateSource.USER_OVERRIDE,
        stance_polarity=polarity,
        entities=entities,
        topics=topics
    )

    tmu_ids = Repository.insert_tmus([tmu])
    tmu_id = tmu_ids[0]

    # Re-evaluate change points and relationships for this user
    ChangePointDetector.detect_all_changes(user_id=user_id)
    ContradictionDetector.detect_contradictions(user_id=user_id)
    MemoryGraphBuilder.build_graph(user_id=user_id)

    saved_tmu = Repository.get_tmu(tmu_id)
    if not saved_tmu:
        raise HTTPException(status_code=500, detail="Failed to retrieve lodged memory")
    return saved_tmu
