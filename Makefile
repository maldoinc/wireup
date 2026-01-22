.PHONY: install lint check-fmt check-ruff check-mypy test profile fix format docs-deploy publish

ifdef GITHUB_ACTIONS
RUFF_ARGS := --output-format github
endif

install:
	pip install uv
	uv sync --group dev

lint: check-fmt check-ruff check-mypy check-docs

check-fmt:
	uv run ruff format . --check

check-ruff:
	uv run ruff check wireup test $(RUFF_ARGS)

check-mypy:
	uv run mypy wireup --strict

check-docs:
	find docs -name "*.md" -not -path "docs/pages/class/*" | xargs uv run --python 3.14 mdformat --wrap 120 --check

test:
	uv run pytest test/unit

profile ./profile_tests $(num_runs):
	uv run python ./profile_tests.py $(num_runs)

format: format-docs
	uv run ruff format .

fix:
	uv run ruff wireup --fix

format-docs:
	find docs -name "*.md" -not -path "docs/pages/class/*" | xargs uv run --python 3.14 mdformat --wrap 120
	find docs -name "*.md" -not -path "docs/pages/class/*" | xargs uv run --python 3.14 blacken-docs -l 80 || true

build-docs:
	uv run --python 3.14 mkdocs build --strict -f docs/mkdocs.yml


# make docs-deploy version=...
docs-deploy $(version):
	cd docs && uv run mike deploy --push --update-aliases $(version) latest

publish:
	uv build
	uv publish