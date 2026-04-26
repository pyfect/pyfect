"""Tests for effect.or_die_with."""

import pytest

from pyfect import effect, pipe


def test_or_die_with_success_passes_through() -> None:
    eff = pipe(
        effect.succeed(42),
        effect.or_die_with(lambda e: RuntimeError(f"defect: {e}")),
    )
    result = effect.run_sync(eff)
    assert result == 42  # noqa: PLR2004


def test_or_die_with_applies_transform_then_raises() -> None:
    eff = pipe(
        effect.fail("something went wrong"),
        effect.or_die_with(lambda e: RuntimeError(f"defect: {e}")),
    )
    with pytest.raises(RuntimeError, match="defect: something went wrong"):
        effect.run_sync(eff)


def test_or_die_with_custom_exception_type() -> None:
    class DomainDefectError(Exception):
        pass

    def to_defect(e: str) -> DomainDefectError:
        return DomainDefectError(e)

    eff = pipe(effect.fail("bad"), effect.or_die_with(to_defect))
    with pytest.raises(DomainDefectError, match="bad"):
        effect.run_sync(eff)


def test_or_die_with_type_inference() -> None:
    """Hover over eff — error type should be Never."""

    def to_defect(e: ValueError) -> RuntimeError:
        return RuntimeError(str(e))

    eff = pipe(effect.fail(ValueError("oops")), effect.or_die_with(to_defect))
    with pytest.raises(RuntimeError):
        effect.run_sync(eff)


@pytest.mark.asyncio
async def test_or_die_with_async_success_passes_through() -> None:
    result = await effect.run_async(
        pipe(
            effect.succeed("hello"),
            effect.or_die_with(lambda e: RuntimeError(str(e))),
        )
    )
    assert result == "hello"


@pytest.mark.asyncio
async def test_or_die_with_async_failure_raises() -> None:
    eff = pipe(
        effect.fail("async error"),
        effect.or_die_with(lambda e: ValueError(f"mapped: {e}")),
    )
    with pytest.raises(ValueError, match="mapped: async error"):
        await effect.run_async(eff)
