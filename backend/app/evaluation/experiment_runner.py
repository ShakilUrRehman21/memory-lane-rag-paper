import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List

from app.evaluation.benchmark_dataset import BENCHMARK_CORPUS_DOCUMENTS, BENCHMARK_QUERIES
from app.evaluation.metrics import EvaluationMetrics as M, mean_defined
from app.ingestion.ingestion_service import ingestion_service
from app.models.schemas import EvaluationRunResponse, PipelineMetric, QueryRequest
from app.storage.repository import Repository
from app.synthesis.grounded_synthesizer import grounded_synthesizer

BENCHMARK_USER = "benchmark_eval_user"


class ExperimentRunner:
    """
    Small built-in demo benchmark (5 documents, 3 queries). It is a smoke test, not evidence:
    use the scripts in /scripts for the experiments reported in the paper.
    """

    @staticmethod
    def ensure_benchmark_corpus_loaded() -> None:
        if len(Repository.list_documents(user_id=BENCHMARK_USER)) < len(BENCHMARK_CORPUS_DOCUMENTS):
            for d in BENCHMARK_CORPUS_DOCUMENTS:
                ingestion_service.ingest_text_content(content=d["content"], title=d["title"],
                                                      user_id=BENCHMARK_USER, document_date=d["date"])

    @staticmethod
    def run_benchmark(run_name: str = "Longitudinal Architecture Benchmark",
                      pipelines: List[str] = ["baseline", "temporal", "memory_lane"]) -> EvaluationRunResponse:
        ExperimentRunner.ensure_benchmark_corpus_loaded()
        run_id = f"eval_{uuid.uuid4().hex[:10]}"
        metrics: Dict[str, PipelineMetric] = {}
        for pipe in pipelines:
            coa, tcr, f1, pr, rc, uh, lat = [], [], [], [], [], [], []
            backend = "deterministic"
            for q in BENCHMARK_QUERIES:
                t0 = time.perf_counter()
                res = grounded_synthesizer.synthesize(QueryRequest(query=q["query"], user_id=BENCHMARK_USER,
                                                                   pipeline_mode=pipe, top_k=5))
                lat.append((time.perf_counter() - t0) * 1000)
                backend = res.synthesis_backend
                coa.append(M.chronological_ordering_accuracy(res.grounded_claims, res.retrieved_tmus, backend))
                tcr.append(M.temporal_coverage_recall(res.timeline, q["expected_years"]))
                prf = M.change_point_prf(res.detected_changes, q["ground_truth_transitions"], topic=q.get("topic"))
                f1.append(prf["f1"]); pr.append(prf["precision"]); rc.append(prf["recall"])
                uh.append(M.unsupported_claim_rate(res.grounded_claims, backend))
            metrics[pipe] = PipelineMetric(
                pipeline=pipe, chronological_ordering_accuracy=mean_defined(coa),
                temporal_coverage_recall=mean_defined(tcr), change_point_f1=mean_defined(f1),
                change_point_precision=mean_defined(pr), change_point_recall=mean_defined(rc),
                unsupported_claim_rate=mean_defined(uh), average_latency_ms=round(sum(lat) / len(lat), 2),
                total_token_usage=0, synthesis_backend=backend, n_queries=len(BENCHMARK_QUERIES))

        def fmt(v):
            return "n/a" if v is None else f"{v:.3f}"
        b, m = metrics.get("baseline"), metrics.get("memory_lane")
        summary = (f"Smoke-test benchmark ({len(BENCHMARK_QUERIES)} queries, {len(BENCHMARK_CORPUS_DOCUMENTS)} documents; "
                   f"too small for statistical claims). Temporal coverage recall: baseline {fmt(b.temporal_coverage_recall if b else None)}, "
                   f"Memory Lane {fmt(m.temporal_coverage_recall if m else None)}. Change-point F1 (topic-matched, defined queries only): "
                   f"Memory Lane {fmt(m.change_point_f1 if m else None)}. Synthesis backend: {m.synthesis_backend if m else 'n/a'}.")
        resp = EvaluationRunResponse(id=run_id, run_name=run_name, created_at=datetime.now(timezone.utc).isoformat(),
                                     metrics=metrics, summary_findings=summary)
        Repository.save_evaluation_run(run_id=run_id, run_name=run_name,
                                       config={"pipelines": pipelines, "benchmark_suite": "temporal_longitudinal_v1.1"},
                                       metrics={k: v.model_dump() for k, v in metrics.items()}, summary=summary)
        return resp
