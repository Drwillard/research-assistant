import json
import statistics
import time
from typing import Any

from .config import normalize_provider
from .ingestion import ingest_pdf
from .rag import query_rag


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    k = (len(values) - 1) * p
    f = int(k)
    c = min(f + 1, len(values) - 1)
    if f == c:
        return values[f]
    return values[f] + (values[c] - values[f]) * (k - f)


def summarize(values_ms: list[float]) -> dict[str, float]:
    ordered = sorted(values_ms)
    if not ordered:
        return {"count": 0.0, "min_ms": 0.0, "max_ms": 0.0, "mean_ms": 0.0, "median_ms": 0.0, "p95_ms": 0.0}
    return {
        "count": float(len(ordered)),
        "min_ms": round(min(ordered), 2),
        "max_ms": round(max(ordered), 2),
        "mean_ms": round(statistics.mean(ordered), 2),
        "median_ms": round(statistics.median(ordered), 2),
        "p95_ms": round(percentile(ordered, 0.95), 2),
    }


async def run_latency_benchmark(
    *,
    pdf_bytes: bytes,
    filename: str,
    provider: str,
    queries: list[str],
    runs: int,
    warmup_runs: int,
) -> dict[str, Any]:
    provider = normalize_provider(provider)
    cleaned = [q.strip() for q in queries if q.strip()]
    if not cleaned:
        raise ValueError("At least one query is required.")
    if runs < 1 or runs > 100:
        raise ValueError("Runs must be between 1 and 100.")
    if warmup_runs < 0 or warmup_runs > 20:
        raise ValueError("Warmup runs must be between 0 and 20.")

    ingest_result = await ingest_pdf(pdf_bytes, filename, provider=provider)

    warmup_count = 0
    for _ in range(warmup_runs):
        for q in cleaned:
            await query_rag(q, [], provider=provider)
            warmup_count += 1

    overall: list[float] = []
    per_query: dict[str, list[float]] = {q: [] for q in cleaned}
    for _ in range(runs):
        for q in cleaned:
            start = time.perf_counter()
            await query_rag(q, [], provider=provider)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            overall.append(elapsed_ms)
            per_query[q].append(elapsed_ms)

    return {
        "provider": provider,
        "ingest_result": ingest_result,
        "warmup_count": warmup_count,
        "summary": summarize(overall),
        "per_query": {q: summarize(v) for q, v in per_query.items()},
    }


def run_cost_model(
    *,
    monthly_requests: int,
    avg_input_tokens: int,
    avg_output_tokens: int,
    openai_input_per_1m: float,
    openai_output_per_1m: float,
    local_fixed_monthly: float,
    local_power_monthly: float,
) -> dict[str, Any]:
    if monthly_requests <= 0:
        raise ValueError("monthly_requests must be > 0.")
    if avg_input_tokens < 0 or avg_output_tokens < 0:
        raise ValueError("Token values must be >= 0.")

    input_tokens_month = monthly_requests * avg_input_tokens
    output_tokens_month = monthly_requests * avg_output_tokens

    openai_input_cost = (input_tokens_month / 1_000_000) * openai_input_per_1m
    openai_output_cost = (output_tokens_month / 1_000_000) * openai_output_per_1m
    openai_total = openai_input_cost + openai_output_cost
    local_total = local_fixed_monthly + local_power_monthly

    delta = openai_total - local_total
    savings_pct = (delta / openai_total * 100.0) if openai_total > 0 else 0.0

    return {
        "openai_monthly_total_usd": round(openai_total, 2),
        "local_monthly_total_usd": round(local_total, 2),
        "monthly_delta_usd_openai_minus_local": round(delta, 2),
        "local_savings_percent_vs_openai": round(savings_pct, 2),
        "openai_cost_per_request_usd": round(openai_total / monthly_requests, 6),
        "local_cost_per_request_usd": round(local_total / monthly_requests, 6),
    }


def run_compare_benchmarks(cpu_report: dict[str, Any], gpu_report: dict[str, Any]) -> dict[str, Any]:
    try:
        cpu_mean = float(cpu_report["summary"]["mean_ms"])
        cpu_p95 = float(cpu_report["summary"]["p95_ms"])
        gpu_mean = float(gpu_report["summary"]["mean_ms"])
        gpu_p95 = float(gpu_report["summary"]["p95_ms"])
    except Exception as exc:
        raise ValueError("Both reports must include summary.mean_ms and summary.p95_ms.") from exc

    if cpu_mean <= 0 or gpu_mean <= 0:
        raise ValueError("mean_ms must be > 0 in both reports.")
    if cpu_p95 <= 0 or gpu_p95 <= 0:
        raise ValueError("p95_ms must be > 0 in both reports.")

    mean_speedup = cpu_mean / gpu_mean
    p95_speedup = cpu_p95 / gpu_p95
    cpu_rps = 1000.0 / cpu_mean
    gpu_rps = 1000.0 / gpu_mean

    return {
        "cpu_label": cpu_report.get("label", "cpu"),
        "gpu_label": gpu_report.get("label", "gpu"),
        "cpu_mean_ms": round(cpu_mean, 2),
        "gpu_mean_ms": round(gpu_mean, 2),
        "cpu_p95_ms": round(cpu_p95, 2),
        "gpu_p95_ms": round(gpu_p95, 2),
        "mean_speedup_x": round(mean_speedup, 2),
        "p95_speedup_x": round(p95_speedup, 2),
        "cpu_rps": round(cpu_rps, 3),
        "gpu_rps": round(gpu_rps, 3),
    }


def parse_queries(raw: str | None) -> list[str]:
    if raw is None or not raw.strip():
        return [
            "Summarize the paper in three bullet points.",
            "What method is used and what are the key limitations?",
        ]
    try:
        decoded = json.loads(raw)
        if isinstance(decoded, list):
            return [str(x) for x in decoded]
    except Exception:
        pass
    return [line.strip() for line in raw.splitlines() if line.strip()]
