"""Dataset-driven baseline evaluation for internal comparisons."""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any

from src.agents.graph.workflow import get_workflow
from src.agents.workers.faq_worker import FAQWorker
from src.rag.retriever import clear_retrieval_logs, get_retrieval_logs

VALID_MODES = ("single_agent", "rag_baseline", "current_system")
_NORMALIZE_RE = re.compile(r"[^0-9A-Za-z\u4e00-\u9fff]+")


@dataclass(frozen=True)
class EvaluationCase:
    """A single question and its scoring hints."""

    id: str
    query: str
    expected_all_of: list[str]
    expected_any_of: list[str]
    notes: str = ""


class BaselineRunner:
    """Run the requested evaluation modes against a fixed dataset."""

    def __init__(
        self,
        dataset_path: str | Path | None = None,
        modes: list[str] | None = None,
        output_dir: str | Path | None = None,
    ):
        root = Path(__file__).resolve().parents[2]
        self.dataset_path = Path(dataset_path) if dataset_path else root / "data" / "eval_queries" / "baseline_product_qa.json"
        self.output_dir = Path(output_dir) if output_dir else root / "reports" / "baseline"
        requested_modes = modes or list(VALID_MODES)
        invalid_modes = [mode for mode in requested_modes if mode not in VALID_MODES]
        if invalid_modes:
            raise ValueError(f"Unsupported modes: {', '.join(invalid_modes)}")
        self.modes = requested_modes

    def load_dataset(self) -> list[EvaluationCase]:
        """Load and validate the evaluation dataset."""
        payload = json.loads(self.dataset_path.read_text(encoding="utf-8"))
        cases: list[EvaluationCase] = []
        for item in payload:
            cases.append(
                EvaluationCase(
                    id=str(item["id"]),
                    query=str(item["query"]),
                    expected_all_of=[str(value) for value in item.get("expected_all_of", [])],
                    expected_any_of=[str(value) for value in item.get("expected_any_of", [])],
                    notes=str(item.get("notes", "")),
                )
            )
        return cases

    async def run(self) -> dict[str, Any]:
        """Execute the configured modes and write JSON/Markdown reports."""
        cases = self.load_dataset()
        results: list[dict[str, Any]] = []

        for mode in self.modes:
            for case in cases:
                results.append(await self._run_case(mode, case))

        summary = self._build_summary(results)
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload = {
            "generated_at": generated_at,
            "dataset": str(self.dataset_path),
            "modes": self.modes,
            "summary": summary,
            "results": results,
        }
        report_paths = self._write_reports(payload)
        payload["report_paths"] = report_paths
        return payload

    async def _run_case(self, mode: str, case: EvaluationCase) -> dict[str, Any]:
        clear_retrieval_logs()
        started = perf_counter()
        answer = ""
        status = "ok"
        error = None
        worker_type = "faq_worker"

        try:
            if mode == "single_agent":
                answer = await self._run_single_agent(case.query)
            elif mode == "rag_baseline":
                answer = await self._run_rag_baseline(case.query)
            else:
                answer, worker_type = await self._run_current_system(case.query, case.id)
        except Exception as exc:
            status = "error"
            error = str(exc)

        latency_ms = int((perf_counter() - started) * 1000)
        vector_hits, graph_hits, retrieval_sources = self._collect_retrieval_metrics()
        correct = status == "ok" and self._score_answer(answer, case)

        return {
            "mode": mode,
            "query_id": case.id,
            "query": case.query,
            "answer": answer,
            "status": status,
            "error": error,
            "latency_ms": latency_ms,
            "worker_type": worker_type,
            "vector_hits": vector_hits,
            "graph_hits": graph_hits,
            "retrieval_sources": retrieval_sources,
            "correct": correct,
        }

    async def _run_single_agent(self, query: str) -> str:
        worker = FAQWorker()
        return await worker.handle(
            user_input=query,
            context={
                "enable_retrieval": False,
            },
            history="",
        )

    async def _run_rag_baseline(self, query: str) -> str:
        worker = FAQWorker()
        return await worker.handle(
            user_input=query,
            context={
                "enable_retrieval": True,
                "use_vector": True,
                "use_graph": False,
                "use_reranker": False,
            },
            history="",
        )

    async def _run_current_system(self, query: str, query_id: str) -> tuple[str, str]:
        workflow = get_workflow()
        result = await workflow.ainvoke(
            {
                "messages": [],
                "user_input": query,
                "conversation_id": f"baseline-{query_id}",
                "user_id": None,
                "context": {"baseline_eval": True},
                "needs_human": False,
                "web_search": False,
                "retry_count": 0,
            }
        )
        answer = str(result.get("response") or result.get("worker_result") or "")
        worker_type = str(result.get("worker_type") or "faq_worker")
        return answer, worker_type

    def _collect_retrieval_metrics(self) -> tuple[int, int, list[str]]:
        logs = get_retrieval_logs()
        if not logs:
            return 0, 0, []

        vector_hits = sum(int(entry.get("vector_hits", 0)) for entry in logs)
        graph_hits = sum(int(entry.get("graph_hits", 0)) for entry in logs)
        sources: list[str] = []
        for entry in logs:
            for source in entry.get("sources", []):
                if source not in sources:
                    sources.append(source)
        return vector_hits, graph_hits, sources

    def _build_summary(self, results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        summary: dict[str, dict[str, Any]] = {}
        for mode in self.modes:
            mode_results = [result for result in results if result["mode"] == mode]
            if not mode_results:
                continue

            success_results = [result for result in mode_results if result["status"] == "ok"]
            summary[mode] = {
                "total": len(mode_results),
                "success_rate": round(len(success_results) / len(mode_results), 4),
                "correct_rate": round(sum(1 for result in mode_results if result["correct"]) / len(mode_results), 4),
                "avg_latency_ms": round(mean(result["latency_ms"] for result in success_results), 2) if success_results else 0,
                "avg_vector_hits": round(mean(result["vector_hits"] for result in mode_results), 2),
                "avg_graph_hits": round(mean(result["graph_hits"] for result in mode_results), 2),
                "failed_samples": [
                    {
                        "query_id": result["query_id"],
                        "status": result["status"],
                        "correct": result["correct"],
                        "error": result["error"],
                    }
                    for result in mode_results
                    if result["status"] != "ok" or not result["correct"]
                ][:5],
            }
        return summary

    def _write_reports(self, payload: dict[str, Any]) -> dict[str, str]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        json_path = self.output_dir / f"baseline-{timestamp}.json"
        md_path = self.output_dir / f"baseline-{timestamp}.md"

        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        md_path.write_text(self._render_markdown(payload), encoding="utf-8")

        return {
            "json": str(json_path),
            "markdown": str(md_path),
        }

    def _render_markdown(self, payload: dict[str, Any]) -> str:
        lines = [
            "# Baseline Evaluation Report",
            "",
            f"- Generated at: {payload['generated_at']}",
            f"- Dataset: `{payload['dataset']}`",
            f"- Modes: `{', '.join(payload['modes'])}`",
            "",
            "## Summary",
            "",
            "| Mode | Success Rate | Correct Rate | Avg Latency (ms) | Avg Vector Hits | Avg Graph Hits |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for mode in payload["modes"]:
            item = payload["summary"][mode]
            lines.append(
                f"| {mode} | {item['success_rate']:.2%} | {item['correct_rate']:.2%} | "
                f"{item['avg_latency_ms']} | {item['avg_vector_hits']} | {item['avg_graph_hits']} |"
            )

        lines.extend(["", "## Failures", ""])
        failures = [
            result
            for result in payload["results"]
            if result["status"] != "ok" or not result["correct"]
        ]
        if not failures:
            lines.append("No failures recorded.")
        else:
            for result in failures:
                lines.append(
                    f"- `{result['mode']}` / `{result['query_id']}` / status=`{result['status']}` / "
                    f"correct=`{result['correct']}` / worker=`{result['worker_type']}`"
                )
                if result["error"]:
                    lines.append(f"  error: `{result['error']}`")
                else:
                    lines.append(f"  answer: {self._clip_text(result['answer'])}")

        lines.extend(["", "## Results", ""])
        lines.append("| Mode | Query ID | Status | Correct | Worker | Latency (ms) | Vector Hits | Graph Hits | Sources |")
        lines.append("| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |")
        for result in payload["results"]:
            sources = ", ".join(result["retrieval_sources"]) if result["retrieval_sources"] else "-"
            lines.append(
                f"| {result['mode']} | {result['query_id']} | {result['status']} | {result['correct']} | "
                f"{result['worker_type']} | {result['latency_ms']} | {result['vector_hits']} | "
                f"{result['graph_hits']} | {sources} |"
            )
        return "\n".join(lines) + "\n"

    @staticmethod
    def _score_answer(answer: str, case: EvaluationCase) -> bool:
        normalized_answer = BaselineRunner._normalize_text(answer)
        all_of_ok = all(BaselineRunner._normalize_text(token) in normalized_answer for token in case.expected_all_of)
        any_of_ok = True
        if case.expected_any_of:
            any_of_ok = any(BaselineRunner._normalize_text(token) in normalized_answer for token in case.expected_any_of)
        return all_of_ok and any_of_ok

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = (
            text.replace("×", "x")
            .replace("脳", "x")
            .replace("╳", "x")
            .replace("＊", "x")
        )
        return _NORMALIZE_RE.sub("", normalized).lower()

    @staticmethod
    def _clip_text(text: str, max_len: int = 180) -> str:
        compact = " ".join(text.split())
        if len(compact) <= max_len:
            return compact
        return compact[: max_len - 3] + "..."


def parse_modes(raw_modes: str | None) -> list[str]:
    """Parse comma-separated modes from the CLI."""
    if not raw_modes:
        return list(VALID_MODES)
    return [mode.strip() for mode in raw_modes.split(",") if mode.strip()]


async def run_from_cli(dataset: str | None = None, modes: str | None = None) -> dict[str, Any]:
    """Run the evaluation with CLI-style inputs."""
    runner = BaselineRunner(dataset_path=dataset, modes=parse_modes(modes))
    return await runner.run()


def main_sync(dataset: str | None = None, modes: str | None = None) -> dict[str, Any]:
    """Synchronous wrapper for script entrypoints."""
    return asyncio.run(run_from_cli(dataset=dataset, modes=modes))
