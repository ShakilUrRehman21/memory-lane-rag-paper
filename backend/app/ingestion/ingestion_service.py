import hashlib
import uuid
import re
from pathlib import Path
from typing import Dict, Any, Optional
from app.core.config import settings
from app.ingestion.parsers import DocumentParser
from app.ingestion.date_extractor import DateExtractor
from app.ingestion.chunker import SemanticTemporalChunker
from app.ingestion.tmu_extractor import TMUExtractor
from app.storage.repository import Repository
from app.models.schemas import DocumentResponse

class IngestionService:
    """
    Coordinates end-to-end ingestion pipeline:
    File Read -> Parsing -> Quad-Date Resolution -> Semantic-Temporal Chunking
    -> TMU Extraction -> Indexing (SQLite + FTS5 + Vectors).
    """

    def __init__(self):
        self.chunker = SemanticTemporalChunker(target_chunk_size=400, min_chunk_size=80)

    def ingest_file(
        self,
        file_path: Path,
        user_id: str = "default_user",
        manual_date: Optional[str] = None,
        manual_title: Optional[str] = None
    ) -> DocumentResponse:
        # 1. Parse text and file metadata
        text, meta = DocumentParser.parse(file_path)
        
        # 2. Compute SHA256 hash
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        sha256_hash = hasher.hexdigest()

        # 3. Resolve Document Date t_doc
        if manual_date:
            doc_date = manual_date
            doc_date_conf = 1.0
        else:
            doc_date, doc_date_conf = DateExtractor.infer_document_date(file_path.name, text, meta)

        title = manual_title or meta.get("title") or file_path.stem.replace("_", " ").title()
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        file_size = file_path.stat().st_size

        meta["date_confidence"] = doc_date_conf
        meta["inferred_document_date"] = doc_date

        # 4. Save Document record
        doc_record = Repository.create_document(
            doc_id=doc_id,
            user_id=user_id,
            title=title,
            file_path=str(file_path),
            file_type=file_path.suffix.lstrip("."),
            file_size=file_size,
            hash_sha256=sha256_hash,
            document_date=doc_date,
            metadata=meta
        )

        # 5. Semantic-Temporal Chunking
        chunks_data = self.chunker.chunk(text, doc_id)
        if chunks_data:
            Repository.insert_chunks(chunks_data, user_id=user_id)  # v1.1: user_id was missing

            # 6. TMU Extraction per chunk
            all_tmus = []
            for chk in chunks_data:
                tmus = TMUExtractor.extract_from_chunk(
                    chunk_content=chk["content"],
                    chunk_id=chk["id"],
                    document_id=doc_id,
                    document_date=doc_date,
                    user_id=user_id
                )
                all_tmus.extend(tmus)
            
            if all_tmus:
                Repository.insert_tmus(all_tmus)

        # 7. Check for version series tagging (e.g. Resume_v1, Resume_2022)
        version_match = re.search(r"(resume|cv|proposal|statement)[_-]?(v\d+|\d{4})", file_path.name, re.IGNORECASE)
        if version_match and doc_date:
            series = version_match.group(1).capitalize()
            label = version_match.group(2).lower()
            # Count existing in series
            existing = Repository.list_document_versions(series)
            Repository.insert_document_version({
                "series_name": series,
                "version_label": label,
                "document_id": doc_id,
                "version_order": len(existing) + 1,
                "version_date": doc_date
            })

        return Repository.get_document(doc_id)

    def ingest_text_content(
        self,
        content: str,
        title: str,
        user_id: str = "default_user",
        document_date: Optional[str] = None
    ) -> DocumentResponse:
        """Ingests raw text directly (useful for tests and manual note entries)."""
        settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        # v1.1: unique per upload; v1.0 used the sanitised title, so equal titles from
        # different users overwrote each other on disk.
        safe_user = re.sub(r'[^a-zA-Z0-9_-]', '_', user_id)[:40]
        safe_title = re.sub(r'[^a-zA-Z0-9_-]', '_', title.lower())[:80]
        safe_filename = f"{safe_user}__{uuid.uuid4().hex[:10]}__{safe_title}.txt"
        file_path = settings.UPLOADS_DIR / safe_filename
        file_path.write_text(content, encoding="utf-8")
        return self.ingest_file(file_path, user_id=user_id, manual_date=document_date, manual_title=title)

ingestion_service = IngestionService()
