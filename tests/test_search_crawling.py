"""Tests for the Apify search and crawling tools."""

import json
from unittest.mock import MagicMock, patch

import pytest

from strands_apify.search_crawling import (
    apify_ecommerce_scraper,
    apify_google_places_scraper,
    apify_google_search_scraper,
    apify_website_content_crawler,
    apify_youtube_scraper,
)

MOCK_ACTOR_RUN = {
    "id": "run-HG7ml5fB1hCp8YEBA",
    "actId": "actor~my-scraper",
    "userId": "user-abc123",
    "startedAt": "2026-03-15T14:30:00.000Z",
    "finishedAt": "2026-03-15T14:35:22.000Z",
    "status": "SUCCEEDED",
    "statusMessage": "Actor finished successfully",
    "defaultDatasetId": "dataset-WkC9gct8rq1uR5vDZ",
    "defaultKeyValueStoreId": "kvs-Xb3A8gct8rq1uR5vD",
    "buildNumber": "1.2.3",
}

MOCK_FAILED_RUN = {
    **MOCK_ACTOR_RUN,
    "status": "FAILED",
    "statusMessage": "Actor failed with an error",
}

MOCK_DATASET_ITEMS = [
    {"url": "https://example.com/product/1", "title": "Widget A", "price": 19.99, "currency": "USD"},
    {"url": "https://example.com/product/2", "title": "Widget B", "price": 29.99, "currency": "USD"},
    {"url": "https://example.com/product/3", "title": "Widget C", "price": 39.99, "currency": "EUR"},
]


@pytest.fixture
def mock_apify_client():
    """Create a mock ApifyClient with pre-configured responses."""
    client = MagicMock()

    mock_actor = MagicMock()
    mock_actor.call.return_value = MOCK_ACTOR_RUN
    client.actor.return_value = mock_actor

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


# --- apify_google_search_scraper ---


def test_google_search_scraper_success(mock_apify_env, mock_apify_client):
    """Google Search Scraper returns structured results with correct input mapping."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_google_search_scraper(search_query="best AI frameworks", results_limit=5)

    assert result["status"] == "success"
    data = json.loads(result["content"][0]["text"])
    assert data["run_id"] == "run-HG7ml5fB1hCp8YEBA"
    assert len(data["items"]) == 3

    mock_apify_client.actor.assert_called_once_with("apify/google-search-scraper")
    run_input = mock_apify_client.actor.return_value.call.call_args.kwargs["run_input"]
    assert run_input["queries"] == "best AI frameworks"
    assert run_input["maxPagesPerQuery"] == 1
    assert "resultsPerPage" not in run_input


def test_google_search_scraper_multi_page(mock_apify_env, mock_apify_client):
    """Google Search Scraper calculates correct page count when results_limit exceeds 10."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        apify_google_search_scraper(search_query="AI", results_limit=25)

    run_input = mock_apify_client.actor.return_value.call.call_args.kwargs["run_input"]
    assert run_input["maxPagesPerQuery"] == 3
    assert "resultsPerPage" not in run_input


def test_google_search_scraper_optional_params(mock_apify_env, mock_apify_client):
    """Google Search Scraper includes optional country and language codes when provided."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        apify_google_search_scraper(search_query="AI", results_limit=10, country_code="de", language_code="de")

    run_input = mock_apify_client.actor.return_value.call.call_args.kwargs["run_input"]
    assert run_input["countryCode"] == "de"
    assert run_input["languageCode"] == "de"


def test_google_search_scraper_optional_params_omitted(mock_apify_env, mock_apify_client):
    """Google Search Scraper omits optional fields when not provided."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        apify_google_search_scraper(search_query="AI")

    run_input = mock_apify_client.actor.return_value.call.call_args.kwargs["run_input"]
    assert "countryCode" not in run_input
    assert "languageCode" not in run_input


def test_google_search_scraper_missing_dependency(mock_apify_env):
    """Google Search Scraper returns error when apify-client is not installed."""
    with patch("strands_apify.utils.HAS_APIFY_CLIENT", False):
        result = apify_google_search_scraper(search_query="test")

    assert result["status"] == "error"
    assert "apify-client" in result["content"][0]["text"]


def test_google_search_scraper_missing_token(monkeypatch):
    """Google Search Scraper returns error when APIFY_TOKEN is missing."""
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    result = apify_google_search_scraper(search_query="test")

    assert result["status"] == "error"
    assert "APIFY_TOKEN" in result["content"][0]["text"]


def test_google_search_scraper_actor_failure(mock_apify_env, mock_apify_client):
    """Google Search Scraper returns error when Actor fails."""
    mock_apify_client.actor.return_value.call.return_value = MOCK_FAILED_RUN

    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_google_search_scraper(search_query="test")

    assert result["status"] == "error"
    assert "FAILED" in result["content"][0]["text"]


# --- apify_google_places_scraper ---


def test_google_places_scraper_success(mock_apify_env, mock_apify_client):
    """Google Places Scraper returns structured results with correct input mapping."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_google_places_scraper(search_query="restaurants in Prague", results_limit=10)

    assert result["status"] == "success"
    data = json.loads(result["content"][0]["text"])
    assert data["run_id"] == "run-HG7ml5fB1hCp8YEBA"

    mock_apify_client.actor.assert_called_once_with("compass/crawler-google-places")
    run_input = mock_apify_client.actor.return_value.call.call_args.kwargs["run_input"]
    assert run_input["searchStringsArray"] == ["restaurants in Prague"]
    assert run_input["maxCrawledPlacesPerSearch"] == 10
    assert run_input["maxReviews"] == 0


def test_google_places_scraper_with_reviews(mock_apify_env, mock_apify_client):
    """Google Places Scraper sets maxReviews when include_reviews is True."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        apify_google_places_scraper(search_query="hotels in Berlin", include_reviews=True, max_reviews=10)

    run_input = mock_apify_client.actor.return_value.call.call_args.kwargs["run_input"]
    assert run_input["maxReviews"] == 10


def test_google_places_scraper_reviews_disabled(mock_apify_env, mock_apify_client):
    """Google Places Scraper sets maxReviews to 0 when include_reviews is False."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        apify_google_places_scraper(search_query="cafes", include_reviews=False, max_reviews=10)

    run_input = mock_apify_client.actor.return_value.call.call_args.kwargs["run_input"]
    assert run_input["maxReviews"] == 0


def test_google_places_scraper_optional_language(mock_apify_env, mock_apify_client):
    """Google Places Scraper includes language when provided."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        apify_google_places_scraper(search_query="cafes", language="de")

    run_input = mock_apify_client.actor.return_value.call.call_args.kwargs["run_input"]
    assert run_input["language"] == "de"


# --- apify_youtube_scraper ---


def test_youtube_scraper_search_query(mock_apify_env, mock_apify_client):
    """YouTube Scraper returns results when given a search query."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_youtube_scraper(search_query="python tutorial", results_limit=5)

    assert result["status"] == "success"
    mock_apify_client.actor.assert_called_once_with("streamers/youtube-scraper")
    run_input = mock_apify_client.actor.return_value.call.call_args.kwargs["run_input"]
    assert run_input["searchQueries"] == ["python tutorial"]
    assert run_input["maxResults"] == 5
    assert "startUrls" not in run_input


def test_youtube_scraper_urls(mock_apify_env, mock_apify_client):
    """YouTube Scraper returns results when given specific URLs."""
    urls = ["https://www.youtube.com/watch?v=abc123"]
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_youtube_scraper(urls=urls)

    assert result["status"] == "success"
    run_input = mock_apify_client.actor.return_value.call.call_args.kwargs["run_input"]
    assert run_input["startUrls"] == [{"url": "https://www.youtube.com/watch?v=abc123"}]
    assert "searchQueries" not in run_input


def test_youtube_scraper_both_query_and_urls(mock_apify_env, mock_apify_client):
    """YouTube Scraper accepts both search_query and urls simultaneously."""
    urls = ["https://www.youtube.com/watch?v=abc123"]
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_youtube_scraper(search_query="python", urls=urls)

    assert result["status"] == "success"
    run_input = mock_apify_client.actor.return_value.call.call_args.kwargs["run_input"]
    assert run_input["searchQueries"] == ["python"]
    assert run_input["startUrls"] == [{"url": "https://www.youtube.com/watch?v=abc123"}]


def test_youtube_scraper_no_input(mock_apify_env):
    """YouTube Scraper returns error when neither search_query nor urls is provided."""
    result = apify_youtube_scraper()

    assert result["status"] == "error"
    assert "search_query" in result["content"][0]["text"]


def test_youtube_scraper_invalid_url_in_list(mock_apify_env):
    """YouTube Scraper returns error when any URL in the urls list is invalid."""
    result = apify_youtube_scraper(urls=["https://youtube.com/watch?v=ok", "ftp://bad"])

    assert result["status"] == "error"
    text = result["content"][0]["text"]
    assert "urls[1]" in text
    assert "Invalid URL scheme" in text


# --- apify_website_content_crawler ---


def test_website_content_crawler_success(mock_apify_env, mock_apify_client):
    """Website Content Crawler returns results with correct input mapping."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_website_content_crawler(start_url="https://docs.example.com", max_pages=5, max_depth=3)

    assert result["status"] == "success"
    mock_apify_client.actor.assert_called_once_with("apify/website-content-crawler")
    run_input = mock_apify_client.actor.return_value.call.call_args.kwargs["run_input"]
    assert run_input["startUrls"] == [{"url": "https://docs.example.com"}]
    assert run_input["maxCrawlPages"] == 5
    assert run_input["maxCrawlDepth"] == 3
    assert run_input["proxyConfiguration"] == {"useApifyProxy": True}


def test_website_content_crawler_defaults(mock_apify_env, mock_apify_client):
    """Website Content Crawler uses correct defaults for max_pages and max_depth."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        apify_website_content_crawler(start_url="https://example.com")

    run_input = mock_apify_client.actor.return_value.call.call_args.kwargs["run_input"]
    assert run_input["maxCrawlPages"] == 10
    assert run_input["maxCrawlDepth"] == 2


def test_website_content_crawler_invalid_url(mock_apify_env):
    """Website Content Crawler returns error for invalid URL."""
    result = apify_website_content_crawler(start_url="not-a-url")

    assert result["status"] == "error"
    assert "Invalid URL" in result["content"][0]["text"]


# --- apify_ecommerce_scraper ---


def test_ecommerce_scraper_success(mock_apify_env, mock_apify_client):
    """E-commerce Scraper returns results with correct input mapping for product URL."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_ecommerce_scraper(url="https://www.amazon.com/dp/B0TEST", results_limit=10)

    assert result["status"] == "success"
    data = json.loads(result["content"][0]["text"])
    assert data["run_id"] == "run-HG7ml5fB1hCp8YEBA"

    mock_apify_client.actor.assert_called_once_with("apify/e-commerce-scraping-tool")
    run_input = mock_apify_client.actor.return_value.call.call_args.kwargs["run_input"]
    assert run_input["detailsUrls"] == [{"url": "https://www.amazon.com/dp/B0TEST"}]
    assert "listingUrls" not in run_input
    assert run_input["maxProductResults"] == 10


def test_ecommerce_scraper_listing_url(mock_apify_env, mock_apify_client):
    """E-commerce Scraper uses listingUrls when url_type is 'listing'."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_ecommerce_scraper(
            url="https://www.amazon.com/s?k=headphones", url_type="listing", results_limit=10
        )

    assert result["status"] == "success"
    run_input = mock_apify_client.actor.return_value.call.call_args.kwargs["run_input"]
    assert run_input["listingUrls"] == [{"url": "https://www.amazon.com/s?k=headphones"}]
    assert "detailsUrls" not in run_input


def test_ecommerce_scraper_invalid_url_type(mock_apify_env):
    """E-commerce Scraper returns error for invalid url_type."""
    result = apify_ecommerce_scraper(url="https://www.amazon.com/dp/B0TEST", url_type="invalid")

    assert result["status"] == "error"
    assert "url_type" in result["content"][0]["text"]


def test_ecommerce_scraper_invalid_url(mock_apify_env):
    """E-commerce Scraper returns error for invalid URL."""
    result = apify_ecommerce_scraper(url="not-a-url")

    assert result["status"] == "error"
    assert "Invalid URL" in result["content"][0]["text"]


def test_ecommerce_scraper_actor_failure(mock_apify_env, mock_apify_client):
    """E-commerce Scraper returns error when Actor fails."""
    mock_apify_client.actor.return_value.call.return_value = MOCK_FAILED_RUN

    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_ecommerce_scraper(url="https://www.amazon.com/dp/B0TEST")

    assert result["status"] == "error"
    assert "FAILED" in result["content"][0]["text"]
