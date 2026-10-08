"""
Vector index persisted in SQLite (table `vectors`).

Fixes relative to v1.0:
* v1.0 rewrote one JSON file containing *all* vectors after every document, making ingestion
  O(N^2) overall. Rows are now inserted incrementally inside the same transaction as the
  document's other records.
* v1.0 scanned every user's vectors in a Python loop and filtered afterwards. Search now loads
  only the requesting user's matrix (cached in memory) and scores it with one matrix product.
* The embedding function is pluggable (see embeddings.py) instead of word hashing.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

from app.core.database import get_db
from app.storage.embeddings import Embedder, get_embedder


class VectorStore:
    def __init__(self, index_name: str = "default", embedder: Optional[Embedder] = None):
        self.index_name = index_name
        self._embedder = embedder
        self._cache: Dict[str, Tuple[List[str], List[Dict[str, Any]], np.ndarray]] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------ embedding
    @property
    def embedder(self) -> Embedder:
        if self._embedder is None:
            self._embedder = get_embedder()
        return self._embedder

    def set_embedder(self, embedder: Embedder) -> None:
        self._embedder = embedder
        self.invalidate()

    def generate_embedding(self, text: str) -> np.ndarray:
        return self.embedder.embed_one(text)

    # ------------------------------------------------------------------ writes
    def add_many(self, items: Iterable[Tuple[str, str, Dict[str, Any]]],
                 conn: Optional[sqlite3.Connection] = None) -> None:
        items = list(items)
        if not items:
            return
        vecs = self.embedder.embed([t for _, t, _ in items])
        rows = [(self.index_name, iid, meta.get("user_id"), meta.get("document_id"), json.dumps(meta), text,
                 self.embedder.name, vec.astype(np.float32).tobytes())
                for (iid, text, meta), vec in zip(items, vecs)]
        sql = ("INSERT OR REPLACE INTO vectors (index_name, item_id, user_id, document_id, meta, text, embedder, vec) "
               "VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
        if conn is not None:
            conn.executemany(sql, rows)
        else:
            with get_db() as c:
                c.executemany(sql, rows)
        for uid in {r[2] for r in rows}:
            self._cache.pop(uid, None)

    def add(self, item_id: str, text: str, meta: Dict[str, Any], conn: Optional[sqlite3.Connection] = None) -> None:
        self.add_many([(item_id, text, meta)], conn=conn)

    def delete_by_document(self, document_id: str, conn: Optional[sqlite3.Connection] = None) -> None:
        sql = "DELETE FROM vectors WHERE index_name = ? AND document_id = ?"
        if conn is not None:
            conn.execute(sql, (self.index_name, document_id))
        else:
            with get_db() as c:
                c.execute(sql, (self.index_name, document_id))
        self.invalidate()

    def delete(self, item_id: str) -> None:
        with get_db() as c:
            c.execute("DELETE FROM vectors WHERE index_name = ? AND item_id = ?", (self.index_name, item_id))
        self.invalidate()

    def save(self) -> None:  # backward compatibility: persistence is now transactional
        return None

    def invalidate(self, user_id: Optional[str] = None) -> None:
        if user_id is None:
            self._cache.clear()
        else:
            self._cache.pop(user_id, None)

    # ------------------------------------------------------------------ reads
    def _fetch(self, user_id: str):
        with get_db() as c:
            return c.execute(
                "SELECT item_id, meta, text, embedder, vec FROM vectors WHERE index_name = ? AND user_id = ?",
                (self.index_name, user_id)).fetchall()

    def _load_user(self, user_id: str):
        with self._lock:
            if user_id in self._cache:
                return self._cache[user_id]
            rows = self._fetch(user_id)
            stale = [r for r in rows if r["embedder"] != self.embedder.name]
            if stale:  # embedder changed since indexing: re-embed transparently
                self.add_many([(r["item_id"], r["text"], json.loads(r["meta"])) for r in stale])
                rows = self._fetch(user_id)
            ids = [r["item_id"] for r in rows]
            metas = [json.loads(r["meta"]) for r in rows]
            mat = (np.frombuffer(b"".join(r["vec"] for r in rows), dtype=np.float32).reshape(len(rows), -1)
                   if rows else np.zeros((0, self.embedder.dim), np.float32))
            self._cache[user_id] = (ids, metas, mat)
            return self._cache[user_id]

    def search(self, query: str, top_k: int = 10,
               filter_meta: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        filter_meta = dict(filter_meta or {})
        user_id = filter_meta.pop("user_id", None)
        if user_id is None:
            raise ValueError("VectorStore.search requires filter_meta['user_id'] (per-user isolation).")
        ids, metas, mat = self._load_user(user_id)
        if not ids or top_k <= 0:
            return []
        scores = mat @ self.generate_embedding(query)
        if filter_meta:
            mask = np.array([all(m.get(k) == v for k, v in filter_meta.items() if k in m) for m in metas])
            scores = np.where(mask, scores, -np.inf)
        k = min(top_k, len(ids))
        top = np.argpartition(-scores, k - 1)[:k]
        top = top[np.argsort(-scores[top], kind="stable")]
        return [{"id": ids[i], "score": float(scores[i]), "metadata": metas[i]} for i in top if np.isfinite(scores[i])]

    def count(self, user_id: Optional[str] = None) -> int:
        with get_db() as c:
            if user_id is None:
                return c.execute("SELECT COUNT(*) FROM vectors WHERE index_name = ?", (self.index_name,)).fetchone()[0]
            return c.execute("SELECT COUNT(*) FROM vectors WHERE index_name = ? AND user_id = ?",
                             (self.index_name, user_id)).fetchone()[0]


chunk_vector_store = VectorStore(index_name="chunks")
tmu_vector_store = VectorStore(index_name="tmus")
