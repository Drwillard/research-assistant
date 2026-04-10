import os

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8001"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL_ID = os.getenv("MODEL_ID", "gpt-4o")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "llama3.1:8b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "openai")

COLLECTION_NAME = "research_papers"
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200
TOP_K_RESULTS = 6

SUPPORTED_PROVIDERS = {"openai", "ollama"}


def normalize_provider(provider: str | None) -> str:
    resolved = (provider or DEFAULT_PROVIDER).strip().lower()
    if resolved not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported provider '{provider}'. Use one of: {', '.join(sorted(SUPPORTED_PROVIDERS))}.")
    return resolved


def collection_name_for(provider: str) -> str:
    return f"{COLLECTION_NAME}__{provider}"
