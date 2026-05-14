<!-- Thanks for contributing to strands-apify! Please fill in the sections below. -->

## Summary

<!-- 1-3 sentences describing the change and the motivation. -->

## Changes

<!-- Bullet list of the concrete code/doc changes. -->

-
-

## Test plan

<!-- How did you verify this works? Include commands you ran. -->

- [ ] `hatch run prepare` passes (format, lint, mypy, pytest)
- [ ] New / changed tools have tests covering: happy path, missing `APIFY_API_TOKEN`, missing `apify-client`, Actor failure, at least one input-validation failure
- [ ] Docstrings include `Args:` and `Returns:` blocks (these become LLM-facing tool descriptions)

## Checklist

- [ ] My changes follow the existing tool patterns (`@tool`, `_check_dependency`, `ApifyToolClient`, `_success_result` / `_error_result`)
- [ ] I updated the README tool table if I added or renamed a tool
- [ ] I added an entry under `## [Unreleased]` in `CHANGELOG.md`
- [ ] If I added a new Actor wrapper, I linked the Actor (e.g. `username/actor-name`) in the docstring

## Related issues

<!-- e.g. Closes #123 -->
