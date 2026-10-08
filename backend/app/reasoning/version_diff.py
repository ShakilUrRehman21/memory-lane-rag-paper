from typing import List, Dict, Any, Optional
from app.models.schemas import VersionDiffResponse, DocumentResponse, DocumentVersionResponse
from app.storage.repository import Repository
from app.storage.vector_store import chunk_vector_store
import numpy as np

class VersionDiffEngine:
    """
    Computes structural and semantic diffs across document versions
    (e.g. Resume v1 vs Resume v2, Proposal v1 vs v3).
    """

    @staticmethod
    def compare_versions(
        series_name: str,
        earlier_label: str,
        later_label: str,
        user_id: Optional[str] = None
    ) -> Optional[VersionDiffResponse]:
        versions = Repository.list_document_versions(series_name)
        if user_id:
            filtered = []
            for v in versions:
                d = Repository.get_document(v.document_id)
                if d and d.user_id == user_id:
                    filtered.append(v)
            versions = filtered

        v_early = next((v for v in versions if v.version_label.lower() == earlier_label.lower()), None)
        v_late = next((v for v in versions if v.version_label.lower() == later_label.lower()), None)

        if not v_early or not v_late:
            return None

        doc_early = Repository.get_document(v_early.document_id)
        doc_late = Repository.get_document(v_late.document_id)

        if not doc_early or not doc_late:
            return None

        # Fetch TMUs for both documents
        tmus_early = [t for t in Repository.list_tmus(user_id=doc_early.user_id) if t.document_id == doc_early.id]
        tmus_late = [t for t in Repository.list_tmus(user_id=doc_late.user_id) if t.document_id == doc_late.id]

        # Extract unique entities & topics
        skills_early = set()
        for t in tmus_early:
            skills_early.update(t.entities)
        
        skills_late = set()
        for t in tmus_late:
            skills_late.update(t.entities)

        added = sorted(list(skills_late - skills_early))
        removed = sorted(list(skills_early - skills_late))
        retained = sorted(list(skills_early.intersection(skills_late)))

        # Semantic diffs between propositions
        semantic_changes = []
        for te in tmus_early:
            v_e = chunk_vector_store.generate_embedding(te.statement)
            # Find closest in later doc
            best_match = None
            best_sim = -1.0
            for tl in tmus_late:
                v_l = chunk_vector_store.generate_embedding(tl.statement)
                sim = float(np.dot(v_e, v_l))
                if sim > best_sim:
                    best_sim = sim
                    best_match = tl
            
            if best_match and 0.40 <= best_sim < 0.85:
                semantic_changes.append({
                    "earlier_statement": te.statement,
                    "later_statement": best_match.statement,
                    "similarity": round(best_sim, 2),
                    "drift": round(1.0 - best_sim, 2)
                })

        summary = (
            f"Comparing '{series_name}' ({earlier_label} -> {later_label}): "
            f"Added {len(added)} technologies ({', '.join(added[:4]) if added else 'None'}), "
            f"Removed {len(removed)} technologies ({', '.join(removed[:4]) if removed else 'None'}), "
            f"and retained {len(retained)} common skills."
        )

        return VersionDiffResponse(
            series_name=series_name,
            earlier_version=earlier_label,
            later_version=later_label,
            added_skills_or_topics=added,
            removed_skills_or_topics=removed,
            retained_skills_or_topics=retained,
            semantic_changes=semantic_changes[:5],
            summary=summary
        )
