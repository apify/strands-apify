"""The `(clamped to N max by default)` note in each tool description must match the ceiling the code applies."""

import pytest

from strands_apify import APIFY_ALL_TOOLS
from strands_apify.social_media import LINKEDIN_POSTS_MAX_RESULTS
from strands_apify.utils import MAX_CRAWL_DEPTH, MAX_ITEMS, MAX_MEMORY_MBYTES, MAX_TIMEOUT_SECS

CEILINGS = {
    "timeout_secs": MAX_TIMEOUT_SECS,
    "memory_mbytes": MAX_MEMORY_MBYTES,
    "limit": MAX_ITEMS,
    "dataset_items_limit": MAX_ITEMS,
    "results_limit": MAX_ITEMS,
    "search_limit": MAX_ITEMS,
    "max_reviews": MAX_ITEMS,
    "max_pages": MAX_ITEMS,
    "max_depth": MAX_CRAWL_DEPTH,
}
# Parameters whose effective ceiling is lower than the general one.
LOWER_CEILINGS = {("apify_linkedin_profile_posts", "results_limit"): LINKEDIN_POSTS_MAX_RESULTS}

PARAMETERS = [
    (tool.tool_name, name, prop["description"])
    for tool in APIFY_ALL_TOOLS
    for name, prop in tool.tool_spec["inputSchema"]["json"]["properties"].items()
]
CLAMPED = [
    pytest.param(tool_name, name, description, id=f"{tool_name}-{name}")
    for tool_name, name, description in PARAMETERS
    if name in CEILINGS
]
UNCLAMPED = [
    pytest.param(tool_name, name, description, id=f"{tool_name}-{name}")
    for tool_name, name, description in PARAMETERS
    if name not in CEILINGS
]


@pytest.mark.parametrize(("tool_name", "param", "description"), CLAMPED)
def test_clamped_parameter_states_its_ceiling(tool_name, param, description):
    """Each clamped parameter's description states the ceiling the code applies."""
    ceiling = LOWER_CEILINGS.get((tool_name, param), CEILINGS[param])

    assert f"(clamped to {ceiling} max by default)" in description


@pytest.mark.parametrize(("tool_name", "param", "description"), UNCLAMPED)
def test_unclamped_parameter_does_not_claim_a_ceiling(tool_name, param, description):
    """No other parameter's description claims a ceiling."""
    assert "clamped to" not in description
