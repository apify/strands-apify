"""Shared fixtures and mock payloads for strands-apify tests.

Pytest auto-discovers fixtures defined here, so every test module in this
directory can use ``mock_apify_client`` and ``mock_apify_env`` without an
explicit import. Mock payload constants (``MOCK_ACTOR_RUN`` etc.) are
imported explicitly by test modules that need them.
"""

from unittest.mock import MagicMock

import pytest
from apify_client._models import Run

# Shaped like a real `GET /v2/actor-runs/{id}` response and validated into the
# `Run` model that apify-client 3.x returns from `.call()`, so a regression to
# dict-style access in `utils.py` fails here instead of only in production.
MOCK_ACTOR_RUN = Run.model_validate(
    {
        "id": "run-HG7ml5fB1hCp8YEBA",
        "actId": "actor~my-scraper",
        "userId": "user-abc123",
        "startedAt": "2026-03-15T14:30:00.000Z",
        "finishedAt": "2026-03-15T14:35:22.000Z",
        "status": "SUCCEEDED",
        "statusMessage": "Actor finished successfully",
        "meta": {"origin": "API"},
        "stats": {},
        "options": {"build": "latest", "timeoutSecs": 300, "memoryMbytes": 1024, "diskMbytes": 2048},
        "buildId": "build-Zx8Kq2fB1hCp8YEBA",
        "buildNumber": "1.2.3",
        "defaultDatasetId": "dataset-WkC9gct8rq1uR5vDZ",
        "defaultKeyValueStoreId": "kvs-Xb3A8gct8rq1uR5vD",
        "defaultRequestQueueId": "rq-Pq7Lm2gct8rq1uR5v",
    }
)

MOCK_FAILED_RUN = MOCK_ACTOR_RUN.model_copy(
    update={"status": "FAILED", "status_message": "Actor failed with an error"},
)

MOCK_TIMED_OUT_RUN = MOCK_ACTOR_RUN.model_copy(
    update={"status": "TIMED-OUT", "status_message": "Actor run timed out"},
)

MOCK_DATASET_ITEMS = [
    {"url": "https://example.com/product/1", "title": "Widget A", "price": 19.99, "currency": "USD"},
    {"url": "https://example.com/product/2", "title": "Widget B", "price": 29.99, "currency": "USD"},
    {"url": "https://example.com/product/3", "title": "Widget C", "price": 39.99, "currency": "EUR"},
]


@pytest.fixture
def mock_apify_client():
    """Create a mock ApifyClient with pre-configured Actor / task / dataset responses.

    All three sub-clients (``actor``, ``task``, ``dataset``) are wired up so
    a single fixture covers core, search/crawling, and social-media tools.
    """
    client = MagicMock()

    mock_actor = MagicMock()
    mock_actor.call.return_value = MOCK_ACTOR_RUN
    client.actor.return_value = mock_actor

    mock_task = MagicMock()
    mock_task.call.return_value = MOCK_ACTOR_RUN
    client.task.return_value = mock_task

    mock_dataset = MagicMock()
    mock_list_result = MagicMock()
    mock_list_result.items = MOCK_DATASET_ITEMS
    mock_dataset.list_items.return_value = mock_list_result
    client.dataset.return_value = mock_dataset

    return client


@pytest.fixture
def mock_apify_env(monkeypatch):
    """Set required Apify environment variables."""
    monkeypatch.setenv("APIFY_TOKEN", "apify_api_test-token-12345")
