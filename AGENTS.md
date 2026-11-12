# Coding guidelines

This file provides guidance to programming agents when working with code in this repository.

Apify tools for the [Strands Agents SDK](https://strandsagents.com/), published on PyPI as `strands-apify` (module
`strands_apify`). The public API is what `src/strands_apify/__init__.py` exports: the tools in `core.py`,
`social_media.py` and `search_crawling.py`, the `APIFY_*_TOOLS` presets and `ApifyToolClient` from `utils.py`.

Read [CONTRIBUTING.md](CONTRIBUTING.md) for setup, tasks, PR conventions and releases. It applies to agents too.

@CONTRIBUTING.md

## Components

- Every tool is a module-level `@tool` function in `core.py`, `social_media.py` or `search_crawling.py`, exported from
  `__init__.py` and listed in its `APIFY_*_TOOLS` preset.
- Tools never raise. They return `_success_result(...)` or `_error_result(...)` from `utils.py`, i.e.
  `{"status": "success" | "error", "content": [{"text": ...}]}`.
- The docstring `Args:` block is the LLM-facing parameter description. Keep it accurate when changing a signature.
- Strands builds the tool spec from the annotations at runtime, so imports used in `@tool` signatures stay outside
  `TYPE_CHECKING` blocks.
- Numeric values the LLM supplies go through the `_clamp_*` helpers in `utils.py`. A clamped parameter's description
  states its ceiling as `(clamped to N max by default)`, which `tests/test_clamp_descriptions.py` checks.
- API access goes through `ApifyToolClient`. It reads `APIFY_TOKEN` and sends the
  `x-apify-integration-platform: strands-agents` tracking header. Keep both.
- Apify Console links to the API token page (`console.apify.com/settings/integrations`) carry
  `?utm_source=strands-agents&utm_medium=integrations`. Other links, including sign-up, stay without UTM.

## apify-client

- `.call()` returns a pydantic `Run` model. Read snake_case attributes (`run.default_dataset_id`), never dict keys.
- `Run` is importable only from the private `apify_client._models`. Import it under `TYPE_CHECKING` in `src/`.
- The public `timeout_secs: int` tool parameter is passed to `.call()` as `run_timeout=timedelta(seconds=...)`.
- Test fixtures must validate into a real `Run` (`Run.model_validate`), not a dict or `MagicMock`, so dict-style access
  fails in tests. The fixture must stay valid on the lowest `apify-client` that `pyproject.toml` allows.

## Tests

New or changed tools need tests for: happy path, missing `APIFY_TOKEN`, missing `apify-client`, Actor failure and at
least one input-validation failure. Mock `ApifyClient` at the boundary (see `tests/conftest.py`).

## Conventions

- Run `uv run poe check-code` before finishing a change.
- Use single quotes and follow the Google docstring convention. Docstrings use single backticks for code (`name`),
  never reStructuredText double backticks.
- Wrap docstrings and comments at 120 characters, the ruff `line-length`.
- Don't name library versions in docstrings or comments ("in apify-client 3.x ..."). Describe the current behavior.
- Comment only what the code can't say: a constraint, a workaround, a non-obvious why.
- Commits and PR titles follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`,
  `chore:`; `!` for breaking changes). CI enforces it.
- Never edit `version` in `pyproject.toml` or `CHANGELOG.md` by hand, and never create tags. The release workflow does
  all three.
