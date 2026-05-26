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

Releases are cut by manually triggering the **Create a release** workflow
(`release.yml`) from the
[Actions tab](https://github.com/apify/strands-apify/actions/workflows/release.yml).
The workflow generates the tag and GitHub release, then publishes the wheel to
PyPI via OIDC trusted publishing. This follows the same pattern as other Apify
Python packages (`langchain-apify`, `crawlee-python`), with stricter CI gates
(adds a unit-tests job that `langchain-apify` does not have).

### Stable releases (workflow_dispatch)

1. Go to **Actions** > **Create a release** >
   [**Run workflow**](https://github.com/apify/strands-apify/actions/workflows/release.yml).
2. Pick a **release type**:
   - `auto`: bump version based on conventional commits since the last tag
     (recommended).
   - `patch` / `minor` / `major`: explicit semver bump.
   - `custom`: pick an exact version (fill in **custom version** below).
3. If `custom` was selected, type the **custom version** (e.g. `0.1.0`).
4. Click **Run workflow**.

The workflow then:

- Computes the version, tag name, and release notes via
  `apify/actions/git-cliff-release`.
- Runs lint, type, and test checks.
- Creates the tag `vX.Y.Z` and a GitHub release with notes via
  `softprops/action-gh-release`.
- Publishes the wheel to [PyPI](https://pypi.org/project/strands-apify/) via
  OIDC trusted publishing.

Watch the [Actions tab](https://github.com/apify/strands-apify/actions); the
run completes in about 4 to 6 minutes.

### Beta releases (automatic on push to main)

`pre_release.yml` runs on every push to `main` (excluding `docs:` and `ci:`
prefixed commits). For each qualifying push it:

1. Bumps `pyproject.toml` to the next stable patch version (e.g. `0.2.1`) and
   updates `CHANGELOG.md`, committing both back to `main`. This step uses the
   `apify/workflows/.../python_bump_and_update_changelog.yaml` reusable
   workflow, which works correctly here because `push` events keep HEAD on a
   branch (the same workflow fails when called from a `release: published`
   context, which is why `release.yml` does not invoke it).
2. Publishes a beta wheel `X.Y.Zb<N>` to PyPI. The `bN` suffix is added by
   `apify/actions/prepare-pypi-distribution` at build time and is **not**
   written back to `pyproject.toml` on `main`; only the bumped base version
   (e.g. `0.2.1`) is committed.

No manual action required; keep merging PRs to `main` and betas appear
automatically.

### How beta and stable releases compose

Because `pre_release.yml` keeps `pyproject.toml` at the next stable base
version, the stable cut becomes mechanical:

- After betas have been running, `pyproject.toml` says e.g. `version = "0.2.1"`.
- When you trigger `release.yml` with `release_type: auto`, `git-cliff`
  computes the same `0.2.1` from conventional commits.
- `prepare-pypi-distribution` reads `pyproject.toml` as-is (no bump on stable
  releases) and builds the wheel as `0.2.1`. The tag, GitHub release, and
  PyPI artifact all agree.

**Edge case to know about:** `release.yml` does **not** itself bump
`pyproject.toml` or update `CHANGELOG.md` on stable releases. Both updates
happen exclusively through `pre_release.yml`. If a stable release is cut
without any qualifying push having run `pre_release.yml` in between (for
example, only `docs:` / `ci:` commits since the last stable, or the very
first release ever), `pyproject.toml` will not reflect the new version that
the workflow tags and creates a release for, and the resulting wheel will
have the old version in its metadata while the git tag claims the new one.

For the first release specifically (no prior tags, `pyproject.toml` ships
at `0.1.0` from initial setup) this works out cleanly when you pick
`release_type: custom` with `custom_version: 0.1.0`. After that, let
`pre_release.yml` do its job and stable releases will stay consistent.

### Notes

- Release notes for stable releases are generated from conventional commit
  subjects via `git-cliff`. If you want a hand-curated release page (e.g. for
  the first impression of v0.1.0 on PyPI / the Strands catalog), edit the
  GitHub release body after the workflow finishes, before announcing the
  release externally. The PyPI artifact is unaffected; only the GitHub release
  page changes.
- Tag and release are both created by the workflow. Do not create them
  manually on the Releases page; that would trigger nothing (the workflow
  only listens for `workflow_dispatch`) and would leave the tag pointing at a
  commit without a matching PyPI publish.


## Security issue notifications

If you discover a potential security issue, please notify us privately via the repository's security advisory feature rather than filing a public issue.
