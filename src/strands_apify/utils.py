"""Shared infrastructure for Apify tools: client wrapper, error formatting, validators."""

import json
import logging
import os
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Literal, get_args
from urllib.parse import urlparse

import impit
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

if TYPE_CHECKING:
    # apify-client 3.x exports its response models only from this private module.
    from apify_client._models import Run

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

TRACKING_HEADER = {"x-apify-integration-platform": "strands-agents"}
ERROR_PANEL_TITLE = "[bold red]Apify Error[/bold red]"
DEFAULT_TIMEOUT_SECS = 300
DEFAULT_SCRAPE_TIMEOUT_SECS = 120
DEFAULT_DATASET_ITEMS_LIMIT = 100

# Ceilings for numeric values the LLM supplies. Each can be overridden with the matching STRANDS_APIFY_MAX_*
# environment variable, read on every call. Memory can only be lowered: 32768 MB is the platform's maximum.
MAX_TIMEOUT_SECS = 600
MAX_MEMORY_MBYTES = 32768
MAX_ITEMS = 1000
MAX_CRAWL_DEPTH = 5

MIN_MEMORY_MBYTES = 128

WEBSITE_CONTENT_CRAWLER = "apify/website-content-crawler"
CrawlerType = Literal["playwright:adaptive", "playwright:firefox", "cheerio"]
WEBSITE_CONTENT_CRAWLER_TYPES = get_args(CrawlerType)

WEB_FETCH_URL = "https://web-fetch.apify.actor/"
WebFetchFormat = Literal["markdown", "html", "text", "links", "raw"]
DEFAULT_WEB_FETCH_TIMEOUT_SECS = 180
HTTP_ERROR_STATUS = 400


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


def _check_run_status(actor_run: "Run", label: str) -> None:
    """Raise RuntimeError if the Actor run did not succeed.

    Includes the run's `status_message` in the error when present so callers can see why a run failed without having
    to look up the run in the Apify Console.
    """
    status = actor_run.status
    if status == "SUCCEEDED":
        return
    status_msg = actor_run.status_message
    parts = [f"{label} finished with status {status}", f"Run ID: {actor_run.id}"]
    if status_msg:
        parts.append(f"Message: {status_msg}")
    raise RuntimeError(". ".join(parts))


def _ceiling(env_var: str, default: int) -> int:
    """Return the ceiling set in `env_var`, or `default` when it is unset or not a positive integer."""
    raw = os.getenv(env_var, "")
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        value = 0
    if value <= 0:
        logger.warning("Ignoring %s=%r, expected a positive integer. Using %d.", env_var, raw, default)
        return default
    return value


# The clamps only cap the upper end. Zero and negative values pass through, so the validators reject them.
def _clamp_timeout(value: int) -> int:
    return min(value, _ceiling("STRANDS_APIFY_MAX_TIMEOUT_SECS", MAX_TIMEOUT_SECS))


def _clamp_items(value: int) -> int:
    return min(value, _ceiling("STRANDS_APIFY_MAX_ITEMS", MAX_ITEMS))


def _clamp_depth(value: int) -> int:
    return min(value, _ceiling("STRANDS_APIFY_MAX_CRAWL_DEPTH", MAX_CRAWL_DEPTH))


def _clamp_memory(value: int) -> int:
    """Clamp memory to the platform minimum and the ceiling, then snap it to the power of 2 the platform requires.

    Rounds up, unless that would exceed the ceiling. A ceiling below the platform minimum yields the minimum. Zero and
    negative values pass through for the validators, like in the other clamps.
    """
    if value <= 0:
        return value
    ceiling = min(_ceiling("STRANDS_APIFY_MAX_MEMORY_MBYTES", MAX_MEMORY_MBYTES), MAX_MEMORY_MBYTES)
    clamped = max(MIN_MEMORY_MBYTES, min(value, ceiling))
    power = 1 << (clamped - 1).bit_length()
    if power > ceiling:
        power = 1 << (ceiling.bit_length() - 1)
    return max(power, MIN_MEMORY_MBYTES)


def _web_fetch_error_message(response: impit.Response) -> str:
    """Build an error message from a failed Web Fetch response in standby mode.

    The Actor reports its own errors as `{"error": str, "code": str}`, the standby gateway as
    `{"error": {"type": str, "message": str}}`. A gateway error page may not be JSON at all.
    """
    message = f"Web Fetch failed with status {response.status_code}"
    try:
        body = response.json()
    except (ValueError, impit.DecodingError):
        return message
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, str):
        code = body.get("code")
        return f"{message}: {error} (code: {code})" if isinstance(code, str) else f"{message}: {error}"
    if isinstance(error, dict) and isinstance(error.get("message"), str):
        return f"{message}: {error['message']}"
    return message


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
                "Get your token at https://console.apify.com/settings/integrations"
                "?utm_source=strands-agents&utm_medium=integrations"
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
            memory_mbytes = _clamp_memory(memory_mbytes)
        timeout_secs = _clamp_timeout(timeout_secs)

        call_kwargs: dict[str, Any] = {
            "run_input": run_input if run_input is not None else {},
            "run_timeout": timedelta(seconds=timeout_secs),
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
            "run_id": actor_run.id,
            "status": actor_run.status,
            "dataset_id": actor_run.default_dataset_id,
            "started_at": actor_run.started_at.isoformat(),
            "finished_at": actor_run.finished_at.isoformat() if actor_run.finished_at else None,
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
        limit = _clamp_items(limit)

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
        items = self.get_dataset_items(
            dataset_id=run_metadata["dataset_id"], limit=dataset_items_limit, offset=dataset_items_offset
        )
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
        timeout_secs = _clamp_timeout(timeout_secs)
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
            run_timeout=timedelta(seconds=timeout_secs),
            logger=None,
        )
        if actor_run is None:
            raise RuntimeError("Website Content Crawler returned no run data (possible wait timeout).")
        _check_run_status(actor_run, "Website Content Crawler")

        result = self.client.dataset(actor_run.default_dataset_id).list_items(limit=1)
        items = list(result.items)

        if not items:
            raise RuntimeError(f"No content returned for URL: {url}")

        return str(items[0].get("markdown") or items[0].get("text", ""))

    def web_fetch(
        self,
        url: str,
        formats: list[WebFetchFormat] | None = None,
        headers: dict[str, str] | None = None,
        wait_ms: int | None = None,
        timeout_secs: int = DEFAULT_WEB_FETCH_TIMEOUT_SECS,
    ) -> dict[str, Any]:
        """Fetch a single URL through the Web Fetch Actor in standby mode and return the requested formats.

        The Actor validates `formats` and `wait` itself and rejects bad values with a 400 that names the problem.
        """
        _validate_url(url)
        _validate_positive(timeout_secs, "timeout_secs")
        timeout_secs = _clamp_timeout(timeout_secs)
        # An empty list makes the Actor pick a format itself, which this method could not map back into the result.
        formats = formats or ["markdown"]

        request_body: dict[str, Any] = {"url": url, "formats": formats}
        if headers:
            request_body["headers"] = headers
        if wait_ms is not None:
            request_body["wait"] = wait_ms

        # Requests in standby mode bypass ApifyClient, so the tracking header has to be sent here explicitly.
        with impit.Client(timeout=timeout_secs) as client:
            try:
                response = client.post(
                    WEB_FETCH_URL,
                    content=json.dumps(request_body),
                    headers={
                        **TRACKING_HEADER,
                        "Authorization": f"Bearer {self.client.token}",
                        "Content-Type": "application/json",
                    },
                )
            except impit.TransportError as e:
                reason = str(e).partition("\n")[0]
                raise RuntimeError(f"Request to Web Fetch at {WEB_FETCH_URL} failed: {reason}") from e
            # Check the status before parsing: gateway error pages are not guaranteed to be JSON.
            if response.status_code >= HTTP_ERROR_STATUS:
                raise RuntimeError(_web_fetch_error_message(response))
            try:
                data = response.json()
            except (ValueError, impit.DecodingError) as e:
                raise RuntimeError("Web Fetch returned a response that is not valid JSON.") from e
        if not isinstance(data, dict):
            raise RuntimeError("Web Fetch returned an unexpected response body.")

        fetch = data.get("fetch") or {}
        metadata = data.get("metadata") or {}
        # The target page's own status. Error pages still carry content, so it is returned rather than raised.
        return {
            "url": url,
            "final_url": fetch.get("loadedUrl") or url,
            "title": metadata.get("title"),
            "http_status": fetch.get("httpStatusCode"),
            **{f: data.get(f) for f in formats},
        }

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
            memory_mbytes = _clamp_memory(memory_mbytes)
        timeout_secs = _clamp_timeout(timeout_secs)

        call_kwargs: dict[str, Any] = {"run_timeout": timedelta(seconds=timeout_secs)}
        if task_input is not None:
            call_kwargs["task_input"] = task_input
        if memory_mbytes is not None:
            call_kwargs["memory_mbytes"] = memory_mbytes

        task_run = self.client.task(task_id).call(**call_kwargs)
        if task_run is None:
            raise RuntimeError(f"Task {task_id} returned no run data (possible wait timeout).")
        _check_run_status(task_run, f"Task {task_id}")

        return {
            "run_id": task_run.id,
            "status": task_run.status,
            "dataset_id": task_run.default_dataset_id,
            "started_at": task_run.started_at.isoformat(),
            "finished_at": task_run.finished_at.isoformat() if task_run.finished_at else None,
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
        items = self.get_dataset_items(
            dataset_id=run_metadata["dataset_id"], limit=dataset_items_limit, offset=dataset_items_offset
        )
        return {**run_metadata, "items": items}
