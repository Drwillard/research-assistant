# Research RAG

Academic PDF research assistant: ingest papers, ask questions, get cited answers.

## Model Provider Options

This app supports two modes:

- `OpenAI` mode: uses OpenAI for embeddings + chat.
- `Local (Ollama)` mode: uses your local Ollama server for embeddings + chat (no OpenAI key required).

You can switch between providers in the UI (top-right toggle).  
Document indexes are provider-specific, so upload PDFs separately per provider.

## Stack

- FastAPI backend
- Next.js frontend
- ChromaDB vector store
- OpenAI or local Ollama models (toggle in UI)
- Docker Compose

## Quick start

```bash
cp .env.example .env
# edit .env (pick OpenAI or Ollama settings)
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

## Provider Setup

### Use OpenAI

Set in `.env`:

```env
OPENAI_API_KEY=your_key_here
MODEL_ID=gpt-4o
DEFAULT_PROVIDER=openai
```

### Use Local Ollama

1. Make sure Ollama is running on your machine.
2. Pull models (example):

```bash
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

3. Set in `.env`:

```env
DEFAULT_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_CHAT_MODEL=qwen2.5:7b
OLLAMA_EMBED_MODEL=nomic-embed-text
```

If you run backend outside Docker, `OLLAMA_BASE_URL` is usually:

```env
OLLAMA_BASE_URL=http://localhost:11434
```

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
- If an Ollama model is missing, ingestion/chat will return a clear error with installed model names and pull instructions.
