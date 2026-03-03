---
hide:
    - toc
---


!!! abstract "A note on benchmarks"

    Measuring dependency injection overhead in isolation often produces performance numbers 
    that may not fully reflect real-world patterns. For most practical applications,
    the DI container will rarely be your performance bottleneck.
    Database queries, network calls, and business logic usually dominate response times.

    That said, optimizations compound: a faster DI layer, faster serialization, faster validation, 
    etc. all add up to meaningful improvements.

    While these results aim to be as objective as possible, Wireup is actively optimized for performance,
    so I expect it to perform well in this benchmark.
    Even so, I would not pick a DI container solely from performance benchmarks, but if you're happy with Wireup's
    features and want to see how it stacks up against the field, here are the results.

## Benchmark Design & Stress Test

This benchmark uses an artificial workload to measure the overhead of the dependency injection container. By using empty
services, the test focuses on how fast the library can resolve and inject dependencies without the results being hidden
by application logic.

Testing is done within a FastAPI + Uvicorn environment to measure performance in a realistic web-based environment.
Notably, this also allows for the inclusion of `fastapi.Depends` in the comparison, 
as it is the most popular choice by virtue of being the FastAPI default. 

This setup tests also the overall dependency injection package of each library which includes container resolution, scoping,
injecting into functions/route handlers as well as framework integration rather than a microbenchmark where 
you repeatedly resolve dependencies from the raw container instance in a tight loop.
This benchmark intentionally uses non-trivial singleton/scoped graphs to stress test the containers.

The workload uses two separate, independent graphs:
the singleton graph (`Settings -> A -> B`) and the scoped graph (`C -> I`) where each service depends on multiple others.
H is a context manager, I is an async context manager.

This graph is intentionally non-trivial: large enough to emulate realistic container behavior, but still representative of practical applications (rather than 100-node chains). The exact shape is less important than the workload characteristics: multiple dependencies and lifecycle-managed resources, which stress container resolution, scoping, and teardown more than a simple linear graph.

??? "Click to view the graphs"

    **Singleton graph**

    ```mermaid
    graph LR
        Settings[Settings] --> A[Service A]
        A --> B[Service B]
    ```

    **Per-Request Injected graph**

    ```mermaid
    graph TD
        C --> D
        C --> E
        D --> E
        C --> F
        D --> F
        E --> F
        C --> G
        D --> G
        E --> G
        F --> G
        C --> H
        D --> H
        E --> I
        F --> I
    ```


!!! info "For library authors"

    If you are benchmarking Wireup against your library, `container.get(...)` is not Wireup's canonical
    entry point. It is primarily intended as an advanced feature for users who want to access the container directly in edge cases, not as the main way to resolve dependencies.

    For representative results, benchmark function-based injection via `inject_from_container(...)`, which reflects
    Wireup's recommended dependency-injection usage pattern rather than service-locator style access.


Summary comparisons below always use Wireup (not Wireup Class-Based) as the reference to avoid cherry-picking the best-performing variant.


## Benchmark Setup

The benchmarks were run on a local machine with <!-- meta:iterations -->50<!-- /meta:iterations --> rounds of
    <!-- meta:requests -->100,000<!-- /meta:requests --> requests per round per library. The tables and bar charts show the result of the
**Representative Median Run**:

1. All rounds are sorted by **RPS**.
1. The median round is selected.
1. **RPS** and **Latency** are taken from this specific run to ensure consistency.
1. **RSS (Memory)** shows the *peak* usage observed across **all** rounds.

For each run, the server is started, a liveness probe must pass, warmup traffic is sent, and only then the measured run begins.

Actual requests per second (RPS) will change based on your hardware. The most important metric is how the libraries
perform relative to each other.

**Manual Wiring (No DI)** represents the theoretical maximum performance. In this setup, services are manually instantiated
within the route handler, bypassing DI containers entirely.
This row exists purely to establish an upper bound on DI overhead, not as an endorsement of global state or manual wiring.

**Wireup Class-Based** represents the performance of Wireup when using the
[Class-Based Handlers](integrations/fastapi/class_based_handlers.md) for FastAPI.

### Metrics

The benchmark measures the following:

- **RPS (Requests Per Second)**: The number of requests the server can handle in one second. **Higher is better.**
- **Latency (p50, p95, p99)**: The time it takes for a request to be completed, measured in milliseconds. **Lower is
    better.**
    - **p50 (Median)**: Half of the requests are faster than this.
    - **p95**: 95% of requests are faster than this.
    - **p99**: 99% of requests are faster than this.
- **σ (Standard Deviation)**: Measures the stability of response times (Jitter). A lower number means more consistent
    performance with fewer outliers. **Lower is better.**
- **RSS Memory Peak (MB)**: The highest post-iteration RSS sample observed across runs. **Lower is better.**
    This includes the full server process footprint (Uvicorn + FastAPI app + framework runtime), not only service objects.
    Summary percentages and relative-throughput comparisons on this page are computed from the main Median Run tables, not the Stability or Total Time tables.

### Hardware Environment

- **CPU**: 12th Gen Intel(R) Core(TM) i7-12700K
- **Memory**: 32 GB RAM
- **OS**: Fedora Linux 43 (Workstation Edition); Kernel 6.18.13-200.fc43.x86_64

### Execution Details

- **Python**: <!-- meta:python_version -->v3.14.3<!-- /meta:python_version -->
- **Server**: Uvicorn with 1 worker process
- **Event Loop**: `uvloop`
- **Load generator**: [`hey`](https://github.com/rakyll/hey) v0.1.5 (must be installed and available on `PATH`)
- **CPU pinning**: The benchmark runner pins the load generator to CPU 1 and the server process to CPU 2, both mapped to performance cores on this machine.
    For reproducibility on hybrid CPUs, pin benchmark processes to performance cores (P-cores), not efficiency cores (E-cores).
- **Startup liveness probe**: Each server process is polled on `/healthz` before warmup and measurement begin.
- **Load Parameters**: <!-- meta:concurrency -->50<!-- /meta:concurrency --> concurrent connections
- **Warmup**: <!-- meta:warmup_requests -->2,000<!-- /meta:warmup_requests --> warmup requests per run, using the same concurrency as measured runs.
- **Verification**: All endpoints are verified for correctness (status code 200 plus endpoint-level assertions on
    dependency values and scoping behavior).
- **Workload assertions**: When `BENCH_ASSERT=1`, creation/lifecycle counters are checked against the expected
    workload shape and mismatches are reported as observed.



??? "See exact package versions used"

    <!-- versions-start -->

    | Package | Version |
    | :--- | :--- |
    | wireup | local@6f38e1d |
    | fastapi | 0.124.4 |
    | uvicorn[standard] | 0.40.0 |
    | aioinject | 1.10.2 |
    | dishka | 1.7.2 |
    | dependency-injector | 4.48.3 |
    | lagom | 2.7.7 |
    | injector | 0.24.0 |
    | fastapi-injector | 0.9.0 |
    | svcs | 25.1.0 |
    | that-depends | 3.9.1 |
    | diwire | 1.3.0 |

    <!-- versions-end -->



## Feature Completeness

Not all libraries support the same features. Some required test simplifications and are marked with a `†` in the tables and charts below.
In general, these simplifications tend to favor the affected libraries because they skip work that fully modeled implementations still perform.

* **FastAPI**: FastAPI DI is request-scoped by default; singletons are not a first-class DI concept. This benchmark uses
  the documented `Depends` + `@lru_cache` pattern for singletons, which is the recommended approach in the FastAPI documentation. See:
  [Creating the settings only once with lru_cache](https://fastapi.tiangolo.com/advanced/settings/#creating-the-settings-only-once-with-lru-cache).


* **Injector**: Uses `fastapi-injector` for FastAPI integration. The library does not support async dependencies or
  request-scoped context managers, so services H and I are implemented as plain request-scoped objects (no enter/exit).

* **Lagom**: Does not support async context managers. Service I (which should be an async iterator in the specification)
    is implemented as a sync iterator.

* **Dependency Injector**: The resource lifecycle for H and I is not modeled per request. They are provided as
  context-local singletons without entering/exiting context managers.

## Per-Request Injection Performance

Each request to `/scoped` creates new instances only for scoped services (C through I), without resolving any singleton services.
This test emphasizes container lifecycle and graph traversal performance, as the container must create and tear down
a dense dependency graph on **every** request.

<!-- scoped-summary-start -->
In this benchmark, **Wireup Class-Based** operates at <!-- meta:scoped_wireup_cbr_pct -->**99.38%**<!-- /meta:scoped_wireup_cbr_pct --> of manual wiring throughput, and **Wireup** at <!-- meta:scoped_wireup_pct -->**99.87%**<!-- /meta:scoped_wireup_pct -->, placing both near the manual-wiring upper bound in this workload.
For context, this corresponds to roughly <!-- meta:scoped_wireup_vs_fastapi_x -->**2.79x**<!-- /meta:scoped_wireup_vs_fastapi_x --> the throughput of **FastAPI Depends** and <!-- meta:scoped_wireup_vs_next_best_x -->**1.29x**<!-- /meta:scoped_wireup_vs_next_best_x --> the next closest library in this benchmark (**<!-- meta:scoped_next_best_name -->Dishka<!-- /meta:scoped_next_best_name -->**).
<!-- scoped-summary-end -->

![Scoped Performance](img/benchmarks_scoped_light.svg#only-light)
![Scoped Performance](img/benchmarks_scoped_dark.svg#only-dark)

<!-- scoped-start -->
| Project | RPS (Median Run) | P50 (ms) | P95 (ms) | P99 (ms) | σ (ms) | Mem Peak |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Manual Wiring (No DI)** | 11,044 <span class="bench-diff">(100.00%)</span> | 4.20 | 4.50 | 4.70 | 0.70 | 52.93 MB |
| **Wireup** | 11,030 <span class="bench-diff">(99.87%)</span> | 4.20 | 4.50 | 4.70 | 0.83 | 53.69 MB |
| **Wireup Class-Based** | 10,976 <span class="bench-diff">(99.38%)</span> | 4.30 | 4.50 | 4.70 | 0.70 | 53.80 MB |
| **Dishka** | 8,538 <span class="bench-diff">(77.30%)</span> | 5.30 | 6.30 | 9.40 | 1.30 | 103.23 MB |
| **Svcs** | 8,394 <span class="bench-diff">(76.00%)</span> | 5.70 | 6.00 | 6.20 | 0.93 | 67.09 MB |
| **Aioinject** | 8,177 <span class="bench-diff">(74.04%)</span> | 5.60 | 6.60 | 10.40 | 1.31 | 100.52 MB |
| **diwire** | 7,390 <span class="bench-diff">(66.91%)</span> | 6.50 | 6.90 | 7.10 | 1.07 | 58.22 MB |
| **That Depends** | 4,892 <span class="bench-diff">(44.30%)</span> | 9.80 | 10.40 | 10.60 | 0.59 | 53.82 MB |
| **FastAPI Depends** | 3,950 <span class="bench-diff">(35.76%)</span> | 12.30 | 13.80 | 14.10 | 1.39 | 57.68 MB |
| **Injector †** | 3,192 <span class="bench-diff">(28.90%)</span> | 15.20 | 15.40 | 16.10 | 0.58 | 53.52 MB |
| **Dependency Injector †** | 2,576 <span class="bench-diff">(23.33%)</span> | 19.10 | 19.70 | 20.10 | 0.75 | 60.55 MB |
| **Lagom †** | 898 <span class="bench-diff">(8.13%)</span> | 55.30 | 57.20 | 58.30 | 1.63 | 1.32 GB |

#### Stability (Across Runs)

These values summarize all runs for each project in this test. **Median P50/P95/P99** are the medians of those per-run latency percentiles, while **Within ±3%** shows the share of runs whose RPS stayed within 3% of that project's median-run RPS.
Look for **smaller Δ RPS**, **higher Within ±3%**, and **lower median tail latencies (P95/P99)** for the most consistent behavior.

| Project | Min RPS | Max RPS | Δ RPS | Within ±3% | Med P50 (ms) | Med P95 (ms) | Med P99 (ms) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Manual Wiring (No DI)** | 10,910 | 11,112 | 1.84% | 100.0% | 4.20 | 4.50 | 4.70 |
| **Wireup** | 10,917 | 11,108 | 1.73% | 100.0% | 4.20 | 4.50 | 4.70 |
| **Wireup Class-Based** | 10,838 | 11,076 | 2.17% | 100.0% | 4.20 | 4.50 | 4.70 |
| **Dishka** | 8,466 | 8,639 | 2.02% | 100.0% | 5.30 | 6.30 | 9.40 |
| **Svcs** | 8,268 | 8,513 | 2.91% | 100.0% | 5.70 | 6.00 | 6.20 |
| **Aioinject** | 8,102 | 8,283 | 2.21% | 100.0% | 5.60 | 6.60 | 10.10 |
| **diwire** | 7,257 | 7,483 | 3.06% | 100.0% | 6.50 | 6.90 | 7.10 |
| **That Depends** | 4,817 | 4,968 | 3.09% | 100.0% | 9.80 | 10.20 | 10.60 |
| **FastAPI Depends** | 3,922 | 3,973 | 1.28% | 100.0% | 12.25 | 13.70 | 14.10 |
| **Injector †** | 3,136 | 3,225 | 2.79% | 100.0% | 15.20 | 15.40 | 15.90 |
| **Dependency Injector †** | 2,559 | 2,605 | 1.76% | 100.0% | 19.00 | 19.70 | 20.00 |
| **Lagom †** | 893 | 903 | 1.19% | 100.0% | 55.30 | 57.10 | 58.20 |

#### Time to Complete All Runs (Lower Is Better)

This aggregates measured request-phase runtime across all runs for each project in this test.

| Project | Total Time (HH:MM:SS) | Total Time (s) | + vs Fastest | Avg Time / Run | Runs |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Manual Wiring (No DI)** | 07:33 | 452.97 | +00:00 | 9.06s | 50 |
| **Wireup** | 07:34 | 453.51 | +00:01 | 9.07s | 50 |
| **Wireup Class-Based** | 07:36 | 455.81 | +00:03 | 9.12s | 50 |
| **Dishka** | 09:45 | 585.49 | +02:13 | 11.71s | 50 |
| **Svcs** | 09:56 | 596.05 | +02:23 | 11.92s | 50 |
| **Aioinject** | 10:11 | 611.25 | +02:38 | 12.23s | 50 |
| **diwire** | 11:17 | 677.42 | +03:44 | 13.55s | 50 |
| **That Depends** | 17:03 | 1023.26 | +09:30 | 20.47s | 50 |
| **FastAPI Depends** | 21:06 | 1265.92 | +13:33 | 25.32s | 50 |
| **Injector †** | 26:06 | 1566.24 | +18:33 | 31.32s | 50 |
| **Dependency Injector †** | 32:20 | 1940.33 | +24:47 | 38.81s | 50 |
| **Lagom †** | 1:32:46 | 5566.48 | +1:25:14 | 111.33s | 50 |
<!-- scoped-end -->


## Singleton Performance

Services are created once when the app starts and reused throughout. In this test, the endpoint injects **Services A, B,
and Settings** from the graph.
This tests the container's bookkeeping performance and how efficiently it can return existing instances.

<!-- singleton-summary-start -->
In this benchmark, both **Wireup Class-Based** (<!-- meta:singleton_wireup_cbr_pct -->**99.93%**<!-- /meta:singleton_wireup_cbr_pct -->) and **Wireup** (<!-- meta:singleton_wireup_pct -->**98.97%**<!-- /meta:singleton_wireup_pct -->) operate very close to manual wiring throughput, showing very small overhead vs manual wiring in this workload.
For context, this corresponds to roughly <!-- meta:singleton_wireup_vs_fastapi_x -->**2.15x**<!-- /meta:singleton_wireup_vs_fastapi_x --> the throughput of **FastAPI Depends** and <!-- meta:singleton_wireup_vs_next_best_x -->**1.25x**<!-- /meta:singleton_wireup_vs_next_best_x --> the next closest library in this benchmark (**<!-- meta:singleton_next_best_name -->diwire<!-- /meta:singleton_next_best_name -->**).
<!-- singleton-summary-end -->

![Singleton Performance](img/benchmarks_singleton_light.svg#only-light)
![Singleton Performance](img/benchmarks_singleton_dark.svg#only-dark)

<!-- singleton-start -->
| Project | RPS (Median Run) | P50 (ms) | P95 (ms) | P99 (ms) | σ (ms) | Mem Peak |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Manual Wiring (No DI)** | 13,351 <span class="bench-diff">(100.00%)</span> | 3.40 | 3.60 | 3.90 | 0.72 | 52.98 MB |
| **Wireup Class-Based** | 13,342 <span class="bench-diff">(99.93%)</span> | 3.40 | 3.60 | 3.80 | 0.73 | 53.73 MB |
| **Wireup** | 13,214 <span class="bench-diff">(98.97%)</span> | 3.50 | 3.70 | 3.90 | 0.58 | 53.64 MB |
| **diwire** | 10,532 <span class="bench-diff">(78.88%)</span> | 4.50 | 4.80 | 4.90 | 0.74 | 58.21 MB |
| **Svcs** | 10,447 <span class="bench-diff">(78.25%)</span> | 4.50 | 4.80 | 5.00 | 0.75 | 67.02 MB |
| **Injector †** | 10,269 <span class="bench-diff">(76.92%)</span> | 4.60 | 4.90 | 5.00 | 0.75 | 53.46 MB |
| **Aioinject** | 10,219 <span class="bench-diff">(76.54%)</span> | 4.40 | 5.20 | 8.00 | 1.17 | 103.16 MB |
| **Dishka** | 9,650 <span class="bench-diff">(72.28%)</span> | 4.70 | 5.30 | 8.20 | 1.21 | 105.03 MB |
| **That Depends** | 7,792 <span class="bench-diff">(58.36%)</span> | 6.20 | 6.50 | 6.70 | 1.00 | 53.82 MB |
| **Dependency Injector †** | 6,905 <span class="bench-diff">(51.71%)</span> | 6.80 | 7.30 | 7.70 | 0.60 | 60.42 MB |
| **FastAPI Depends** | 6,153 <span class="bench-diff">(46.08%)</span> | 7.70 | 8.20 | 8.60 | 0.37 | 55.74 MB |
| **Lagom †** | 2,936 <span class="bench-diff">(21.99%)</span> | 16.70 | 18.30 | 20.10 | 1.29 | 238.93 MB |

#### Stability (Across Runs)

These values summarize all runs for each project in this test. **Median P50/P95/P99** are the medians of those per-run latency percentiles, while **Within ±3%** shows the share of runs whose RPS stayed within 3% of that project's median-run RPS.
Look for **smaller Δ RPS**, **higher Within ±3%**, and **lower median tail latencies (P95/P99)** for the most consistent behavior.

| Project | Min RPS | Max RPS | Δ RPS | Within ±3% | Med P50 (ms) | Med P95 (ms) | Med P99 (ms) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Manual Wiring (No DI)** | 13,169 | 13,460 | 2.18% | 100.0% | 3.40 | 3.70 | 3.80 |
| **Wireup Class-Based** | 13,168 | 13,439 | 2.03% | 100.0% | 3.40 | 3.70 | 3.80 |
| **Wireup** | 13,031 | 13,332 | 2.28% | 100.0% | 3.50 | 3.70 | 3.90 |
| <span class="bench-worse"><strong>diwire</strong></span> | <span class="bench-worse"><strong>8,871</strong></span> | <span class="bench-worse"><strong>10,667</strong></span> | <span class="bench-worse"><strong>17.05%</strong></span> | <span class="bench-worse"><strong>98.0%</strong></span> | <span class="bench-worse"><strong>4.40</strong></span> | <span class="bench-worse"><strong>4.80</strong></span> | <span class="bench-worse"><strong>4.90</strong></span> |
| **Svcs** | 10,291 | 10,536 | 2.34% | 100.0% | 4.50 | 4.80 | 5.00 |
| **Injector †** | 10,164 | 10,333 | 1.65% | 100.0% | 4.60 | 4.90 | 5.10 |
| **Aioinject** | 10,133 | 10,301 | 1.64% | 100.0% | 4.40 | 5.20 | 7.90 |
| **Dishka** | 9,551 | 9,732 | 1.88% | 100.0% | 4.70 | 5.30 | 8.20 |
| **That Depends** | 7,647 | 7,898 | 3.22% | 100.0% | 6.20 | 6.50 | 6.70 |
| **Dependency Injector †** | 6,852 | 6,991 | 2.00% | 100.0% | 6.80 | 7.30 | 7.70 |
| **FastAPI Depends** | 6,069 | 6,197 | 2.07% | 100.0% | 7.70 | 8.20 | 8.60 |
| **Lagom †** | 2,908 | 2,949 | 1.40% | 100.0% | 16.70 | 18.30 | 20.30 |

#### Time to Complete All Runs (Lower Is Better)

This aggregates measured request-phase runtime across all runs for each project in this test.

| Project | Total Time (HH:MM:SS) | Total Time (s) | + vs Fastest | Avg Time / Run | Runs |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Manual Wiring (No DI)** | 06:15 | 374.52 | +00:00 | 7.49s | 50 |
| **Wireup Class-Based** | 06:15 | 375.27 | +00:01 | 7.51s | 50 |
| **Wireup** | 06:18 | 378.28 | +00:04 | 7.57s | 50 |
| **diwire** | 07:57 | 477.04 | +01:43 | 9.54s | 50 |
| **Svcs** | 07:59 | 478.80 | +01:44 | 9.58s | 50 |
| **Injector †** | 08:07 | 487.14 | +01:53 | 9.74s | 50 |
| **Aioinject** | 08:09 | 489.38 | +01:55 | 9.79s | 50 |
| **Dishka** | 08:38 | 518.09 | +02:24 | 10.36s | 50 |
| **That Depends** | 10:42 | 642.13 | +04:28 | 12.84s | 50 |
| **Dependency Injector †** | 12:04 | 724.05 | +05:50 | 14.48s | 50 |
| **FastAPI Depends** | 13:33 | 813.17 | +07:19 | 16.26s | 50 |
| **Lagom †** | 28:23 | 1703.37 | +22:09 | 34.07s | 50 |
<!-- singleton-end -->


### Reproducibility

Prerequisite:

- Install [`hey`](https://github.com/rakyll/hey) and ensure the `hey` binary is available on your `PATH`.

Run from repository root:

```bash
make bench
```

Enable workload-shape assertions:

```bash
make bench bench_assert=1
```

If you want to reproduce this exact run pass iterations=<!-- meta:iterations -->50<!-- /meta:iterations --> requests=<!-- meta:requests -->100,000<!-- /meta:requests --> to the make command.

This command reruns benchmarks and regenerates charts/tables/versions for this page.


## Source Code

The benchmark code is available in the [`benchmarks/`](https://github.com/maldoinc/wireup/tree/master/benchmarks) directory.
