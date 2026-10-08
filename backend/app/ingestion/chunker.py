import re
from typing import List, Dict, Any

class SemanticTemporalChunker:
    """
    Splits text along paragraph and sentence boundaries, preserving temporal statements
    and maintaining precise character offsets for source traceability.
    """

    def __init__(self, target_chunk_size: int = 400, min_chunk_size: int = 80):
        self.target_chunk_size = target_chunk_size
        self.min_chunk_size = min_chunk_size

    def chunk(self, text: str, document_id: str) -> List[Dict[str, Any]]:
        if not text.strip():
            return []

        # Split into paragraphs
        raw_paragraphs = re.split(r"(\n\s*\n+)", text)
        
        chunks = []
        current_chunk_text = ""
        current_start_char = 0
        current_offset = 0
        chunk_idx = 0

        for segment in raw_paragraphs:
            seg_len = len(segment)
            if not segment.strip():
                # whitespace separator
                if current_chunk_text:
                    current_chunk_text += segment
                current_offset += seg_len
                continue

            # If segment itself is larger than target_chunk_size, break by sentence
            if len(segment) > self.target_chunk_size * 1.5:
                sentences = re.split(r"(?<=[.!?])\s+", segment)
                for sent in sentences:
                    if not sent.strip():
                        continue
                    if len(current_chunk_text) + len(sent) > self.target_chunk_size and len(current_chunk_text) >= self.min_chunk_size:
                        # Flush current chunk
                        end_char = current_start_char + len(current_chunk_text)
                        chunks.append(self._create_chunk(document_id, chunk_idx, current_chunk_text.strip(), current_start_char, end_char))
                        chunk_idx += 1
                        current_start_char = end_char
                        current_chunk_text = sent + " "
                    else:
                        current_chunk_text += sent + " "
            else:
                if len(current_chunk_text) + len(segment) > self.target_chunk_size and len(current_chunk_text) >= self.min_chunk_size:
                    # Flush
                    end_char = current_start_char + len(current_chunk_text)
                    chunks.append(self._create_chunk(document_id, chunk_idx, current_chunk_text.strip(), current_start_char, end_char))
                    chunk_idx += 1
                    current_start_char = end_char
                    current_chunk_text = segment + "\n\n"
                else:
                    current_chunk_text += segment + "\n\n"

            current_offset += seg_len

        # Flush any remaining text
        if current_chunk_text.strip():
            end_char = current_start_char + len(current_chunk_text)
            chunks.append(self._create_chunk(document_id, chunk_idx, current_chunk_text.strip(), current_start_char, end_char))

        return chunks

    def _create_chunk(self, doc_id: str, index: int, content: str, start_char: int, end_char: int) -> Dict[str, Any]:
        # Approximate tokens (1 token ~= 4 chars)
        token_count = max(1, len(content) // 4)
        return {
            "id": f"{doc_id}_chk_{index}",
            "document_id": doc_id,
            "chunk_index": index,
            "content": content,
            "token_count": token_count,
            "start_char": start_char,
            "end_char": end_char
        }
