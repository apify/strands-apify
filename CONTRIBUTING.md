# Contributing to strands-apify

Thank you for your interest in contributing!

## Development setup

```bash
git clone https://github.com/apify/strands-apify.git
cd strands-apify
pip install -e ".[dev]"
```

## Running checks

```bash
hatch run prepare  # Runs format, lint, typecheck, and tests
```

Or run individually:

```bash
hatch run format     # ruff format
hatch run lint       # ruff check
hatch run typecheck  # mypy
hatch run test       # pytest
```

## Submitting changes

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `hatch run prepare` and ensure all checks pass
5. Submit a pull request

## Adding a new Apify tool

1. Identify the Actor on the [Apify Store](https://apify.com/store) and its input schema
2. Add a new `@tool`-decorated function in the appropriate module (`core.py`, `social_media.py`, or `search_crawling.py`)
3. Reuse `ApifyToolClient`, `_check_dependency`, `_success_result`, and `_error_result` from `utils.py`
4. Export the function in `__init__.py` and add it to the relevant `APIFY_*_TOOLS` preset list
5. Add tests covering: happy path, missing token, missing dependency, Actor failure, parameter validation

## Security issue notifications

If you discover a potential security issue, please notify us privately via the repository's security advisory feature rather than filing a public issue.
