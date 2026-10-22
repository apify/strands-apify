"""Core Apify platform tools for Strands Agents.

Available Tools:
---------------
- apify_run_actor: Run any Apify Actor with custom input
- apify_get_dataset_items: Fetch items from an Apify dataset with pagination
- apify_run_actor_and_get_dataset: Run an Actor and fetch results in one step
- apify_run_task: Run a saved Actor task with optional input overrides
- apify_run_task_and_get_dataset: Run a task and fetch results in one step
- apify_web_fetch: Fetch a single URL as Markdown, HTML, text, links or raw content
- apify_scrape_url: Deprecated, use apify_web_fetch
"""

import json
import logging
from typing import Any

from strands import tool

from .utils import (
    DEFAULT_DATASET_ITEMS_LIMIT,
    DEFAULT_SCRAPE_TIMEOUT_SECS,
    DEFAULT_TIMEOUT_SECS,
    DEFAULT_WEB_FETCH_TIMEOUT_SECS,
    ApifyToolClient,
    CrawlerType,
    WebFetchFormat,
    _check_dependency,
    _error_result,
    _success_result,
)

logger = logging.getLogger(__name__)


@tool
def apify_run_actor(
    actor_id: str,
    run_input: dict[str, Any] | None = None,
    timeout_secs: int = DEFAULT_TIMEOUT_SECS,
    memory_mbytes: int | None = None,
    build: str | None = None,
) -> dict[str, Any]:
    """Run any Apify Actor and return the run metadata as JSON.

    An Actor is a serverless cloud app on the Apify platform - it takes JSON input,
    runs the scraping or automation job, and writes results to a dataset. This tool
    executes the Actor synchronously and returns run metadata only (run_id, status,
    dataset_id, timestamps). Use apify_run_actor_and_get_dataset to also fetch the
    output data in one call, or apify_web_fetch for quick single-URL extraction.

    Common Actors:
    - "apify/website-content-crawler" - scrape websites and extract content as Markdown
    - "apify/web-scraper" - general-purpose web scraper with JS rendering
    - "apify/google-search-scraper" - scrape Google search results

    Args:
        actor_id: Actor identifier in "username/actor-name" format,
            e.g. "apify/website-content-crawler". Find Actors at https://apify.com/store.
        run_input: JSON-serializable input for the Actor. Each Actor defines its own
            input schema - check the Actor README on Apify Store for required fields.
        timeout_secs: Maximum time in seconds to wait for the Actor run to finish. Defaults to 300.
        memory_mbytes: Memory allocation in MB for the Actor run. Uses Actor default `memory` value if not set.
        build: Actor build tag or number to run a specific version. Uses latest build if not set.

    Returns:
        Dict with status and content containing run metadata: run_id, status, dataset_id,
        started_at, finished_at.
    """
    try:
        _check_dependency()
        client = ApifyToolClient()
        result = client.run_actor(
            actor_id=actor_id,
            run_input=run_input,
            timeout_secs=timeout_secs,
            memory_mbytes=memory_mbytes,
            build=build,
        )
        return _success_result(
            text=json.dumps(result, indent=2, default=str),
            panel_body=(
                f"[green]Actor run completed[/green]\n"
                f"Actor: {actor_id}\n"
                f"Run ID: {result['run_id']}\n"
                f"Status: {result['status']}\n"
                f"Dataset ID: {result['dataset_id']}"
            ),
            panel_title="Apify: Run Actor",
        )
    except Exception as e:
        return _error_result(e, "apify_run_actor")


@tool
def apify_get_dataset_items(
    dataset_id: str,
    limit: int = DEFAULT_DATASET_ITEMS_LIMIT,
    offset: int = 0,
) -> dict[str, Any]:
    """Fetch items from an existing Apify dataset and return them as JSON.

    Every Actor run writes its output to a dataset - a structured, append-only store
    for tabular data. Use the dataset_id from the run metadata returned by apify_run_actor
    or apify_run_task. Use offset for pagination through large datasets.

    Args:
        dataset_id: The Apify dataset ID to fetch items from.
        limit: Maximum number of items to return. Defaults to 100.
        offset: Number of items to skip for pagination. Defaults to 0.

    Returns:
        Dict with status and content containing an array of dataset items.
    """
    try:
        _check_dependency()
        client = ApifyToolClient()
        items = client.get_dataset_items(dataset_id=dataset_id, limit=limit, offset=offset)
        return _success_result(
            text=json.dumps(items, indent=2, default=str),
            panel_body=(
                f"[green]Dataset items retrieved[/green]\nDataset ID: {dataset_id}\nItems returned: {len(items)}"
            ),
            panel_title="Apify: Dataset Items",
        )
    except Exception as e:
        return _error_result(e, "apify_get_dataset_items")


@tool
def apify_run_actor_and_get_dataset(
    actor_id: str,
    run_input: dict[str, Any] | None = None,
    timeout_secs: int = DEFAULT_TIMEOUT_SECS,
    memory_mbytes: int | None = None,
    build: str | None = None,
    dataset_items_limit: int = DEFAULT_DATASET_ITEMS_LIMIT,
    dataset_items_offset: int = 0,
) -> dict[str, Any]:
    """Run an Apify Actor and fetch its dataset results in one step.

    Convenience tool that combines running an Actor and fetching its default dataset
    items into a single call. Use this when you want both the run metadata and the
    result data without making two separate tool calls.

    Args:
        actor_id: Actor identifier in "username/actor-name" format,
            e.g. "apify/website-content-crawler". Find Actors at https://apify.com/store.
        run_input: JSON-serializable input for the Actor. Each Actor defines its own
            input schema - check the Actor README on Apify Store for required fields.
        timeout_secs: Maximum time in seconds to wait for the Actor run to finish. Defaults to 300.
        memory_mbytes: Memory allocation in MB for the Actor run. Uses Actor default `memory` value if not set.
        build: Actor build tag or number to run a specific version. Uses latest build if not set.
        dataset_items_limit: Maximum number of dataset items to return. Defaults to 100.
        dataset_items_offset: Number of dataset items to skip for pagination. Defaults to 0.

    Returns:
        Dict with status and content containing run metadata (run_id, status, dataset_id,
        started_at, finished_at) plus an "items" array containing the dataset results.
    """
    try:
        _check_dependency()
        client = ApifyToolClient()
        result = client.run_actor_and_get_dataset(
            actor_id=actor_id,
            run_input=run_input,
            timeout_secs=timeout_secs,
            memory_mbytes=memory_mbytes,
            build=build,
            dataset_items_limit=dataset_items_limit,
            dataset_items_offset=dataset_items_offset,
        )
        return _success_result(
            text=json.dumps(result, indent=2, default=str),
            panel_body=(
                f"[green]Actor run completed with dataset[/green]\n"
                f"Actor: {actor_id}\n"
                f"Run ID: {result['run_id']}\n"
                f"Status: {result['status']}\n"
                f"Dataset ID: {result['dataset_id']}\n"
                f"Items returned: {len(result['items'])}"
            ),
            panel_title="Apify: Run Actor + Dataset",
        )
    except Exception as e:
        return _error_result(e, "apify_run_actor_and_get_dataset")


@tool
def apify_run_task(
    task_id: str,
    task_input: dict[str, Any] | None = None,
    timeout_secs: int = DEFAULT_TIMEOUT_SECS,
    memory_mbytes: int | None = None,
) -> dict[str, Any]:
    """Run a saved Apify task and return the run metadata as JSON.

    Tasks are saved Actor configurations with preset inputs, managed in Apify Console.
    Use this when a task has already been configured, so you don't need to specify
    the full Actor input every time. Use apify_run_task_and_get_dataset to also fetch
    the output data in one call.

    Args:
        task_id: Task identifier in "username/task-name" format or a task ID string.
        task_input: Optional JSON-serializable input to override the task's default input fields.
        timeout_secs: Maximum time in seconds to wait for the task run to finish. Defaults to 300.
        memory_mbytes: Memory allocation in MB for the task run. Uses task default `memory` value if not set.

    Returns:
        Dict with status and content containing run metadata: run_id, status, dataset_id,
        started_at, finished_at.
    """
    try:
        _check_dependency()
        client = ApifyToolClient()
        result = client.run_task(
            task_id=task_id,
            task_input=task_input,
            timeout_secs=timeout_secs,
            memory_mbytes=memory_mbytes,
        )
        return _success_result(
            text=json.dumps(result, indent=2, default=str),
            panel_body=(
                f"[green]Task run completed[/green]\n"
                f"Task: {task_id}\n"
                f"Run ID: {result['run_id']}\n"
                f"Status: {result['status']}\n"
                f"Dataset ID: {result['dataset_id']}"
            ),
            panel_title="Apify: Run Task",
        )
    except Exception as e:
        return _error_result(e, "apify_run_task")


@tool
def apify_run_task_and_get_dataset(
    task_id: str,
    task_input: dict[str, Any] | None = None,
    timeout_secs: int = DEFAULT_TIMEOUT_SECS,
    memory_mbytes: int | None = None,
    dataset_items_limit: int = DEFAULT_DATASET_ITEMS_LIMIT,
    dataset_items_offset: int = 0,
) -> dict[str, Any]:
    """Run a saved Apify task and fetch its dataset results in one step.

    Convenience tool that combines running a task and fetching its default dataset
    items into a single call. Use this when you want both the run metadata and the
    result data without making two separate tool calls.

    Args:
        task_id: Task identifier in "username/task-name" format or a task ID string.
        task_input: Optional JSON-serializable input to override the task's default input fields.
        timeout_secs: Maximum time in seconds to wait for the task run to finish. Defaults to 300.
        memory_mbytes: Memory allocation in MB for the task run. Uses task default `memory` value if not set.
        dataset_items_limit: Maximum number of dataset items to return. Defaults to 100.
        dataset_items_offset: Number of dataset items to skip for pagination. Defaults to 0.

    Returns:
        Dict with status and content containing run metadata (run_id, status, dataset_id,
        started_at, finished_at) plus an "items" array containing the dataset results.
    """
    try:
        _check_dependency()
        client = ApifyToolClient()
        result = client.run_task_and_get_dataset(
            task_id=task_id,
            task_input=task_input,
            timeout_secs=timeout_secs,
            memory_mbytes=memory_mbytes,
            dataset_items_limit=dataset_items_limit,
            dataset_items_offset=dataset_items_offset,
        )
        return _success_result(
            text=json.dumps(result, indent=2, default=str),
            panel_body=(
                f"[green]Task run completed with dataset[/green]\n"
                f"Task: {task_id}\n"
                f"Run ID: {result['run_id']}\n"
                f"Status: {result['status']}\n"
                f"Dataset ID: {result['dataset_id']}\n"
                f"Items returned: {len(result['items'])}"
            ),
            panel_title="Apify: Run Task + Dataset",
        )
    except Exception as e:
        return _error_result(e, "apify_run_task_and_get_dataset")


@tool
def apify_web_fetch(
    url: str,
    formats: list[WebFetchFormat] | None = None,
    headers: dict[str, str] | None = None,
    wait_ms: int | None = None,
    timeout_secs: int = DEFAULT_WEB_FETCH_TIMEOUT_SECS,
) -> dict[str, Any]:
    """Fetch a single web page and return its content as Markdown, HTML, plain text, links or raw content.

    Uses the Web Fetch Actor, which answers in one real-time request, renders JavaScript and works around bot
    protection on its own. This is the fastest way to read one page. For multi-page crawls, use
    apify_website_content_crawler instead.

    Args:
        url: The URL to fetch, e.g. "https://example.com". Only http and https URLs are supported.
        formats: Output formats to return. Any of "markdown", "html", "text", "links" (a deduplicated list of the
            page's links) and "raw" (the original bytes, base64-encoded for binary content). Defaults to
            ["markdown"]. Prefer "markdown" or "text": "html" and "raw" are much larger.
        headers: Optional HTTP headers to send to the target URL, e.g. {"Accept-Language": "fr-FR"}.
        wait_ms: Optional milliseconds to wait after the page loads, from 1 to 60000. Setting it renders the page
            in a real browser so content loaded later by JavaScript is included, but makes the request slower.
        timeout_secs: Maximum time in seconds to wait for the response. Defaults to 180.

    Returns:
        Dict with status and content containing JSON with url, final_url (after redirects), title, http_status
        (the target page's own HTTP status, e.g. 404 for a missing page) and one key per requested format.
        A format that does not apply to the page is null.
    """
    try:
        _check_dependency()
        client = ApifyToolClient()
        result = client.web_fetch(url=url, formats=formats, headers=headers, wait_ms=wait_ms, timeout_secs=timeout_secs)
        return _success_result(
            text=json.dumps(result, indent=2, default=str),
            panel_body=(
                f"[green]URL fetched[/green]\n"
                f"URL: {result['final_url']}\n"
                f"HTTP status: {result['http_status']}\n"
                f"Title: {result['title']}"
            ),
            panel_title="Apify: Web Fetch",
        )
    except Exception as e:
        return _error_result(e, "apify_web_fetch")


@tool
def apify_scrape_url(
    url: str,
    timeout_secs: int = DEFAULT_SCRAPE_TIMEOUT_SECS,
    crawler_type: CrawlerType = "cheerio",
) -> dict[str, Any]:
    """Deprecated: use apify_web_fetch instead, it is faster and needs no crawler_type.

    Scrape a single URL and return its content as Markdown.

    Uses the Website Content Crawler Actor under the hood, pre-configured for
    fast single-page scraping. This is the simplest way to extract readable content
    from any web page - no Actor input schema needed. For multi-page crawls, use
    apify_run_actor_and_get_dataset with "apify/website-content-crawler" directly.

    Args:
        url: The URL to scrape, e.g. "https://example.com".
        timeout_secs: Maximum time in seconds to wait for scraping to finish. Defaults to 120.
        crawler_type: Crawler engine to use. One of:
            - "cheerio" (default): Fastest, no JavaScript rendering. Best for static HTML.
            - "playwright:adaptive": Renders JS only when needed. Good general-purpose choice.
            - "playwright:firefox": Full JS rendering, best at bypassing anti-bot protection but slowest.

    Returns:
        Dict with status and content containing the Markdown content of the scraped page.
    """
    logger.warning("apify_scrape_url is deprecated and will be removed in a future release. Use apify_web_fetch.")
    try:
        _check_dependency()
        client = ApifyToolClient()
        content = client.scrape_url(url=url, timeout_secs=timeout_secs, crawler_type=crawler_type)
        return _success_result(
            text=content,
            panel_body=(
                f"[green]URL scraped successfully[/green]\nURL: {url}\nContent length: {len(content)} characters"
            ),
            panel_title="Apify: Scrape URL",
        )
    except Exception as e:
        return _error_result(e, "apify_scrape_url")


APIFY_CORE_TOOLS = [
    apify_run_actor,
    apify_get_dataset_items,
    apify_run_actor_and_get_dataset,
    apify_run_task,
    apify_run_task_and_get_dataset,
    apify_web_fetch,
    apify_scrape_url,
]
