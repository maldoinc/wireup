.PHONY: install format lint check-fmt check-ruff check-mypy test

ifdef GITHUB_ACTIONS
RUFF_ARGS := --format=github
endif

install:
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/pip install poetry
	.venv/bin/poetry install --no-root

format:
	.venv/bin/black .

lint: check-fmt check-ruff check-mypy

check-fmt:
	.venv/bin/black . --check

check-ruff:
	.venv/bin/ruff wireup $(RUFF_ARGS)

check-mypy:
	.venv/bin/mypy wireup --strict

test:
	.venv/bin/python -m unittest discover -s test/
