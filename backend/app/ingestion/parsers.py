from pathlib import Path
from typing import Dict, Any, Tuple
import re
import pypdf
import docx

class DocumentParser:
    """Extracts raw text and structural metadata from PDF, DOCX, TXT, and Markdown."""

    @staticmethod
    def parse(file_path: Path) -> Tuple[str, Dict[str, Any]]:
        ext = file_path.suffix.lower()
        if ext in [".txt", ".md", ".markdown"]:
            return DocumentParser._parse_text(file_path)
        elif ext == ".pdf":
            return DocumentParser._parse_pdf(file_path)
        elif ext in [".docx", ".doc"]:
            return DocumentParser._parse_docx(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    @staticmethod
    def _parse_text(file_path: Path) -> Tuple[str, Dict[str, Any]]:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        metadata = {
            "source_file": file_path.name,
            "format": file_path.suffix.lower().lstrip("."),
            "char_count": len(content)
        }
        # Check for YAML/Markdown frontmatter
        if content.startswith("---"):
            match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
            if match:
                frontmatter, body = match.groups()
                for line in frontmatter.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        metadata[k.strip().lower()] = v.strip().strip('"\'')
                content = body
        return content.strip(), metadata

    @staticmethod
    def _parse_pdf(file_path: Path) -> Tuple[str, Dict[str, Any]]:
        text_parts = []
        metadata = {
            "source_file": file_path.name,
            "format": "pdf",
            "page_count": 0
        }
        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            metadata["page_count"] = len(reader.pages)
            if reader.metadata:
                if reader.metadata.title:
                    metadata["title"] = reader.metadata.title
                if reader.metadata.creation_date:
                    metadata["creation_date"] = str(reader.metadata.creation_date)
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_parts.append(page_text.strip())
        full_text = "\n\n".join(text_parts)
        metadata["char_count"] = len(full_text)
        return full_text, metadata

    @staticmethod
    def _parse_docx(file_path: Path) -> Tuple[str, Dict[str, Any]]:
        doc = docx.Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        full_text = "\n\n".join(paragraphs)
        metadata = {
            "source_file": file_path.name,
            "format": "docx",
            "paragraph_count": len(paragraphs),
            "char_count": len(full_text)
        }
        core_props = doc.core_properties
        if core_props:
            if core_props.title:
                metadata["title"] = core_props.title
            if core_props.created:
                metadata["creation_date"] = core_props.created.isoformat()
        return full_text, metadata
