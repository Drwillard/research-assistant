import argparse
import json
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


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
    return {
        "count": float(len(ordered)),
        "min_ms": round(min(ordered), 2),
        "max_ms": round(max(ordered), 2),
        "mean_ms": round(statistics.mean(ordered), 2),
        "median_ms": round(statistics.median(ordered), 2),
        "p95_ms": round(percentile(ordered, 0.95), 2),
    }


def ingest_once(client: httpx.Client, api_url: str, provider: str, pdf_path: Path) -> dict[str, Any]:
    with pdf_path.open("rb") as f:
        files = {"file": (pdf_path.name, f, "application/pdf")}
        data = {"provider": provider}
        r = client.post(f"{api_url}/ingest", files=files, data=data, timeout=300.0)
    r.raise_for_status()
    return r.json()


def chat_once(client: httpx.Client, api_url: str, provider: str, prompt: str) -> tuple[float, dict[str, Any]]:
    payload = {"message": prompt, "conversation_history": [], "provider": provider}
    start = time.perf_counter()
    r = client.post(f"{api_url}/chat", json=payload, timeout=300.0)
    elapsed_ms = (time.perf_counter() - start) * 1000
    r.raise_for_status()
    return elapsed_ms, r.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark local-first RAG latency via API.")
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--provider", default="ollama", choices=["openai", "ollama"])
    parser.add_argument("--pdf", required=True, help="Path to a PDF to ingest.")
    parser.add_argument("--query", action="append", dest="queries", default=[])
    parser.add_argument("--runs", type=int, default=5, help="Runs per query.")
    parser.add_argument("--warmup-runs", type=int, default=1)
    parser.add_argument("--label", default="local-benchmark")
    parser.add_argument("--output", default="", help="Optional output JSON file path.")
    args = parser.parse_args()

    queries = args.queries or [
        "Summarize the main contribution in three bullets.",
        "What method is used and what are its limitations?",
    ]
    pdf_path = Path(args.pdf).resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    with httpx.Client() as client:
        ingest_result = ingest_once(client, args.api_url, args.provider, pdf_path)

        warmup_latencies: list[float] = []
        for _ in range(args.warmup_runs):
            for q in queries:
                ms, _ = chat_once(client, args.api_url, args.provider, q)
                warmup_latencies.append(ms)

        latencies: list[float] = []
        per_query: dict[str, list[float]] = {q: [] for q in queries}
        for _ in range(args.runs):
            for q in queries:
                ms, _ = chat_once(client, args.api_url, args.provider, q)
                latencies.append(ms)
                per_query[q].append(ms)

    overall = summarize(latencies)
    query_stats = {q: summarize(v) for q, v in per_query.items()}
    report = {
        "label": args.label,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "system": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "processor": platform.processor(),
            "machine": platform.machine(),
        },
        "config": {
            "api_url": args.api_url,
            "provider": args.provider,
            "pdf": str(pdf_path),
            "runs_per_query": args.runs,
            "warmup_runs": args.warmup_runs,
            "queries": queries,
        },
        "ingest_result": ingest_result,
        "warmup_count": len(warmup_latencies),
        "summary": overall,
        "per_query": query_stats,
    }

    print(f"Benchmark label: {args.label}")
    print(f"Provider: {args.provider}")
    print(f"Ingest status: {ingest_result.get('status')} ({ingest_result.get('chunks')} chunks)")
    print(
        "Latency ms (mean / p95 / min / max): "
        f"{overall['mean_ms']} / {overall['p95_ms']} / {overall['min_ms']} / {overall['max_ms']}"
    )

    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote report: {output_path}")


if __name__ == "__main__":
    main()
