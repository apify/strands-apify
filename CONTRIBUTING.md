# Contributing to strands-apify

Thank you for your interest in contributing!

## Development setup

```bash
git clone https://github.com/apify/strands-apify.git
cd strands-apify

uv run poe install-dev
```

The project uses [uv](https://docs.astral.sh/uv/) for dependencies and [Poe the Poet](https://poethepoet.natn.io/) for
tasks. Run `uv run poe` to list the tasks. Use uv 0.10 or newer (`uv self update`); older versions such as 0.9.0 can't
parse `pyproject.toml`.

## Running checks

```bash
uv run poe check-code  # Runs lint, type check, and unit tests
```

Or run individually:

```bash
uv run poe format      # Fix lint issues and format code
uv run poe lint        # ruff format --check and ruff check
uv run poe type-check  # ty
uv run poe unit-tests  # pytest
```

CI also runs the integration tests in `tests/integration` against the Apify platform with its own token, on `main` and
on pull requests from branches in this repository. Pull requests from forks skip them, because forks don't get the
token. To run them yourself:

```bash
APIFY_TOKEN=... uv run poe integration-tests
```

## Submitting changes

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `uv run poe check-code` and ensure all checks pass
5. Submit a pull request

## Adding a new Apify tool

1. Identify the Actor on the [Apify Store](https://apify.com/store) and its input schema
2. Add a new `@tool`-decorated function in the appropriate module (`core.py`, `social_media.py`, or `search_crawling.py`)
3. Reuse `ApifyToolClient`, `_check_dependency`, `_success_result`, and `_error_result` from `utils.py`
4. Export the function in `__init__.py` and add it to the relevant `APIFY_*_TOOLS` preset list
5. Add tests covering: happy path, missing token, missing dependency, Actor failure, parameter validation

## PR conventions

PR titles must follow [Conventional Commits](https://www.conventionalcommits.org/). The `pr_title_check` workflow
enforces this, and [git-cliff](https://git-cliff.org/) generates the version bump and the changelog from these types:

- `feat:` for a new feature
- `fix:` for a bug fix
- `perf:` for a performance improvement
- `refactor:` or `style:` for a source change that doesn't change behavior
- `test:`, `docs:`, `build:`, `chore:` or `ci:` for everything else

A `feat`, `fix`, `perf`, `refactor` or `style` commit on `main` publishes a beta, so use those types for source changes
only. Mark a breaking change with `!` after the type (`feat!:`) or a `BREAKING CHANGE:` footer. While the version is
below 1.0, a breaking change bumps the minor version and a feature bumps the patch version.

## Releases

- **Betas are automatic.** After a PR merges to `main`, `on_main.yaml` runs the checks and, for a `feat`, `fix`,
  `perf`, `refactor` or `style` commit, dispatches
  [`manual_release_beta.yaml`](https://github.com/apify/strands-apify/actions/workflows/manual_release_beta.yaml),
  which publishes an `X.Y.ZbN` beta to [PyPI](https://pypi.org/project/strands-apify/). It can also be run by hand.
- **Stable releases are manual.** A maintainer runs
  [`manual_release_stable.yaml`](https://github.com/apify/strands-apify/actions/workflows/manual_release_stable.yaml)
  from `main`. With `auto`, git-cliff picks the version from the commits since the last tag; `custom` takes an exact
  version. The workflow bumps `pyproject.toml`, writes the changelog, tags the release, creates the GitHub release and
  publishes to PyPI.

Both wait for the `Checks` workflow to pass on the commit. Don't edit the version or `CHANGELOG.md` by hand, and don't
create tags or releases manually.

## Security issue notifications

If you discover a potential security issue, please notify us privately via the repository's security advisory feature rather than filing a public issue.
