"""Tests for effect.match_ and effect.match_effect."""

import pytest

from pyfect import effect, pipe

# ============================================================================
# match_
# ============================================================================


def test_match_success() -> None:
    eff = pipe(
        effect.succeed(42),
        effect.match_(
            on_failure=lambda e: f"failed: {e}",
            on_success=lambda v: f"got: {v}",
        ),
    )
    result = effect.run_sync(eff)
    assert result == "got: 42"


def test_match_failure() -> None:
    eff = pipe(
        effect.fail("oops"),
        effect.match_(
            on_failure=lambda e: f"failed: {e}",
            on_success=lambda v: f"got: {v}",
        ),
    )
    result = effect.run_sync(eff)
    assert result == "failed: oops"


def test_match_error_type_erased() -> None:
    """After match_, the effect always succeeds — error type is Never."""
    eff = pipe(
        effect.fail("gone"),
        effect.match_(on_failure=lambda _: "default", on_success=lambda v: v),
    )
    result = effect.run_sync_exit(eff)
    assert isinstance(result, effect.Success)


def test_match_type_inference_homogeneous() -> None:
    """Hover over eff — both handlers return str, so Effect[str, Never, Never]."""

    def on_fail(e: int) -> str:
        return f"error {e}"

    def on_ok(v: str) -> str:
        return f"ok {v}"

    eff = pipe(effect.fail(404), effect.match_(on_failure=on_fail, on_success=on_ok))
    result = effect.run_sync(eff)
    assert result == "error 404"


def test_match_type_inference_heterogeneous() -> None:
    """Hover over eff — handlers return different types, so Effect[int | str, Never, Never]."""

    def on_fail(e: str) -> int:
        return -1

    def on_ok(v: int) -> str:
        return f"value: {v}"

    eff = pipe(effect.succeed(42), effect.match_(on_failure=on_fail, on_success=on_ok))
    result = effect.run_sync(eff)
    assert result == "value: 42"


@pytest.mark.asyncio
async def test_match_async_success() -> None:
    eff = pipe(
        effect.succeed(10),
        effect.match_(on_failure=lambda _: 0, on_success=lambda v: v * 2),
    )
    result = await effect.run_async(eff)
    assert result == 20  # noqa: PLR2004


@pytest.mark.asyncio
async def test_match_async_failure() -> None:
    eff = pipe(
        effect.fail("async error"),
        effect.match_(on_failure=lambda e: f"caught: {e}", on_success=lambda v: v),
    )
    result = await effect.run_async(eff)
    assert result == "caught: async error"


# ============================================================================
# match_effect
# ============================================================================


def test_match_effect_success() -> None:
    executed: list[str] = []

    eff = pipe(
        effect.succeed(42),
        effect.match_effect(
            on_failure=lambda e: effect.sync(lambda: (executed.append(f"fail:{e}"), "")[1]),
            on_success=lambda v: effect.sync(lambda: (executed.append(f"ok:{v}"), "")[1]),
        ),
    )
    effect.run_sync(eff)
    assert executed == ["ok:42"]


def test_match_effect_failure() -> None:
    executed: list[str] = []

    eff = pipe(
        effect.fail("oops"),
        effect.match_effect(
            on_failure=lambda e: effect.sync(lambda: (executed.append(f"fail:{e}"), "")[1]),
            on_success=lambda v: effect.sync(lambda: (executed.append(f"ok:{v}"), "")[1]),
        ),
    )
    effect.run_sync(eff)
    assert executed == ["fail:oops"]


def test_match_effect_type_inference() -> None:
    """Hover over eff — handlers return Effect[str, ValueError, Never],
    so Effect[str, ValueError, Never]."""

    def on_fail(e: int) -> effect.Effect[str, ValueError]:
        return effect.fail(ValueError(f"bad: {e}"))

    def on_ok(v: int) -> effect.Effect[str, ValueError]:
        return effect.succeed(f"got {v}")

    eff = pipe(effect.succeed(10), effect.match_effect(on_failure=on_fail, on_success=on_ok))
    result = effect.run_sync(eff)
    assert result == "got 10"


def test_match_effect_heterogeneous_type_inference() -> None:
    """Hover over eff — on_failure returns Effect[int, ...], on_success returns Effect[str, ...],
    so Effect[int | str, ValueError, Never]."""

    def on_fail(e: str) -> effect.Effect[int, ValueError]:
        return effect.succeed(-1)

    def on_ok(v: int) -> effect.Effect[str, ValueError]:
        return effect.succeed(f"value: {v}")

    eff = pipe(effect.fail("error"), effect.match_effect(on_failure=on_fail, on_success=on_ok))
    result = effect.run_sync(eff)
    assert result == -1


@pytest.mark.asyncio
async def test_match_effect_async_failure() -> None:
    eff = pipe(
        effect.fail("async error"),
        effect.match_effect(
            on_failure=lambda e: effect.succeed(f"caught: {e}"),
            on_success=effect.succeed,
        ),
    )
    result = await effect.run_async(eff)
    assert result == "caught: async error"
