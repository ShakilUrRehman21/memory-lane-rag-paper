import sqlite3
import json
from contextlib import contextmanager
from typing import Generator
from app.core.config import settings

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(settings.DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db() -> None:
    """Initializes the database schema with relational tables and FTS5 indices."""
    settings.ensure_directories()
    with get_db() as conn:
        cursor = conn.cursor()
        # 0. Users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            password_salt TEXT,
            display_name TEXT NOT NULL,
            avatar_color TEXT NOT NULL,
            bio TEXT,
            created_at TEXT NOT NULL
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")

        # Migrate existing users table if columns don't exist
        cursor.execute("PRAGMA table_info(users);")
        existing_cols = {row[1] for row in cursor.fetchall()}
        if "email" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN email TEXT;")
        if "password_hash" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT;")
        if "password_salt" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN password_salt TEXT;")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")

        # Sessions table for token auth
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);")

        # 1. Documents table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            hash_sha256 TEXT NOT NULL,
            document_date TEXT,
            created_at TEXT NOT NULL,
            metadata TEXT NOT NULL
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_docs_user ON documents(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_docs_date ON documents(document_date);")

        # 2. Chunks table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            token_count INTEGER NOT NULL,
            page_number INTEGER,
            start_char INTEGER NOT NULL,
            end_char INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);")

        # 3. Temporal Memory Units (TMU)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS temporal_memories (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            chunk_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            memory_type TEXT NOT NULL,
            statement TEXT NOT NULL,
            event_date_start TEXT,
            event_date_end TEXT,
            date_granularity TEXT NOT NULL,
            date_confidence REAL NOT NULL,
            date_source TEXT NOT NULL,
            stance_polarity REAL NOT NULL,
            entities TEXT NOT NULL,
            topics TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
            FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tmu_user ON temporal_memories(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tmu_dates ON temporal_memories(event_date_start, event_date_end);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tmu_type ON temporal_memories(memory_type);")

        # 4. Memory Relationships (Graph Edges)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory_relationships (
            id TEXT PRIMARY KEY,
            source_memory_id TEXT NOT NULL,
            target_memory_id TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            confidence REAL NOT NULL,
            evidence_rationale TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (source_memory_id) REFERENCES temporal_memories(id) ON DELETE CASCADE,
            FOREIGN KEY (target_memory_id) REFERENCES temporal_memories(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rel_source ON memory_relationships(source_memory_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rel_target ON memory_relationships(target_memory_id);")

        # 5. Change Points
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS change_points (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            topic_or_entity TEXT NOT NULL,
            from_period TEXT NOT NULL,
            to_period TEXT NOT NULL,
            change_type TEXT NOT NULL,
            magnitude REAL NOT NULL,
            earlier_memory_id TEXT NOT NULL,
            later_memory_id TEXT NOT NULL,
            uncertainty_bounds TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (earlier_memory_id) REFERENCES temporal_memories(id) ON DELETE CASCADE,
            FOREIGN KEY (later_memory_id) REFERENCES temporal_memories(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cp_user ON change_points(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cp_topic ON change_points(topic_or_entity);")

        # 6. Document Versions
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_versions (
            id TEXT PRIMARY KEY,
            series_name TEXT NOT NULL,
            version_label TEXT NOT NULL,
            document_id TEXT NOT NULL,
            version_order INTEGER NOT NULL,
            version_date TEXT NOT NULL,
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ver_series ON document_versions(series_name);")

        # 7. Evaluation Runs
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS evaluation_runs (
            id TEXT PRIMARY KEY,
            run_name TEXT NOT NULL,
            config TEXT NOT NULL,
            metrics TEXT NOT NULL,
            summary_findings TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)

        # 8. FTS5 Virtual Tables for full-text BM25 search
        cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            id UNINDEXED,
            document_id UNINDEXED,
            content,
            tokenize='porter unicode61'
        );
        """)
        
        cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS tmus_fts USING fts5(
            id UNINDEXED,
            statement,
            entities,
            topics,
            tokenize='porter unicode61'
        );
        """)

        # 9. Dense vector index (v1.1: replaces the JSON files rewritten on every insert)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS vectors (
            index_name TEXT NOT NULL,
            item_id TEXT NOT NULL,
            user_id TEXT,
            document_id TEXT,
            meta TEXT,
            text TEXT,
            embedder TEXT,
            vec BLOB NOT NULL,
            PRIMARY KEY (index_name, item_id)
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vectors_user ON vectors(index_name, user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vectors_doc ON vectors(index_name, document_id);")
