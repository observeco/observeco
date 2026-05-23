# Contributing

## Development Setup

```bash
git clone https://github.com/observeco/observeco
cd observeco
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Code Style

- Ruff for linting and formatting
- Mypy for type checking (strict mode)
- Pre-commit hooks: `ruff check && mypy src/`

## Testing

```bash
pytest                       # Run all tests
pytest -v                    # Verbose
pytest tests/test_cli.py     # Single file
```

## Pull Requests

1. Create a feature branch from `main`
2. Add tests for new functionality
3. Ensure all tests pass
4. Run `ruff check src/` and `mypy src/`
5. Open a PR with a clear description

## Issues

- Bug reports: include Python version, OS, and reproduction steps
- Feature requests: describe the problem you're solving, not your proposed solution
