import sqlite3
import re
from typing import List, Dict, Any, Optional
from app.core.database import get_db

class FTSStore:
    """Manages SQLite FTS5 Full-Text BM25 Search across chunks and TMUs with user scoping."""

    @staticmethod
    def sanitize_query(query: str) -> str:
        cleaned = re.sub(r'[^\w\s]', ' ', query)
        words = [w.strip() for w in cleaned.split() if len(w.strip()) > 1]
        if not words:
            return '""'
        return " OR ".join(f'"{w}"*' for w in words)

    @staticmethod
    def index_chunk(chunk_id: str, document_id: str, content: str, conn: Optional[sqlite3.Connection] = None) -> None:
        if conn:
            conn.execute(
                "INSERT INTO chunks_fts (id, document_id, content) VALUES (?, ?, ?);",
                (chunk_id, document_id, content)
            )
        else:
            with get_db() as c:
                c.execute(
                    "INSERT INTO chunks_fts (id, document_id, content) VALUES (?, ?, ?);",
                    (chunk_id, document_id, content)
                )

    @staticmethod
    def index_tmu(tmu_id: str, statement: str, entities: List[str], topics: List[str], conn: Optional[sqlite3.Connection] = None) -> None:
        if conn:
            conn.execute(
                "INSERT INTO tmus_fts (id, statement, entities, topics) VALUES (?, ?, ?, ?);",
                (tmu_id, statement, " ".join(entities), " ".join(topics))
            )
        else:
            with get_db() as c:
                c.execute(
                    "INSERT INTO tmus_fts (id, statement, entities, topics) VALUES (?, ?, ?, ?);",
                    (tmu_id, statement, " ".join(entities), " ".join(topics))
                )

    @staticmethod
    def search_chunks(query: str, user_id: Optional[str] = None, limit: int = 25) -> List[Dict[str, Any]]:
        safe_q = FTSStore.sanitize_query(query)
        if safe_q == '""':
            return []
        with get_db() as conn:
            cursor = conn.cursor()
            try:
                if user_id:
                    cursor.execute("""
                        SELECT c_fts.id, c_fts.document_id, c_fts.content, bm25(chunks_fts) as bm25_score
                        FROM chunks_fts c_fts
                        JOIN documents d ON c_fts.document_id = d.id
                        WHERE chunks_fts MATCH ? AND d.user_id = ?
                        ORDER BY bm25_score ASC
                        LIMIT ?;
                    """, (safe_q, user_id, limit))
                else:
                    cursor.execute("""
                        SELECT id, document_id, content, bm25(chunks_fts) as bm25_score
                        FROM chunks_fts
                        WHERE chunks_fts MATCH ?
                        ORDER BY bm25_score ASC
                        LIMIT ?;
                    """, (safe_q, limit))
                results = []
                for row in cursor.fetchall():
                    raw_score = float(row["bm25_score"])
                    norm_score = 1.0 / (1.0 + abs(raw_score))
                    results.append({
                        "chunk_id": row["id"],
                        "document_id": row["document_id"],
                        "content": row["content"],
                        "score": norm_score
                    })
                return results
            except sqlite3.OperationalError:
                return []

    @staticmethod
    def search_tmus(query: str, user_id: Optional[str] = None, limit: int = 30) -> List[Dict[str, Any]]:
        safe_q = FTSStore.sanitize_query(query)
        if safe_q == '""':
            return []
        with get_db() as conn:
            cursor = conn.cursor()
            try:
                if user_id:
                    cursor.execute("""
                        SELECT t_fts.id, t_fts.statement, t_fts.entities, t_fts.topics, bm25(tmus_fts) as bm25_score
                        FROM tmus_fts t_fts
                        JOIN temporal_memories tm ON t_fts.id = tm.id
                        WHERE tmus_fts MATCH ? AND tm.user_id = ?
                        ORDER BY bm25_score ASC
                        LIMIT ?;
                    """, (safe_q, user_id, limit))
                else:
                    cursor.execute("""
                        SELECT id, statement, entities, topics, bm25(tmus_fts) as bm25_score
                        FROM tmus_fts
                        WHERE tmus_fts MATCH ?
                        ORDER BY bm25_score ASC
                        LIMIT ?;
                    """, (safe_q, limit))
                results = []
                for row in cursor.fetchall():
                    raw_score = float(row["bm25_score"])
                    norm_score = 1.0 / (1.0 + abs(raw_score))
                    results.append({
                        "tmu_id": row["id"],
                        "statement": row["statement"],
                        "entities": row["entities"],
                        "topics": row["topics"],
                        "score": norm_score
                    })
                return results
            except sqlite3.OperationalError:
                return []

    @staticmethod
    def delete_by_document(document_id: str, conn: Optional[sqlite3.Connection] = None) -> None:
        if conn:
            conn.execute("DELETE FROM chunks_fts WHERE document_id = ?;", (document_id,))
        else:
            with get_db() as c:
                c.execute("DELETE FROM chunks_fts WHERE document_id = ?;", (document_id,))
