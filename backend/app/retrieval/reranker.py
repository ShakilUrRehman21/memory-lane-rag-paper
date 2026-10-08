from typing import List, Dict, Any
from app.models.schemas import TMUResponse, MemoryType

class LongitudinalReranker:
    """
    Reranks candidate memories using Reciprocal Rank Fusion (RRF),
    semantic-temporal alignment, and milestone diversity weighting.
    """

    @staticmethod
    def fuse_and_rerank(
        dense_results: List[Dict[str, Any]],   # [{'id': ..., 'score': ...}]
        sparse_results: List[Dict[str, Any]],  # [{'tmu_id': ..., 'score': ...}]
        all_tmus: Dict[str, TMUResponse],
        is_evolution_query: bool = False,
        rrf_k: int = 60  # overridden by settings.RRF_K from the retriever
    ) -> List[Dict[str, Any]]:
        scores: Dict[str, float] = {}

        # 1. RRF from dense vector search
        for rank, item in enumerate(dense_results):
            tmu_id = item["id"]
            scores[tmu_id] = scores.get(tmu_id, 0.0) + (1.0 / (rrf_k + rank + 1))

        # 2. RRF from sparse BM25 FTS5 search
        for rank, item in enumerate(sparse_results):
            tmu_id = item["tmu_id"]
            scores[tmu_id] = scores.get(tmu_id, 0.0) + (1.0 / (rrf_k + rank + 1))

        # 3. Apply Milestone & Stance Boosts
        reranked = []
        for tmu_id, base_score in scores.items():
            tmu = all_tmus.get(tmu_id)
            if not tmu:
                continue

            multiplier = 1.0

            # Boost high-signal memory types for longitudinal queries
            if is_evolution_query:
                if tmu.memory_type in [MemoryType.GOAL, MemoryType.DECISION, MemoryType.BELIEF]:
                    multiplier += 0.25
                # Boost statements with high polarity (clear stance or rejection)
                if abs(tmu.stance_polarity) > 0.4:
                    multiplier += 0.20

            final_score = base_score * multiplier
            reranked.append({
                "tmu": tmu,
                "score": final_score
            })

        reranked.sort(key=lambda x: x["score"], reverse=True)
        return reranked
