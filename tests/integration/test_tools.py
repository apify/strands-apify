"""Integration tests that call the Apify platform with the `APIFY_TOKEN` token.

They skip without the token. Keep Actor runs few and small: `apify/hello-world` is free, and Web Fetch fetches one
Apify-owned page.
"""

import json
import os
from typing import Any

import pytest
from apify_client import ApifyClient

from strands_apify import (
    apify_get_dataset_items,
    apify_run_actor,
    apify_run_actor_and_get_dataset,
    apify_web_fetch,
)

pytestmark = pytest.mark.skipif(not os.environ.get('APIFY_TOKEN'), reason='APIFY_TOKEN is not set')

HELLO_WORLD = 'apify/hello-world'


START = '<<<EXTERNAL_UNTRUSTED_CONTENT>>>\n'
END = '\n<<<END_EXTERNAL_UNTRUSTED_CONTENT>>>'


def _payload(result: dict[str, Any]) -> Any:
    """Return the tool's JSON payload, failing with the tool's error message if the call did not succeed.

    Third-party content comes wrapped in untrusted content markers, so those are checked and removed first.
    """
    text = result['content'][0]['text']
    assert result['status'] == 'success', text
    if text.startswith(START):
        assert text.endswith(END), text[-200:]
        text = text[len(START) : -len(END)].split('\n', 1)[1]
    return json.loads(text)


def test_run_actor() -> None:
    run = _payload(apify_run_actor(actor_id=HELLO_WORLD, timeout_secs=120, memory_mbytes=128))

    assert run['status'] == 'SUCCEEDED'
    assert run['run_id']
    assert run['dataset_id']


def test_run_actor_and_get_dataset() -> None:
    result = _payload(apify_run_actor_and_get_dataset(actor_id=HELLO_WORLD, timeout_secs=120, memory_mbytes=128))

    assert result['status'] == 'SUCCEEDED'
    assert isinstance(result['items'], list)


def test_get_dataset_items() -> None:
    client = ApifyClient(os.environ['APIFY_TOKEN'])
    # An unnamed dataset gets a unique ID, so parallel runs don't collide, and the test deletes it at the end.
    dataset = client.datasets().get_or_create()
    dataset_client = client.dataset(dataset.id)
    try:
        dataset_client.push_items([{'n': 1}, {'n': 2}, {'n': 3}])

        assert _payload(apify_get_dataset_items(dataset_id=dataset.id)) == [{'n': 1}, {'n': 2}, {'n': 3}]
        assert _payload(apify_get_dataset_items(dataset_id=dataset.id, limit=1, offset=1)) == [{'n': 2}]
    finally:
        dataset_client.delete()


def test_web_fetch() -> None:
    page = _payload(apify_web_fetch(url='https://docs.apify.com/'))

    assert page['http_status'] == 200
    assert 'Apify' in page['title']
    assert page['markdown']


def test_invalid_token_returns_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('APIFY_TOKEN', 'apify_api_invalid-token')

    result = apify_get_dataset_items(dataset_id='nonexistent-dataset')

    assert result['status'] == 'error'
