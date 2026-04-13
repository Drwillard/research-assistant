from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .benchmarking import parse_queries, run_compare_benchmarks, run_cost_model, run_latency_benchmark
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


class CostModelRequest(BaseModel):
    monthly_requests: int
    avg_input_tokens: int
    avg_output_tokens: int
    openai_input_per_1m: float = 0.15
    openai_output_per_1m: float = 0.60
    local_fixed_monthly: float = 0.0
    local_power_monthly: float = 0.0


class CompareBenchmarkRequest(BaseModel):
    cpu_report: dict
    gpu_report: dict


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


@app.post("/benchmarks/latency")
async def benchmark_latency(
    file: UploadFile = File(...),
    provider: str = Form(DEFAULT_PROVIDER),
    runs: int = Form(5),
    warmup_runs: int = Form(1),
    queries: str | None = Form(None),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        resolved_provider = normalize_provider(provider)
        query_list = parse_queries(queries)
        result = await run_latency_benchmark(
            pdf_bytes=content,
            filename=file.filename,
            provider=resolved_provider,
            queries=query_list,
            runs=runs,
            warmup_runs=warmup_runs,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Benchmark failed: {str(e)}")


@app.post("/benchmarks/cost-model")
async def benchmark_cost_model(request: CostModelRequest):
    try:
        return run_cost_model(
            monthly_requests=request.monthly_requests,
            avg_input_tokens=request.avg_input_tokens,
            avg_output_tokens=request.avg_output_tokens,
            openai_input_per_1m=request.openai_input_per_1m,
            openai_output_per_1m=request.openai_output_per_1m,
            local_fixed_monthly=request.local_fixed_monthly,
            local_power_monthly=request.local_power_monthly,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/benchmarks/compare")
async def benchmark_compare(request: CompareBenchmarkRequest):
    try:
        return run_compare_benchmarks(request.cpu_report, request.gpu_report)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
