"""Apify social media scraping tools for Strands Agents.

Available Tools:
---------------
- apify_instagram_scraper: Scrape Instagram profiles, posts, or hashtags
- apify_linkedin_profile_posts: Scrape posts from a LinkedIn profile
- apify_linkedin_profile_search: Search for LinkedIn profiles by keywords
- apify_linkedin_profile_detail: Get detailed LinkedIn profile information
- apify_twitter_scraper: Scrape tweets from Twitter/X
- apify_tiktok_scraper: Scrape TikTok videos, profiles, or hashtags
- apify_facebook_posts_scraper: Scrape posts from Facebook pages
"""

import json
from typing import Any
from urllib.parse import urlparse

from strands import tool

from .utils import (
    DEFAULT_DATASET_ITEMS_LIMIT,
    DEFAULT_TIMEOUT_SECS,
    ApifyToolClient,
    _check_dependency,
    _error_result,
    _success_result,
    _validate_url,
    _validate_urls,
)

DEFAULT_SOCIAL_MEDIA_RESULTS_LIMIT = 20
INSTAGRAM_SCRAPER = "apify/instagram-scraper"
LINKEDIN_PROFILE_POSTS = "apimaestro/linkedin-profile-posts"
LINKEDIN_PROFILE_SEARCH = "harvestapi/linkedin-profile-search"
LINKEDIN_PROFILE_DETAIL = "apimaestro/linkedin-profile-detail"
TWITTER_SCRAPER = "apidojo/twitter-scraper-lite"
TIKTOK_SCRAPER = "clockworks/tiktok-scraper"
FACEBOOK_POSTS_SCRAPER = "apify/facebook-posts-scraper"
_MISSING_SEARCH_OR_URLS = "Provide at least one of 'search_query' or 'urls'."

VALID_INSTAGRAM_SEARCH_TYPES = ("hashtag", "user", "place")
VALID_INSTAGRAM_RESULTS_TYPES = ("posts", "comments", "details")
VALID_TWITTER_SORT_OPTIONS = ("Latest", "Top")
VALID_LINKEDIN_SCRAPER_MODES = ("Short", "Full")


def _extract_linkedin_username(profile_url: str) -> str:
    """Extract a LinkedIn username from a profile URL, or return the value as-is if already a username."""
    parsed = urlparse(profile_url)
    if parsed.netloc and "linkedin.com" in parsed.netloc:
        parts = [p for p in parsed.path.strip("/").split("/") if p]
        if len(parts) >= 2 and parts[0] == "in":
            return parts[1]
    return profile_url


def _social_media_result(
    actor_name: str,
    client: ApifyToolClient,
    run_input: dict[str, Any],
    actor_id: str,
    timeout_secs: int,
    results_limit: int,
) -> dict[str, Any]:
    """Shared execution logic for social media scraper tools."""
    result = client.run_actor_and_get_dataset(
        actor_id=actor_id,
        run_input=run_input,
        timeout_secs=timeout_secs,
        dataset_items_limit=results_limit,
    )
    return _success_result(
        text=json.dumps(result, indent=2, default=str),
        panel_body=(
            f"[green]{actor_name} completed[/green]\n"
            f"Actor: {actor_id}\n"
            f"Run ID: {result['run_id']}\n"
            f"Status: {result['status']}\n"
            f"Items returned: {len(result['items'])}"
        ),
        panel_title=f"Apify: {actor_name}",
    )


@tool
def apify_instagram_scraper(
    search_query: str | None = None,
    urls: list[str] | None = None,
    results_type: str = "posts",
    results_limit: int = DEFAULT_SOCIAL_MEDIA_RESULTS_LIMIT,
    search_type: str = "hashtag",
    search_limit: int = 10,
    timeout_secs: int = DEFAULT_TIMEOUT_SECS,
) -> dict[str, Any]:
    """Scrape Instagram profiles, posts, reels, or hashtags.

    Provide either a search query to discover content or direct Instagram URLs to scrape.
    Supports searching by user profile, hashtag, or place.

    Args:
        search_query: Username, hashtag, or keyword to search for on Instagram.
            If the value looks like an Instagram URL it is treated as a direct URL instead.
        urls: One or more Instagram URLs to scrape directly (profiles, posts, reels, etc.).
        results_type: What to scrape from each page: "posts" (default), "comments", or
            "details" (profile metadata only).
        results_limit: Maximum number of items to return per URL or search hit. Defaults to 20.
        search_type: What kind of search to perform: "hashtag" (default), "user", or "place".
            Only used when search_query is a plain keyword (not a URL).
        search_limit: How many search results (hashtags, users, or places) to process.
            Defaults to 10. Each search hit then returns up to results_limit items.
        timeout_secs: Maximum time in seconds to wait for the Actor run. Defaults to 300.

    Returns:
        Dict with status and content containing scraped Instagram data items.
    """
    try:
        _check_dependency()
        if not search_query and not urls:
            raise ValueError(_MISSING_SEARCH_OR_URLS)
        if results_type not in VALID_INSTAGRAM_RESULTS_TYPES:
            raise ValueError(
                f"Invalid results_type '{results_type}'. Must be one of: {', '.join(VALID_INSTAGRAM_RESULTS_TYPES)}."
            )
        if search_type not in VALID_INSTAGRAM_SEARCH_TYPES:
            raise ValueError(
                f"Invalid search_type '{search_type}'. Must be one of: {', '.join(VALID_INSTAGRAM_SEARCH_TYPES)}."
            )
        if urls is not None:
            _validate_urls(urls, "urls")

        client = ApifyToolClient()
        run_input: dict[str, Any] = {
            "resultsType": results_type,
            "resultsLimit": results_limit,
        }

        if urls:
            run_input["directUrls"] = urls
        elif search_query and ("instagram.com" in search_query or search_query.startswith("http")):
            run_input["directUrls"] = [search_query]
        else:
            run_input["search"] = search_query
            run_input["searchType"] = search_type
            run_input["searchLimit"] = search_limit

        return _social_media_result(
            actor_name="Instagram Scraper",
            client=client,
            run_input=run_input,
            actor_id=INSTAGRAM_SCRAPER,
            timeout_secs=timeout_secs,
            results_limit=results_limit,
        )
    except Exception as e:
        return _error_result(e, "apify_instagram_scraper")


@tool
def apify_linkedin_profile_posts(
    profile_url: str,
    results_limit: int = DEFAULT_SOCIAL_MEDIA_RESULTS_LIMIT,
    timeout_secs: int = DEFAULT_TIMEOUT_SECS,
) -> dict[str, Any]:
    """Scrape posts from a LinkedIn profile.

    Accepts a LinkedIn profile URL (e.g. "https://www.linkedin.com/in/username") or
    a bare username. Returns the most recent posts from that profile.

    Args:
        profile_url: LinkedIn profile URL or username to scrape posts from.
        results_limit: Maximum number of posts to return (1-100). Defaults to 20.
        timeout_secs: Maximum time in seconds to wait for the Actor run. Defaults to 300.

    Returns:
        Dict with status and content containing scraped LinkedIn post data.
    """
    try:
        _check_dependency()
        client = ApifyToolClient()
        username = _extract_linkedin_username(profile_url)
        run_input: dict[str, Any] = {
            "username": username,
            "limit": min(results_limit, 100),
        }
        return _social_media_result(
            actor_name="LinkedIn Profile Posts",
            client=client,
            run_input=run_input,
            actor_id=LINKEDIN_PROFILE_POSTS,
            timeout_secs=timeout_secs,
            results_limit=results_limit,
        )
    except Exception as e:
        return _error_result(e, "apify_linkedin_profile_posts")


@tool
def apify_linkedin_profile_search(
    search_query: str,
    results_limit: int = DEFAULT_SOCIAL_MEDIA_RESULTS_LIMIT,
    locations: list[str] | None = None,
    current_job_titles: list[str] | None = None,
    profile_scraper_mode: str = "Short",
    timeout_secs: int = DEFAULT_TIMEOUT_SECS,
) -> dict[str, Any]:
    """Search for LinkedIn profiles with filters.

    Find people on LinkedIn using a keyword query combined with optional filters
    for location and job title. Returns basic profile data in Short mode or
    full details (experience, education, skills) in Full mode.

    Args:
        search_query: Search keywords such as job titles, skills, or names
            (e.g. "software engineer", "marketing manager"). Supports LinkedIn
            search operators.
        results_limit: Maximum number of profiles to return. Defaults to 20.
        locations: Filter by locations (e.g. ["San Francisco", "New York"]).
            Use full names - LinkedIn may misinterpret abbreviations.
        current_job_titles: Filter by current job titles
            (e.g. ["Software Engineer", "Data Scientist"]).
        profile_scraper_mode: Amount of detail to return. "Short" (default)
            returns basic profile data from search results. "Full" opens each
            profile to scrape complete details including experience and education.
        timeout_secs: Maximum time in seconds to wait for the Actor run. Defaults to 300.

    Returns:
        Dict with status and content containing matched LinkedIn profile data.
    """
    try:
        _check_dependency()
        if profile_scraper_mode not in VALID_LINKEDIN_SCRAPER_MODES:
            raise ValueError(
                f"Invalid profile_scraper_mode '{profile_scraper_mode}'. "
                f"Must be one of: {', '.join(VALID_LINKEDIN_SCRAPER_MODES)}."
            )

        client = ApifyToolClient()
        run_input: dict[str, Any] = {
            "searchQuery": search_query,
            "maxItems": results_limit,
            "profileScraperMode": profile_scraper_mode,
        }
        if locations is not None:
            run_input["locations"] = locations
        if current_job_titles is not None:
            run_input["currentJobTitles"] = current_job_titles

        return _social_media_result(
            actor_name="LinkedIn Profile Search",
            client=client,
            run_input=run_input,
            actor_id=LINKEDIN_PROFILE_SEARCH,
            timeout_secs=timeout_secs,
            results_limit=results_limit,
        )
    except Exception as e:
        return _error_result(e, "apify_linkedin_profile_search")


@tool
def apify_linkedin_profile_detail(
    profile_url: str,
    include_email: bool = False,
    timeout_secs: int = DEFAULT_TIMEOUT_SECS,
) -> dict[str, Any]:
    """Get detailed information from a LinkedIn profile.

    Accepts a LinkedIn profile URL (e.g. "https://www.linkedin.com/in/username") or
    a bare username. Returns full profile details including work experience, education,
    skills, and more. No LinkedIn account or cookies required.

    Args:
        profile_url: LinkedIn profile URL or username to scrape.
        include_email: Whether to include the email address in results if publicly
            available. Defaults to False.
        timeout_secs: Maximum time in seconds to wait for the Actor run. Defaults to 300.

    Returns:
        Dict with status and content containing detailed LinkedIn profile data
        (work experience, education, certifications, location, and optionally email).
    """
    try:
        _check_dependency()
        client = ApifyToolClient()
        username = _extract_linkedin_username(profile_url)
        run_input: dict[str, Any] = {
            "username": username,
            "includeEmail": include_email,
        }
        return _social_media_result(
            actor_name="LinkedIn Profile Detail",
            client=client,
            run_input=run_input,
            actor_id=LINKEDIN_PROFILE_DETAIL,
            timeout_secs=timeout_secs,
            results_limit=DEFAULT_DATASET_ITEMS_LIMIT,
        )
    except Exception as e:
        return _error_result(e, "apify_linkedin_profile_detail")


@tool
def apify_twitter_scraper(
    search_query: str | None = None,
    urls: list[str] | None = None,
    twitter_handles: list[str] | None = None,
    results_limit: int = DEFAULT_SOCIAL_MEDIA_RESULTS_LIMIT,
    sort: str = "Latest",
    tweet_language: str | None = None,
    timeout_secs: int = DEFAULT_TIMEOUT_SECS,
) -> dict[str, Any]:
    """Scrape tweets from Twitter/X by search query, handles, or specific URLs.

    Supports Twitter advanced search syntax (e.g. "from:NASA", "#AI min_faves:100",
    "bitcoin min_faves:1000 min_retweets:100"). Provide at least one of search_query,
    urls, or twitter_handles.

    Args:
        search_query: Search query to find tweets. Supports Twitter advanced search
            operators like "from:user", "#hashtag", "min_faves:N", date ranges with
            "since:YYYY-MM-DD until:YYYY-MM-DD", and boolean operators.
        urls: Specific tweet, profile, search, or list URLs to scrape directly.
        twitter_handles: Twitter handles to scrape (without the @ symbol,
            e.g. ["NASA", "WHO"]).
        results_limit: Maximum number of tweets to return. Defaults to 20.
        sort: Sort order for search results: "Latest" (default, chronological) or
            "Top" (most popular/relevant).
        tweet_language: Restrict tweets to this language. Use an ISO 639-1 code
            (e.g. "en", "es", "de"). Defaults to all languages.
        timeout_secs: Maximum time in seconds to wait for the Actor run. Defaults to 300.

    Returns:
        Dict with status and content containing scraped tweet data.
    """
    try:
        _check_dependency()
        if not search_query and not urls and not twitter_handles:
            raise ValueError("Provide at least one of 'search_query', 'urls', or 'twitter_handles'.")
        if sort not in VALID_TWITTER_SORT_OPTIONS:
            raise ValueError(f"Invalid sort '{sort}'. Must be one of: {', '.join(VALID_TWITTER_SORT_OPTIONS)}.")
        if urls is not None:
            _validate_urls(urls, "urls")

        client = ApifyToolClient()
        run_input: dict[str, Any] = {
            "maxItems": results_limit,
            "sort": sort,
        }

        if search_query:
            run_input["searchTerms"] = [search_query]
        if urls:
            run_input["startUrls"] = urls
        if twitter_handles:
            run_input["twitterHandles"] = twitter_handles
        if tweet_language is not None:
            run_input["tweetLanguage"] = tweet_language

        return _social_media_result(
            actor_name="Twitter Scraper",
            client=client,
            run_input=run_input,
            actor_id=TWITTER_SCRAPER,
            timeout_secs=timeout_secs,
            results_limit=results_limit,
        )
    except Exception as e:
        return _error_result(e, "apify_twitter_scraper")


@tool
def apify_tiktok_scraper(
    search_query: str | None = None,
    hashtags: list[str] | None = None,
    profiles: list[str] | None = None,
    urls: list[str] | None = None,
    results_limit: int = DEFAULT_SOCIAL_MEDIA_RESULTS_LIMIT,
    timeout_secs: int = DEFAULT_TIMEOUT_SECS,
) -> dict[str, Any]:
    """Scrape TikTok videos by search, hashtag, profile, or direct post URL.

    Use the input that best matches your intent:
    - search_query: keyword search across videos and profiles
    - hashtags: scrape videos tagged with specific hashtags (e.g. ["fyp", "cooking"])
    - profiles: scrape videos from specific users (e.g. ["username1", "username2"])
    - urls: scrape specific TikTok post URLs

    Provide at least one of the above.

    Args:
        search_query: Keyword to search TikTok. Applies to both videos and profiles.
        hashtags: One or more TikTok hashtags (without #) to scrape videos from.
        profiles: One or more TikTok usernames to scrape videos from.
        urls: Specific TikTok post URLs to scrape.
        results_limit: Maximum number of videos per hashtag, profile, or search.
            Defaults to 20.
        timeout_secs: Maximum time in seconds to wait for the Actor run. Defaults to 300.

    Returns:
        Dict with status and content containing scraped TikTok video data.
    """
    try:
        _check_dependency()
        if not search_query and not hashtags and not profiles and not urls:
            raise ValueError("Provide at least one of 'search_query', 'hashtags', 'profiles', or 'urls'.")
        if urls is not None:
            _validate_urls(urls, "urls")

        client = ApifyToolClient()
        run_input: dict[str, Any] = {"resultsPerPage": results_limit}

        if search_query:
            run_input["searchQueries"] = [search_query]
        if hashtags:
            run_input["hashtags"] = hashtags
        if profiles:
            run_input["profiles"] = profiles
        if urls:
            run_input["postURLs"] = urls

        return _social_media_result(
            actor_name="TikTok Scraper",
            client=client,
            run_input=run_input,
            actor_id=TIKTOK_SCRAPER,
            timeout_secs=timeout_secs,
            results_limit=results_limit,
        )
    except Exception as e:
        return _error_result(e, "apify_tiktok_scraper")


@tool
def apify_facebook_posts_scraper(
    page_url: str,
    results_limit: int = DEFAULT_SOCIAL_MEDIA_RESULTS_LIMIT,
    only_posts_newer_than: str | None = None,
    timeout_secs: int = DEFAULT_TIMEOUT_SECS,
) -> dict[str, Any]:
    """Scrape posts from a Facebook page or profile.

    Provide a Facebook page or profile URL to scrape its posts. Optionally filter
    to only return recent posts.

    Args:
        page_url: Facebook page or profile URL to scrape posts from.
        results_limit: Maximum number of posts to return. Defaults to 20.
        only_posts_newer_than: Only return posts newer than this date. Use a
            natural-language date string like "2024-01-01", "1 week ago", or
            "3 months ago". Defaults to no date filter.
        timeout_secs: Maximum time in seconds to wait for the Actor run. Defaults to 300.

    Returns:
        Dict with status and content containing scraped Facebook post data.
    """
    try:
        _check_dependency()
        _validate_url(page_url)
        client = ApifyToolClient()
        run_input: dict[str, Any] = {
            "startUrls": [{"url": page_url}],
            "resultsLimit": results_limit,
        }
        if only_posts_newer_than is not None:
            run_input["onlyPostsNewerThan"] = only_posts_newer_than

        return _social_media_result(
            actor_name="Facebook Posts Scraper",
            client=client,
            run_input=run_input,
            actor_id=FACEBOOK_POSTS_SCRAPER,
            timeout_secs=timeout_secs,
            results_limit=results_limit,
        )
    except Exception as e:
        return _error_result(e, "apify_facebook_posts_scraper")


APIFY_SOCIAL_TOOLS = [
    apify_instagram_scraper,
    apify_linkedin_profile_posts,
    apify_linkedin_profile_search,
    apify_linkedin_profile_detail,
    apify_twitter_scraper,
    apify_tiktok_scraper,
    apify_facebook_posts_scraper,
]
