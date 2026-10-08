from typing import Dict, Any
from fastapi import APIRouter
from app.reasoning.memory_graph import MemoryGraphBuilder

router = APIRouter(prefix="/graph", tags=["graph"])

@router.get("", response_model=Dict[str, Any])
def get_memory_graph(user_id: str = "default_user"):
    return MemoryGraphBuilder.build_graph(user_id=user_id)
