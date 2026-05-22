"""Shared infrastructure for Apify tools: client wrapper, error formatting, validators."""

import logging
import os
from typing import Any, Literal, get_args
from urllib.parse import urlparse

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

logger = logging.getLogger(__name__)

# Rich panels are decoration — write them to stderr so they never mix with the
# structured tool output that Strands consumes from stdout. The panels are only
# emitted when stderr is attached to a terminal, so production / non-interactive
# deployments stay silent without any configuration. Set STRANDS_APIFY_QUIET=1
# to suppress panels even in interactive shells.
console = Console(stderr=True)
_QUIET_ENV_VALUES = frozenset({"1", "true", "yes", "on"})


def _panels_enabled() -> bool:
    """Return True if rich panels should be printed for the current call.

    Suppresses output when:
    - stderr is not a TTY (CI, Docker, web service, background worker), or
    - STRANDS_APIFY_QUIET is set to a truthy value.
    """
    if os.getenv("STRANDS_APIFY_QUIET", "").lower() in _QUIET_ENV_VALUES:
        return False
    return console.is_terminal


try:
    from apify_client import ApifyClient
    from apify_client.errors import ApifyApiError

    HAS_APIFY_CLIENT = True
except ImportError:
    HAS_APIFY_CLIENT = False

TRACKING_HEADER = {"x-apify-integration-platform": "strands-apify"}
ERROR_PANEL_TITLE = "[bold red]Apify Error[/bold red]"
DEFAULT_TIMEOUT_SECS = 300
DEFAULT_SCRAPE_TIMEOUT_SECS = 120
DEFAULT_DATASET_ITEMS_LIMIT = 100

WEBSITE_CONTENT_CRAWLER = "apify/website-content-crawler"
CrawlerType = Literal["playwright:adaptive", "playwright:firefox", "cheerio"]
WEBSITE_CONTENT_CRAWLER_TYPES = get_args(CrawlerType)


def _check_dependency() -> None:
    """Raise ImportError if apify-client is not installed."""
    if not HAS_APIFY_CLIENT:
        raise ImportError("apify-client package is required. Install with: pip install strands-apify")


def _format_error(e: Exception) -> str:
    """Map exceptions to user-friendly error messages, with special handling for ApifyApiError."""
    if HAS_APIFY_CLIENT and isinstance(e, ApifyApiError):
        status_code = getattr(e, "status_code", None)
        msg = getattr(e, "message", str(e))
        match status_code:
            case 400:
                return f"Invalid request: {msg}"
            case 401:
                return "Authentication failed. Verify your APIFY_TOKEN is valid."
            case 402:
                return "Insufficient Apify plan credits or subscription limits exceeded."
            case 404:
                return f"Resource not found: {msg}"
            case 408:
                return f"Actor run timed out: {msg}"
            case 429:
                return (
                    "Rate limit exceeded. The Apify client retries automatically; "
                    "if this persists, reduce request frequency."
                )
            case None:
                return f"Apify API error: {msg}"
            case _:
                return f"Apify API error ({status_code}): {msg}"
    return str(e)


def _error_result(e: Exception, tool_name: str) -> dict[str, Any]:
    """Build a structured error response and display an error panel."""
    message = _format_error(e)
    logger.error("%s failed: %s", tool_name, message)
    if _panels_enabled():
        console.print(Panel(Text(message, style="red"), title=ERROR_PANEL_TITLE, border_style="red"))
    return {"status": "error", "content": [{"text": message}]}


def _success_result(text: str, panel_body: str, panel_title: str) -> dict[str, Any]:
    """Build a structured success response and display a success panel."""
    if _panels_enabled():
        console.print(Panel(panel_body, title=f"[bold cyan]{panel_title}[/bold cyan]", border_style="green"))
    return {"status": "success", "content": [{"text": text}]}


# Module-level validators
# These are package-private (underscore-prefixed) but used across submodules.


def _check_run_status(actor_run: dict[str, Any], label: str) -> None:
    """Raise RuntimeError if the Actor run did not succeed.

    Includes the Apify-provided ``statusMessage`` in the error when present so
    callers can see why a run failed without having to look up the run in the
    Apify Console.
    """
    status = actor_run.get("status", "UNKNOWN")
    if status == "SUCCEEDED":
        return
    run_id = actor_run.get("id", "N/A")
    status_msg = actor_run.get("statusMessage")
    parts = [f"{label} finished with status {status}", f"Run ID: {run_id}"]
    if status_msg:
        parts.append(f"Message: {status_msg}")
    raise RuntimeError(". ".join(parts))


def _validate_url(url: str) -> None:
    """Raise ValueError if the URL does not have a valid HTTP(S) scheme and domain."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Invalid URL scheme '{parsed.scheme}'. Only http and https URLs are supported.")
    if not parsed.netloc:
        raise ValueError(f"Invalid URL '{url}'. A domain is required.")


def _validate_urls(urls: list[str], name: str) -> None:
    """Raise ValueError if any URL in the list is invalid; error names the offending index."""
    for i, url in enumerate(urls):
        try:
            _validate_url(url)
        except ValueError as e:
            raise ValueError(f"{name}[{i}]: {e}") from e


def _validate_identifier(value: str, name: str) -> None:
    """Raise ValueError if a required string identifier is empty or whitespace-only."""
    if not value.strip():
        raise ValueError(f"'{name}' must be a non-empty string.")


def _validate_positive(value: int, name: str) -> None:
    """Raise ValueError if the value is not a positive integer (> 0)."""
    if value <= 0:
        raise ValueError(f"'{name}' must be a positive integer, got {value}.")


def _validate_non_negative(value: int, name: str) -> None:
    """Raise ValueError if the value is negative."""
    if value < 0:
        raise ValueError(f"'{name}' must be a non-negative integer, got {value}.")


class ApifyToolClient:
    """Helper class encapsulating Apify API interactions via apify-client."""

    def __init__(self) -> None:
        token = os.getenv("APIFY_TOKEN", "")
        if not token:
            raise ValueError(
                "APIFY_TOKEN environment variable is not set. "
                "Get your token at https://console.apify.com/account/integrations"
            )
        self.client: ApifyClient = ApifyClient(token, headers=TRACKING_HEADER)

    def run_actor(
        self,
        actor_id: str,
        run_input: dict[str, Any] | None = None,
        timeout_secs: int = DEFAULT_TIMEOUT_SECS,
        memory_mbytes: int | None = None,
        build: str | None = None,
    ) -> dict[str, Any]:
        """Run an Apify Actor synchronously and return run metadata."""
        _validate_identifier(actor_id, "actor_id")
        _validate_positive(timeout_secs, "timeout_secs")
        if memory_mbytes is not None:
            _validate_positive(memory_mbytes, "memory_mbytes")

        call_kwargs: dict[str, Any] = {
            "run_input": run_input if run_input is not None else {},
            "timeout_secs": timeout_secs,
            "logger": None,
        }
        if memory_mbytes is not None:
            call_kwargs["memory_mbytes"] = memory_mbytes
        if build is not None:
            call_kwargs["build"] = build

        actor_run = self.client.actor(actor_id).call(**call_kwargs)
        if actor_run is None:
            raise RuntimeError(f"Actor {actor_id} returned no run data (possible wait timeout).")
        _check_run_status(actor_run, f"Actor {actor_id}")

        return {
            "run_id": actor_run.get("id"),
            "status": actor_run.get("status"),
            "dataset_id": actor_run.get("defaultDatasetId"),
            "started_at": actor_run.get("startedAt"),
            "finished_at": actor_run.get("finishedAt"),
        }

    def get_dataset_items(
        self,
        dataset_id: str,
        limit: int = DEFAULT_DATASET_ITEMS_LIMIT,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Fetch items from an Apify dataset."""
        _validate_identifier(dataset_id, "dataset_id")
        _validate_positive(limit, "limit")
        _validate_non_negative(offset, "offset")

        result = self.client.dataset(dataset_id).list_items(limit=limit, offset=offset)
        return list(result.items)

    def run_actor_and_get_dataset(
        self,
        actor_id: str,
        run_input: dict[str, Any] | None = None,
        timeout_secs: int = DEFAULT_TIMEOUT_SECS,
        memory_mbytes: int | None = None,
        build: str | None = None,
        dataset_items_limit: int = DEFAULT_DATASET_ITEMS_LIMIT,
        dataset_items_offset: int = 0,
    ) -> dict[str, Any]:
        """Run an Actor synchronously, then fetch its default dataset items."""
        _validate_positive(dataset_items_limit, "dataset_items_limit")
        _validate_non_negative(dataset_items_offset, "dataset_items_offset")

        run_metadata = self.run_actor(
            actor_id=actor_id,
            run_input=run_input,
            timeout_secs=timeout_secs,
            memory_mbytes=memory_mbytes,
            build=build,
        )
        dataset_id = run_metadata["dataset_id"]
        if not dataset_id:
            raise RuntimeError(f"Actor {actor_id} run has no default dataset.")
        items = self.get_dataset_items(dataset_id=dataset_id, limit=dataset_items_limit, offset=dataset_items_offset)
        return {**run_metadata, "items": items}

    def scrape_url(
        self,
        url: str,
        timeout_secs: int = DEFAULT_SCRAPE_TIMEOUT_SECS,
        crawler_type: "CrawlerType" = "cheerio",
    ) -> str:
        """Scrape a single URL using Website Content Crawler and return Markdown."""
        _validate_url(url)
        _validate_positive(timeout_secs, "timeout_secs")
        if crawler_type not in WEBSITE_CONTENT_CRAWLER_TYPES:
            raise ValueError(
                f"Invalid crawler_type '{crawler_type}'. Must be one of: {', '.join(WEBSITE_CONTENT_CRAWLER_TYPES)}."
            )

        run_input: dict[str, Any] = {
            "startUrls": [{"url": url}],
            "maxCrawlPages": 1,
            "crawlerType": crawler_type,
        }
        actor_run = self.client.actor(WEBSITE_CONTENT_CRAWLER).call(
            run_input=run_input,
            timeout_secs=timeout_secs,
            logger=None,
        )
        if actor_run is None:
            raise RuntimeError("Website Content Crawler returned no run data (possible wait timeout).")
        _check_run_status(actor_run, "Website Content Crawler")

        dataset_id = actor_run.get("defaultDatasetId")
        if not dataset_id:
            raise RuntimeError("Website Content Crawler run has no default dataset.")
        result = self.client.dataset(dataset_id).list_items(limit=1)
        items = list(result.items)

        if not items:
            raise RuntimeError(f"No content returned for URL: {url}")

        return str(items[0].get("markdown") or items[0].get("text", ""))

    def run_task(
        self,
        task_id: str,
        task_input: dict[str, Any] | None = None,
        timeout_secs: int = DEFAULT_TIMEOUT_SECS,
        memory_mbytes: int | None = None,
    ) -> dict[str, Any]:
        """Run an Apify task synchronously and return run metadata."""
        _validate_identifier(task_id, "task_id")
        _validate_positive(timeout_secs, "timeout_secs")
        if memory_mbytes is not None:
            _validate_positive(memory_mbytes, "memory_mbytes")

        call_kwargs: dict[str, Any] = {"timeout_secs": timeout_secs}
        if task_input is not None:
            call_kwargs["task_input"] = task_input
        if memory_mbytes is not None:
            call_kwargs["memory_mbytes"] = memory_mbytes

        task_run = self.client.task(task_id).call(**call_kwargs)
        if task_run is None:
            raise RuntimeError(f"Task {task_id} returned no run data (possible wait timeout).")
        _check_run_status(task_run, f"Task {task_id}")

        return {
            "run_id": task_run.get("id"),
            "status": task_run.get("status"),
            "dataset_id": task_run.get("defaultDatasetId"),
            "started_at": task_run.get("startedAt"),
            "finished_at": task_run.get("finishedAt"),
        }

    def run_task_and_get_dataset(
        self,
        task_id: str,
        task_input: dict[str, Any] | None = None,
        timeout_secs: int = DEFAULT_TIMEOUT_SECS,
        memory_mbytes: int | None = None,
        dataset_items_limit: int = DEFAULT_DATASET_ITEMS_LIMIT,
        dataset_items_offset: int = 0,
    ) -> dict[str, Any]:
        """Run a task synchronously, then fetch its default dataset items."""
        _validate_positive(dataset_items_limit, "dataset_items_limit")
        _validate_non_negative(dataset_items_offset, "dataset_items_offset")

        run_metadata = self.run_task(
            task_id=task_id,
            task_input=task_input,
            timeout_secs=timeout_secs,
            memory_mbytes=memory_mbytes,
        )
        dataset_id = run_metadata["dataset_id"]
        if not dataset_id:
            raise RuntimeError(f"Task {task_id} run has no default dataset.")
        items = self.get_dataset_items(dataset_id=dataset_id, limit=dataset_items_limit, offset=dataset_items_offset)
        return {**run_metadata, "items": items}
