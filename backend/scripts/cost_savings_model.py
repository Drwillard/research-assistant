import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Estimate OpenAI vs local monthly cost.")
    parser.add_argument("--monthly-requests", type=int, required=True)
    parser.add_argument("--avg-input-tokens", type=int, required=True)
    parser.add_argument("--avg-output-tokens", type=int, required=True)
    parser.add_argument("--openai-input-per-1m", type=float, default=0.15)
    parser.add_argument("--openai-output-per-1m", type=float, default=0.60)
    parser.add_argument("--local-fixed-monthly", type=float, default=0.0, help="Server/GPU amortized monthly cost.")
    parser.add_argument("--local-power-monthly", type=float, default=0.0)
    parser.add_argument("--output", default="", help="Optional JSON output path.")
    args = parser.parse_args()

    input_tokens_month = args.monthly_requests * args.avg_input_tokens
    output_tokens_month = args.monthly_requests * args.avg_output_tokens

    openai_input_cost = (input_tokens_month / 1_000_000) * args.openai_input_per_1m
    openai_output_cost = (output_tokens_month / 1_000_000) * args.openai_output_per_1m
    openai_total = openai_input_cost + openai_output_cost

    local_total = args.local_fixed_monthly + args.local_power_monthly

    delta = openai_total - local_total
    savings_pct = (delta / openai_total * 100.0) if openai_total > 0 else 0.0

    openai_cost_per_req = openai_total / args.monthly_requests if args.monthly_requests else 0.0
    local_cost_per_req = local_total / args.monthly_requests if args.monthly_requests else 0.0

    report = {
        "inputs": {
            "monthly_requests": args.monthly_requests,
            "avg_input_tokens": args.avg_input_tokens,
            "avg_output_tokens": args.avg_output_tokens,
            "openai_input_per_1m": args.openai_input_per_1m,
            "openai_output_per_1m": args.openai_output_per_1m,
            "local_fixed_monthly": args.local_fixed_monthly,
            "local_power_monthly": args.local_power_monthly,
        },
        "results": {
            "openai_monthly_total_usd": round(openai_total, 2),
            "local_monthly_total_usd": round(local_total, 2),
            "monthly_delta_usd_openai_minus_local": round(delta, 2),
            "local_savings_percent_vs_openai": round(savings_pct, 2),
            "openai_cost_per_request_usd": round(openai_cost_per_req, 6),
            "local_cost_per_request_usd": round(local_cost_per_req, 6),
        },
    }

    print("Cost comparison (monthly)")
    print(f"OpenAI total: ${report['results']['openai_monthly_total_usd']}")
    print(f"Local total:  ${report['results']['local_monthly_total_usd']}")
    print(f"Delta:        ${report['results']['monthly_delta_usd_openai_minus_local']} (OpenAI - Local)")
    print(f"Savings %:    {report['results']['local_savings_percent_vs_openai']}%")

    if args.output:
        out_path = Path(args.output).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote report: {out_path}")


if __name__ == "__main__":
    main()
