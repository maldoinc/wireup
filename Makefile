.PHONY: install lint check-fmt check-ruff check-mypy test profile fix format docs-deploy publish docs-serve docs-preview

ifdef GITHUB_ACTIONS
RUFF_ARGS := --output-format github
endif

install:
	pip install uv
	uv sync --group dev

lint: check-fmt check-ruff check-mypy check-docs

check-fmt:
	uv run ruff format wireup test benchmarks --check

check-ruff:
	uv run ruff check wireup test benchmarks $(RUFF_ARGS)

check-mypy:
	uv run mypy wireup --strict
	uv run mypy benchmarks --ignore-missing-imports
	uv run mypy test/typing_tests.py --strict

check-docs:
	uv run ruff format docs --line-length 80 --exclude docs/pages/class --check

test:
	uv run pytest test/unit

iterations ?= 5
requests ?= 10000
warmup ?= 2000
output ?= benchmarks/benchmark_results.csv
bench_assert ?= 0

ifeq ($(version),)
BENCH_WIREUP_WITH := wireup @ .
BENCH_LOCAL_FLAG := --local
BENCH_WIREUP_VERSION := local@$(shell git rev-parse --short HEAD 2>/dev/null || echo unknown)
else ifeq ($(version),local)
BENCH_WIREUP_WITH := wireup @ .
BENCH_LOCAL_FLAG := --local
BENCH_WIREUP_VERSION := local@$(shell git rev-parse --short HEAD 2>/dev/null || echo unknown)
else
BENCH_WIREUP_WITH := wireup==$(version)
BENCH_LOCAL_FLAG :=
BENCH_WIREUP_VERSION := $(version)
endif


# Bench examples
# make bench requests=10000 iterations=1
# make bench version=2.4.0 requests=10000 iterations=5
# make bench version=local requests=10000 iterations=5
bench:
	uv run --no-project --with "$(BENCH_WIREUP_WITH)" benchmarks/bench_runner.py --iterations $(iterations) --requests $(requests) --warmup $(warmup) --output $(output) $(BENCH_LOCAL_FLAG) $(if $(filter 1,$(bench_assert)),--bench-assert,)
	uv run benchmarks/generate_charts.py $(output)
	BENCH_WIREUP_VERSION="$(BENCH_WIREUP_VERSION)" uv run benchmarks/generate_versions.py
	uv run benchmarks/generate_tables.py $(output)

profile ./profile_tests $(num_runs):
	uv run python ./profile_tests.py $(num_runs)

format: format-docs
	uv run ruff format . --extend-exclude '*.md'

fix: format
	uv run ruff check wireup test benchmarks --fix

format-docs:
	uv run ruff format docs --line-length 80 --exclude docs/pages/class

build-docs:
	uv run --python 3.14 zensical build --strict -f docs/zensical.toml


docs-serve:
	uv run --python 3.14 zensical serve -f docs/zensical.toml

# make docs-deploy version=...
docs-deploy $(version):
	git fetch origin gh-pages:gh-pages
	cd docs && uv run --python 3.14 mike deploy -F zensical.toml --push --update-aliases $(version) latest

publish:
	uv build
	uv publish
