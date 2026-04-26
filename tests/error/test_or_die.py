"""Tests for effect.or_die."""

import pytest

from pyfect import effect, pipe


def test_or_die_success_passes_through() -> None:
    result = effect.run_sync(pipe(effect.succeed(42), effect.or_die()))
    assert result == 42  # noqa: PLR2004


def test_or_die_base_exception_raised_as_defect() -> None:
    eff = pipe(effect.fail(ValueError("unrecoverable")), effect.or_die())
    with pytest.raises(ValueError, match="unrecoverable"):
        effect.run_sync(eff)


def test_or_die_non_exception_wrapped_in_runtime_error() -> None:
    eff = pipe(effect.fail("plain string error"), effect.or_die())
    with pytest.raises(RuntimeError, match="plain string error"):
        effect.run_sync(eff)


def test_or_die_defect_bypasses_exit() -> None:
    """or_die produces a defect — it raises even with run_sync_exit."""
    eff = pipe(effect.fail(ValueError("defect")), effect.or_die())
    with pytest.raises(ValueError):  # noqa: PT011
        effect.run_sync_exit(eff)


def test_or_die_type_inference() -> None:
    """Hover over eff — error type should be Never."""

    def make_failing_effect() -> effect.Effect[int, ValueError]:
        return effect.fail(ValueError("oops"))

    eff = pipe(make_failing_effect(), effect.or_die())
    with pytest.raises(ValueError):  # noqa: PT011
        effect.run_sync(eff)


@pytest.mark.asyncio
async def test_or_die_async_success_passes_through() -> None:
    result = await effect.run_async(pipe(effect.succeed("hello"), effect.or_die()))
    assert result == "hello"


@pytest.mark.asyncio
async def test_or_die_async_failure_raises() -> None:
    eff = pipe(effect.fail(RuntimeError("async defect")), effect.or_die())
    with pytest.raises(RuntimeError, match="async defect"):
        await effect.run_async(eff)
