from typing import List
from fastapi import APIRouter
from app.models.schemas import ChangePointResponse, MemoryRelationshipResponse
from app.reasoning.change_detector import ChangePointDetector
from app.reasoning.contradiction_detector import ContradictionDetector
from app.storage.repository import Repository

router = APIRouter(tags=["changes"])

@router.get("/changes", response_model=List[ChangePointResponse])
def get_changes(user_id: str = "default_user"):
    # Re-detect or list cached
    changes = Repository.list_change_points(user_id=user_id)
    if not changes:
        changes = ChangePointDetector.detect_all_changes(user_id=user_id)
    return changes

@router.get("/contradictions", response_model=List[MemoryRelationshipResponse])
def get_contradictions(user_id: str = "default_user"):
    return ContradictionDetector.detect_contradictions(user_id=user_id)
