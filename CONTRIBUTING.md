# Contributing to strands-apify

Thank you for your interest in contributing!

## Development setup

```bash
git clone https://github.com/apify/strands-apify.git
cd strands-apify

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

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

## PR conventions

PR titles must follow [Conventional Commits](https://www.conventionalcommits.org/)
(`feat:`, `fix:`, `docs:`, `chore:`, ...). The `check_pr_title` workflow enforces this,
and the changelog is generated from these prefixes via [git-cliff](https://git-cliff.org/).

## Releases

### Stable releases

1. Go to **Actions** > [**Create a release**](https://github.com/apify/strands-apify/actions/workflows/release.yml) > **Run workflow**.
2. Pick a release type (`auto` recommended, or `patch`/`minor`/`major`/`custom`).
3. Click **Run workflow**. The workflow runs checks, creates a tag + GitHub
   release, bumps `pyproject.toml` and `CHANGELOG.md`, and publishes to
   [PyPI](https://pypi.org/project/strands-apify/).

### Beta releases

Beta releases are also triggered manually, from **Actions** >
[**Create a pre-release**](https://github.com/apify/strands-apify/actions/workflows/pre_release.yml)
> **Run workflow**. The workflow runs the same checks as the stable release,
bumps to the next beta version, updates the changelog, and publishes a
`X.Y.Zb<N>` wheel to PyPI. (Automatic beta-on-push-to-main may be enabled
later; for now both stable and beta releases are manual.)

### Notes

- Do not create tags or releases manually, the workflow handles both.
- Release notes come from conventional commit subjects via git-cliff. You can
  edit the GitHub release body afterward if you want hand-curated notes.


## Security issue notifications

If you discover a potential security issue, please notify us privately via the repository's security advisory feature rather than filing a public issue.
