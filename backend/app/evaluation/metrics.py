"""
Evaluation metrics (v1.1).

Changes from v1.0, where three of four metrics were fixed by construction:
* COA was computed on a timeline the synthesizer always sorts (=1.0 for every pipeline). It is
  now computed on the order in which the *answer* presents its claims. For the deterministic
  synthesizer that order is chronological by construction, so COA is reported as None there.
* UHCR counted claims lacking evidence ids, which the deterministic synthesizer always attaches.
  It now counts claims whose cited ids are not among the retrieved memories (the synthesizer
  strips such ids), and is reported as None for the deterministic synthesizer. Use an NLI/LLM
  judge (scripts/eval_llm_qa.py) to measure whether cited evidence actually entails a claim.
* Change-F1 returned 1.0 when there was no ground truth and nothing was detected (free credit
  for a disabled detector). Such cases are now undefined (None) and excluded from averages.
  Matching now requires the right topic and allows a year tolerance.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from app.models.schemas import ChangePointResponse, GroundedClaim, TimelinePoint, TMUResponse


def mean_defined(xs: Iterable[Optional[float]]) -> Optional[float]:
    v = [x for x in xs if x is not None]
    return round(sum(v) / len(v), 3) if v else None


class EvaluationMetrics:

    @staticmethod
    def chronological_ordering_accuracy(claims: Sequence[GroundedClaim], retrieved: Sequence[TMUResponse],
                                        backend: str = "llm") -> Optional[float]:
        """Pairwise concordance of the dates of claims, in the order the answer presents them."""
        if backend == "deterministic":
            return None
        date_of = {t.id: t.event_date_start for t in retrieved if t.event_date_start}
        seq = []
        for c in claims:
            ds = sorted(date_of[i] for i in c.evidence_tmu_ids if i in date_of)
            if ds:
                seq.append(ds[0])
        if len(seq) < 2:
            return None
        pairs = conc = 0
        for i in range(len(seq)):
            for j in range(i + 1, len(seq)):
                if seq[i] == seq[j]:
                    continue
                pairs += 1
                conc += seq[i] < seq[j]
        return round(conc / pairs, 3) if pairs else None

    @staticmethod
    def timeline_order_accuracy(timeline: List[TimelinePoint]) -> float:
        """v1.0 COA (kept for comparison only; always 1.0 because the timeline is sorted)."""
        dates = [p.event_date for p in timeline if p.event_date and p.event_date != "Unrecorded"]
        pairs = [(a, b) for i, a in enumerate(dates) for b in dates[i + 1:]]
        return round(sum(a <= b for a, b in pairs) / len(pairs), 3) if pairs else 1.0

    @staticmethod
    def temporal_coverage_recall(timeline: List[TimelinePoint], expected_years: List[str]) -> Optional[float]:
        if not expected_years:
            return None
        covered = {p.event_date[:4] for p in timeline if p.event_date and p.event_date[:4] in expected_years}
        return round(len(covered) / len(set(expected_years)), 3)

    @staticmethod
    def change_point_prf(detected: List[ChangePointResponse], ground_truth: List[Tuple[str, str, str]],
                         topic: Optional[str] = None, year_tolerance: int = 0) -> Dict[str, Optional[float]]:
        """
        Precision/recall/F1 of detected change points. A detection matches a ground-truth
        transition (from_year, to_year, type) if both years are within `year_tolerance` and, when
        `topic` is given, the detection concerns that topic. Each ground-truth item matches once.
        Returns None values when both sets are empty (undefined, excluded from averages).
        """
        if not ground_truth and not detected:
            return {"precision": None, "recall": None, "f1": None, "tp": 0, "n_detected": 0, "n_true": 0}

        def about_topic(c: ChangePointResponse) -> bool:
            if not topic:
                return True
            t = topic.lower()
            return t in (c.topic_or_entity or "").lower() or t in (c.earlier_statement + " " + c.later_statement).lower()

        def yr(s: Optional[str]) -> Optional[int]:
            return int(s[:4]) if s and s[:4].isdigit() else None

        used = set()
        tp = 0
        for c in detected:
            if not about_topic(c):
                continue
            f, t = yr(c.from_period), yr(c.to_period)
            for k, (gf, gt, _) in enumerate(ground_truth):
                if k in used or f is None or t is None:
                    continue
                if abs(f - int(gf)) <= year_tolerance and abs(t - int(gt)) <= year_tolerance:
                    used.add(k); tp += 1
                    break
        p = tp / len(detected) if detected else 0.0
        r = tp / len(ground_truth) if ground_truth else 0.0
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        return {"precision": round(p, 3), "recall": round(r, 3), "f1": round(f1, 3), "tp": tp,
                "n_detected": len(detected), "n_true": len(ground_truth)}

    @staticmethod
    def change_point_f1(detected, ground_truth, topic: Optional[str] = None, year_tolerance: int = 0) -> Optional[float]:
        return EvaluationMetrics.change_point_prf(detected, ground_truth, topic, year_tolerance)["f1"]

    @staticmethod
    def unsupported_claim_rate(claims: List[GroundedClaim], backend: str = "llm") -> Optional[float]:
        """Share of claims citing no retrieved evidence (structural check; see module docstring)."""
        if backend == "deterministic":
            return None
        if not claims:
            return None
        return round(sum(1 for c in claims if not c.evidence_tmu_ids) / len(claims), 3)
