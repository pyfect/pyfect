"""Tests for run_sync_exit missing coverage branches."""

import asyncio

import pytest

from pyfect import effect


def test_tap_on_failure_returns_failure() -> None:
    eff = effect.tap(lambda _: effect.succeed(None))(effect.fail("oops"))
    result = effect.run_sync_exit(eff)
    assert isinstance(result, effect.Failure)
    assert result.error == "oops"


def test_async_primitive_raises_runtime_error() -> None:
    eff = effect.async_(lambda: asyncio.sleep(0))
    with pytest.raises(RuntimeError, match="Cannot run Async synchronously"):
        effect.run_sync_exit(eff)
