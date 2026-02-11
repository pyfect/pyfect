"""Tests for run_async missing coverage branches."""

import pytest

from pyfect import effect


async def test_fail_non_exception_raises_runtime_error() -> None:
    with pytest.raises(RuntimeError, match="effect failed: oops"):
        await effect.run_async(effect.fail("oops"))


async def test_map_error_exception_from_non_exception_error() -> None:
    eff = effect.map_error(lambda s: ValueError(str(s)))(effect.fail("bad"))
    with pytest.raises(ValueError, match="bad"):
        await effect.run_async(eff)


async def test_map_error_non_exception_transformed_raises_runtime_error() -> None:
    eff = effect.map_error(lambda s: f"wrapped: {s}")(effect.fail("bad"))
    with pytest.raises(RuntimeError, match="effect failed: wrapped: bad"):
        await effect.run_async(eff)


async def test_try_sync_succeeds_in_run_async() -> None:
    result = await effect.run_async(effect.try_sync(lambda: 42))
    assert result == 42  # noqa: PLR2004
