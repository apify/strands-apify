"""Tests for the Apify social media tools."""

from unittest.mock import patch

import pytest
from conftest import MOCK_FAILED_RUN

from strands_apify.social_media import (
    _extract_linkedin_username,
    _looks_like_instagram_url,
    apify_facebook_posts_scraper,
    apify_instagram_scraper,
    apify_linkedin_profile_detail,
    apify_linkedin_profile_posts,
    apify_linkedin_profile_search,
    apify_tiktok_scraper,
    apify_twitter_scraper,
)

# --- _extract_linkedin_username ---


def test_extract_linkedin_username_from_url():
    """Extracts username from a standard LinkedIn profile URL."""
    assert _extract_linkedin_username("https://www.linkedin.com/in/neal-mohan") == "neal-mohan"


def test_extract_linkedin_username_from_url_trailing_slash():
    """Extracts username from a LinkedIn URL with trailing slash."""
    assert _extract_linkedin_username("https://www.linkedin.com/in/neal-mohan/") == "neal-mohan"


def test_extract_linkedin_username_bare():
    """Passes through a bare username unchanged."""
    assert _extract_linkedin_username("neal-mohan") == "neal-mohan"


def test_extract_linkedin_username_non_profile_url():
    """Non-/in/ LinkedIn URL is returned as-is."""
    assert (
        _extract_linkedin_username("https://www.linkedin.com/company/apify") == "https://www.linkedin.com/company/apify"
    )


# --- apify_instagram_scraper ---


def test_instagram_scraper_search_success(mock_apify_env, mock_apify_client):
    """Instagram scraper with search query maps to 'search' field with resultsType and searchLimit."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_instagram_scraper(search_query="apify", results_limit=10, search_type="user")

    assert result["status"] == "success"
    call_kwargs = mock_apify_client.actor.return_value.call.call_args.kwargs
    run_input = call_kwargs["run_input"]
    assert run_input["search"] == "apify"
    assert run_input["searchType"] == "user"
    assert run_input["resultsLimit"] == 10
    assert run_input["resultsType"] == "posts"
    assert run_input["searchLimit"] == 10
    mock_apify_client.actor.assert_called_once_with("apify/instagram-scraper")


def test_instagram_scraper_with_urls(mock_apify_env, mock_apify_client):
    """Instagram scraper with explicit URLs maps to 'directUrls'."""
    urls = ["https://www.instagram.com/apify/"]
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_instagram_scraper(urls=urls, results_limit=5)

    assert result["status"] == "success"
    call_kwargs = mock_apify_client.actor.return_value.call.call_args.kwargs
    run_input = call_kwargs["run_input"]
    assert run_input["directUrls"] == urls
    assert run_input["resultsType"] == "posts"
    assert "search" not in run_input


def test_instagram_scraper_results_type(mock_apify_env, mock_apify_client):
    """Instagram scraper passes results_type to Actor input."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_instagram_scraper(search_query="apify", results_type="comments")

    assert result["status"] == "success"
    run_input = mock_apify_client.actor.return_value.call.call_args.kwargs["run_input"]
    assert run_input["resultsType"] == "comments"


def test_instagram_scraper_invalid_results_type(mock_apify_env):
    """Instagram scraper returns error for invalid results_type."""
    result = apify_instagram_scraper(search_query="apify", results_type="invalid")

    assert result["status"] == "error"
    assert "results_type" in result["content"][0]["text"]


def test_instagram_scraper_invalid_search_type(mock_apify_env):
    """Instagram scraper returns error for invalid search_type."""
    result = apify_instagram_scraper(search_query="apify", search_type="invalid")

    assert result["status"] == "error"
    assert "search_type" in result["content"][0]["text"]


def test_instagram_scraper_url_in_search_query(mock_apify_env, mock_apify_client):
    """Instagram scraper routes URL-like search_query to 'directUrls'."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_instagram_scraper(search_query="https://www.instagram.com/apify/")

    assert result["status"] == "success"
    call_kwargs = mock_apify_client.actor.return_value.call.call_args.kwargs
    run_input = call_kwargs["run_input"]
    assert run_input["directUrls"] == ["https://www.instagram.com/apify/"]
    assert "search" not in run_input


@pytest.mark.parametrize(
    "value",
    [
        "https://www.instagram.com/apify/",
        "https://instagram.com/apify",
        "http://instagram.com/explore/tags/cooking/",
        "https://www.instagram.com/p/AbCdEfG/",
    ],
)
def test_looks_like_instagram_url_true(value):
    """Helper returns True for real Instagram URLs (with and without subdomain)."""
    assert _looks_like_instagram_url(value) is True


@pytest.mark.parametrize(
    "value",
    [
        "apify",  # plain handle
        "#cooking",  # hashtag
        "why-instagram.com-matters",  # substring trap the old heuristic fell into
        "http",  # bare scheme prefix the old heuristic accepted
        "https://example.com/instagram.com",  # not actually hosted on instagram.com
        "ftp://instagram.com/apify",  # wrong scheme
        "javascript:alert(1)",
        "",
    ],
)
def test_looks_like_instagram_url_false(value):
    """Helper rejects plain queries, lookalikes, and non-http(s) schemes."""
    assert _looks_like_instagram_url(value) is False


def test_instagram_scraper_search_query_with_instagram_substring(mock_apify_env, mock_apify_client):
    """A search_query that merely contains 'instagram.com' is treated as a search, not a URL."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_instagram_scraper(search_query="why-instagram.com-matters")

    assert result["status"] == "success"
    run_input = mock_apify_client.actor.return_value.call.call_args.kwargs["run_input"]
    assert run_input["search"] == "why-instagram.com-matters"
    assert "directUrls" not in run_input


def test_instagram_scraper_missing_params(mock_apify_env):
    """Instagram scraper returns error when neither search_query nor urls provided."""
    result = apify_instagram_scraper()

    assert result["status"] == "error"
    assert "search_query" in result["content"][0]["text"] or "urls" in result["content"][0]["text"]


# --- apify_linkedin_profile_posts ---


def test_linkedin_profile_posts_success(mock_apify_env, mock_apify_client):
    """LinkedIn profile posts maps profile URL to username and results_limit to limit."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_linkedin_profile_posts(
            profile_url="https://www.linkedin.com/in/neal-mohan",
            results_limit=15,
        )

    assert result["status"] == "success"
    call_kwargs = mock_apify_client.actor.return_value.call.call_args.kwargs
    run_input = call_kwargs["run_input"]
    assert run_input["username"] == "neal-mohan"
    assert run_input["limit"] == 15
    mock_apify_client.actor.assert_called_once_with("apimaestro/linkedin-profile-posts")


def test_linkedin_profile_posts_caps_limit(mock_apify_env, mock_apify_client):
    """LinkedIn profile posts caps the limit at 100 per Actor constraint."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        apify_linkedin_profile_posts(profile_url="neal-mohan", results_limit=200)

    call_kwargs = mock_apify_client.actor.return_value.call.call_args.kwargs
    assert call_kwargs["run_input"]["limit"] == 100


# --- apify_linkedin_profile_search ---


def test_linkedin_profile_search_success(mock_apify_env, mock_apify_client):
    """LinkedIn profile search maps search_query to searchQuery and results_limit to maxItems."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_linkedin_profile_search(search_query="software engineer SF", results_limit=25)

    assert result["status"] == "success"
    call_kwargs = mock_apify_client.actor.return_value.call.call_args.kwargs
    run_input = call_kwargs["run_input"]
    assert run_input["searchQuery"] == "software engineer SF"
    assert run_input["maxItems"] == 25
    assert run_input["profileScraperMode"] == "Short"
    assert "locations" not in run_input
    assert "currentJobTitles" not in run_input
    mock_apify_client.actor.assert_called_once_with("harvestapi/linkedin-profile-search")


def test_linkedin_profile_search_with_filters(mock_apify_env, mock_apify_client):
    """LinkedIn profile search passes locations and job title filters."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_linkedin_profile_search(
            search_query="engineer",
            locations=["San Francisco", "New York"],
            current_job_titles=["Software Engineer"],
            profile_scraper_mode="Full",
        )

    assert result["status"] == "success"
    run_input = mock_apify_client.actor.return_value.call.call_args.kwargs["run_input"]
    assert run_input["locations"] == ["San Francisco", "New York"]
    assert run_input["currentJobTitles"] == ["Software Engineer"]
    assert run_input["profileScraperMode"] == "Full"


def test_linkedin_profile_search_invalid_mode(mock_apify_env):
    """LinkedIn profile search returns error for invalid profile_scraper_mode."""
    result = apify_linkedin_profile_search(search_query="test", profile_scraper_mode="Invalid")

    assert result["status"] == "error"
    assert "profile_scraper_mode" in result["content"][0]["text"]


# --- apify_linkedin_profile_detail ---


def test_linkedin_profile_detail_success(mock_apify_env, mock_apify_client):
    """LinkedIn profile detail maps profile URL to username field."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_linkedin_profile_detail(profile_url="https://www.linkedin.com/in/neal-mohan")

    assert result["status"] == "success"
    call_kwargs = mock_apify_client.actor.return_value.call.call_args.kwargs
    run_input = call_kwargs["run_input"]
    assert run_input["username"] == "neal-mohan"
    assert run_input["includeEmail"] is False
    mock_apify_client.actor.assert_called_once_with("apimaestro/linkedin-profile-detail")


def test_linkedin_profile_detail_bare_username(mock_apify_env, mock_apify_client):
    """LinkedIn profile detail accepts a bare username."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_linkedin_profile_detail(profile_url="neal-mohan")

    assert result["status"] == "success"
    call_kwargs = mock_apify_client.actor.return_value.call.call_args.kwargs
    assert call_kwargs["run_input"]["username"] == "neal-mohan"


def test_linkedin_profile_detail_include_email(mock_apify_env, mock_apify_client):
    """LinkedIn profile detail passes includeEmail when requested."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_linkedin_profile_detail(profile_url="neal-mohan", include_email=True)

    assert result["status"] == "success"
    run_input = mock_apify_client.actor.return_value.call.call_args.kwargs["run_input"]
    assert run_input["includeEmail"] is True


# --- apify_twitter_scraper ---


def test_twitter_scraper_search_success(mock_apify_env, mock_apify_client):
    """Twitter scraper maps search_query to searchTerms array with sort and maxItems."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_twitter_scraper(search_query="from:NASA", results_limit=30)

    assert result["status"] == "success"
    call_kwargs = mock_apify_client.actor.return_value.call.call_args.kwargs
    run_input = call_kwargs["run_input"]
    assert run_input["searchTerms"] == ["from:NASA"]
    assert run_input["maxItems"] == 30
    assert run_input["sort"] == "Latest"
    assert "tweetLanguage" not in run_input
    mock_apify_client.actor.assert_called_once_with("apidojo/twitter-scraper-lite")


def test_twitter_scraper_with_urls(mock_apify_env, mock_apify_client):
    """Twitter scraper maps urls to startUrls as objects."""
    tweet_urls = ["https://x.com/elonmusk/status/1728108619189874825"]
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_twitter_scraper(urls=tweet_urls)

    assert result["status"] == "success"
    call_kwargs = mock_apify_client.actor.return_value.call.call_args.kwargs
    assert call_kwargs["run_input"]["startUrls"] == ["https://x.com/elonmusk/status/1728108619189874825"]


def test_twitter_scraper_with_handles(mock_apify_env, mock_apify_client):
    """Twitter scraper passes twitterHandles when provided."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_twitter_scraper(twitter_handles=["NASA", "elonmusk"])

    assert result["status"] == "success"
    run_input = mock_apify_client.actor.return_value.call.call_args.kwargs["run_input"]
    assert run_input["twitterHandles"] == ["NASA", "elonmusk"]


def test_twitter_scraper_sort_and_language(mock_apify_env, mock_apify_client):
    """Twitter scraper passes sort and tweet_language parameters."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_twitter_scraper(search_query="AI", sort="Top", tweet_language="en")

    assert result["status"] == "success"
    run_input = mock_apify_client.actor.return_value.call.call_args.kwargs["run_input"]
    assert run_input["sort"] == "Top"
    assert run_input["tweetLanguage"] == "en"


def test_twitter_scraper_invalid_sort(mock_apify_env):
    """Twitter scraper returns error for invalid sort option."""
    result = apify_twitter_scraper(search_query="test", sort="Invalid")

    assert result["status"] == "error"
    assert "sort" in result["content"][0]["text"]


def test_twitter_scraper_missing_params(mock_apify_env):
    """Twitter scraper returns error when no input provided."""
    result = apify_twitter_scraper()

    assert result["status"] == "error"
    assert "search_query" in result["content"][0]["text"] or "urls" in result["content"][0]["text"]


# --- apify_tiktok_scraper ---


def test_tiktok_scraper_search_success(mock_apify_env, mock_apify_client):
    """TikTok scraper maps search_query to searchQueries and results_limit to resultsPerPage."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_tiktok_scraper(search_query="cooking", results_limit=15)

    assert result["status"] == "success"
    call_kwargs = mock_apify_client.actor.return_value.call.call_args.kwargs
    run_input = call_kwargs["run_input"]
    assert run_input["searchQueries"] == ["cooking"]
    assert run_input["resultsPerPage"] == 15
    mock_apify_client.actor.assert_called_once_with("clockworks/tiktok-scraper")


def test_tiktok_scraper_with_urls(mock_apify_env, mock_apify_client):
    """TikTok scraper maps urls to postURLs."""
    post_urls = ["https://www.tiktok.com/@user/video/123"]
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_tiktok_scraper(urls=post_urls)

    assert result["status"] == "success"
    call_kwargs = mock_apify_client.actor.return_value.call.call_args.kwargs
    assert call_kwargs["run_input"]["postURLs"] == post_urls


def test_tiktok_scraper_with_hashtags(mock_apify_env, mock_apify_client):
    """TikTok scraper passes hashtags to the dedicated hashtags input."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_tiktok_scraper(hashtags=["fyp", "cooking"])

    assert result["status"] == "success"
    run_input = mock_apify_client.actor.return_value.call.call_args.kwargs["run_input"]
    assert run_input["hashtags"] == ["fyp", "cooking"]
    assert "searchQueries" not in run_input


def test_tiktok_scraper_with_profiles(mock_apify_env, mock_apify_client):
    """TikTok scraper passes profiles to the dedicated profiles input."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_tiktok_scraper(profiles=["charlidamelio", "khaby.lame"])

    assert result["status"] == "success"
    run_input = mock_apify_client.actor.return_value.call.call_args.kwargs["run_input"]
    assert run_input["profiles"] == ["charlidamelio", "khaby.lame"]
    assert "searchQueries" not in run_input


def test_tiktok_scraper_missing_params(mock_apify_env):
    """TikTok scraper returns error when no input provided."""
    result = apify_tiktok_scraper()

    assert result["status"] == "error"
    assert "search_query" in result["content"][0]["text"] or "hashtags" in result["content"][0]["text"]


# --- apify_facebook_posts_scraper ---


def test_facebook_posts_scraper_success(mock_apify_env, mock_apify_client):
    """Facebook posts scraper maps page_url to startUrls and results_limit to resultsLimit."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_facebook_posts_scraper(
            page_url="https://www.facebook.com/apify",
            results_limit=10,
        )

    assert result["status"] == "success"
    call_kwargs = mock_apify_client.actor.return_value.call.call_args.kwargs
    run_input = call_kwargs["run_input"]
    assert run_input["startUrls"] == [{"url": "https://www.facebook.com/apify"}]
    assert run_input["resultsLimit"] == 10
    assert "onlyPostsNewerThan" not in run_input
    mock_apify_client.actor.assert_called_once_with("apify/facebook-posts-scraper")


def test_facebook_posts_scraper_with_date_filter(mock_apify_env, mock_apify_client):
    """Facebook posts scraper passes onlyPostsNewerThan when provided."""
    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_facebook_posts_scraper(
            page_url="https://www.facebook.com/apify",
            only_posts_newer_than="2024-01-01",
        )

    assert result["status"] == "success"
    run_input = mock_apify_client.actor.return_value.call.call_args.kwargs["run_input"]
    assert run_input["onlyPostsNewerThan"] == "2024-01-01"


def test_facebook_posts_scraper_invalid_page_url(mock_apify_env):
    """Facebook posts scraper returns error for non-http(s) page_url."""
    result = apify_facebook_posts_scraper(page_url="not-a-url")

    assert result["status"] == "error"
    assert "Invalid URL" in result["content"][0]["text"]


def test_twitter_scraper_invalid_url_in_list(mock_apify_env):
    """Twitter scraper returns error when any URL in the list is invalid; error names the index."""
    result = apify_twitter_scraper(urls=["https://x.com/valid", "ftp://bad"])

    assert result["status"] == "error"
    text = result["content"][0]["text"]
    assert "urls[1]" in text
    assert "Invalid URL scheme" in text


def test_tiktok_scraper_invalid_url_in_list(mock_apify_env):
    """TikTok scraper returns error when any URL in the list is invalid."""
    result = apify_tiktok_scraper(urls=["not-a-url"])

    assert result["status"] == "error"
    assert "urls[0]" in result["content"][0]["text"]


def test_instagram_scraper_invalid_url_in_list(mock_apify_env):
    """Instagram scraper returns error when any URL in the urls list is invalid."""
    result = apify_instagram_scraper(urls=["https://www.instagram.com/apify/", "javascript:alert(1)"])

    assert result["status"] == "error"
    assert "urls[1]" in result["content"][0]["text"]


# --- Social media: dependency and token guards ---


def test_social_media_missing_dependency(mock_apify_env):
    """Social media tools return error when apify-client is not installed."""
    with patch("strands_apify.utils.HAS_APIFY_CLIENT", False):
        result = apify_instagram_scraper(search_query="test")

    assert result["status"] == "error"
    assert "apify-client" in result["content"][0]["text"]


def test_social_media_missing_token(monkeypatch):
    """Social media tools return error when APIFY_TOKEN is missing."""
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    result = apify_twitter_scraper(search_query="test")

    assert result["status"] == "error"
    assert "APIFY_TOKEN" in result["content"][0]["text"]


def test_social_media_actor_failure(mock_apify_env, mock_apify_client):
    """Social media tools return error when the underlying Actor run fails."""
    mock_apify_client.actor.return_value.call.return_value = MOCK_FAILED_RUN

    with patch("strands_apify.utils.ApifyClient", return_value=mock_apify_client):
        result = apify_facebook_posts_scraper(page_url="https://www.facebook.com/apify")

    assert result["status"] == "error"
    assert "FAILED" in result["content"][0]["text"]
