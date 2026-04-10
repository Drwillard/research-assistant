import hashlib
from typing import List

import chromadb
import fitz  # pymupdf

from .config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CHROMA_HOST,
    CHROMA_PORT,
    collection_name_for,
    normalize_provider,
)
from .embeddings import embed


def get_collection(provider: str):
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    # embedding_function=None; we always pass pre-computed embeddings
    return client.get_or_create_collection(
        collection_name_for(provider),
        embedding_function=None,
    )


def chunk_text(text: str) -> List[str]:
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + CHUNK_SIZE, text_len)
        if end < text_len:
            for sep in (". ", ".\n", "\n\n", "\n"):
                pos = text.rfind(sep, start + CHUNK_SIZE // 2, end)
                if pos != -1:
                    end = pos + len(sep)
                    break
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_len:
            break
        # Always move the cursor forward to avoid infinite loops on short texts.
        start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks


async def ingest_pdf(content: bytes, filename: str, provider: str) -> dict:
    provider = normalize_provider(provider)
    doc = fitz.open(stream=content, filetype="pdf")
    pages_text = [page.get_text() for page in doc]
    doc.close()

    full_text = "\n\n".join(pages_text).strip()
    if not full_text:
        raise ValueError("No extractable text found in PDF.")

    doc_id = hashlib.md5(content).hexdigest()
    collection = get_collection(provider)

    existing = collection.get(where={"doc_id": doc_id}, limit=1)
    if existing["ids"]:
        return {
            "status": "already_exists",
            "doc_id": doc_id,
            "filename": filename,
            "chunks": 0,
            "provider": provider,
        }

    chunks = chunk_text(full_text)
    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    metadatas = [
        {"doc_id": doc_id, "filename": filename, "chunk_index": i, "total_chunks": len(chunks)}
        for i in range(len(chunks))
    ]

    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        embeddings = embed(batch, provider=provider)
        collection.add(
            documents=batch,
            embeddings=embeddings,
            ids=ids[i : i + batch_size],
            metadatas=metadatas[i : i + batch_size],
        )

    return {
        "status": "success",
        "doc_id": doc_id,
        "filename": filename,
        "chunks": len(chunks),
        "provider": provider,
    }


async def list_documents(provider: str) -> dict:
    provider = normalize_provider(provider)
    try:
        collection = get_collection(provider)
        results = collection.get(include=["metadatas"])
        seen: dict[str, dict] = {}
        for meta in results["metadatas"]:
            did = meta["doc_id"]
            if did not in seen:
                seen[did] = {"doc_id": did, "filename": meta["filename"]}
        return {"documents": list(seen.values())}
    except Exception:
        return {"documents": []}


async def delete_document(doc_id: str, provider: str) -> dict:
    provider = normalize_provider(provider)
    collection = get_collection(provider)
    collection.delete(where={"doc_id": doc_id})
    return {"status": "success", "doc_id": doc_id, "provider": provider}
