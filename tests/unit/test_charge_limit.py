"""`STRANDS_APIFY_MAX_TOTAL_CHARGE_USD` caps what each Actor or task run may cost.

The developer sets it, never the LLM, so it is an environment variable and not a tool parameter. Every run gets it as
`max_total_charge_usd`, and an invalid value fails the tool instead of silently removing the cap.
"""

from collections.abc import Callable
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from strands_apify import (
    apify_google_search_scraper,
    apify_run_actor,
    apify_run_actor_and_get_dataset,
    apify_run_task,
    apify_run_task_and_get_dataset,
    apify_scrape_url,
)

ENV_VAR = 'STRANDS_APIFY_MAX_TOTAL_CHARGE_USD'

ignore_scrape_deprecation = pytest.mark.filterwarnings('ignore:apify_scrape_url is deprecated:FutureWarning')

# Every tool that starts a run, with the sub-client whose `.call()` receives the limit.
RUNS = [
    pytest.param(lambda: apify_run_actor(actor_id='actor/my-scraper'), 'actor', id='run_actor'),
    pytest.param(
        lambda: apify_run_actor_and_get_dataset(actor_id='actor/my-scraper'), 'actor', id='run_actor_and_get_dataset'
    ),
    pytest.param(lambda: apify_run_task(task_id='user~my-task'), 'task', id='run_task'),
    pytest.param(lambda: apify_run_task_and_get_dataset(task_id='user~my-task'), 'task', id='run_task_and_get_dataset'),
    pytest.param(lambda: apify_google_search_scraper(search_query='test'), 'actor', id='google_search_scraper'),
    pytest.param(
        lambda: apify_scrape_url(url='https://example.com'),
        'actor',
        id='scrape_url',
        marks=ignore_scrape_deprecation,
    ),
]


def _call_kwargs(mock_apify_client: MagicMock, sub_client: str) -> dict[str, Any]:
    return getattr(mock_apify_client, sub_client).return_value.call.call_args.kwargs


@pytest.mark.parametrize(('run', 'sub_client'), RUNS)
@pytest.mark.usefixtures('mock_apify_env')
def test_runs_carry_the_charge_limit(
    monkeypatch: pytest.MonkeyPatch, mock_apify_client: MagicMock, run: Callable[[], dict], sub_client: str
) -> None:
    monkeypatch.setenv(ENV_VAR, '0.1')

    with patch('strands_apify.utils.ApifyClient', return_value=mock_apify_client):
        result = run()

    assert result['status'] == 'success', result['content'][0]['text']
    # Parsed from the string, so the amount stays exact (`Decimal(0.1)` would not be).
    assert _call_kwargs(mock_apify_client, sub_client)['max_total_charge_usd'] == Decimal('0.1')


@pytest.mark.parametrize('value', [None, ''])
@pytest.mark.parametrize(('run', 'sub_client'), RUNS)
@pytest.mark.usefixtures('mock_apify_env')
def test_runs_have_no_charge_limit_by_default(
    monkeypatch: pytest.MonkeyPatch,
    mock_apify_client: MagicMock,
    run: Callable[[], dict],
    sub_client: str,
    value: str | None,
) -> None:
    if value is not None:
        monkeypatch.setenv(ENV_VAR, value)

    with patch('strands_apify.utils.ApifyClient', return_value=mock_apify_client):
        result = run()

    assert result['status'] == 'success', result['content'][0]['text']
    assert 'max_total_charge_usd' not in _call_kwargs(mock_apify_client, sub_client)


@pytest.mark.parametrize('value', ['abc', '0', '-1', 'nan', 'inf'])
@pytest.mark.parametrize(('run', 'sub_client'), RUNS)
@pytest.mark.usefixtures('mock_apify_env')
def test_an_invalid_charge_limit_fails_the_run(
    monkeypatch: pytest.MonkeyPatch,
    mock_apify_client: MagicMock,
    run: Callable[[], dict],
    sub_client: str,
    value: str,
) -> None:
    monkeypatch.setenv(ENV_VAR, value)

    with patch('strands_apify.utils.ApifyClient', return_value=mock_apify_client):
        result = run()

    assert result['status'] == 'error'
    assert ENV_VAR in result['content'][0]['text']
    getattr(mock_apify_client, sub_client).return_value.call.assert_not_called()
