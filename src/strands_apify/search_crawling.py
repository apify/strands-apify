"""Apify search and web crawling tools for Strands Agents.

Available Tools:
---------------
- apify_google_search_scraper: Search Google and return structured results
- apify_google_places_scraper: Search Google Maps for places and businesses
- apify_youtube_scraper: Scrape YouTube videos, channels, or search results
- apify_website_content_crawler: Multi-page website crawl with markdown extraction
- apify_ecommerce_scraper: Scrape product data from e-commerce sites
"""

import json
from typing import Any, Dict, List, Optional

from strands import tool

from .utils import (
    DEFAULT_TIMEOUT_SECS,
    WEBSITE_CONTENT_CRAWLER,
    ApifyToolClient,
    _check_dependency,
    _error_result,
    _success_result,
)

GOOGLE_SEARCH_SCRAPER_ID = "apify/google-search-scraper"
GOOGLE_PLACES_SCRAPER_ID = "compass/crawler-google-places"
YOUTUBE_SCRAPER_ID = "streamers/youtube-scraper"
ECOMMERCE_SCRAPER_ID = "apify/e-commerce-scraping-tool"
DEFAULT_SEARCH_RESULTS_LIMIT = 20

VALID_ECOMMERCE_URL_TYPES = ("product", "listing")


def _search_crawl_result(
    actor_name: str,
    client: ApifyToolClient,
    run_input: Dict[str, Any],
    actor_id: str,
    timeout_secs: int,
    results_limit: int,
) -> Dict[str, Any]:
    """Run a search/crawling Actor and return formatted results."""
    result = client.run_actor_and_get_dataset(
        actor_id=actor_id,
        run_input=run_input,
        timeout_secs=timeout_secs,
        dataset_items_limit=results_limit,
    )
    return _success_result(
        text=json.dumps(result, indent=2, default=str),
        panel_body=(
            f"[green]{actor_name} completed[/green]\nRun ID: {result['run_id']}\nItems returned: {len(result['items'])}"
        ),
        panel_title=f"Apify: {actor_name}",
    )


@tool
def apify_google_search_scraper(
    search_query: str,
    results_limit: int = 10,
    country_code: Optional[str] = None,
    language_code: Optional[str] = None,
    timeout_secs: int = DEFAULT_TIMEOUT_SECS,
) -> Dict[str, Any]:
    """Search Google and return structured search results.

    Uses the Google Search Scraper Actor to perform a Google search and return
    organic results, ads, People Also Ask, and related queries in a structured format.

    Args:
        search_query: The search query string, e.g. "best AI frameworks 2025".
            Supports advanced Google operators like "site:example.com" or "AI OR ML".
        results_limit: Maximum number of results to return. Google returns ~10 results
            per page, so requesting more triggers additional page scraping. Defaults to 10.
        country_code: Two-letter country code for localized results, e.g. "us", "de".
        language_code: Two-letter language code for the interface, e.g. "en", "de".
        timeout_secs: Maximum time in seconds to wait for the run to finish. Defaults to 300.

    Returns:
        Dict with status and content containing structured Google search results including
        organic results, ads, and People Also Ask data.
    """
    try:
        _check_dependency()
        client = ApifyToolClient()
        max_pages = max(1, (results_limit + 9) // 10)
        run_input: Dict[str, Any] = {
            "queries": search_query,
            "maxPagesPerQuery": max_pages,
        }
        if country_code is not None:
            run_input["countryCode"] = country_code
        if language_code is not None:
            run_input["languageCode"] = language_code
        return _search_crawl_result(
            actor_name="Google Search Scraper",
            client=client,
            run_input=run_input,
            actor_id=GOOGLE_SEARCH_SCRAPER_ID,
            timeout_secs=timeout_secs,
            results_limit=results_limit,
        )
    except Exception as e:
        return _error_result(e, "apify_google_search_scraper")


@tool
def apify_google_places_scraper(
    search_query: str,
    results_limit: int = DEFAULT_SEARCH_RESULTS_LIMIT,
    language: Optional[str] = None,
    include_reviews: bool = False,
    max_reviews: int = 5,
    timeout_secs: int = DEFAULT_TIMEOUT_SECS,
) -> Dict[str, Any]:
    """Search Google Maps for businesses and places, optionally including reviews.

    Uses the Google Maps Scraper Actor to find places matching a search query
    and return structured data including name, address, rating, phone, and website.

    Args:
        search_query: Search query for Google Maps, e.g. "restaurants in Prague".
        results_limit: Maximum number of places to return. Defaults to 20.
        language: Language for results, e.g. "en", "de". Defaults to English.
        include_reviews: Whether to include user reviews for each place. Defaults to False.
        max_reviews: Maximum reviews per place when include_reviews is True. Defaults to 5.
        timeout_secs: Maximum time in seconds to wait for the run to finish. Defaults to 300.

    Returns:
        Dict with status and content containing structured Google Maps place data.
    """
    try:
        _check_dependency()
        client = ApifyToolClient()
        run_input: Dict[str, Any] = {
            "searchStringsArray": [search_query],
            "maxCrawledPlacesPerSearch": results_limit,
            "maxReviews": max_reviews if include_reviews else 0,
        }
        if language is not None:
            run_input["language"] = language
        return _search_crawl_result(
            actor_name="Google Places Scraper",
            client=client,
            run_input=run_input,
            actor_id=GOOGLE_PLACES_SCRAPER_ID,
            timeout_secs=timeout_secs,
            results_limit=results_limit,
        )
    except Exception as e:
        return _error_result(e, "apify_google_places_scraper")


@tool
def apify_youtube_scraper(
    search_query: Optional[str] = None,
    urls: Optional[List[str]] = None,
    results_limit: int = DEFAULT_SEARCH_RESULTS_LIMIT,
    timeout_secs: int = DEFAULT_TIMEOUT_SECS,
) -> Dict[str, Any]:
    """Scrape YouTube videos, channels, or search results.

    Uses the YouTube Scraper Actor to search YouTube or scrape specific video/channel
    URLs. Provide either a search query, specific URLs, or both.

    Args:
        search_query: YouTube search query, e.g. "python tutorial".
        urls: Specific YouTube video or channel URLs to scrape.
        results_limit: Maximum number of results to return. Defaults to 20.
        timeout_secs: Maximum time in seconds to wait for the run to finish. Defaults to 300.

    Returns:
        Dict with status and content containing structured YouTube video/channel data.
    """
    try:
        _check_dependency()
        if not search_query and not urls:
            raise ValueError("At least one of 'search_query' or 'urls' must be provided.")
        client = ApifyToolClient()
        run_input: Dict[str, Any] = {
            "maxResults": results_limit,
        }
        if search_query is not None:
            run_input["searchQueries"] = [search_query]
        if urls is not None:
            run_input["startUrls"] = [{"url": u} for u in urls]
        return _search_crawl_result(
            actor_name="YouTube Scraper",
            client=client,
            run_input=run_input,
            actor_id=YOUTUBE_SCRAPER_ID,
            timeout_secs=timeout_secs,
            results_limit=results_limit,
        )
    except Exception as e:
        return _error_result(e, "apify_youtube_scraper")


@tool
def apify_website_content_crawler(
    start_url: str,
    max_pages: int = 10,
    max_depth: int = 2,
    timeout_secs: int = DEFAULT_TIMEOUT_SECS,
) -> Dict[str, Any]:
    """Crawl a website and extract content from multiple pages.

    Uses the Website Content Crawler Actor to perform a multi-page crawl starting
    from the given URL. Returns page content as markdown. This is the extended
    multi-page version - distinct from apify_scrape_url which scrapes a single page.

    Args:
        start_url: The starting URL to crawl, e.g. "https://docs.example.com".
        max_pages: Maximum number of pages to crawl. Defaults to 10.
        max_depth: Maximum crawl depth from the start URL. Defaults to 2.
        timeout_secs: Maximum time in seconds to wait for the run to finish. Defaults to 300.

    Returns:
        Dict with status and content containing crawled page data with markdown content.
    """
    try:
        _check_dependency()
        client = ApifyToolClient()
        client._validate_url(start_url)
        run_input: Dict[str, Any] = {
            "startUrls": [{"url": start_url}],
            "maxCrawlPages": max_pages,
            "maxCrawlDepth": max_depth,
            "proxyConfiguration": {"useApifyProxy": True},
        }
        return _search_crawl_result(
            actor_name="Website Content Crawler",
            client=client,
            run_input=run_input,
            actor_id=WEBSITE_CONTENT_CRAWLER,
            timeout_secs=timeout_secs,
            results_limit=max_pages,
        )
    except Exception as e:
        return _error_result(e, "apify_website_content_crawler")


@tool
def apify_ecommerce_scraper(
    url: str,
    url_type: str = "product",
    results_limit: int = DEFAULT_SEARCH_RESULTS_LIMIT,
    timeout_secs: int = DEFAULT_TIMEOUT_SECS,
) -> Dict[str, Any]:
    """Scrape product data from e-commerce websites.

    Uses the E-commerce Scraping Tool Actor to extract structured product data
    (title, price, description, images, etc.) from supported e-commerce platforms
    including Amazon, eBay, Walmart, and others. The Actor auto-detects the site.

    Args:
        url: The URL to scrape.
        url_type: Type of URL being scraped. Use "product" (default) for a direct product
            detail page, or "listing" for a category page or search results page containing
            multiple products.
        results_limit: Maximum number of products to return. Defaults to 20.
        timeout_secs: Maximum time in seconds to wait for the run to finish. Defaults to 300.

    Returns:
        Dict with status and content containing structured product data.
    """
    try:
        _check_dependency()
        client = ApifyToolClient()
        client._validate_url(url)
        if url_type not in VALID_ECOMMERCE_URL_TYPES:
            raise ValueError(f"Invalid url_type '{url_type}'. Must be one of: {', '.join(VALID_ECOMMERCE_URL_TYPES)}.")
        url_field = "listingUrls" if url_type == "listing" else "detailsUrls"
        run_input: Dict[str, Any] = {
            url_field: [{"url": url}],
            "maxProductResults": results_limit,
        }
        return _search_crawl_result(
            actor_name="E-commerce Scraper",
            client=client,
            run_input=run_input,
            actor_id=ECOMMERCE_SCRAPER_ID,
            timeout_secs=timeout_secs,
            results_limit=results_limit,
        )
    except Exception as e:
        return _error_result(e, "apify_ecommerce_scraper")


APIFY_SEARCH_TOOLS = [
    apify_google_search_scraper,
    apify_google_places_scraper,
    apify_youtube_scraper,
    apify_website_content_crawler,
    apify_ecommerce_scraper,
]
