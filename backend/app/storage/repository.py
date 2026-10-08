import json
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from app.core.database import get_db
from app.models.schemas import (
    DocumentResponse, ChunkResponse, TMUResponse, TMUCreate,
    MemoryRelationshipResponse, ChangePointResponse,
    DocumentVersionResponse, EvaluationRunResponse, MemoryType,
    UserResponse
)
from app.storage.fts_store import FTSStore
from app.storage.vector_store import chunk_vector_store, tmu_vector_store

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class Repository:
    """Relational & temporal data repository backed by SQLite with strict user isolation."""

    # ----------------- Users & Authentication -----------------
    @staticmethod
    def create_user(
        user_id: str,
        username: str,
        display_name: str,
        email: Optional[str] = None,
        password_hash: Optional[str] = None,
        password_salt: Optional[str] = None,
        avatar_color: str = "#38bdf8",
        bio: Optional[str] = None
    ) -> UserResponse:
        now = now_iso()
        with get_db() as conn:
            conn.execute("""
                INSERT INTO users (id, email, username, password_hash, password_salt, display_name, avatar_color, bio, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (user_id, email, username, password_hash, password_salt, display_name, avatar_color, bio, now))
        return Repository.get_user(user_id)

    @staticmethod
    def get_user(user_id: str) -> Optional[UserResponse]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?;", (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            cursor.execute("SELECT COUNT(*) as cnt FROM documents WHERE user_id = ?;", (user_id,))
            doc_cnt = cursor.fetchone()["cnt"]

            cursor.execute("SELECT COUNT(*) as cnt FROM temporal_memories WHERE user_id = ?;", (user_id,))
            tmu_cnt = cursor.fetchone()["cnt"]

            cursor.execute("SELECT MIN(event_date_start) as min_dt, MAX(event_date_start) as max_dt FROM temporal_memories WHERE user_id = ?;", (user_id,))
            dt_row = cursor.fetchone()

            row_dict = dict(row)
            return UserResponse(
                id=row_dict["id"],
                username=row_dict["username"],
                display_name=row_dict["display_name"],
                email=row_dict.get("email"),
                avatar_color=row_dict["avatar_color"],
                bio=row_dict.get("bio"),
                created_at=row_dict["created_at"],
                document_count=doc_cnt,
                tmu_count=tmu_cnt,
                earliest_memory_date=dt_row["min_dt"] if dt_row else None,
                latest_memory_date=dt_row["max_dt"] if dt_row else None
            )

    @staticmethod
    def get_user_by_username(username: str) -> Optional[UserResponse]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(?);", (username,))
            row = cursor.fetchone()
            if not row:
                return None
            return Repository.get_user(row["id"])

    @staticmethod
    def get_user_by_email(email: str) -> Optional[UserResponse]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(?);", (email,))
            row = cursor.fetchone()
            if not row:
                return None
            return Repository.get_user(row["id"])

    @staticmethod
    def get_raw_user_for_auth(identifier: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM users 
                WHERE LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?);
            """, (identifier, identifier))
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    @staticmethod
    def create_session(token: str, user_id: str, expires_days: int = 30) -> None:
        now = datetime.now(timezone.utc)
        expires = (now + timedelta(days=expires_days)).isoformat()
        with get_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sessions (token, user_id, created_at, expires_at)
                VALUES (?, ?, ?, ?);
            """, (token, user_id, now.isoformat(), expires))

    @staticmethod
    def get_session_user(token: str) -> Optional[UserResponse]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, expires_at FROM sessions WHERE token = ?;", (token,))
            row = cursor.fetchone()
            if not row:
                return None
            expires_at = datetime.fromisoformat(row["expires_at"])
            if expires_at < datetime.now(timezone.utc):
                cursor.execute("DELETE FROM sessions WHERE token = ?;", (token,))
                return None
            return Repository.get_user(row["user_id"])

    @staticmethod
    def delete_session(token: str) -> None:
        with get_db() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?;", (token,))

    @staticmethod
    def list_users() -> List[UserResponse]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users ORDER BY created_at ASC;")
            rows = cursor.fetchall()
            users = []
            for r in rows:
                u = Repository.get_user(r["id"])
                if u:
                    users.append(u)
            return users

    # ----------------- Documents -----------------
    @staticmethod
    def create_document(
        doc_id: str,
        user_id: str,
        title: str,
        file_path: str,
        file_type: str,
        file_size: int,
        hash_sha256: str,
        document_date: Optional[str],
        metadata: Dict[str, Any]
    ) -> DocumentResponse:
        now = now_iso()
        with get_db() as conn:
            conn.execute("""
                INSERT INTO documents (id, user_id, title, file_path, file_type, file_size, hash_sha256, document_date, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (doc_id, user_id, title, file_path, file_type, file_size, hash_sha256, document_date, now, json.dumps(metadata)))
        return Repository.get_document(doc_id)

    @staticmethod
    def get_document(doc_id: str) -> Optional[DocumentResponse]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE id = ?;", (doc_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            cursor.execute("SELECT COUNT(*) as cnt FROM chunks WHERE document_id = ?;", (doc_id,))
            chunk_cnt = cursor.fetchone()["cnt"]

            cursor.execute("SELECT COUNT(*) as cnt FROM temporal_memories WHERE document_id = ?;", (doc_id,))
            tmu_cnt = cursor.fetchone()["cnt"]

            return DocumentResponse(
                id=row["id"],
                user_id=row["user_id"],
                title=row["title"],
                file_path=row["file_path"],
                file_type=row["file_type"],
                file_size=row["file_size"],
                hash_sha256=row["hash_sha256"],
                document_date=row["document_date"],
                created_at=row["created_at"],
                metadata=json.loads(row["metadata"]),
                chunk_count=chunk_cnt,
                tmu_count=tmu_cnt
            )

    @staticmethod
    def list_documents(user_id: str = "default_user") -> List[DocumentResponse]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM documents WHERE user_id = ? ORDER BY document_date ASC, created_at ASC;", (user_id,))
            rows = cursor.fetchall()
            return [Repository.get_document(r["id"]) for r in rows if r]

    @staticmethod
    def delete_document(doc_id: str) -> bool:
        with get_db() as conn:
            # v1.1: TMU full-text rows were previously left behind after deletion
            conn.execute("DELETE FROM tmus_fts WHERE id IN (SELECT id FROM temporal_memories WHERE document_id = ?);", (doc_id,))
            FTSStore.delete_by_document(doc_id, conn=conn)
            chunk_vector_store.delete_by_document(doc_id, conn=conn)
            tmu_vector_store.delete_by_document(doc_id, conn=conn)
            conn.execute("DELETE FROM documents WHERE id = ?;", (doc_id,))
        return True

    # ----------------- Chunks -----------------
    @staticmethod
    def insert_chunks(chunks_data: List[Dict[str, Any]], user_id: str = "default_user") -> None:
        now = now_iso()
        vec_items = []
        with get_db() as conn:
            cursor = conn.cursor()
            for chk in chunks_data:
                cursor.execute("""
                    INSERT INTO chunks (id, document_id, chunk_index, content, token_count, page_number, start_char, end_char, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    chk["id"], chk["document_id"], chk["chunk_index"],
                    chk["content"], chk["token_count"], chk.get("page_number"),
                    chk["start_char"], chk["end_char"], now
                ))
                FTSStore.index_chunk(chk["id"], chk["document_id"], chk["content"], conn=conn)
                vec_items.append((chk["id"], chk["content"],
                                  {"document_id": chk["document_id"], "chunk_index": chk["chunk_index"], "user_id": user_id}))
            # one batched embedding call, same transaction
            chunk_vector_store.add_many(vec_items, conn=conn)

    @staticmethod
    def get_chunk(chunk_id: str) -> Optional[ChunkResponse]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM chunks WHERE id = ?;", (chunk_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return ChunkResponse(
                id=row["id"],
                document_id=row["document_id"],
                chunk_index=row["chunk_index"],
                content=row["content"],
                token_count=row["token_count"],
                page_number=row["page_number"],
                start_char=row["start_char"],
                end_char=row["end_char"],
                created_at=row["created_at"]
            )

    # ----------------- TMU (Temporal Memory Units) -----------------
    @staticmethod
    def insert_tmus(tmus: List[TMUCreate]) -> List[str]:
        now = now_iso()
        ids = []
        vec_items = []
        with get_db() as conn:
            cursor = conn.cursor()
            for i, tmu in enumerate(tmus):
                tmu_id = f"{tmu.chunk_id}_tmu_{i}"
                cursor.execute("""
                    INSERT INTO temporal_memories (
                        id, document_id, chunk_id, user_id, memory_type, statement,
                        event_date_start, event_date_end, date_granularity,
                        date_confidence, date_source, stance_polarity, entities, topics, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    tmu_id, tmu.document_id, tmu.chunk_id, tmu.user_id,
                    tmu.memory_type.value, tmu.statement,
                    tmu.event_date_start, tmu.event_date_end,
                    tmu.date_granularity.value, tmu.date_confidence,
                    tmu.date_source.value, tmu.stance_polarity,
                    json.dumps(tmu.entities), json.dumps(tmu.topics), now
                ))
                ids.append(tmu_id)
                # FTS5 indexing with same connection
                FTSStore.index_tmu(tmu_id, tmu.statement, tmu.entities, tmu.topics, conn=conn)
                vec_items.append((tmu_id, f"{tmu.statement} {' '.join(tmu.entities)} {' '.join(tmu.topics)}", {
                    "document_id": tmu.document_id, "chunk_id": tmu.chunk_id, "user_id": tmu.user_id,
                    "memory_type": tmu.memory_type.value, "event_date": tmu.event_date_start}))
            tmu_vector_store.add_many(vec_items, conn=conn)
        return ids

    @staticmethod
    def get_tmu(tmu_id: str) -> Optional[TMUResponse]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT tm.*, d.title as doc_title
                FROM temporal_memories tm
                JOIN documents d ON tm.document_id = d.id
                WHERE tm.id = ?;
            """, (tmu_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return TMUResponse(
                id=row["id"],
                document_id=row["document_id"],
                chunk_id=row["chunk_id"],
                user_id=row["user_id"],
                document_title=row["doc_title"],
                memory_type=MemoryType(row["memory_type"]),
                statement=row["statement"],
                event_date_start=row["event_date_start"],
                event_date_end=row["event_date_end"],
                date_granularity=row["date_granularity"],
                date_confidence=row["date_confidence"],
                date_source=row["date_source"],
                stance_polarity=row["stance_polarity"],
                entities=json.loads(row["entities"]),
                topics=json.loads(row["topics"]),
                created_at=row["created_at"]
            )

    @staticmethod
    def list_tmus(
        user_id: str = "default_user",
        topic: Optional[str] = None,
        entity: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None
    ) -> List[TMUResponse]:
        with get_db() as conn:
            cursor = conn.cursor()
            query = """
                SELECT tm.*, d.title as doc_title
                FROM temporal_memories tm
                JOIN documents d ON tm.document_id = d.id
                WHERE tm.user_id = ?
            """
            params: List[Any] = [user_id]

            if memory_type:
                query += " AND tm.memory_type = ?"
                params.append(memory_type.value)

            if start_year:
                query += " AND (tm.event_date_start >= ? OR tm.event_date_start IS NULL)"
                params.append(f"{start_year}-01-01")

            if end_year:
                query += " AND (tm.event_date_end <= ? OR tm.event_date_end IS NULL)"
                params.append(f"{end_year}-12-31")

            query += " ORDER BY tm.event_date_start ASC, tm.created_at ASC;"
            cursor.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for r in rows:
                ents = json.loads(r["entities"])
                tops = json.loads(r["topics"])
                if topic and topic not in tops:
                    continue
                if entity and entity not in ents:
                    continue
                results.append(TMUResponse(
                    id=r["id"],
                    document_id=r["document_id"],
                    chunk_id=r["chunk_id"],
                    user_id=r["user_id"],
                    document_title=r["doc_title"],
                    memory_type=MemoryType(r["memory_type"]),
                    statement=r["statement"],
                    event_date_start=r["event_date_start"],
                    event_date_end=r["event_date_end"],
                    date_granularity=r["date_granularity"],
                    date_confidence=r["date_confidence"],
                    date_source=r["date_source"],
                    stance_polarity=r["stance_polarity"],
                    entities=ents,
                    topics=tops,
                    created_at=r["created_at"]
                ))
            return results

    # ----------------- Relationships & Graph -----------------
    @staticmethod
    def insert_relationship(rel: Dict[str, Any]) -> str:
        now = now_iso()
        rel_id = rel.get("id") or f"rel_{datetime.now().timestamp()}"
        with get_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memory_relationships (id, source_memory_id, target_memory_id, relation_type, confidence, evidence_rationale, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (rel_id, rel["source_memory_id"], rel["target_memory_id"], rel["relation_type"], rel["confidence"], rel.get("evidence_rationale"), now))
        return rel_id

    @staticmethod
    def list_relationships(user_id: Optional[str] = None) -> List[MemoryRelationshipResponse]:
        with get_db() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute("""
                    SELECT mr.*, 
                           sm.statement as s_stmt, sm.event_date_start as s_date,
                           tm.statement as t_stmt, tm.event_date_start as t_date
                    FROM memory_relationships mr
                    JOIN temporal_memories sm ON mr.source_memory_id = sm.id
                    JOIN temporal_memories tm ON mr.target_memory_id = tm.id
                    WHERE sm.user_id = ?
                    ORDER BY mr.confidence DESC;
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT mr.*, 
                           sm.statement as s_stmt, sm.event_date_start as s_date,
                           tm.statement as t_stmt, tm.event_date_start as t_date
                    FROM memory_relationships mr
                    JOIN temporal_memories sm ON mr.source_memory_id = sm.id
                    JOIN temporal_memories tm ON mr.target_memory_id = tm.id
                    ORDER BY mr.confidence DESC;
                """)
            rows = cursor.fetchall()
            return [
                MemoryRelationshipResponse(
                    id=r["id"],
                    source_memory_id=r["source_memory_id"],
                    target_memory_id=r["target_memory_id"],
                    relation_type=r["relation_type"],
                    confidence=r["confidence"],
                    evidence_rationale=r["evidence_rationale"],
                    source_statement=r["s_stmt"],
                    target_statement=r["t_stmt"],
                    source_date=r["s_date"],
                    target_date=r["t_date"],
                    created_at=r["created_at"]
                ) for r in rows
            ]

    # ----------------- Change Points -----------------
    @staticmethod
    def insert_change_point(cp: Dict[str, Any]) -> str:
        now = now_iso()
        cp_id = cp.get("id") or f"cp_{datetime.now().timestamp()}"
        with get_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO change_points (id, user_id, topic_or_entity, from_period, to_period, change_type, magnitude, earlier_memory_id, later_memory_id, uncertainty_bounds, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                cp_id, cp["user_id"], cp["topic_or_entity"], cp["from_period"], cp["to_period"],
                cp["change_type"], cp["magnitude"], cp["earlier_memory_id"], cp["later_memory_id"],
                cp.get("uncertainty_bounds"), now
            ))
        return cp_id

    @staticmethod
    def list_change_points(user_id: str = "default_user") -> List[ChangePointResponse]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT cp.*,
                       em.statement as e_stmt, em.event_date_start as e_date,
                       lm.statement as l_stmt, lm.event_date_start as l_date
                FROM change_points cp
                JOIN temporal_memories em ON cp.earlier_memory_id = em.id
                JOIN temporal_memories lm ON cp.later_memory_id = lm.id
                WHERE cp.user_id = ?
                ORDER BY cp.from_period ASC;
            """, (user_id,))
            rows = cursor.fetchall()
            return [
                ChangePointResponse(
                    id=r["id"],
                    user_id=r["user_id"],
                    topic_or_entity=r["topic_or_entity"],
                    from_period=r["from_period"],
                    to_period=r["to_period"],
                    change_type=r["change_type"],
                    magnitude=r["magnitude"],
                    earlier_memory_id=r["earlier_memory_id"],
                    later_memory_id=r["later_memory_id"],
                    earlier_statement=r["e_stmt"],
                    later_statement=r["l_stmt"],
                    earlier_date=r["e_date"],
                    later_date=r["l_date"],
                    uncertainty_bounds=r["uncertainty_bounds"],
                    created_at=r["created_at"]
                ) for r in rows
            ]

    # ----------------- Document Versions -----------------
    @staticmethod
    def insert_document_version(dv: Dict[str, Any]) -> str:
        dv_id = dv.get("id") or f"ver_{datetime.now().timestamp()}"
        with get_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO document_versions (id, series_name, version_label, document_id, version_order, version_date)
                VALUES (?, ?, ?, ?, ?, ?);
            """, (dv_id, dv["series_name"], dv["version_label"], dv["document_id"], dv["version_order"], dv["version_date"]))
        return dv_id

    @staticmethod
    def list_document_versions(series_name: Optional[str] = None) -> List[DocumentVersionResponse]:
        with get_db() as conn:
            cursor = conn.cursor()
            if series_name:
                cursor.execute("SELECT * FROM document_versions WHERE series_name = ? ORDER BY version_order ASC;", (series_name,))
            else:
                cursor.execute("SELECT * FROM document_versions ORDER BY series_name ASC, version_order ASC;")
            rows = cursor.fetchall()
            return [
                DocumentVersionResponse(
                    id=r["id"],
                    series_name=r["series_name"],
                    version_label=r["version_label"],
                    document_id=r["document_id"],
                    version_order=r["version_order"],
                    version_date=r["version_date"]
                ) for r in rows
            ]

    # ----------------- Evaluation Runs -----------------
    @staticmethod
    def save_evaluation_run(run_id: str, run_name: str, config: Dict[str, Any], metrics: Dict[str, Any], summary: str) -> None:
        now = now_iso()
        with get_db() as conn:
            conn.execute("""
                INSERT INTO evaluation_runs (id, run_name, config, metrics, summary_findings, created_at)
                VALUES (?, ?, ?, ?, ?, ?);
            """, (run_id, run_name, json.dumps(config), json.dumps(metrics), summary, now))

    @staticmethod
    def list_evaluation_runs() -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM evaluation_runs ORDER BY created_at DESC;")
            rows = cursor.fetchall()
            return [{
                "id": r["id"],
                "run_name": r["run_name"],
                "config": json.loads(r["config"]),
                "metrics": json.loads(r["metrics"]),
                "summary_findings": r["summary_findings"],
                "created_at": r["created_at"]
            } for r in rows]
