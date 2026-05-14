# strands-apify

[![PyPI version](https://img.shields.io/pypi/v/strands-apify.svg)](https://pypi.org/project/strands-apify/)
[![Python versions](https://img.shields.io/pypi/pyversions/strands-apify.svg)](https://pypi.org/project/strands-apify/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Code checks](https://github.com/apify/strands-apify/actions/workflows/run_code_checks.yml/badge.svg?branch=main)](https://github.com/apify/strands-apify/actions/workflows/run_code_checks.yml)

Apify tools for the [Strands Agents SDK](https://strandsagents.com/) - web scraping, social media, search, and automation.

This package gives Strands agents access to [Apify Actors](https://apify.com/store): serverless cloud programs that scrape websites, social platforms, search engines, and e-commerce sites, returning structured JSON or Markdown.

## Installation

```bash
pip install strands-apify
```

Set your Apify API token:

```bash
export APIFY_API_TOKEN=your_api_token_here
```

Get a token at [Apify Console > Settings > API & Integrations](https://console.apify.com/account/integrations).

## Quick start

```python
from strands import Agent
from strands_apify import APIFY_CORE_TOOLS

agent = Agent(tools=APIFY_CORE_TOOLS)
result = agent("Scrape https://example.com and summarize it.")
```

Or register specific tools:

```python
from strands import Agent
from strands_apify import apify_scrape_url, apify_google_search_scraper

agent = Agent(tools=[apify_scrape_url, apify_google_search_scraper])
```

Convenience presets:

- `APIFY_CORE_TOOLS` — generic Actor/task/dataset/scrape tools
- `APIFY_SOCIAL_TOOLS` — Instagram, LinkedIn, Twitter/X, TikTok, Facebook
- `APIFY_SEARCH_TOOLS` — Google Search, Google Maps, YouTube, multi-page crawler, e-commerce
- `APIFY_ALL_TOOLS` — everything (use sparingly; many tools may overwhelm an LLM's tool choice)

## Tools

### Core tools

Generic Apify platform access — run any Actor, run saved tasks, fetch dataset items, and scrape a single URL.

| Tool | What it does |
|------|--------------|
| `apify_run_actor` | Run any Apify Actor by id with custom input; returns run metadata |
| `apify_get_dataset_items` | Fetch items from an Apify dataset with pagination |
| `apify_run_actor_and_get_dataset` | Run an Actor and fetch its default dataset in one step |
| `apify_run_task` | Run a saved Actor task |
| `apify_run_task_and_get_dataset` | Run a task and fetch its dataset in one step |
| `apify_scrape_url` | Scrape a single URL via the Website Content Crawler, return Markdown |

```python
from strands_apify import apify_scrape_url, apify_run_actor_and_get_dataset

# Single URL
apify_scrape_url(url="https://example.com")

# Any Actor with custom input
apify_run_actor_and_get_dataset(
    actor_id="apify/website-content-crawler",
    run_input={"startUrls": [{"url": "https://docs.example.com"}], "maxCrawlPages": 5},
)
```

### Social media tools

Scrape structured data from popular social platforms.

| Tool | Platform | Actor |
|------|----------|-------|
| `apify_instagram_scraper` | Instagram (profiles, posts, hashtags, places) | `apify/instagram-scraper` |
| `apify_linkedin_profile_posts` | LinkedIn profile posts | `apimaestro/linkedin-profile-posts` |
| `apify_linkedin_profile_search` | LinkedIn profile search | `harvestapi/linkedin-profile-search` |
| `apify_linkedin_profile_detail` | LinkedIn profile details | `apimaestro/linkedin-profile-detail` |
| `apify_twitter_scraper` | Twitter/X (search, handles, URLs) | `apidojo/twitter-scraper-lite` |
| `apify_tiktok_scraper` | TikTok (search, hashtags, profiles, URLs) | `clockworks/tiktok-scraper` |
| `apify_facebook_posts_scraper` | Facebook page posts | `apify/facebook-posts-scraper` |

```python
from strands_apify import apify_twitter_scraper, apify_linkedin_profile_search

apify_twitter_scraper(search_query="from:NASA min_faves:100", results_limit=30)

apify_linkedin_profile_search(
    search_query="software engineer",
    locations=["San Francisco"],
    profile_scraper_mode="Full",
)
```

### Search & crawling tools

Search engines, maps, video, multi-page crawls, and e-commerce.

| Tool | What it does | Actor |
|------|--------------|-------|
| `apify_google_search_scraper` | Google search (organic, ads, People Also Ask) | `apify/google-search-scraper` |
| `apify_google_places_scraper` | Google Maps places and reviews | `compass/crawler-google-places` |
| `apify_youtube_scraper` | YouTube search and video/channel URLs | `streamers/youtube-scraper` |
| `apify_website_content_crawler` | Multi-page website crawl with Markdown extraction | `apify/website-content-crawler` |
| `apify_ecommerce_scraper` | Product data from Amazon, eBay, Walmart, etc. | `apify/e-commerce-scraping-tool` |

```python
from strands_apify import apify_google_search_scraper, apify_website_content_crawler

apify_google_search_scraper(search_query="best AI frameworks 2025", country_code="us")

apify_website_content_crawler(
    start_url="https://docs.example.com",
    max_pages=20,
    max_depth=3,
)
```

## Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `APIFY_API_TOKEN` | Your Apify API token from [console.apify.com](https://console.apify.com/account/integrations) | Yes |

## Development

```bash
git clone https://github.com/apify/strands-apify.git
cd strands-apify
pip install -e ".[dev]"
hatch run prepare  # format check, lint, typecheck, test
```

PR titles must follow [Conventional Commits](https://www.conventionalcommits.org/)
(`feat:`, `fix:`, `docs:`, `chore:`, ...) — the `check_pr_title` workflow enforces
this and the changelog is generated from these prefixes via
[git-cliff](https://git-cliff.org/). Releases are cut from the
[Actions tab](https://github.com/apify/strands-apify/actions/workflows/release.yml)
by manually triggering the **Create a release** workflow.

## License

Apache-2.0

## References

- [Apify Platform](https://apify.com/)
- [Apify Store (find Actors)](https://apify.com/store)
- [Strands Agents SDK](https://strandsagents.com/)
- [Strands Community Catalog](https://strandsagents.com/docs/community/community-packages/)
