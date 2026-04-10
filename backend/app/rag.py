from typing import Optional

import chromadb
import httpx
from openai import OpenAI

from .config import (
    CHROMA_HOST,
    CHROMA_PORT,
    MODEL_ID,
    OLLAMA_BASE_URL,
    OLLAMA_CHAT_MODEL,
    OPENAI_API_KEY,
    TOP_K_RESULTS,
    collection_name_for,
    normalize_provider,
)
from .embeddings import embed

SYSTEM_PROMPT = """You are an expert academic research assistant helping researchers understand and synthesize academic literature.

Guidelines:
- Answer questions based strictly on the provided document excerpts
- Cite the source document filename when referencing specific claims (e.g., "According to 'paper.pdf', ...")
- If the answer is not found in the provided context, explicitly say so rather than speculating
- Highlight key findings, methodologies, limitations, and implications when relevant
- Use precise, scholarly language appropriate for academic discourse
- When comparing multiple papers, clearly distinguish between their respective contributions"""

_openai_client: OpenAI | None = None


def _get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=OPENAI_API_KEY)
    return _openai_client


def _get_ollama_model_names(base_url: str) -> list[str]:
    try:
        tags = httpx.get(f"{base_url}/api/tags", timeout=20.0)
        tags.raise_for_status()
        data = tags.json()
        models = data.get("models", [])
        return [m.get("name", "") for m in models if isinstance(m, dict) and isinstance(m.get("name"), str)]
    except Exception:
        return []


def _raise_ollama_chat_model_missing(base_url: str) -> None:
    installed = _get_ollama_model_names(base_url)
    installed_str = ", ".join(installed) if installed else "(unable to list models)"
    raise ValueError(
        f"Ollama chat model '{OLLAMA_CHAT_MODEL}' is not installed. "
        f"Installed models: {installed_str}. "
        f"Set OLLAMA_CHAT_MODEL to an installed model or run: ollama pull {OLLAMA_CHAT_MODEL}"
    )


def get_collection(provider: str):
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    return client.get_or_create_collection(collection_name_for(provider), embedding_function=None)


def retrieve_context(query: str, provider: str) -> list[dict]:
    collection = get_collection(provider)
    count = collection.count()
    if count == 0:
        return []

    n = min(TOP_K_RESULTS, count)
    query_embedding = embed([query], provider=provider)[0]
    results = collection.query(query_embeddings=[query_embedding], n_results=n)

    sources = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        sources.append(
            {
                "content": doc,
                "filename": meta["filename"],
                "chunk_index": meta.get("chunk_index", 0),
                "score": round(float(1 - dist), 4),
            }
        )
    return sources


def _build_messages(message: str, conversation_history: list, context_block: str) -> list[dict]:
    system_with_context = (
        f"{SYSTEM_PROMPT}\n\n"
        f"## Retrieved Document Excerpts\n\n"
        f"{context_block}\n\n"
        f"Answer the user's question using only the excerpts above. "
        f"Reference specific filenames when citing information."
    )
    messages = [{"role": "system", "content": system_with_context}]
    for msg in conversation_history:
        role = msg.get("role")
        content = msg.get("content")
        if role in {"user", "assistant"} and isinstance(content, str):
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})
    return messages


def _generate_with_openai(messages: list[dict]) -> str:
    client = _get_openai_client()
    response = client.chat.completions.create(
        model=MODEL_ID,
        messages=messages,
        max_tokens=1200,
    )
    content = response.choices[0].message.content
    return content or "No response generated."


def _generate_with_ollama(messages: list[dict]) -> str:
    base_url = OLLAMA_BASE_URL.rstrip("/")
    response = httpx.post(
        f"{base_url}/api/chat",
        json={"model": OLLAMA_CHAT_MODEL, "messages": messages, "stream": False},
        timeout=180.0,
    )
    if response.status_code == 404 and "not found" in (response.text or "").lower():
        _raise_ollama_chat_model_missing(base_url)
    if response.status_code != 404:
        response.raise_for_status()
        data = response.json()
        content = data.get("message", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            return "No response generated."
        return content

    compat = httpx.post(
        f"{base_url}/v1/chat/completions",
        json={"model": OLLAMA_CHAT_MODEL, "messages": messages, "stream": False},
        timeout=180.0,
    )
    if compat.status_code == 404 and "not found" in (compat.text or "").lower():
        _raise_ollama_chat_model_missing(base_url)
    compat.raise_for_status()
    data = compat.json()
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return "No response generated."
    content = choices[0].get("message", {}).get("content")
    if not isinstance(content, str) or not content.strip():
        return "No response generated."
    return content


async def query_rag(message: str, conversation_history: Optional[list] = None, provider: str = "openai") -> dict:
    provider = normalize_provider(provider)
    if conversation_history is None:
        conversation_history = []

    sources = retrieve_context(message, provider=provider)

    if not sources:
        return {
            "answer": (
                "No documents have been ingested for this provider, or no relevant content was found. "
                "Upload PDFs and ask again."
            ),
            "sources": [],
        }

    context_parts = []
    for i, s in enumerate(sources, 1):
        context_parts.append(f"[Excerpt {i} - {s['filename']}]\n{s['content']}")
    context_block = "\n\n---\n\n".join(context_parts)
    messages = _build_messages(message, conversation_history, context_block)

    if provider == "openai":
        answer = _generate_with_openai(messages)
    else:
        answer = _generate_with_ollama(messages)

    return {
        "answer": answer,
        "sources": [
            {
                "filename": s["filename"],
                "score": s["score"],
                "chunk_index": s["chunk_index"],
            }
            for s in sources
        ],
    }
