from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.models.schemas import TMUResponse
from app.retrieval.query_router import QueryRouter
from app.retrieval.reranker import LongitudinalReranker
from app.retrieval.stratified_sampler import StratifiedTemporalSampler
from app.storage.fts_store import FTSStore
from app.storage.repository import Repository
from app.storage.vector_store import tmu_vector_store


class HybridTemporalRetriever:
    """
    Hybrid sparse (FTS5 BM25) + dense retrieval, RRF fusion, optional temporal stratification,
    with strict per-user isolation.

    Pipelines (see GroundedSynthesizer):
      baseline    : dense top-k only.
      temporal    : dense top-k with query date filter, then chronological sort (a conventional
                    "temporal RAG" baseline; v1.0 described it but never implemented it).
      memory_lane : BM25 + dense RRF, type/stance boosts, stratified sampling.
    """

    def retrieve(self, query: str, user_id: str = "default_user", top_k: int = 10,
                 disable_temporal: bool = False, disable_rerank: bool = False,
                 filter_start_year: Optional[int] = None, filter_end_year: Optional[int] = None,
                 stratification_mode: Optional[str] = None, dense_only: bool = False,
                 sparse_only: bool = False) -> Dict[str, Any]:
        analysis = QueryRouter.analyze_query(query)
        start_year = filter_start_year or analysis["start_year"]
        end_year = filter_end_year or analysis["end_year"]
        mode = (stratification_mode or settings.STRATIFICATION_MODE).lower()
        if disable_temporal or mode == "off":
            stratify = False
        elif mode == "router":
            stratify = analysis["is_evolution_query"]
        else:  # "always" or "soft"
            stratify = True

        pool = top_k * 4
        dense = [] if sparse_only else tmu_vector_store.search(query=query, top_k=pool, filter_meta={"user_id": user_id})
        sparse = [] if dense_only else FTSStore.search_tmus(query=query, user_id=user_id, limit=pool)

        candidate_ids = [r["id"] for r in dense] + [r["tmu_id"] for r in sparse if r["tmu_id"] not in {d["id"] for d in dense}]
        all_tmus: Dict[str, TMUResponse] = {}
        for cid in candidate_ids:
            t = Repository.get_tmu(cid)
            if not t or t.user_id != user_id:
                continue
            if not disable_temporal:
                if start_year and t.event_date_start and t.event_date_start[:4].isdigit() and int(t.event_date_start[:4]) < start_year:
                    continue
                end_ref = t.event_date_end or t.event_date_start
                if end_year and end_ref and end_ref[:4].isdigit() and int(end_ref[:4]) > end_year:
                    continue
            all_tmus[cid] = t

        if disable_rerank:
            src = dense if dense else [{"id": r["tmu_id"], "score": r["score"]} for r in sparse]
            scored = [{"tmu": all_tmus[r["id"]], "score": r["score"]} for r in src if r["id"] in all_tmus]
        else:
            scored = LongitudinalReranker.fuse_and_rerank(
                dense_results=dense, sparse_results=sparse, all_tmus=all_tmus,
                is_evolution_query=analysis["is_evolution_query"], rrf_k=settings.RRF_K)

        if stratify:
            rel = 0
            if mode == "soft":
                rel = int(round(settings.SOFT_RELEVANCE_FRACTION * top_k))
            final = StratifiedTemporalSampler.sample(scored_tmus=scored, target_k=top_k, relevance_slots=rel)
            ranked = sorted(final, key=lambda x: -x["score"])
        else:
            final = scored[:top_k]
            ranked = list(final)

        return {"query": query, "analysis": analysis, "stratified": stratify,
                "results": [it["tmu"] for it in final],          # presentation order
                "ranked_results": [it["tmu"] for it in ranked],  # relevance order (for rank metrics)
                "scored_results": final}


hybrid_retriever = HybridTemporalRetriever()
