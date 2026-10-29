# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0](https://github.com/apify/strands-apify/releases/tag/v0.2.0) (2026-10-29)

### 🚀 Features

- [**breaking**] Migrate to apify-client 3.x and require Python 3.11+ ([8a2ef3a](https://github.com/apify/strands-apify/commit/8a2ef3aeb9e47c864c0c343da9d204424b39e7f2)) by [@daveomri](https://github.com/daveomri)
- Add apify_web_fetch tool and deprecate apify_scrape_url ([#16](https://github.com/apify/strands-apify/pull/16)) ([3ad482c](https://github.com/apify/strands-apify/commit/3ad482c2f154e8ec2e2626ac02180f413f8f61e0)) by [@daveomri](https://github.com/daveomri)
- Clamp LLM-supplied limits and describe the ceilings ([#17](https://github.com/apify/strands-apify/pull/17)) ([4c930bb](https://github.com/apify/strands-apify/commit/4c930bb97eee4de54be9ff3fecd0dc988d6efdb1)) by [@daveomri](https://github.com/daveomri)


## [0.1.2](https://github.com/apify/strands-apify/releases/tag/v0.1.2) (2026-09-09)


## [0.1.0](https://github.com/apify/strands-apify/releases/tag/v0.1.0) (2026-05-28)

### 🚀 Features

- Implementation of strands-apify core functionality, social media, and search tools, along with necessary configuration files, docs , and a code of conduct ([6383dc7](https://github.com/apify/strands-apify/commit/6383dc76e4c8b7a6d055c6f59042efb7fa67fee1)) by [@daveomri](https://github.com/daveomri)
- Update project files, and implement github workflows for code checks and releases ([b1ba51e](https://github.com/apify/strands-apify/commit/b1ba51e1935dfb24ebdb1838f8c3066657323f95)) by [@daveomri](https://github.com/daveomri)
- Use uv for dependency installs in reusable workflows ([94ac8ed](https://github.com/apify/strands-apify/commit/94ac8edad089539f6116a5db80ea4cf035a6f048)) by [@daveomri](https://github.com/daveomri)
- Gate rich panel output on TTY and add STRANDS_APIFY_QUIET opt-out ([c061001](https://github.com/apify/strands-apify/commit/c061001412714c55fcd6426663a7229d6f55fc0e)) by [@daveomri](https://github.com/daveomri)
- Publish strands-apify as standalone PyPI package ([#1](https://github.com/apify/strands-apify/pull/1)) ([6866498](https://github.com/apify/strands-apify/commit/6866498c2ca1c0deec94c2ab0acef9f66477f6b1)) by [@daveomri](https://github.com/daveomri)

### 🐛 Bug Fixes

- Pin apify-client&gt;=2.5.0 and SHA-pin release workflows for supply-chain safety ([54af678](https://github.com/apify/strands-apify/commit/54af678a727d1d3f6179a4588ad36af3871a977e)) by [@daveomri](https://github.com/daveomri)
- Tighten Instagram URL detection and propagate Actor statusMessage ([df7e5f6](https://github.com/apify/strands-apify/commit/df7e5f6496c5f5fb7e2280fef794e3c6a15e5345)) by [@daveomri](https://github.com/daveomri)
- Cap apify-client&lt;3.0.0 to keep the 2.x API contract ([d682f13](https://github.com/apify/strands-apify/commit/d682f133e52d096b6119acd4465edf428dad64f3)) by [@daveomri](https://github.com/daveomri)
- Bump apify&#x2F;workflows SHA pins to uv-based version ([#8](https://github.com/apify/strands-apify/pull/8)) ([2f5c64a](https://github.com/apify/strands-apify/commit/2f5c64a905b61ff698678e08929e73ae11638d8e)) by [@daveomri](https://github.com/daveomri)


# Changelog

All notable changes to `strands-apify` are documented here.

This file is maintained automatically by [git-cliff](https://git-cliff.org/) on every
release via the [`apify/workflows`](https://github.com/apify/workflows/tree/main/git-cliff-release)
reusable action - entries are derived from [Conventional Commits](https://www.conventionalcommits.org/)
in the git history.