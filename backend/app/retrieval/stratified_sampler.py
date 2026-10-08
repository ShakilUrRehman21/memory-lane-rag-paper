from __future__ import annotations

import math
from collections import defaultdict
from datetime import date
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.models.schemas import TMUResponse


def _to_date(s: Optional[str]) -> Optional[date]:
    if not s or len(s) < 4 or not s[:4].isdigit():
        return None
    try:
        y = int(s[:4]); m = int(s[5:7]) if len(s) >= 7 and s[5:7].isdigit() else 1
        d = int(s[8:10]) if len(s) >= 10 and s[8:10].isdigit() else 1
        return date(y, m, d)
    except ValueError:
        return date(int(s[:4]), 1, 1)


class StratifiedTemporalSampler:
    """
    Prevents recency/density bias by grouping candidates into chronological epochs and
    sampling round-robin across epochs (best-scored first within each epoch).

    epoch_mode="year"     : calendar years (v1.0 behaviour).
    epoch_mode="adaptive" : the time span of the candidate pool is split into at most
                            `max_epochs` (and at most target_k) equal-width bins, each at least
                            `min_epoch_days` wide, so histories inside a single year are also
                            stratified and very long histories are not over-fragmented.
    """

    @staticmethod
    def epoch_keys(scored_tmus: List[Dict[str, Any]], target_k: int, epoch_mode: str,
                   max_epochs: int, min_epoch_days: int) -> List[str]:
        dates = [_to_date(it["tmu"].event_date_start or it["tmu"].created_at) for it in scored_tmus]
        if epoch_mode == "year":
            return [d.strftime("%Y") if d else "Unrecorded" for d in dates]
        known = [d for d in dates if d]
        if not known:
            return ["Unrecorded"] * len(dates)
        lo, hi = min(known), max(known)
        span = (hi - lo).days
        n_bins = max(1, min(max_epochs, max(1, target_k), math.ceil((span + 1) / max(1, min_epoch_days))))
        width = (span + 1) / n_bins
        keys = []
        for d in dates:
            if d is None:
                keys.append("Unrecorded")
            else:
                b = min(n_bins - 1, int(((d - lo).days) / width)) if width > 0 else 0
                keys.append(f"E{b:03d}")
        return keys

    @staticmethod
    def sample(scored_tmus: List[Dict[str, Any]], target_k: int = 10, min_per_epoch: int = 1,
               epoch_mode: Optional[str] = None, max_epochs: Optional[int] = None,
               min_epoch_days: Optional[int] = None, relevance_slots: int = 0) -> List[Dict[str, Any]]:
        if not scored_tmus or target_k <= 0:
            return []
        epoch_mode = epoch_mode or settings.EPOCH_MODE
        keys = StratifiedTemporalSampler.epoch_keys(
            scored_tmus, target_k, epoch_mode, max_epochs or settings.MAX_EPOCHS,
            min_epoch_days or settings.MIN_EPOCH_DAYS)

        epochs: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for item, k in zip(scored_tmus, keys):
            epochs[k].append(item)
        for k in epochs:
            epochs[k].sort(key=lambda x: x["score"], reverse=True)
        order = sorted(k for k in epochs if k != "Unrecorded") + (["Unrecorded"] if "Unrecorded" in epochs else [])

        selected: List[Dict[str, Any]] = []
        seen = set()
        # Soft stratification: the first `relevance_slots` items are taken purely by score; the
        # remaining slots go round-robin to epochs not yet represented, then to the rest.
        if relevance_slots:
            covered = set()
            for it, k in sorted(zip(scored_tmus, keys), key=lambda x: -x[0]["score"])[:relevance_slots]:
                selected.append(it); seen.add(it["tmu"].id); covered.add(k)
            order = [k for k in order if k not in covered] + [k for k in order if k in covered]
        depth = 0
        while len(selected) < target_k:
            added = 0
            for k in order:
                if len(selected) >= target_k:
                    break
                if len(epochs[k]) > depth:
                    it = epochs[k][depth]
                    if it["tmu"].id not in seen:
                        selected.append(it); seen.add(it["tmu"].id); added += 1
            if added == 0:
                break
            depth += 1
        # Chronological order for presentation; retrieval rank is preserved in item["score"].
        selected.sort(key=lambda x: (x["tmu"].event_date_start or "9999", -x["score"]))
        return selected
