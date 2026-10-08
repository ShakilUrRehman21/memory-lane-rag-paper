import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.core.config import settings
from app.ingestion.ingestion_service import ingestion_service
from app.storage.repository import Repository
from app.models.schemas import DocumentResponse, DocumentCreate

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Form("default_user"),
    document_date: Optional[str] = Form(None),
    title: Optional[str] = Form(None)
):
    settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = settings.UPLOADS_DIR / file.filename
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        doc = ingestion_service.ingest_file(
            file_path=temp_path,
            user_id=user_id,
            manual_date=document_date,
            manual_title=title
        )
        return doc
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to ingest document: {str(e)}")

@router.post("/text", response_model=DocumentResponse)
def create_text_document(doc_in: DocumentCreate):
    if not doc_in.content or not doc_in.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty.")
    
    doc = ingestion_service.ingest_text_content(
        content=doc_in.content,
        title=doc_in.title,
        user_id=doc_in.user_id,
        document_date=doc_in.document_date
    )
    return doc

@router.get("", response_model=List[DocumentResponse])
def list_documents(user_id: str = "default_user"):
    return Repository.list_documents(user_id=user_id)

@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str):
    doc = Repository.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.delete("/{document_id}")
def delete_document(document_id: str):
    doc = Repository.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    Repository.delete_document(document_id)
    return {"status": "success", "deleted_id": document_id}
