from fastapi import APIRouter
from app.models.schemas import QueryRequest, QueryResponse
from app.synthesis.grounded_synthesizer import grounded_synthesizer

router = APIRouter(prefix="/query", tags=["query"])

@router.post("", response_model=QueryResponse)
def ask_memory_lane(req: QueryRequest):
    return grounded_synthesizer.synthesize(req)
