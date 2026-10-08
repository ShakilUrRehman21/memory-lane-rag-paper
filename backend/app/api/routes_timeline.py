from typing import List, Optional
from fastapi import APIRouter, Query
from app.models.schemas import TimelinePoint, MemoryType
from app.storage.repository import Repository

router = APIRouter(prefix="/timeline", tags=["timeline"])

@router.get("", response_model=List[TimelinePoint])
def get_timeline(
    user_id: str = "default_user",
    topic: Optional[str] = None,
    entity: Optional[str] = None,
    memory_type: Optional[MemoryType] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None
):
    tmus = Repository.list_tmus(
        user_id=user_id,
        topic=topic,
        entity=entity,
        memory_type=memory_type,
        start_year=start_year,
        end_year=end_year
    )
    
    timeline = []
    for t in tmus:
        dt = t.event_date_start or t.created_at
        timeline.append(TimelinePoint(
            period=dt[:7] if dt else "Unrecorded",
            date_display=dt[:10] if dt else "Unrecorded",
            event_date=dt or "Unrecorded",
            headline=t.statement[:60] + ("..." if len(t.statement) > 60 else ""),
            statement=t.statement,
            memory_type=t.memory_type,
            document_title=t.document_title or "Document",
            document_id=t.document_id,
            tmu_id=t.id,
            confidence=t.date_confidence,
            stance_polarity=t.stance_polarity
        ))
    return timeline
