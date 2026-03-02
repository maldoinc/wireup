from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from typing import Any

# Configuration
CSV_PATH = "benchmarks/benchmark_results.csv"
RUN_CSV_PATH = "benchmarks/benchmark_run_metrics.csv"
DOCS_PATH = "docs/pages/benchmarks.md"
PROJECT_ALIASES = {
    "FastAPI": "FastAPI Depends",
    "Injector (+fastapi-injector) †": "Injector †",
}


def load_results(csv_path: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["project"] = PROJECT_ALIASES.get(row["project"], row["project"])
            row["rps"] = float(row["rps"])
            row["p50"] = float(row["p50"])
            row["p95"] = float(row["p95"])
            row["p99"] = float(row["p99"])
            row["stdev"] = float(row.get("stdev", 0))
            row["rss_peak"] = float(row.get("rss_peak", 0))
            row["min_rps"] = float(row.get("min_rps", 0))
            row["max_rps"] = float(row.get("max_rps", 0))
            row["rps_cv_pct"] = float(row.get("rps_cv_pct", 0))
            results.append(row)
    return results


def load_run_consistency(run_csv_path: str) -> dict[tuple[str, str], dict[str, float]]:
    grouped_rps: dict[tuple[str, str], list[float]] = {}
    grouped_p50: dict[tuple[str, str], list[float]] = {}
    grouped_p95: dict[tuple[str, str], list[float]] = {}
    grouped_p99: dict[tuple[str, str], list[float]] = {}
    grouped_duration: dict[tuple[str, str], list[float]] = {}
    with open(run_csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            project = PROJECT_ALIASES.get(row["project"], row["project"])
            key = (project, row["test"])
            grouped_rps.setdefault(key, []).append(float(row["rps_requested"]))
            grouped_p50.setdefault(key, []).append(float(row["p50"]))
            grouped_p95.setdefault(key, []).append(float(row["p95"]))
            grouped_p99.setdefault(key, []).append(float(row["p99"]))
            grouped_duration.setdefault(key, []).append(float(row["duration_s"]))

    consistency: dict[tuple[str, str], dict[str, float]] = {}

    for key, rps_values in grouped_rps.items():
        if not rps_values:
            consistency[key] = {
                "within_3_pct": 0.0,
                "median_p50": 0.0,
                "median_p95": 0.0,
                "median_p99": 0.0,
                "total_duration_s": 0.0,
                "avg_duration_s": 0.0,
                "runs_count": 0.0,
            }
            continue
        durations = grouped_duration.get(key, [])
        total_duration_s = sum(durations)
        avg_duration_s = (total_duration_s / len(durations)) if durations else 0.0
        median_rps = statistics.median(rps_values)
        lower = median_rps * 0.97
        upper = median_rps * 1.03
        within_3 = sum(1 for x in rps_values if lower <= x <= upper)
        consistency[key] = {
            "within_3_pct": within_3 / len(rps_values) * 100.0,
            "median_p50": statistics.median(grouped_p50.get(key, [0.0])),
            "median_p95": statistics.median(grouped_p95.get(key, [0.0])),
            "median_p99": statistics.median(grouped_p99.get(key, [0.0])),
            "total_duration_s": total_duration_s,
            "avg_duration_s": avg_duration_s,
            "runs_count": float(len(durations)),
        }
    return consistency


def format_memory_mb(value_mb: float) -> str:
    if value_mb < 1:
        return f"{value_mb * 1024:.0f} KB"
    if value_mb < 1024:
        return f"{value_mb:.2f} MB"
    return f"{value_mb / 1024:.2f} GB"


def generate_markdown_table(test_name: str, results: list[dict[str, Any]]) -> str:
    globals_row = next(r for r in results if r["project"] == "Manual Wiring (No DI)" and r["test"] == test_name)

    test_results = [r for r in results if r["test"] == test_name]
    test_results.sort(key=lambda x: x["rps"], reverse=True)

    lines = [
        "| Project | RPS (Median Run) | P50 (ms) | P95 (ms) | P99 (ms) | σ (ms) | Mem Peak |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for r in test_results:
        project_name = f"**{r['project']}**"

        # Round RPS and format with commas
        rps_formatted = f"{int(round(r['rps'])):,}"
        globals_pct = (r["rps"] / globals_row["rps"] * 100.0) if globals_row["rps"] else 0.0
        rps_with_globals = f'{rps_formatted} <span class="bench-diff">({globals_pct:.2f}%)</span>'
        rss_formatted = format_memory_mb(r["rss_peak"])

        lines.append(
            f"| {project_name} | {rps_with_globals} | {r['p50']:.2f} | "
            f"{r['p95']:.2f} | {r['p99']:.2f} | {r['stdev']:.2f} | {rss_formatted} |"
        )

    return "\n".join(lines)


def generate_stability_table(
    test_name: str, results: list[dict[str, Any]], consistency: dict[tuple[str, str], dict[str, float]]
) -> str:
    test_results = [r for r in results if r["test"] == test_name]
    test_results.sort(key=lambda x: x["rps"], reverse=True)

    lines = [
        "#### Stability (Across Runs)",
        "",
        "These values summarize all runs for each project in this test. "
        "**Median P50/P95/P99** are the medians of those per-run latency percentiles, while **Within ±3%** shows the share of runs whose RPS stayed within 3% of that project's median-run RPS.",
        "Look for **smaller Δ RPS**, **higher Within ±3%**, and **lower median tail latencies (P95/P99)** for the most consistent behavior.",
        "",
        "| Project | Min RPS | Max RPS | Δ RPS | Within ±3% | Med P50 (ms) | Med P95 (ms) | Med P99 (ms) |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for r in test_results:
        project_name = r["project"]
        min_rps_formatted = f"{int(round(r['min_rps'])):,}"
        max_rps_formatted = f"{int(round(r['max_rps'])):,}"
        delta_rps_pct = ((r["max_rps"] - r["min_rps"]) / r["rps"] * 100.0) if r["rps"] else 0.0
        c = consistency.get((r["project"], test_name), {})
        within_3_pct = c.get("within_3_pct", 0.0)
        median_p50 = c.get("median_p50", 0.0)
        median_p95 = c.get("median_p95", 0.0)
        median_p99 = c.get("median_p99", 0.0)
        row_values = [
            f"**{project_name}**",
            min_rps_formatted,
            max_rps_formatted,
            f"{delta_rps_pct:.2f}%",
            f"{within_3_pct:.1f}%",
            f"{median_p50:.2f}",
            f"{median_p95:.2f}",
            f"{median_p99:.2f}",
        ]
        if within_3_pct < 100.0:
            row_values = [
                f'<span class="bench-worse"><strong>{v}</strong></span>' for v in [project_name, *row_values[1:]]
            ]

        lines.append(
            f"| {row_values[0]} | {row_values[1]} | {row_values[2]} | {row_values[3]} | "
            f"{row_values[4]} | {row_values[5]} | {row_values[6]} | {row_values[7]} |"
        )

    return "\n".join(lines)


def format_duration(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours > 0:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def generate_duration_table(
    test_name: str, results: list[dict[str, Any]], consistency: dict[tuple[str, str], dict[str, float]]
) -> str:
    test_results = [r for r in results if r["test"] == test_name]
    test_results.sort(key=lambda x: consistency.get((x["project"], test_name), {}).get("total_duration_s", 0.0))
    fastest_total_s = (
        consistency.get((test_results[0]["project"], test_name), {}).get("total_duration_s", 0.0)
        if test_results
        else 0.0
    )

    lines = [
        "#### Time to Complete All Runs (Lower Is Better)",
        "",
        "This aggregates measured request-phase runtime across all runs for each project in this test.",
        "",
        "| Project | Total Time (HH:MM:SS) | Total Time (s) | + vs Fastest | Avg Time / Run | Runs |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for r in test_results:
        project_name = f"**{r['project']}**"
        c = consistency.get((r["project"], test_name), {})
        total_duration_s = c.get("total_duration_s", 0.0)
        avg_duration_s = c.get("avg_duration_s", 0.0)
        runs_count = int(round(c.get("runs_count", 0.0)))
        delta_vs_fastest = max(0.0, total_duration_s - fastest_total_s)
        lines.append(
            f"| {project_name} | {format_duration(total_duration_s)} | {total_duration_s:.2f} | "
            f"+{format_duration(delta_vs_fastest)} | {avg_duration_s:.2f}s | {runs_count} |"
        )

    return "\n".join(lines)


def _find_result(results: list[dict[str, Any]], test_name: str, project_name: str) -> dict[str, Any]:
    return next(r for r in results if r["test"] == test_name and r["project"] == project_name)


def _summary_meta_values(results: list[dict[str, Any]], test_name: str) -> dict[str, str]:
    globals_rps = _find_result(results, test_name, "Manual Wiring (No DI)")["rps"]
    wireup_rps = _find_result(results, test_name, "Wireup")["rps"]
    wireup_cbr_rps = _find_result(results, test_name, "Wireup Class-Based")["rps"]
    fastapi_rps = _find_result(results, test_name, "FastAPI Depends")["rps"]

    candidates = [
        r
        for r in results
        if r["test"] == test_name
        and not r["project"].lower().startswith("wireup")
        and r["project"] != "Manual Wiring (No DI)"
        # Keep FastAPI as a separate explicit comparator in summaries.
        and r["project"] != "FastAPI Depends"
    ]
    next_best = max(candidates, key=lambda r: r["rps"]) if candidates else None

    prefix = test_name
    values: dict[str, str] = {
        f"{prefix}_wireup_cbr_pct": f"**{(wireup_cbr_rps / globals_rps * 100.0):.2f}%**",
        f"{prefix}_wireup_pct": f"**{(wireup_rps / globals_rps * 100.0):.2f}%**",
        f"{prefix}_wireup_vs_fastapi_x": f"**{(wireup_rps / fastapi_rps):.2f}x**",
    }

    if next_best:
        values[f"{prefix}_wireup_vs_next_best_x"] = f"**{(wireup_rps / next_best['rps']):.2f}x**"
        values[f"{prefix}_next_best_name"] = str(next_best["project"])

    return values


def update_docs(csv_path: str, run_csv_path: str) -> None:
    results = load_results(csv_path)
    consistency = load_run_consistency(run_csv_path)

    with open(DOCS_PATH) as f:
        content = f.read()

    for test in ["singleton", "scoped"]:
        table = generate_markdown_table(test, results)
        stability_table = generate_stability_table(test, results, consistency)
        duration_table = generate_duration_table(test, results, consistency)
        pattern = rf"<!-- {test}-start -->.*?<!-- {test}-end -->"
        replacement = f"<!-- {test}-start -->\n{table}\n\n{stability_table}\n\n{duration_table}\n<!-- {test}-end -->"
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    # Per-test narrative summaries are intentionally maintained manually in docs.

    with open(DOCS_PATH, "w") as f:
        f.write(content)

    print(f"Successfully updated {DOCS_PATH} using {csv_path}")

    # Update metadata
    meta = {}
    try:
        with open("benchmarks/benchmark_meta.json") as f:
            meta = json.load(f)

        with open(DOCS_PATH) as f:
            content = f.read()

        # Helper to replace metadata
        def replace_meta(key: str, value: Any) -> str:
            # Formats: 10000 -> 10,000
            if isinstance(value, int):
                val_str = f"{value:,}"
            else:
                val_str = str(value)

            pattern = f"<!-- meta:{key} -->.*?<!-- /meta:{key} -->"
            replacement = f"<!-- meta:{key} -->{val_str}<!-- /meta:{key} -->"
            return re.sub(pattern, replacement, content, flags=re.DOTALL)

        content = replace_meta("iterations", meta["iterations"])
        content = replace_meta("requests", meta["requests"])
        content = replace_meta("warmup_requests", meta["warmup_requests"])
        content = replace_meta("concurrency", meta["concurrency"])
        content = replace_meta("python_version", "v" + meta["python_version"])

        # Keep narrative text manual while still auto-refreshing summary placeholders.
        summary_values: dict[str, str] = {}
        summary_values.update(_summary_meta_values(results, "scoped"))
        summary_values.update(_summary_meta_values(results, "singleton"))
        for key, value in summary_values.items():
            content = replace_meta(key, value)

        with open(DOCS_PATH, "w") as f:
            f.write(content)
        print("Successfully updated metadata in docs")

    except Exception as e:
        print(f"Could not update metadata: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate benchmark tables from CSV")
    parser.add_argument("input", type=str, nargs="?", default=CSV_PATH, help="Input CSV file path")
    parser.add_argument("--runs-input", type=str, default=RUN_CSV_PATH, help="Input run-level CSV file path")
    args = parser.parse_args()

    update_docs(args.input, args.runs_input)
