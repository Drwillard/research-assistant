import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: str) -> dict[str, Any]:
    p = Path(path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Missing file: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def speedup(a: float, b: float) -> float:
    if b == 0:
        return 0.0
    return a / b


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare CPU and GPU benchmark result JSON files.")
    parser.add_argument("--cpu", required=True, help="Path to CPU benchmark JSON report.")
    parser.add_argument("--gpu", required=True, help="Path to GPU benchmark JSON report.")
    args = parser.parse_args()

    cpu = load_json(args.cpu)
    gpu = load_json(args.gpu)

    cpu_mean = float(cpu["summary"]["mean_ms"])
    cpu_p95 = float(cpu["summary"]["p95_ms"])
    gpu_mean = float(gpu["summary"]["mean_ms"])
    gpu_p95 = float(gpu["summary"]["p95_ms"])

    mean_speedup = speedup(cpu_mean, gpu_mean)
    p95_speedup = speedup(cpu_p95, gpu_p95)

    cpu_rps = 1000.0 / cpu_mean if cpu_mean else 0.0
    gpu_rps = 1000.0 / gpu_mean if gpu_mean else 0.0

    print("CPU vs GPU benchmark comparison")
    print(f"CPU label: {cpu.get('label', 'cpu')}")
    print(f"GPU label: {gpu.get('label', 'gpu')}")
    print("")
    print(f"Mean latency ms: CPU {cpu_mean:.2f} | GPU {gpu_mean:.2f} | Speedup {mean_speedup:.2f}x")
    print(f"P95 latency ms:  CPU {cpu_p95:.2f} | GPU {gpu_p95:.2f} | Speedup {p95_speedup:.2f}x")
    print(f"Throughput RPS:  CPU {cpu_rps:.3f} | GPU {gpu_rps:.3f}")


if __name__ == "__main__":
    main()
