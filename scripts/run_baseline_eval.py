"""CLI entrypoint for internal baseline evaluation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from src.evaluation.baseline_runner import main_sync


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run baseline evaluation for internal comparison.")
    parser.add_argument("--dataset", default=None, help="Optional dataset path.")
    parser.add_argument(
        "--modes",
        default="single_agent,rag_baseline,current_system",
        help="Comma-separated modes to run.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = main_sync(dataset=args.dataset, modes=args.modes)

    print("Baseline evaluation completed.")
    print(f"Dataset: {payload['dataset']}")
    for mode in payload["modes"]:
        summary = payload["summary"][mode]
        print(
            f"{mode}: success={summary['success_rate']:.2%} "
            f"correct={summary['correct_rate']:.2%} "
            f"avg_latency_ms={summary['avg_latency_ms']} "
            f"avg_vector_hits={summary['avg_vector_hits']} "
            f"avg_graph_hits={summary['avg_graph_hits']}"
        )
    print(f"JSON report: {payload['report_paths']['json']}")
    print(f"Markdown report: {payload['report_paths']['markdown']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
