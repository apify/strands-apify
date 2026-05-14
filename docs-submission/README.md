# Strands community catalog submission

This folder contains the artifact you need to PR into the
[`strands-agents/docs`](https://github.com/strands-agents/docs) repository to get
`strands-apify` listed on the [community packages page](https://strandsagents.com/docs/community/community-packages/).

It is **not** shipped in the PyPI wheel — `pyproject.toml` only packages
`src/strands_apify`. This directory exists purely as a staging area for the
docs PR.

## How to submit

1. Wait until the first release is **live on PyPI** (so the install link works).
2. Fork [`strands-agents/docs`](https://github.com/strands-agents/docs) and clone it.
3. Copy [`strands-apify.mdx`](./strands-apify.mdx) into
   `docs/community/tools/strands-apify.mdx` in the fork.
4. Edit `src/config/navigation.yml` in that repo: add `strands-apify` to the
   `community/tools/` section (look for sibling entries like `strands-deepgram`
   or `strands-sql` for the exact YAML shape).
5. Open a PR. Per
   [the Get Featured guide](https://strandsagents.com/docs/community/get-featured/)
   there is no formal review bar — a maintainer will merge it.

## Why the page is so short

The `.mdx` is intentionally a thin landing page. It tells the LLM/the reader
what the package is, how to install it, and links back here for the full
docs. The real documentation lives in the package's own `README.md`.
