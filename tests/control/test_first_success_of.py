"""Tests for effect.first_success_of."""

import pytest

from pyfect import effect


def test_first_success_of_returns_first_success() -> None:
    eff = effect.first_success_of(
        [
            effect.fail("node1 down"),
            effect.fail("node2 down"),
            effect.succeed("node3 ok"),
        ]
    )
    result = effect.run_sync(eff)
    assert result == "node3 ok"


def test_first_success_of_returns_first_effect_if_it_succeeds() -> None:
    eff = effect.first_success_of(
        [
            effect.succeed("first"),
            effect.succeed("second"),
        ]
    )
    result = effect.run_sync(eff)
    assert result == "first"


def test_first_success_of_fails_with_last_error_if_all_fail() -> None:
    eff = effect.first_success_of(
        [
            effect.fail("error1"),
            effect.fail("error2"),
            effect.fail("error3"),
        ]
    )
    result = effect.run_sync_exit(eff)
    assert isinstance(result, effect.Failure)
    assert result.error == "error3"


def test_first_success_of_single_success() -> None:
    eff = effect.first_success_of([effect.succeed(42)])
    result = effect.run_sync(eff)
    assert result == 42  # noqa: PLR2004


def test_first_success_of_single_failure() -> None:
    eff = effect.first_success_of([effect.fail("only error")])
    result = effect.run_sync_exit(eff)
    assert isinstance(result, effect.Failure)
    assert result.error == "only error"


def test_first_success_of_empty_raises() -> None:
    with pytest.raises(ValueError, match="at least one effect"):
        effect.first_success_of([])


def test_first_success_of_stops_at_first_success() -> None:
    """Effects after the first success are never executed."""
    executed: list[str] = []

    eff = effect.first_success_of(
        [
            effect.fail("error"),
            effect.sync(lambda: (executed.append("second"), "found")[1]),
            effect.sync(lambda: (executed.append("third"), "not reached")[1]),
        ]
    )
    effect.run_sync(eff)
    assert executed == ["second"]


def test_first_success_of_type_inference() -> None:
    """Hover over eff — should show Effect[str, int, Never]."""

    def failing(e: int) -> effect.Effect[str, int]:
        return effect.fail(e)

    eff = effect.first_success_of([failing(1), failing(2), effect.succeed("ok")])
    result = effect.run_sync(eff)
    assert result == "ok"


def test_first_success_of_heterogeneous_type_inference() -> None:
    """Hover over eff — should show Effect[int | str, ValueError | TypeError, Never]."""

    def fail_value() -> effect.Effect[int, ValueError]:
        return effect.fail(ValueError("v"))

    def fail_type() -> effect.Effect[str, TypeError]:
        return effect.fail(TypeError("t"))

    def succeed_int() -> effect.Effect[int, TypeError]:
        return effect.succeed(42)

    eff = effect.first_success_of([fail_value(), fail_type(), succeed_int()])
    result = effect.run_sync(eff)
    assert result == 42  # noqa: PLR2004


@pytest.mark.asyncio
async def test_first_success_of_async_returns_first_success() -> None:
    eff = effect.first_success_of(
        [
            effect.fail("async error1"),
            effect.fail("async error2"),
            effect.succeed("async ok"),
        ]
    )
    result = await effect.run_async(eff)
    assert result == "async ok"


@pytest.mark.asyncio
async def test_first_success_of_async_fails_with_last_error() -> None:
    eff = effect.first_success_of(
        [
            effect.fail("e1"),
            effect.fail("e2"),
        ]
    )
    result = await effect.run_async_exit(eff)
    assert isinstance(result, effect.Failure)
    assert result.error == "e2"
