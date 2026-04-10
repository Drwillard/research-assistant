from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import DEFAULT_PROVIDER, normalize_provider
from .ingestion import delete_document, ingest_pdf, list_documents
from .rag import query_rag

app = FastAPI(title="Research RAG API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    conversation_history: list[dict] = []
    provider: str = DEFAULT_PROVIDER


class Source(BaseModel):
    filename: str
    score: float
    chunk_index: int


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/ingest")
async def ingest_document(file: UploadFile = File(...), provider: str = Form(DEFAULT_PROVIDER)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    try:
        result = await ingest_pdf(content, file.filename, provider=normalize_provider(provider))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ingestion failed: {str(e)}")
    return result


@app.get("/documents")
async def get_documents(provider: str = Query(DEFAULT_PROVIDER)):
    try:
        return await list_documents(provider=normalize_provider(provider))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/documents/{doc_id}")
async def remove_document(doc_id: str, provider: str = Query(DEFAULT_PROVIDER)):
    try:
        return await delete_document(doc_id, provider=normalize_provider(provider))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    try:
        provider = normalize_provider(request.provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        result = await query_rag(request.message, request.conversation_history, provider=provider)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Chat failed: {str(e)}")
    return result
