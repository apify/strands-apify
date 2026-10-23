"""Tests for the ceilings applied to LLM-supplied numeric parameters."""

import logging

import pytest

from strands_apify.utils import (
    MAX_CRAWL_DEPTH,
    MAX_ITEMS,
    MAX_MEMORY_MBYTES,
    MAX_TIMEOUT_SECS,
    _clamp_depth,
    _clamp_items,
    _clamp_memory,
    _clamp_timeout,
)

CLAMPS = [
    (_clamp_timeout, MAX_TIMEOUT_SECS, "STRANDS_APIFY_MAX_TIMEOUT_SECS"),
    (_clamp_items, MAX_ITEMS, "STRANDS_APIFY_MAX_ITEMS"),
    (_clamp_depth, MAX_CRAWL_DEPTH, "STRANDS_APIFY_MAX_CRAWL_DEPTH"),
]


@pytest.mark.parametrize(("clamp", "cap", "env_var"), CLAMPS)
def test_clamp_caps_values_above_the_ceiling(clamp, cap, env_var):
    assert clamp(cap + 1) == cap
    assert clamp(cap * 1000) == cap


@pytest.mark.parametrize(("clamp", "cap", "env_var"), CLAMPS)
def test_clamp_keeps_values_within_the_ceiling(clamp, cap, env_var):
    assert clamp(cap) == cap
    assert clamp(1) == 1


@pytest.mark.parametrize("clamp", [_clamp_timeout, _clamp_items, _clamp_depth, _clamp_memory])
def test_clamp_leaves_low_values_to_the_validators(clamp):
    """Zero and negative values pass through unchanged, so the existing validators still reject them."""
    assert clamp(0) == 0
    assert clamp(-5) == -5


@pytest.mark.parametrize(("clamp", "cap", "env_var"), CLAMPS)
def test_clamp_ceiling_can_be_raised_from_the_environment(monkeypatch, clamp, cap, env_var):
    monkeypatch.setenv(env_var, str(cap * 10))

    assert clamp(cap * 5) == cap * 5
    assert clamp(cap * 20) == cap * 10


@pytest.mark.parametrize(("clamp", "cap", "env_var"), CLAMPS)
def test_clamp_ceiling_can_be_lowered_from_the_environment(monkeypatch, clamp, cap, env_var):
    monkeypatch.setenv(env_var, "1")

    assert clamp(cap) == 1


@pytest.mark.parametrize("raw", ["abc", "0", "-5", "1.5"])
@pytest.mark.parametrize(("clamp", "cap", "env_var"), CLAMPS)
def test_clamp_ignores_an_invalid_override(monkeypatch, caplog, clamp, cap, env_var, raw):
    monkeypatch.setenv(env_var, raw)

    with caplog.at_level(logging.WARNING):
        assert clamp(cap * 10) == cap

    assert env_var in caplog.text


@pytest.mark.parametrize(("clamp", "cap", "env_var"), CLAMPS)
def test_clamp_treats_an_empty_override_as_unset(monkeypatch, caplog, clamp, cap, env_var):
    monkeypatch.setenv(env_var, "")

    with caplog.at_level(logging.WARNING):
        assert clamp(cap * 10) == cap

    assert caplog.text == ""


@pytest.mark.parametrize(
    ("requested", "expected"),
    [
        (128, 128),
        (4096, 4096),
        (1000, 1024),
        (12345, 16384),
        (MAX_MEMORY_MBYTES, MAX_MEMORY_MBYTES),
        (100_000, MAX_MEMORY_MBYTES),
        (1, 128),
        (100, 128),
    ],
)
def test_clamp_memory_snaps_to_a_power_of_two_within_bounds(requested, expected):
    assert _clamp_memory(requested) == expected


def test_clamp_memory_rounds_down_when_rounding_up_would_exceed_the_ceiling(monkeypatch):
    monkeypatch.setenv("STRANDS_APIFY_MAX_MEMORY_MBYTES", "5000")

    assert _clamp_memory(4500) == 4096
    assert _clamp_memory(100_000) == 4096


def test_clamp_memory_ceiling_cannot_exceed_the_platform_maximum(monkeypatch):
    """The platform accepts at most 32768 MB, so a higher override has no effect."""
    monkeypatch.setenv("STRANDS_APIFY_MAX_MEMORY_MBYTES", "65536")

    assert _clamp_memory(40000) == MAX_MEMORY_MBYTES
    assert _clamp_memory(90000) == MAX_MEMORY_MBYTES


def test_clamp_memory_never_goes_below_the_platform_minimum(monkeypatch):
    """A ceiling set below 128 MB cannot produce a value the platform rejects."""
    monkeypatch.setenv("STRANDS_APIFY_MAX_MEMORY_MBYTES", "64")

    assert _clamp_memory(1024) == 128
