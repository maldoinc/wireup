# Contributing

## Setup

```bash
git clone https://github.com/maldoinc/wireup.git
cd wireup

python -m venv .venv
source .venv/bin/activate
make install
```

## Development Workflow

```bash
make lint     # Run ruff & mypy checks
make test     # Run unit tests
make format   # Format code
```

### Making Changes

```bash
git checkout -b feature/your-feature-name
# work on the change
make lint test
```


## Project Structure

- `wireup/ioc/` - Dependency injection implementation
- `wireup/integration/` - Framework integrations (FastAPI, Django, etc.)
- `test/unit/` - Unit tests
- `test/integration/` - Integration tests
- `docs/` - Docs

## Guidelines

- **Python Support**: Target Python 3.8+ compatibility
- **Dependencies**: No new dependencies without approval
- **Documentation**: Update docs for user-facing changes
- **Testing**: Maintain test coverage for new code
