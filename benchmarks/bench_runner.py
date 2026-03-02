# /// script
# dependencies = [
#     "rich==14.2.0",
#     "fastapi==0.124.4", # bench-keep
#     "uvicorn[standard]==0.40.0", # bench-keep
#     "aioinject==1.10.2", # bench-keep
#     "dishka==1.7.2", # bench-keep
#     "dependency-injector==4.48.3", # bench-keep
#     "lagom==2.7.7", # bench-keep
#     "injector==0.24.0", # bench-keep
#     "fastapi-injector==0.9.0", # bench-keep
#     "psutil==7.0.0",
#     "pydantic-settings==2.7.1",
#     "svcs==25.1.0", # bench-keep
#     "that-depends==3.9.1", # bench-keep
#     "diwire==1.3.0", # bench-keep
# ]
# ///

import argparse
import csv
import importlib.metadata
import json
import math
import os
import signal
import shutil
import socket
import statistics
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from contextlib import suppress
from io import StringIO
from typing import Any, Callable, Dict, List, Optional, TextIO, Tuple

import psutil
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

# Configuration
PROJECTS = {
    "globals": "Manual Wiring (No DI)",
    "wireup": "Wireup",
    "wireup_cbr": "Wireup Class-Based",
    "dependency_injector": "Dependency Injector †",
    "aioinject": "Aioinject",
    "fastapi": "FastAPI Depends",
    "dishka": "Dishka",
    "injector": "Injector †",
    "svcs": "Svcs",
    "that_depends": "That Depends",
    "diwire": "diwire",
    "lagom": "Lagom †",
}
TESTS = ["singleton", "scoped"]
CONCURRENCY = 50
LOADGEN_CPU = 1
SERVER_CPU = 2
URL_TEMPLATE = "http://127.0.0.1:{port}/{project}/{test_name}"
SERVER_LOG = "benchmarks/server.log"
HEY_BIN = "hey"
STARTUP_TIMEOUT_S = 20.0
STARTUP_POLL_INTERVAL_S = 0.1
BenchIteration = Dict[str, Any]
BenchResult = Dict[str, Any]
TIMING_COLUMNS = [
    ("response-time", "latency"),
]
SUMMARY_FIELDNAMES = [
    "project",
    "test",
    "runs",
    "rps",
    "min_rps",
    "max_rps",
    "p50",
    "p95",
    "p99",
    "stdev",
    "rss_peak",
]
RUN_FIELDNAMES = [
    "project_id",
    "project",
    "test",
    "iteration",
    "duration_s",
    "success_rate_pct",
    "error_rate_pct",
    "non_200_rate_pct",
    "rps_requested",
    "p50",
    "p95",
    "p99",
    "stdev",
    "rss_peak",
]


def pin_current_process_to_cpu(cpu: int) -> None:
    try:
        psutil.Process().cpu_affinity([cpu])
        print(f"Pinned benchmark runner (load generator) to CPU {cpu}")
    except (AttributeError, NotImplementedError):
        print("CPU affinity not supported on this platform; running unpinned.")
    except Exception as e:
        print(f"Could not pin benchmark runner to CPU {cpu}: {e}")


def pin_process_to_cpu(pid: int, cpu: int) -> None:
    try:
        psutil.Process(pid).cpu_affinity([cpu])
        print(f"Pinned server process (pid={pid}) to CPU {cpu}")
    except (AttributeError, NotImplementedError):
        print("CPU affinity not supported on this platform; server running unpinned.")
    except Exception as e:
        print(f"Could not pin server process {pid} to CPU {cpu}: {e}")


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def resolve_repo_paths() -> Tuple[str, str]:
    benchmarks_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(benchmarks_dir)
    return repo_root, benchmarks_dir


def build_runner_env(
    project: str, bench_assert: bool, use_local_version: bool, repo_root: str, benchmarks_dir: str
) -> Dict[str, str]:
    env = os.environ.copy()
    env["PROJECT"] = project
    if bench_assert:
        env["BENCH_ASSERT"] = "1"

    existing_pythonpath = env.get("PYTHONPATH", "")
    paths = [benchmarks_dir, existing_pythonpath]
    if use_local_version:
        paths.insert(0, repo_root)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, paths))
    return env


def wait_for_server_ready(process: subprocess.Popen[Any], port: int, timeout_s: float = STARTUP_TIMEOUT_S) -> None:
    url = f"http://127.0.0.1:{port}/healthz"
    deadline = time.monotonic() + timeout_s
    last_error = "no response"

    while time.monotonic() < deadline:
        if process.poll() is not None:
            msg = f"Server process exited early with code {process.returncode}"
            raise RuntimeError(msg)

        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:  # noqa: S310
                if response.status == 200:
                    return
                last_error = f"unexpected status: {response.status}"
        except urllib.error.URLError as e:
            last_error = str(e)
        except TimeoutError:
            last_error = "health probe timeout"

        time.sleep(STARTUP_POLL_INTERVAL_S)

    msg = f"Server did not become ready within {timeout_s:.1f}s ({last_error})"
    raise TimeoutError(msg)


def start_server(port: int, env: Dict[str, str], benchmarks_dir: str, log_file: TextIO) -> subprocess.Popen[Any]:
    cmd = [sys.executable, "-m", "uvicorn", "wireup_benchmarks.app:app", "--port", str(port)]
    log_file.flush()
    process = subprocess.Popen(
        cmd,
        stdout=log_file,
        stderr=log_file,
        env=env,
        preexec_fn=os.setsid,
        cwd=benchmarks_dir,
    )
    pin_process_to_cpu(process.pid, SERVER_CPU)
    try:
        wait_for_server_ready(process, port)
    except Exception:
        with suppress(ProcessLookupError):
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        with suppress(Exception):
            process.wait(timeout=5)
        raise
    return process


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    if p <= 0:
        return values[0]
    if p >= 100:
        return values[-1]
    idx = (len(values) - 1) * (p / 100.0)
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return values[lo]
    return values[lo] + (values[hi] - values[lo]) * (idx - lo)


def compute_series_stats_ms(values_seconds: List[float]) -> Dict[str, float]:
    if not values_seconds:
        return {
            "p50_ms": 0.0,
            "p95_ms": 0.0,
            "p99_ms": 0.0,
            "stdev_ms": 0.0,
        }

    sorted_vals = sorted(values_seconds)
    stdev_s = statistics.stdev(sorted_vals) if len(sorted_vals) > 1 else 0.0
    stdev_ms = stdev_s * 1000.0
    return {
        "p50_ms": percentile(sorted_vals, 50.0) * 1000.0,
        "p95_ms": percentile(sorted_vals, 95.0) * 1000.0,
        "p99_ms": percentile(sorted_vals, 99.0) * 1000.0,
        "stdev_ms": stdev_ms,
    }


def monitor_memory_usage(
    process: psutil.Process, stop_event: threading.Event, sample_interval_s: float = 0.02
) -> Dict[str, float]:
    rss_peak = 0.0

    while not stop_event.is_set():
        try:
            rss_mb = process.memory_info().rss / 1024 / 1024
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            break
        rss_peak = max(rss_peak, rss_mb)
        stop_event.wait(sample_interval_s)

    return {"rss_peak_mb": rss_peak}


def run_load_test(url: str, total_requests: int, concurrency: int) -> Dict[str, Any]:
    latencies: List[float] = []
    status_codes: List[int] = []

    cmd = [HEY_BIN, "-n", str(total_requests), "-c", str(concurrency), "-o", "csv", url]
    start_global = time.perf_counter()
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    end_global = time.perf_counter()

    if result.stdout:
        reader = csv.DictReader(StringIO(result.stdout))
        for row in reader:
            response_time = row.get("response-time", "")
            status_code = row.get("status-code", "")
            error = row.get("error", "")

            if response_time:
                with suppress(ValueError):
                    latencies.append(float(response_time))

            if error:
                status_codes.append(0)
            elif status_code:
                try:
                    status_codes.append(int(status_code))
                except ValueError:
                    status_codes.append(0)

    if result.returncode != 0 and not status_codes:
        with open(SERVER_LOG, "a") as log_file:
            log_file.write(
                f"[hey] command failed (exit={result.returncode}) for url={url}, n={total_requests}, c={concurrency}\n"
            )
            if result.stderr:
                log_file.write(result.stderr + "\n")
        status_codes = [0] * total_requests
    duration = end_global - start_global
    success_count = sum(1 for c in status_codes if c == 200)
    non_200_count = sum(1 for c in status_codes if c not in (0, 200))
    error_count = sum(1 for c in status_codes if c == 0)
    success_rate_pct = (success_count / total_requests * 100.0) if total_requests else 0.0
    error_rate_pct = (error_count / total_requests * 100.0) if total_requests else 0.0
    non_200_rate_pct = (non_200_count / total_requests * 100.0) if total_requests else 0.0

    latency_stats = compute_series_stats_ms(latencies)
    rps_requested = total_requests / duration if duration > 0 else 0.0

    return {
        "duration_s": duration,
        "rps_requested": rps_requested,
        "latency_stats": latency_stats,
        "status_codes": status_codes,
        "success_rate_pct": success_rate_pct,
        "error_rate_pct": error_rate_pct,
        "non_200_rate_pct": non_200_rate_pct,
    }


def assert_workload(port: int) -> Tuple[bool, Dict[str, Any]]:
    url = f"http://127.0.0.1:{port}/assert-workload"
    try:
        with urllib.request.urlopen(url) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
            return response.status == 200, payload
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            payload = json.loads(body)
        except ValueError:
            payload = {"ok": False, "error": body or str(e)}
        return False, payload


def run_benchmark(
    project: str,
    test_name: str,
    log_file: TextIO,
    requests: int,
    warmup_requests: int,
    use_local_version: bool,
    bench_assert: bool,
) -> Optional[BenchIteration]:
    print(f"--- Benchmarking {project} - {test_name} ---")

    # Start Server
    port = get_free_port()
    repo_root, benchmarks_dir = resolve_repo_paths()
    env = build_runner_env(
        project=project,
        bench_assert=bench_assert,
        use_local_version=use_local_version,
        repo_root=repo_root,
        benchmarks_dir=benchmarks_dir,
    )

    # Using start_new_session to easily kill the process group later
    log_file.write(f"\n--- {project} - {test_name} ---\n")
    process = start_server(port=port, env=env, benchmarks_dir=benchmarks_dir, log_file=log_file)
    p = psutil.Process(process.pid)
    try:
        url = URL_TEMPLATE.format(port=port, project=project, test_name=test_name)

        # Warmup
        if warmup_requests > 0:
            run_load_test(url, warmup_requests, concurrency=CONCURRENCY)

        # Run single measured load test
        stop_event = threading.Event()
        monitor_result: Dict[str, float] = {"rss_peak_mb": 0.0}

        def sample_memory() -> None:
            nonlocal monitor_result
            monitor_result = monitor_memory_usage(p, stop_event)

        monitor_thread = threading.Thread(target=sample_memory, daemon=True)
        monitor_thread.start()
        load_result = run_load_test(url, requests, CONCURRENCY)
        stop_event.set()
        monitor_thread.join(timeout=1.0)

        # Capture a final RSS sample right after the measured run to avoid missing
        # a peak between monitor thread wakeups.
        rss_after_mb = p.memory_info().rss / 1024 / 1024
        latency_stats = load_result["latency_stats"]

        # Check for non-200 responses
        codes = load_result["status_codes"]
        non_200 = [c for c in codes if c != 200]
        if non_200:
            print(f"FAILURE: Non-200 status codes detected! ({len(non_200)}) Aborting benchmark.")
            return None

        if bench_assert:
            workload_ok, workload_payload = assert_workload(port)
            if not workload_ok:
                msg = f"Workload mismatch for {project} - {test_name}: {workload_payload}"
                print(f"WARNING: {msg}")
                log_file.write(f"WARNING: {msg}\n")
                log_file.flush()

    finally:
        # Kill server
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait()
        except ProcessLookupError:
            pass
        time.sleep(1)  # Wait for port release

    duration_s = load_result["duration_s"]
    rss_peak = max(monitor_result["rss_peak_mb"], rss_after_mb)

    return {
        "rps": load_result["rps_requested"],
        "rps_requested": load_result["rps_requested"],
        "duration_s": duration_s,
        "success_rate_pct": load_result["success_rate_pct"],
        "error_rate_pct": load_result["error_rate_pct"],
        "non_200_rate_pct": load_result["non_200_rate_pct"],
        "p50": latency_stats["p50_ms"],
        "p95": latency_stats["p95_ms"],
        "p99": latency_stats["p99_ms"],
        "stdev": latency_stats["stdev_ms"],
        "rss_peak": rss_peak,
    }


def summarize_runs(
    project_id: str,
    test_name: str,
    runs: List[BenchIteration],
    runs_completed: int,
    runs_total: int,
) -> BenchResult:
    runs_sorted = sorted(runs, key=lambda x: x["rps"])
    median_run = runs_sorted[len(runs_sorted) // 2]
    min_rps = runs_sorted[0]["rps"]
    max_rps = runs_sorted[-1]["rps"]
    rss_peak = max(r["rss_peak"] for r in runs) if runs else 0.0

    return {
        "project": PROJECTS.get(project_id, project_id),
        "test": test_name,
        "runs": f"{runs_completed}/{runs_total}",
        "rps": median_run["rps"],
        "min_rps": min_rps,
        "max_rps": max_rps,
        "p50": median_run["p50"],
        "p95": median_run["p95"],
        "p99": median_run["p99"],
        "stdev": median_run["stdev"],
        "rss_peak": rss_peak,
    }


def format_duration(seconds: float) -> str:
    secs = max(0, int(seconds))
    hours, rem = divmod(secs, 3600)
    minutes, secs = divmod(rem, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def main() -> None:
    if shutil.which(HEY_BIN) is None:
        print(f"Error: '{HEY_BIN}' was not found in PATH. Install it from https://github.com/rakyll/hey and try again.")
        sys.exit(1)

    pin_current_process_to_cpu(LOADGEN_CPU)

    print("--- Environment Check ---")
    print(f"Python: {sys.version}")
    try:
        import wireup

        try:
            version = importlib.metadata.version("wireup")
        except importlib.metadata.PackageNotFoundError:
            version = "unknown (package not found)"

        path = os.path.dirname(wireup.__file__) if hasattr(wireup, "__file__") else "unknown"
        print(f"Wireup Version: {version}")
        print(f"Wireup Path: {path}")
    except ImportError:
        print("Wireup not found!")
    print("-------------------------")

    parser = argparse.ArgumentParser(description="Run Wireup benchmarks")
    parser.add_argument("--iterations", type=int, default=5, help="Number of iterations per test")
    parser.add_argument("--requests", type=int, default=10_000, help="Number of requests per iteration")

    parser.add_argument("--warmup", type=int, default=1000, help="Number of warmup requests")
    parser.add_argument("--output", type=str, default="benchmarks/benchmark_results.csv", help="Output CSV file path")
    parser.add_argument(
        "--run-output",
        type=str,
        default="benchmarks/benchmark_run_metrics.csv",
        help="Output CSV file path for per-iteration metrics",
    )
    parser.add_argument("--local", action="store_true", help="Use local wireup version instead of installed one")
    parser.add_argument("--bench-assert", action="store_true", help="Enable workload assertion counters")
    args = parser.parse_args()

    pairs = [(project_id, test_name) for project_id in PROJECTS for test_name in TESTS]
    run_queue = [(project_id, test_name) for _ in range(args.iterations) for project_id, test_name in pairs]
    total_target_runs = len(run_queue)
    completed_runs = 0
    benchmark_start = time.perf_counter()

    all_results: List[BenchResult] = []
    fieldnames = SUMMARY_FIELDNAMES
    run_fieldnames = RUN_FIELDNAMES
    run_state: Dict[Tuple[str, str], List[BenchIteration]] = {pair: [] for pair in pairs}

    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    run_output_dir = os.path.dirname(args.run_output)
    if run_output_dir and not os.path.exists(run_output_dir):
        os.makedirs(run_output_dir)

    # Write CSV header
    with open(args.output, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
    with open(args.run_output, "w", newline="") as run_csv_file:
        run_writer = csv.DictWriter(run_csv_file, fieldnames=run_fieldnames)
        run_writer.writeheader()

    console = Console()

    def build_table(title: str, results: List[BenchResult]) -> Optional[Table]:
        if not results:
            return None

        table = Table(title=title)

        table.add_column("Project", style="cyan", no_wrap=True)
        table.add_column("Test", style="magenta")
        table.add_column("Runs", justify="right")
        table.add_column("RPS", justify="right", style="green")
        table.add_column("P50 (ms)", justify="right")
        table.add_column("P95 (ms)", justify="right")
        table.add_column("P99 (ms)", justify="right")
        table.add_column("σ (ms)", justify="right")
        table.add_column("RSS Peak (MB)", justify="right")

        # Sort by RPS desc
        for res in sorted(results, key=lambda x: x["rps"], reverse=True):
            table.add_row(
                res["project"],
                res["test"],
                res.get("runs", "-"),
                f"{res['rps']:.2f}",
                f"{res['p50']:.2f}",
                f"{res['p95']:.2f}",
                f"{res['p99']:.2f}",
                f"{res.get('stdev', 0):.2f}",
                f"{res.get('rss_peak', 0):.2f}",
            )

        return table

    in_progress: Dict[Tuple[str, str], BenchResult] = {}
    current_iteration_line = ""
    current_iteration_progress = ""

    def noop_refresh() -> None:
        return

    refresh_live: Callable[[], None] = noop_refresh

    def build_live_render() -> Any:
        combined = all_results + list(in_progress.values())
        singleton_results = [r for r in combined if r["test"] == "singleton"]
        scoped_results = [r for r in combined if r["test"] == "scoped"]

        elapsed = time.perf_counter() - benchmark_start
        pct = (completed_runs / total_target_runs) if total_target_runs else 0.0
        filled = int(pct * 30)
        bar = "█" * filled + "░" * (30 - filled)
        eta = (elapsed / completed_runs) * (total_target_runs - completed_runs) if completed_runs > 0 else 0.0
        progress = Text(
            f"{bar}  {completed_runs}/{total_target_runs} ({pct * 100:.1f}%)  "
            f"Elapsed: {format_duration(elapsed)}  ETA: {format_duration(eta)}"
        )

        parts: List[Any] = []
        parts.append(Panel(progress, title="Progress", expand=False))
        singleton_table = build_table("Benchmark Results - Singleton (So Far)", singleton_results)
        scoped_table = build_table("Benchmark Results - Scoped (So Far)", scoped_results)
        if singleton_table:
            parts.append(singleton_table)
        if scoped_table:
            parts.append(scoped_table)
        if current_iteration_line:
            title = "Latest Iteration"
            if current_iteration_progress:
                title = f"{title} {current_iteration_progress}"
            parts.append(Panel(current_iteration_line, title=title, expand=False))

        if not parts:
            return Panel("No results yet.", title="Benchmarks", expand=False)

        return Group(*parts)

    def on_iteration(project_id: str, test_name: str, result_summary: BenchResult) -> None:
        nonlocal current_iteration_line, current_iteration_progress
        in_progress[(project_id, test_name)] = result_summary
        current_iteration_line = (
            f"{PROJECTS.get(project_id, project_id)} - {test_name}: "
            f"{result_summary['rps']:.2f} rps, p50: {result_summary['p50']:.2f} ms, "
            f"p95: {result_summary['p95']:.2f} ms, p99: {result_summary['p99']:.2f} ms, "
            f"stdev: {result_summary['stdev']:.2f} ms"
        )
        current_iteration_progress = f"({result_summary['runs']})"
        refresh_live()

    with Live(build_live_render(), console=console, auto_refresh=False) as live, open(SERVER_LOG, "w") as log_file:

        def live_refresh() -> None:
            live.update(build_live_render(), refresh=True)

        refresh_live = live_refresh
        log_file.write("Pairs: " + ", ".join(f"{p}:{t}" for p, t in pairs) + "\n")
        log_file.flush()

        def abort_failed_run(project_id: str, test: str) -> None:
            msg = f"Failed to get results for {project_id}:{test}"
            raise RuntimeError(msg)

        for run_index, (project_id, test) in enumerate(run_queue, start=1):
            try:
                next_run = len(run_state[(project_id, test)]) + 1
                log_file.write(
                    f"Run {run_index}/{total_target_runs}: {project_id}:{test} ({next_run}/{args.iterations})\n"
                )
                log_file.flush()
                res = run_benchmark(
                    project_id,
                    test,
                    log_file,
                    requests=args.requests,
                    warmup_requests=args.warmup,
                    use_local_version=args.local,
                    bench_assert=args.bench_assert,
                )
                if res:
                    run_row: dict[str, Any] = dict.fromkeys(run_fieldnames, "")
                    run_row.update(
                        {
                            "project_id": project_id,
                            "project": PROJECTS.get(project_id, project_id),
                            "test": test,
                            "iteration": next_run,
                        }
                    )
                    run_row.update({k: res.get(k, "") for k in run_fieldnames if k in res})
                    with open(args.run_output, "a", newline="") as run_csv_file:
                        run_writer = csv.DictWriter(run_csv_file, fieldnames=run_fieldnames)
                        run_writer.writerow(run_row)

                    run_state[(project_id, test)].append(res)
                    completed_runs += 1
                    summary = summarize_runs(
                        project_id=project_id,
                        test_name=test,
                        runs=run_state[(project_id, test)],
                        runs_completed=len(run_state[(project_id, test)]),
                        runs_total=args.iterations,
                    )
                    on_iteration(project_id, test, summary)
                    print(f"Result: {summary['rps']:.2f} req/sec, Memory: {summary['rss_peak']:.2f} MB")
                    if len(run_state[(project_id, test)]) >= args.iterations:
                        in_progress.pop((project_id, test), None)
                        all_results.append(summary)

                        # Append to CSV when a workload is fully completed
                        with open(args.output, "a", newline="") as csvfile:
                            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                            writer.writerow({k: summary[k] for k in fieldnames})
                else:
                    abort_failed_run(project_id, test)
                live.update(build_live_render(), refresh=True)
            except Exception as e:
                in_progress.pop((project_id, test), None)
                live.update(build_live_render(), refresh=True)
                print(f"Error running benchmark for {project_id} - {test}: {e}")
                raise

    print(f"\nBenchmarks complete. Summary written to {args.output}")
    print(f"Per-iteration metrics written to {args.run_output}")

    # Save metadata
    import platform

    meta = {
        "iterations": args.iterations,
        "requests": args.requests,
        "warmup_requests": args.warmup,
        "concurrency": CONCURRENCY,
        "summary_output": args.output,
        "run_output": args.run_output,
        "summary_fields": fieldnames,
        "run_fields": run_fieldnames,
        "python_version": platform.python_version(),
    }
    with open("benchmarks/benchmark_meta.json", "w") as f:
        json.dump(meta, f, indent=4)

    singleton_results = [r for r in all_results if r["test"] == "singleton"]
    scoped_results = [r for r in all_results if r["test"] == "scoped"]

    final_singleton = build_table("Benchmark Results - Singleton", singleton_results)
    final_scoped = build_table("Benchmark Results - Scoped", scoped_results)
    if final_singleton:
        console.print(final_singleton)
        console.print()
    if final_scoped:
        console.print(final_scoped)


if __name__ == "__main__":
    main()
