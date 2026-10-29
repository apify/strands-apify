"""Tests for the Apify core tools."""

import io
import json
from datetime import timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import impit
import pytest
from conftest import MOCK_FAILED_RUN, MOCK_TIMED_OUT_RUN
from rich.console import Console

from strands_apify import core as apify_core
from strands_apify.core import (
    apify_get_dataset_items,
    apify_run_actor,
    apify_run_actor_and_get_dataset,
    apify_run_task,
    apify_run_task_and_get_dataset,
    apify_scrape_url,
    apify_web_fetch,
)
from strands_apify.utils import (
    MAX_ITEMS,
    MAX_MEMORY_MBYTES,
    MAX_TIMEOUT_SECS,
    TRACKING_HEADER,
    WEB_FETCH_URL,
    ApifyToolClient,
)

MOCK_SCRAPED_ITEM = {
    "url": "https://example.com",
    "markdown": "# Example Domain\n\nThis domain is for use in illustrative examples.",
    "text": "Example Domain. This domain is for use in illustrative examples.",
}

MOCK_WEB_FETCH_BODY = {
    "url": "https://example.com",
    "fetch": {"loadedUrl": "https://example.com/", "httpStatusCode": 200, "contentType": "text/html; charset=utf-8"},
    "metadata": {"title": "Example Domain"},
    "markdown": "# Example Domain\n\nThis domain is for use in illustrative examples.",
}

# apify_scrape_url is deprecated; tests that call it for other reasons ignore its FutureWarning.
ignore_scrape_deprecation = pytest.mark.filterwarnings("ignore:apify_scrape_url is deprecated:FutureWarning")


def _web_fetch_response(status_code: int, body: Any) -> impit.Response:
    """Build a real impit response; `bytes` bodies are sent as-is, anything else as JSON."""
    content = body if isinstance(body, bytes) else json.dumps(body).encode()
    return impit.Response(status_code, content=content)


@pytest.fixture
def mock_impit_client():
    """Patch `impit.Client` and return the class mock; the `with` block yields `.return_value.__enter__`."""
    with patch("strands_apify.utils.impit.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.post.return_value = _web_fetch_response(200, MOCK_WEB_FETCH_BODY)
        yield client_cls


def _mock_post(client_cls: MagicMock) -> MagicMock:
    return client_cls.return_value.__enter__.return_value.post


def _make_apify_api_error(status_code: int, message: str) -> Exception:
    """Create an ApifyApiError through its real constructor from a fake HTTP response.

    The constructor dispatches on `response.status_code` to a status subclass (e.g. 401 -> `UnauthorizedError`) and
    reads the message from the JSON error body, so the fake response has to provide both.
    """
    from apify_client.errors import ApifyApiError

    response = MagicMock(status_code=status_code, text=message)
    response.json.return_value = {"error": {"type": "test-error", "message": message}}
    return ApifyApiError(response, attempt=1)


# --- Module import ---


def test_apify_core_module_is_importable():
    """Verify that the core module can be imported."""
    assert apify_core is not None
    assert apify_core.__name__ == "strands_apify.core"


# --- ApifyToolClient ---


def test_client_missing_token(monkeypatch):
    """ApifyToolClient raises ValueError when APIFY_TOKEN is not set."""
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    with pytest.raises(ValueError, match="APIFY_TOKEN"):
        ApifyToolClient()


def test_client_uses_env_token(mock_apify_env):
    """ApifyToolClient passes the env token to ApifyClient."""
    with patch("strands_apify.utils.ApifyClient") as MockClient:
        ApifyToolClient()
        MockClient.assert_called_once_with(
            "apify_api_test-token-12345",
            headers={"x-apify-integration-platform": "strands-agents"},
        )


# --- apify_run_actor ---


def test_run_actor_success(mock_apify_env, mock_apify_client):
    """Successful Actor run returns structured result with run metadata."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_run_actor(actor_id="actor/my-scraper", run_input={"url": "https://example.com"})

    assert result["status"] == "success"
    data = json.loads(result["content"][0]["text"])
    assert data["run_id"] == "run-HG7ml5fB1hCp8YEBA"
    assert data["status"] == "SUCCEEDED"
    assert data["dataset_id"] == "dataset-WkC9gct8rq1uR5vDZ"
    assert data["started_at"] == "2026-03-15T14:30:00+00:00"
    assert data["finished_at"] == "2026-03-15T14:35:22+00:00"
    mock_apify_client.actor.assert_called_once_with("actor/my-scraper")


def test_run_actor_default_input(mock_apify_env, mock_apify_client):
    """Actor run defaults run_input to empty dict when not provided."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_run_actor(actor_id="actor/my-scraper")

    assert result["status"] == "success"
    call_kwargs = mock_apify_client.actor.return_value.call.call_args.kwargs
    assert call_kwargs["run_input"] == {}


def test_run_actor_explicit_empty_input(mock_apify_env, mock_apify_client):
    """Actor run passes through an explicitly empty dict instead of treating it as falsy."""
    empty_input: dict = {}
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_run_actor(actor_id="actor/my-scraper", run_input=empty_input)

    assert result["status"] == "success"
    call_kwargs = mock_apify_client.actor.return_value.call.call_args.kwargs
    assert call_kwargs["run_input"] is empty_input


def test_run_actor_with_memory(mock_apify_env, mock_apify_client):
    """Actor run passes memory_mbytes when provided."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        apify_run_actor(actor_id="actor/my-scraper", memory_mbytes=512)

    call_kwargs = mock_apify_client.actor.return_value.call.call_args.kwargs
    assert call_kwargs["memory_mbytes"] == 512


def test_run_actor_passes_run_timeout(mock_apify_env, mock_apify_client):
    """Actor `timeout_secs` is forwarded to `.call()` as a `run_timeout` timedelta."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        apify_run_actor(actor_id="actor/my-scraper", timeout_secs=42)

    call_kwargs = mock_apify_client.actor.return_value.call.call_args.kwargs
    assert call_kwargs["run_timeout"] == timedelta(seconds=42)
    assert "timeout_secs" not in call_kwargs


def test_run_task_passes_run_timeout(mock_apify_env, mock_apify_client):
    """Task `timeout_secs` is forwarded to `.call()` as a `run_timeout` timedelta."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        apify_run_task(task_id="user/my-task", timeout_secs=42)

    call_kwargs = mock_apify_client.task.return_value.call.call_args.kwargs
    assert call_kwargs["run_timeout"] == timedelta(seconds=42)
    assert "timeout_secs" not in call_kwargs


@ignore_scrape_deprecation
def test_scrape_url_passes_run_timeout(mock_apify_env, mock_apify_client):
    """Scrape `timeout_secs` is forwarded to `.call()` as a `run_timeout` timedelta."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        apify_scrape_url(url="https://example.com", timeout_secs=42)

    call_kwargs = mock_apify_client.actor.return_value.call.call_args.kwargs
    assert call_kwargs["run_timeout"] == timedelta(seconds=42)
    assert "timeout_secs" not in call_kwargs


def test_run_actor_clamps_timeout_and_memory(mock_apify_env, mock_apify_client):
    """An oversized timeout reaches `.call()` capped, and memory is snapped to a power of 2."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_run_actor(actor_id="actor/my-scraper", timeout_secs=86400, memory_mbytes=12345)

    assert result["status"] == "success"
    call_kwargs = mock_apify_client.actor.return_value.call.call_args.kwargs
    assert call_kwargs["run_timeout"] == timedelta(seconds=MAX_TIMEOUT_SECS)
    assert call_kwargs["memory_mbytes"] == 16384


def test_run_task_clamps_timeout_and_memory(mock_apify_env, mock_apify_client):
    """Task runs get the same timeout and memory ceilings as Actor runs."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_run_task(task_id="user~my-task", timeout_secs=86400, memory_mbytes=100_000)

    assert result["status"] == "success"
    call_kwargs = mock_apify_client.task.return_value.call.call_args.kwargs
    assert call_kwargs["run_timeout"] == timedelta(seconds=MAX_TIMEOUT_SECS)
    assert call_kwargs["memory_mbytes"] == MAX_MEMORY_MBYTES


@ignore_scrape_deprecation
def test_scrape_url_clamps_timeout(mock_apify_env, mock_apify_client):
    """An oversized scrape timeout reaches `.call()` capped."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        apify_scrape_url(url="https://example.com", timeout_secs=86400)

    call_kwargs = mock_apify_client.actor.return_value.call.call_args.kwargs
    assert call_kwargs["run_timeout"] == timedelta(seconds=MAX_TIMEOUT_SECS)


def test_get_dataset_items_clamps_limit(mock_apify_env, mock_apify_client):
    """An oversized `limit` reaches `list_items()` capped."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        apify_get_dataset_items(dataset_id="dataset-123", limit=1_000_000)

    mock_apify_client.dataset.return_value.list_items.assert_called_once_with(limit=MAX_ITEMS, offset=0)


def test_run_actor_and_get_dataset_clamps_dataset_items_limit(mock_apify_env, mock_apify_client):
    """An oversized `dataset_items_limit` reaches `list_items()` capped after an Actor run."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        apify_run_actor_and_get_dataset(actor_id="actor/my-scraper", dataset_items_limit=1_000_000)

    mock_apify_client.dataset.return_value.list_items.assert_called_once_with(limit=MAX_ITEMS, offset=0)


def test_run_task_and_get_dataset_clamps_dataset_items_limit(mock_apify_env, mock_apify_client):
    """An oversized `dataset_items_limit` reaches `list_items()` capped after a task run."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        apify_run_task_and_get_dataset(task_id="user~my-task", dataset_items_limit=1_000_000)

    mock_apify_client.dataset.return_value.list_items.assert_called_once_with(limit=MAX_ITEMS, offset=0)


def test_timeout_ceiling_can_be_raised_from_the_environment(monkeypatch, mock_apify_env, mock_apify_client):
    """A developer can allow longer runs than the default ceiling."""
    monkeypatch.setenv("STRANDS_APIFY_MAX_TIMEOUT_SECS", "3600")

    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        apify_run_actor(actor_id="actor/my-scraper", timeout_secs=3600)

    call_kwargs = mock_apify_client.actor.return_value.call.call_args.kwargs
    assert call_kwargs["run_timeout"] == timedelta(seconds=3600)


def test_run_actor_failure(mock_apify_env, mock_apify_client):
    """Actor run returns error dict when Actor fails and surfaces Apify's statusMessage."""
    mock_apify_client.actor.return_value.call.return_value = MOCK_FAILED_RUN

    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_run_actor(actor_id="actor/my-scraper")

    assert result["status"] == "error"
    text = result["content"][0]["text"]
    assert "FAILED" in text
    # statusMessage from MOCK_FAILED_RUN must be propagated to the user-facing error
    assert "Actor failed with an error" in text


def test_run_actor_failure_without_status_message(mock_apify_env, mock_apify_client):
    """Failure error message still works when the Apify run omits statusMessage."""
    run_without_message = MOCK_FAILED_RUN.model_copy(update={"status_message": None})
    mock_apify_client.actor.return_value.call.return_value = run_without_message

    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_run_actor(actor_id="actor/my-scraper")

    assert result["status"] == "error"
    text = result["content"][0]["text"]
    assert "FAILED" in text
    assert "Run ID" in text
    assert "Message:" not in text


def test_run_actor_timeout(mock_apify_env, mock_apify_client):
    """Actor run returns error dict when Actor times out."""
    mock_apify_client.actor.return_value.call.return_value = MOCK_TIMED_OUT_RUN

    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_run_actor(actor_id="actor/my-scraper")

    assert result["status"] == "error"
    assert "TIMED-OUT" in result["content"][0]["text"]


def test_run_actor_api_exception(mock_apify_env, mock_apify_client):
    """Actor run returns error dict on API exceptions."""
    mock_apify_client.actor.return_value.call.side_effect = Exception("Connection failed")

    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_run_actor(actor_id="actor/my-scraper")

    assert result["status"] == "error"
    assert "Connection failed" in result["content"][0]["text"]


def test_run_actor_none_response(mock_apify_env, mock_apify_client):
    """Actor run returns error dict when ActorClient.call() returns None."""
    mock_apify_client.actor.return_value.call.return_value = None

    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_run_actor(actor_id="actor/my-scraper")

    assert result["status"] == "error"
    assert "no run data" in result["content"][0]["text"]


def test_run_actor_apify_api_error_401(mock_apify_env, mock_apify_client):
    """Actor run returns friendly message for 401 authentication errors."""
    error = _make_apify_api_error(401, "Unauthorized")
    mock_apify_client.actor.return_value.call.side_effect = error

    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_run_actor(actor_id="actor/my-scraper")

    assert result["status"] == "error"
    assert "Authentication failed" in result["content"][0]["text"]


def test_run_actor_apify_api_error_404(mock_apify_env, mock_apify_client):
    """Actor run returns friendly message for 404 not-found errors."""
    error = _make_apify_api_error(404, "Actor not found")
    mock_apify_client.actor.return_value.call.side_effect = error

    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_run_actor(actor_id="actor/nonexistent")

    assert result["status"] == "error"
    assert "Resource not found" in result["content"][0]["text"]


# --- apify_get_dataset_items ---


def test_get_dataset_items_success(mock_apify_env, mock_apify_client):
    """Successful dataset retrieval returns structured result with items."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_get_dataset_items(dataset_id="dataset-WkC9gct8rq1uR5vDZ")

    assert result["status"] == "success"
    items = json.loads(result["content"][0]["text"])
    assert len(items) == 3
    assert items[0]["title"] == "Widget A"
    assert items[2]["currency"] == "EUR"
    mock_apify_client.dataset.assert_called_once_with("dataset-WkC9gct8rq1uR5vDZ")


def test_get_dataset_items_with_pagination(mock_apify_env, mock_apify_client):
    """dataset retrieval passes limit and offset."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        apify_get_dataset_items(dataset_id="dataset-xyz", limit=50, offset=10)

    mock_apify_client.dataset.return_value.list_items.assert_called_once_with(limit=50, offset=10)


def test_get_dataset_items_empty(mock_apify_env, mock_apify_client):
    """Empty dataset returns a structured result with empty JSON array."""
    mock_list_result = MagicMock()
    mock_list_result.items = []
    mock_apify_client.dataset.return_value.list_items.return_value = mock_list_result

    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_get_dataset_items(dataset_id="dataset-empty")

    assert result["status"] == "success"
    items = json.loads(result["content"][0]["text"])
    assert items == []


# --- apify_run_actor_and_get_dataset ---


def test_run_actor_and_get_dataset_success(mock_apify_env, mock_apify_client):
    """Combined run + dataset fetch returns structured result with metadata and items."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_run_actor_and_get_dataset(
            actor_id="actor/my-scraper",
            run_input={"url": "https://example.com"},
            dataset_items_limit=50,
        )

    assert result["status"] == "success"
    data = json.loads(result["content"][0]["text"])
    assert data["run_id"] == "run-HG7ml5fB1hCp8YEBA"
    assert data["status"] == "SUCCEEDED"
    assert data["dataset_id"] == "dataset-WkC9gct8rq1uR5vDZ"
    assert len(data["items"]) == 3
    assert data["items"][0]["title"] == "Widget A"


def test_run_actor_and_get_dataset_actor_failure(mock_apify_env, mock_apify_client):
    """Combined tool returns error dict when the Actor fails."""
    mock_apify_client.actor.return_value.call.return_value = MOCK_FAILED_RUN

    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_run_actor_and_get_dataset(actor_id="actor/my-scraper")

    assert result["status"] == "error"
    assert "FAILED" in result["content"][0]["text"]


# --- apify_run_task ---


def test_run_task_success(mock_apify_env, mock_apify_client):
    """Successful task run returns structured result with run metadata."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_run_task(task_id="user~my-task", task_input={"query": "test"})

    assert result["status"] == "success"
    data = json.loads(result["content"][0]["text"])
    assert data["run_id"] == "run-HG7ml5fB1hCp8YEBA"
    assert data["status"] == "SUCCEEDED"
    assert data["dataset_id"] == "dataset-WkC9gct8rq1uR5vDZ"
    mock_apify_client.task.assert_called_once_with("user~my-task")


def test_run_task_no_input(mock_apify_env, mock_apify_client):
    """task run omits task_input kwarg when not provided."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_run_task(task_id="user~my-task")

    assert result["status"] == "success"
    call_kwargs = mock_apify_client.task.return_value.call.call_args.kwargs
    assert "task_input" not in call_kwargs


def test_run_task_with_memory(mock_apify_env, mock_apify_client):
    """task run passes memory_mbytes when provided."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        apify_run_task(task_id="user~my-task", memory_mbytes=1024)

    call_kwargs = mock_apify_client.task.return_value.call.call_args.kwargs
    assert call_kwargs["memory_mbytes"] == 1024


def test_run_task_failure(mock_apify_env, mock_apify_client):
    """task run returns error dict when task fails."""
    mock_apify_client.task.return_value.call.return_value = MOCK_FAILED_RUN

    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_run_task(task_id="user~my-task")

    assert result["status"] == "error"
    assert "FAILED" in result["content"][0]["text"]


def test_run_task_none_response(mock_apify_env, mock_apify_client):
    """task run returns error dict when TaskClient.call() returns None."""
    mock_apify_client.task.return_value.call.return_value = None

    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_run_task(task_id="user~my-task")

    assert result["status"] == "error"
    assert "no run data" in result["content"][0]["text"]


def test_run_task_apify_api_error_401(mock_apify_env, mock_apify_client):
    """task run returns friendly message for 401 authentication errors."""
    error = _make_apify_api_error(401, "Unauthorized")
    mock_apify_client.task.return_value.call.side_effect = error

    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_run_task(task_id="user~my-task")

    assert result["status"] == "error"
    assert "Authentication failed" in result["content"][0]["text"]


# --- apify_run_task_and_get_dataset ---


def test_run_task_and_get_dataset_success(mock_apify_env, mock_apify_client):
    """Combined task run + dataset fetch returns structured result with metadata and items."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_run_task_and_get_dataset(
            task_id="user~my-task",
            task_input={"query": "test"},
            dataset_items_limit=50,
        )

    assert result["status"] == "success"
    data = json.loads(result["content"][0]["text"])
    assert data["run_id"] == "run-HG7ml5fB1hCp8YEBA"
    assert len(data["items"]) == 3
    assert data["items"][0]["title"] == "Widget A"


def test_run_task_and_get_dataset_task_failure(mock_apify_env, mock_apify_client):
    """Combined task tool returns error dict when the task fails."""
    mock_apify_client.task.return_value.call.return_value = MOCK_FAILED_RUN

    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_run_task_and_get_dataset(task_id="user~my-task")

    assert result["status"] == "error"
    assert "FAILED" in result["content"][0]["text"]


# --- apify_web_fetch ---


def test_web_fetch_success(mock_apify_env, mock_impit_client):
    """apify_web_fetch posts to the standby endpoint and returns the requested format with metadata."""
    result = apify_web_fetch(url="https://example.com")

    assert result["status"] == "success"
    data = json.loads(result["content"][0]["text"])
    assert data == {
        "url": "https://example.com",
        "final_url": "https://example.com/",
        "title": "Example Domain",
        "http_status": 200,
        "markdown": MOCK_WEB_FETCH_BODY["markdown"],
    }

    post_kwargs = _mock_post(mock_impit_client).call_args.kwargs
    assert _mock_post(mock_impit_client).call_args.args == (WEB_FETCH_URL,)
    assert json.loads(post_kwargs["content"]) == {"url": "https://example.com", "formats": ["markdown"]}
    assert post_kwargs["headers"] == {
        **TRACKING_HEADER,
        "Authorization": "Bearer apify_api_test-token-12345",
        "Content-Type": "application/json",
    }
    mock_impit_client.assert_called_once_with(timeout=180)
    mock_impit_client.return_value.__exit__.assert_called_once()


def test_web_fetch_passes_options(mock_apify_env, mock_impit_client):
    """Formats, target headers, `wait_ms` and `timeout_secs` reach the request; target headers stay in the body."""
    _mock_post(mock_impit_client).return_value = _web_fetch_response(
        200, {**MOCK_WEB_FETCH_BODY, "text": "Example Domain", "links": []}
    )

    result = apify_web_fetch(
        url="https://example.com",
        formats=["text", "links"],
        headers={"Accept-Language": "fr-FR"},
        wait_ms=500,
        timeout_secs=42,
    )

    assert result["status"] == "success"
    data = json.loads(result["content"][0]["text"])
    assert data["text"] == "Example Domain"
    assert data["links"] == []
    assert "markdown" not in data

    mock_impit_client.assert_called_once_with(timeout=42)
    post_kwargs = _mock_post(mock_impit_client).call_args.kwargs
    assert json.loads(post_kwargs["content"]) == {
        "url": "https://example.com",
        "formats": ["text", "links"],
        "headers": {"Accept-Language": "fr-FR"},
        "wait": 500,
    }
    assert "Accept-Language" not in post_kwargs["headers"]


def test_web_fetch_empty_formats_defaults_to_markdown(mock_apify_env, mock_impit_client):
    """An empty `formats` list falls back to markdown instead of letting the Actor auto-select a format."""
    result = apify_web_fetch(url="https://example.com", formats=[])

    assert result["status"] == "success"
    assert json.loads(result["content"][0]["text"])["markdown"] == MOCK_WEB_FETCH_BODY["markdown"]
    assert json.loads(_mock_post(mock_impit_client).call_args.kwargs["content"])["formats"] == ["markdown"]


def test_web_fetch_target_http_error_returns_content(mock_apify_env, mock_impit_client):
    """A target 4xx arrives as a 200 from Web Fetch; the tool succeeds and reports the page's own status."""
    _mock_post(mock_impit_client).return_value = _web_fetch_response(
        200,
        {
            "fetch": {"loadedUrl": "https://example.com/missing", "httpStatusCode": 404},
            "metadata": {"title": "Page not found"},
            "markdown": "# Page not found",
        },
    )

    result = apify_web_fetch(url="https://example.com/missing")

    assert result["status"] == "success"
    data = json.loads(result["content"][0]["text"])
    assert data["http_status"] == 404
    assert data["markdown"] == "# Page not found"


def test_web_fetch_without_fetch_metadata(mock_apify_env, mock_impit_client):
    """Without `fetch` and `metadata`, the requested URL is reported and status and title are null."""
    _mock_post(mock_impit_client).return_value = _web_fetch_response(200, {"markdown": "# Example"})

    result = apify_web_fetch(url="https://example.com")

    assert result["status"] == "success"
    data = json.loads(result["content"][0]["text"])
    assert data["final_url"] == "https://example.com"
    assert data["http_status"] is None
    assert data["title"] is None
    assert data["markdown"] == "# Example"


def test_web_fetch_actor_error(mock_apify_env, mock_impit_client):
    """An Actor error (`{"error": str, "code": str}`) is reported with its status and code."""
    _mock_post(mock_impit_client).return_value = _web_fetch_response(
        502, {"error": 'Failed to fetch "https://example.com".', "code": "UPSTREAM_FETCH_ERROR"}
    )

    result = apify_web_fetch(url="https://example.com")

    assert result["status"] == "error"
    text = result["content"][0]["text"]
    assert "status 502" in text
    assert "Failed to fetch" in text
    assert "UPSTREAM_FETCH_ERROR" in text


def test_web_fetch_actor_error_without_code(mock_apify_env, mock_impit_client):
    """An Actor error without `code` is reported with its message only."""
    _mock_post(mock_impit_client).return_value = _web_fetch_response(400, {"error": "Invalid input."})

    result = apify_web_fetch(url="https://example.com")

    assert result["status"] == "error"
    assert result["content"][0]["text"] == "Web Fetch failed with status 400: Invalid input."


def test_web_fetch_error_without_message(mock_apify_env, mock_impit_client):
    """An error body without an `error` field reports only the HTTP status."""
    _mock_post(mock_impit_client).return_value = _web_fetch_response(400, {})

    result = apify_web_fetch(url="https://example.com")

    assert result["status"] == "error"
    assert result["content"][0]["text"] == "Web Fetch failed with status 400"


def test_web_fetch_gateway_error(mock_apify_env, mock_impit_client):
    """A standby gateway error (`{"error": {"type", "message"}}`) is reported with its message."""
    _mock_post(mock_impit_client).return_value = _web_fetch_response(
        401, {"error": {"type": "api-token-missing", "message": "You need to pass your Apify API token."}}
    )

    result = apify_web_fetch(url="https://example.com")

    assert result["status"] == "error"
    assert "status 401: You need to pass your Apify API token." in result["content"][0]["text"]


def test_web_fetch_non_json_error_page(mock_apify_env, mock_impit_client):
    """A gateway error page that is not JSON still reports the HTTP status."""
    _mock_post(mock_impit_client).return_value = _web_fetch_response(502, b"<html>Bad Gateway</html>")

    result = apify_web_fetch(url="https://example.com")

    assert result["status"] == "error"
    assert result["content"][0]["text"] == "Web Fetch failed with status 502"


def test_web_fetch_invalid_json_success_body(mock_apify_env, mock_impit_client):
    """A 200 response that is not JSON is an error, not a crash."""
    _mock_post(mock_impit_client).return_value = _web_fetch_response(200, b"not json")

    result = apify_web_fetch(url="https://example.com")

    assert result["status"] == "error"
    assert "not valid JSON" in result["content"][0]["text"]


def test_web_fetch_non_object_success_body(mock_apify_env, mock_impit_client):
    """A 200 response whose JSON is not an object is an error."""
    _mock_post(mock_impit_client).return_value = _web_fetch_response(200, ["unexpected"])

    result = apify_web_fetch(url="https://example.com")

    assert result["status"] == "error"
    assert "unexpected response body" in result["content"][0]["text"]


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (
            impit.ConnectError("Failed to connect to the server.\nReason: hyper_util::client::legacy::Error(...)"),
            "Failed to connect to the server.",
        ),
        (impit.ReadTimeout("Request timeout (180000 ms) exceeded."), "Request timeout (180000 ms) exceeded."),
        (impit.ConnectError(""), ""),
    ],
)
def test_web_fetch_transport_error(mock_apify_env, mock_impit_client, error, reason):
    """A transport failure reports only the readable first line of the impit error, even when it is empty."""
    _mock_post(mock_impit_client).side_effect = error

    result = apify_web_fetch(url="https://example.com")

    assert result["status"] == "error"
    assert result["content"][0]["text"] == f"Request to Web Fetch at {WEB_FETCH_URL} failed: {reason}"


def test_web_fetch_panel_escapes_page_markup(mock_apify_env, mock_impit_client):
    """A page title with Rich markup is shown literally instead of failing the fetch."""
    _mock_post(mock_impit_client).return_value = _web_fetch_response(
        200, {**MOCK_WEB_FETCH_BODY, "metadata": {"title": "[/b] Closing tag"}}
    )
    output = io.StringIO()

    with (
        patch("strands_apify.utils._panels_enabled", return_value=True),
        patch("strands_apify.utils.console", Console(file=output, width=200)),
    ):
        result = apify_web_fetch(url="https://example.com")

    assert result["status"] == "success"
    assert "[/b] Closing tag" in output.getvalue()


def test_web_fetch_invalid_url(mock_apify_env, mock_impit_client):
    """An invalid URL fails before any request is sent."""
    result = apify_web_fetch(url="ftp://example.com")

    assert result["status"] == "error"
    assert "Invalid URL scheme" in result["content"][0]["text"]
    _mock_post(mock_impit_client).assert_not_called()


def test_web_fetch_zero_timeout(mock_apify_env, mock_impit_client):
    """A non-positive `timeout_secs` fails before any request is sent."""
    result = apify_web_fetch(url="https://example.com", timeout_secs=0)

    assert result["status"] == "error"
    assert "timeout_secs" in result["content"][0]["text"]
    _mock_post(mock_impit_client).assert_not_called()


# --- apify_scrape_url ---


def test_scrape_url_deprecation_warning(mock_apify_env, mock_apify_client):
    """apify_scrape_url still works but warns and points to apify_web_fetch."""
    mock_list_result = MagicMock()
    mock_list_result.items = [MOCK_SCRAPED_ITEM]
    mock_apify_client.dataset.return_value.list_items.return_value = mock_list_result

    with (
        patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client),
        pytest.warns(FutureWarning, match="apify_web_fetch") as record,
    ):
        result = apify_scrape_url(url="https://example.com")

    assert result["status"] == "success"
    assert record[0].filename == __file__, "the warning should point at the caller, not at strands internals"


def test_scrape_url_is_left_out_of_the_presets():
    """Agents built from a preset only get apify_web_fetch; the deprecated tool is still importable."""
    import strands_apify

    assert apify_web_fetch in strands_apify.APIFY_CORE_TOOLS
    assert apify_scrape_url not in strands_apify.APIFY_CORE_TOOLS
    assert apify_scrape_url not in strands_apify.APIFY_ALL_TOOLS
    assert strands_apify.apify_scrape_url is apify_scrape_url


@ignore_scrape_deprecation
def test_scrape_url_success(mock_apify_env, mock_apify_client):
    """Scrape URL returns structured result with markdown content."""
    mock_list_result = MagicMock()
    mock_list_result.items = [MOCK_SCRAPED_ITEM]
    mock_apify_client.dataset.return_value.list_items.return_value = mock_list_result

    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_scrape_url(url="https://example.com")

    assert result["status"] == "success"
    assert "Example Domain" in result["content"][0]["text"]
    mock_apify_client.actor.assert_called_once_with("apify/website-content-crawler")


@ignore_scrape_deprecation
def test_scrape_url_none_response(mock_apify_env, mock_apify_client):
    """Scrape URL returns error dict when ActorClient.call() returns None."""
    mock_apify_client.actor.return_value.call.return_value = None

    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_scrape_url(url="https://example.com")

    assert result["status"] == "error"
    assert "no run data" in result["content"][0]["text"]


@ignore_scrape_deprecation
def test_scrape_url_no_content(mock_apify_env, mock_apify_client):
    """Scrape URL returns error dict when no content is returned."""
    mock_list_result = MagicMock()
    mock_list_result.items = []
    mock_apify_client.dataset.return_value.list_items.return_value = mock_list_result

    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_scrape_url(url="https://example.com")

    assert result["status"] == "error"
    assert "No content returned" in result["content"][0]["text"]


@ignore_scrape_deprecation
def test_scrape_url_crawler_failure(mock_apify_env, mock_apify_client):
    """Scrape URL returns error dict when the crawler Actor fails."""
    mock_apify_client.actor.return_value.call.return_value = MOCK_FAILED_RUN

    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_scrape_url(url="https://example.com")

    assert result["status"] == "error"
    assert "FAILED" in result["content"][0]["text"]


@ignore_scrape_deprecation
def test_scrape_url_falls_back_to_text(mock_apify_env, mock_apify_client):
    """Scrape URL falls back to text field when markdown is absent."""
    item_without_markdown = {"url": "https://example.com", "text": "Plain text content"}
    mock_list_result = MagicMock()
    mock_list_result.items = [item_without_markdown]
    mock_apify_client.dataset.return_value.list_items.return_value = mock_list_result

    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_scrape_url(url="https://example.com")

    assert result["status"] == "success"
    assert result["content"][0]["text"] == "Plain text content"


@ignore_scrape_deprecation
def test_scrape_url_invalid_url_scheme(mock_apify_env):
    """apify_scrape_url returns error for invalid URL scheme."""
    result = apify_scrape_url(url="ftp://example.com")

    assert result["status"] == "error"
    assert "Invalid URL scheme" in result["content"][0]["text"]


@ignore_scrape_deprecation
def test_scrape_url_missing_scheme(mock_apify_env):
    """apify_scrape_url returns error for URL without http/https scheme."""
    result = apify_scrape_url(url="example.com")

    assert result["status"] == "error"
    assert "Invalid URL scheme" in result["content"][0]["text"]


# --- Parameter validation ---


def test_run_actor_empty_actor_id(mock_apify_env):
    """apify_run_actor returns error for whitespace-only actor_id."""
    result = apify_run_actor(actor_id="   ")

    assert result["status"] == "error"
    assert "actor_id" in result["content"][0]["text"]


def test_run_actor_zero_timeout(mock_apify_env):
    """apify_run_actor returns error for non-positive timeout_secs."""
    result = apify_run_actor(actor_id="actor/valid", timeout_secs=0)

    assert result["status"] == "error"
    assert "timeout_secs" in result["content"][0]["text"]


def test_run_actor_negative_timeout(mock_apify_env):
    """apify_run_actor returns error for negative timeout_secs."""
    result = apify_run_actor(actor_id="actor/valid", timeout_secs=-5)

    assert result["status"] == "error"
    assert "timeout_secs" in result["content"][0]["text"]


def test_run_actor_zero_memory(mock_apify_env):
    """apify_run_actor returns error for non-positive memory_mbytes."""
    result = apify_run_actor(actor_id="actor/valid", memory_mbytes=0)

    assert result["status"] == "error"
    assert "memory_mbytes" in result["content"][0]["text"]


def test_run_task_empty_task_id(mock_apify_env):
    """apify_run_task returns error for whitespace-only task_id."""
    result = apify_run_task(task_id="  ")

    assert result["status"] == "error"
    assert "task_id" in result["content"][0]["text"]


def test_run_task_zero_timeout(mock_apify_env):
    """apify_run_task returns error for non-positive timeout_secs."""
    result = apify_run_task(task_id="user~my-task", timeout_secs=0)

    assert result["status"] == "error"
    assert "timeout_secs" in result["content"][0]["text"]


def test_run_task_zero_memory(mock_apify_env):
    """apify_run_task returns error for non-positive memory_mbytes."""
    result = apify_run_task(task_id="user~my-task", memory_mbytes=0)

    assert result["status"] == "error"
    assert "memory_mbytes" in result["content"][0]["text"]


def test_get_dataset_items_empty_dataset_id(mock_apify_env):
    """apify_get_dataset_items returns error for whitespace-only dataset_id."""
    result = apify_get_dataset_items(dataset_id="  ")

    assert result["status"] == "error"
    assert "dataset_id" in result["content"][0]["text"]


def test_get_dataset_items_zero_limit(mock_apify_env):
    """apify_get_dataset_items returns error for non-positive limit."""
    result = apify_get_dataset_items(dataset_id="dataset-abc", limit=0)

    assert result["status"] == "error"
    assert "limit" in result["content"][0]["text"]


def test_get_dataset_items_negative_offset(mock_apify_env):
    """apify_get_dataset_items returns error for negative offset."""
    result = apify_get_dataset_items(dataset_id="dataset-abc", offset=-1)

    assert result["status"] == "error"
    assert "offset" in result["content"][0]["text"]


def test_run_actor_and_get_dataset_zero_dataset_limit(mock_apify_env):
    """apify_run_actor_and_get_dataset returns error for non-positive dataset_items_limit."""
    result = apify_run_actor_and_get_dataset(actor_id="actor/valid", dataset_items_limit=0)

    assert result["status"] == "error"
    assert "dataset_items_limit" in result["content"][0]["text"]


def test_run_actor_and_get_dataset_negative_dataset_offset(mock_apify_env):
    """apify_run_actor_and_get_dataset returns error for negative dataset_items_offset."""
    result = apify_run_actor_and_get_dataset(actor_id="actor/valid", dataset_items_offset=-1)

    assert result["status"] == "error"
    assert "dataset_items_offset" in result["content"][0]["text"]


def test_run_task_and_get_dataset_zero_dataset_limit(mock_apify_env):
    """apify_run_task_and_get_dataset returns error for non-positive dataset_items_limit."""
    result = apify_run_task_and_get_dataset(task_id="user~my-task", dataset_items_limit=0)

    assert result["status"] == "error"
    assert "dataset_items_limit" in result["content"][0]["text"]


def test_run_task_and_get_dataset_negative_dataset_offset(mock_apify_env):
    """apify_run_task_and_get_dataset returns error for negative dataset_items_offset."""
    result = apify_run_task_and_get_dataset(task_id="user~my-task", dataset_items_offset=-1)

    assert result["status"] == "error"
    assert "dataset_items_offset" in result["content"][0]["text"]


@ignore_scrape_deprecation
def test_scrape_url_zero_timeout(mock_apify_env):
    """apify_scrape_url returns error for non-positive timeout_secs."""
    result = apify_scrape_url(url="https://example.com", timeout_secs=0)

    assert result["status"] == "error"
    assert "timeout_secs" in result["content"][0]["text"]


@ignore_scrape_deprecation
def test_scrape_url_invalid_crawler_type(mock_apify_env):
    """apify_scrape_url returns error for unsupported crawler_type."""
    result = apify_scrape_url(url="https://example.com", crawler_type="invalid")

    assert result["status"] == "error"
    assert "crawler_type" in result["content"][0]["text"]


@ignore_scrape_deprecation
def test_scrape_url_missing_domain(mock_apify_env):
    """apify_scrape_url returns error for URL with no domain."""
    result = apify_scrape_url(url="https://")

    assert result["status"] == "error"
    assert "domain" in result["content"][0]["text"].lower()


# --- Dependency guard ---


def test_missing_apify_client_run_actor(mock_apify_env):
    """apify_run_actor returns error dict when apify-client is not installed."""
    with patch("strands_apify.utils.HAS_APIFY_CLIENT", False):
        result = apify_run_actor(actor_id="test/actor")

    assert result["status"] == "error"
    assert "apify-client" in result["content"][0]["text"]


def test_missing_apify_client_get_dataset(mock_apify_env):
    """apify_get_dataset_items returns error dict when apify-client is not installed."""
    with patch("strands_apify.utils.HAS_APIFY_CLIENT", False):
        result = apify_get_dataset_items(dataset_id="dataset-123")

    assert result["status"] == "error"
    assert "apify-client" in result["content"][0]["text"]


def test_missing_apify_client_run_and_get(mock_apify_env):
    """apify_run_actor_and_get_dataset returns error dict when apify-client is not installed."""
    with patch("strands_apify.utils.HAS_APIFY_CLIENT", False):
        result = apify_run_actor_and_get_dataset(actor_id="test/actor")

    assert result["status"] == "error"
    assert "apify-client" in result["content"][0]["text"]


def test_missing_apify_client_run_task(mock_apify_env):
    """apify_run_task returns error dict when apify-client is not installed."""
    with patch("strands_apify.utils.HAS_APIFY_CLIENT", False):
        result = apify_run_task(task_id="user~my-task")

    assert result["status"] == "error"
    assert "apify-client" in result["content"][0]["text"]


def test_missing_apify_client_run_task_and_get(mock_apify_env):
    """apify_run_task_and_get_dataset returns error dict when apify-client is not installed."""
    with patch("strands_apify.utils.HAS_APIFY_CLIENT", False):
        result = apify_run_task_and_get_dataset(task_id="user~my-task")

    assert result["status"] == "error"
    assert "apify-client" in result["content"][0]["text"]


def test_missing_apify_client_web_fetch(mock_apify_env, mock_impit_client):
    """apify_web_fetch returns error dict when apify-client is not installed."""
    with patch("strands_apify.utils.HAS_APIFY_CLIENT", False):
        result = apify_web_fetch(url="https://example.com")

    assert result["status"] == "error"
    assert "apify-client" in result["content"][0]["text"]
    _mock_post(mock_impit_client).assert_not_called()


@ignore_scrape_deprecation
def test_missing_apify_client_scrape_url(mock_apify_env):
    """apify_scrape_url returns error dict when apify-client is not installed."""
    with patch("strands_apify.utils.HAS_APIFY_CLIENT", False):
        result = apify_scrape_url(url="https://example.com")

    assert result["status"] == "error"
    assert "apify-client" in result["content"][0]["text"]


# --- Missing token from tool entry points ---


def test_run_actor_missing_token(monkeypatch):
    """apify_run_actor returns error dict when APIFY_TOKEN is missing."""
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    result = apify_run_actor(actor_id="test/actor")

    assert result["status"] == "error"
    assert "APIFY_TOKEN" in result["content"][0]["text"]


def test_get_dataset_items_missing_token(monkeypatch):
    """apify_get_dataset_items returns error dict when APIFY_TOKEN is missing."""
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    result = apify_get_dataset_items(dataset_id="dataset-123")

    assert result["status"] == "error"
    assert "APIFY_TOKEN" in result["content"][0]["text"]


def test_run_actor_and_get_dataset_missing_token(monkeypatch):
    """apify_run_actor_and_get_dataset returns error dict when APIFY_TOKEN is missing."""
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    result = apify_run_actor_and_get_dataset(actor_id="test/actor")

    assert result["status"] == "error"
    assert "APIFY_TOKEN" in result["content"][0]["text"]


def test_run_task_missing_token(monkeypatch):
    """apify_run_task returns error dict when APIFY_TOKEN is missing."""
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    result = apify_run_task(task_id="user~my-task")

    assert result["status"] == "error"
    assert "APIFY_TOKEN" in result["content"][0]["text"]


def test_run_task_and_get_dataset_missing_token(monkeypatch):
    """apify_run_task_and_get_dataset returns error dict when APIFY_TOKEN is missing."""
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    result = apify_run_task_and_get_dataset(task_id="user~my-task")

    assert result["status"] == "error"
    assert "APIFY_TOKEN" in result["content"][0]["text"]


def test_web_fetch_missing_token(monkeypatch, mock_impit_client):
    """apify_web_fetch returns error dict when APIFY_TOKEN is missing."""
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    result = apify_web_fetch(url="https://example.com")

    assert result["status"] == "error"
    assert "APIFY_TOKEN" in result["content"][0]["text"]
    _mock_post(mock_impit_client).assert_not_called()


@ignore_scrape_deprecation
def test_scrape_url_missing_token(monkeypatch):
    """apify_scrape_url returns error dict when APIFY_TOKEN is missing."""
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    result = apify_scrape_url(url="https://example.com")

    assert result["status"] == "error"
    assert "APIFY_TOKEN" in result["content"][0]["text"]
