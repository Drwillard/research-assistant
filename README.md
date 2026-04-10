# Research RAG

Academic PDF research assistant: ingest papers, ask questions, get cited answers.

## Stack

- FastAPI backend
- Next.js frontend
- ChromaDB vector store
- OpenAI or local Ollama models (toggle in UI)
- Docker Compose

## Quick start

```bash
cp .env.example .env
# edit .env
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- ChromaDB: http://localhost:8001

## Usage

1. Open http://localhost:3000
2. Toggle provider in the top-right: `OpenAI` or `Local (Ollama)`
3. Upload PDFs in the sidebar (indexes are provider-specific)
4. Ask questions in chat

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/ingest` | Upload PDF (`multipart file`) + `provider` form field |
| `GET` | `/documents` | List docs for `provider` query param |
| `DELETE` | `/documents/{doc_id}` | Delete doc for `provider` query param |
| `POST` | `/chat` | `{ message, conversation_history, provider }` |
| `GET` | `/health` | Health check |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | empty | OpenAI API key (required for `openai`) |
| `MODEL_ID` | `gpt-4o` | OpenAI chat model |
| `DEFAULT_PROVIDER` | `openai` | Default backend provider |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama endpoint used by backend container |
| `OLLAMA_CHAT_MODEL` | `llama3.1:8b` | Ollama chat model |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Ollama embedding model |

## Notes

- Collections are split by provider (`openai` and `ollama`) so retrieval stays embedding-compatible.
- If using Ollama, pull models first, for example:
  - `ollama pull llama3.1:8b`
  - `ollama pull nomic-embed-text`
