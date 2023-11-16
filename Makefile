.PHONY: install lint check-fmt check-ruff check-mypy test profile fix format

ifdef GITHUB_ACTIONS
RUFF_ARGS := --output-format github
endif

install:
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/pip install poetry
	.venv/bin/poetry install --no-root

lint: check-fmt check-ruff check-mypy

check-fmt:
	.venv/bin/ruff format . --check

check-ruff:
	.venv/bin/ruff wireup $(RUFF_ARGS)

check-mypy:
	.venv/bin/mypy wireup --strict

test:
	.venv/bin/python -m unittest discover -s test/

profile ./profile_tests $(num_runs):
	./.venv/bin/python ./profile_tests.py $(num_runs)

format:
	./.venv/bin/ruff format .

fix:
	./.venv/bin/ruff wireup --fix
