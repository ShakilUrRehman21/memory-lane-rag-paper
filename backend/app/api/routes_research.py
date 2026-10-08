from typing import List, Dict, Any
from fastapi import APIRouter
from app.models.schemas import EvaluationBenchmarkRequest, EvaluationRunResponse
from app.evaluation.experiment_runner import ExperimentRunner
from app.storage.repository import Repository

router = APIRouter(prefix="/research", tags=["research"])

@router.post("/benchmark", response_model=EvaluationRunResponse)
@router.post("/run-benchmark", response_model=EvaluationRunResponse)  # path documented in README (v1.0 returned 404)
def run_benchmark(req: EvaluationBenchmarkRequest):
    return ExperimentRunner.run_benchmark(
        run_name=req.run_name,
        pipelines=req.pipelines
    )

@router.get("/runs", response_model=List[Dict[str, Any]])
def list_benchmark_runs():
    return Repository.list_evaluation_runs()
