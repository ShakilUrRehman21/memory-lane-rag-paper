from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import DocumentVersionResponse, VersionDiffResponse
from app.storage.repository import Repository
from app.reasoning.version_diff import VersionDiffEngine

router = APIRouter(prefix="/versions", tags=["versions"])

@router.get("", response_model=List[DocumentVersionResponse])
def list_versions(series: Optional[str] = None):
    return Repository.list_document_versions(series_name=series)

@router.get("/diff", response_model=VersionDiffResponse)
def get_version_diff(
    series: str = Query(..., description="Document series name, e.g., 'Resume'"),
    earlier: str = Query(..., description="Earlier version label, e.g., '2022' or 'v1'"),
    later: str = Query(..., description="Later version label, e.g., '2025' or 'v2'"),
    user_id: Optional[str] = Query(None, description="User ID scoping")
):
    diff = VersionDiffEngine.compare_versions(
        series_name=series,
        earlier_label=earlier,
        later_label=later,
        user_id=user_id
    )
    if not diff:
        raise HTTPException(status_code=404, detail="Version comparison could not be calculated. Verify series and labels exist.")
    return diff
