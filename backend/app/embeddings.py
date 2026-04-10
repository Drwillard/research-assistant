import httpx
from openai import OpenAI

from .config import OPENAI_API_KEY, OLLAMA_BASE_URL, OLLAMA_EMBED_MODEL

EMBEDDING_MODEL = "text-embedding-3-small"

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def _get_ollama_model_names(base_url: str) -> list[str]:
    try:
        tags = httpx.get(f"{base_url}/api/tags", timeout=20.0)
        tags.raise_for_status()
        data = tags.json()
        models = data.get("models", [])
        return [m.get("name", "") for m in models if isinstance(m, dict) and isinstance(m.get("name"), str)]
    except Exception:
        return []


def _raise_ollama_embedding_model_missing(base_url: str) -> None:
    installed = _get_ollama_model_names(base_url)
    installed_str = ", ".join(installed) if installed else "(unable to list models)"
    raise ValueError(
        f"Ollama embedding model '{OLLAMA_EMBED_MODEL}' is not installed. "
        f"Installed models: {installed_str}. "
        f"Run: ollama pull {OLLAMA_EMBED_MODEL}"
    )


def embed(texts: list[str], provider: str = "openai") -> list[list[float]]:
    if provider == "openai":
        client = _get_client()
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
        return [item.embedding for item in response.data]

    if provider == "ollama":
        base_url = OLLAMA_BASE_URL.rstrip("/")

        # Newer Ollama API: batch embeddings endpoint.
        response = httpx.post(
            f"{base_url}/api/embed",
            json={"model": OLLAMA_EMBED_MODEL, "input": texts},
            timeout=120.0,
        )
        if response.status_code == 404 and "not found" in (response.text or "").lower():
            _raise_ollama_embedding_model_missing(base_url)
        if response.status_code != 404:
            response.raise_for_status()
            data = response.json()
            embeddings = data.get("embeddings")
            if not isinstance(embeddings, list) or len(embeddings) != len(texts):
                raise ValueError("Ollama embedding response was invalid.")
            return embeddings

        # Older Ollama API: single embedding endpoint; run per chunk.
        out: list[list[float]] = []
        for text in texts:
            legacy = httpx.post(
                f"{base_url}/api/embeddings",
                json={"model": OLLAMA_EMBED_MODEL, "prompt": text},
                timeout=120.0,
            )
            if legacy.status_code == 404 and "not found" in (legacy.text or "").lower():
                _raise_ollama_embedding_model_missing(base_url)
            if legacy.status_code == 404:
                out = []
                break
            legacy.raise_for_status()
            data = legacy.json()
            vec = data.get("embedding")
            if not isinstance(vec, list):
                raise ValueError("Ollama legacy embedding response was invalid.")
            out.append(vec)
        if out:
            return out

        # OpenAI-compatible endpoint (common in Ollama gateways/proxies).
        compat = httpx.post(
            f"{base_url}/v1/embeddings",
            json={"model": OLLAMA_EMBED_MODEL, "input": texts},
            timeout=120.0,
        )
        if compat.status_code == 404 and "not found" in (compat.text or "").lower():
            _raise_ollama_embedding_model_missing(base_url)
        compat.raise_for_status()
        data = compat.json()
        rows = data.get("data")
        if not isinstance(rows, list):
            raise ValueError("OpenAI-compatible embedding response was invalid.")
        vectors: list[list[float]] = []
        for row in rows:
            vec = row.get("embedding") if isinstance(row, dict) else None
            if not isinstance(vec, list):
                raise ValueError("OpenAI-compatible embedding response was invalid.")
            vectors.append(vec)
        if len(vectors) != len(texts):
            raise ValueError("Embedding count mismatch in OpenAI-compatible response.")
        return vectors

    raise ValueError(f"Unsupported provider '{provider}'.")
