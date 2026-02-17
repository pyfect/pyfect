"""Tests for the effect.loop combinator."""

import pytest

from pyfect import effect

# ── Collecting (discard=False) ────────────────────────────────────────────────


def test_loop_collects_results() -> None:
    """loop collects body results into a list."""
    result = effect.loop(
        1,
        while_=lambda s: s <= 5,  # noqa: PLR2004
        step=lambda s: s + 1,
        body=effect.succeed,
    )
    assert effect.run_sync(result) == [1, 2, 3, 4, 5]


def test_loop_zero_iterations_returns_empty_list() -> None:
    """When the condition is False from the start, an empty list is returned."""
    result = effect.loop(
        10,
        while_=lambda s: s <= 5,  # noqa: PLR2004
        step=lambda s: s + 1,
        body=effect.succeed,
    )
    assert effect.run_sync(result) == []


def test_loop_single_iteration() -> None:
    """Loop that runs exactly once returns a single-element list."""
    result = effect.loop(
        5,
        while_=lambda s: s <= 5,  # noqa: PLR2004
        step=lambda s: s + 1,
        body=effect.succeed,
    )
    assert effect.run_sync(result) == [5]


def test_loop_body_transforms_state() -> None:
    """Body can produce a different value than the raw state."""
    result = effect.loop(
        1,
        while_=lambda s: s <= 4,  # noqa: PLR2004
        step=lambda s: s + 1,
        body=lambda s: effect.succeed(s * s),
    )
    assert effect.run_sync(result) == [1, 4, 9, 16]


def test_loop_runs_effects_in_order() -> None:
    """Body effects execute in iteration order."""
    executed: list[int] = []
    result = effect.loop(
        1,
        while_=lambda s: s <= 3,  # noqa: PLR2004
        step=lambda s: s + 1,
        body=lambda s: effect.sync(lambda: executed.append(s) or s),  # type: ignore[func-returns-value]
    )
    effect.run_sync(result)
    assert executed == [1, 2, 3]


def test_loop_body_failure_propagates() -> None:
    """If body fails on any iteration, the error propagates immediately."""
    executed: list[int] = []

    def body(s: int) -> effect.Effect[int, ValueError]:
        if s == 3:  # noqa: PLR2004
            return effect.fail(ValueError("stop at 3"))
        return effect.sync(lambda: executed.append(s) or s)  # type: ignore[func-returns-value]

    result = effect.loop(
        1,
        while_=lambda s: s <= 5,  # noqa: PLR2004
        step=lambda s: s + 1,
        body=body,
    )
    with pytest.raises(ValueError, match="stop at 3"):
        effect.run_sync(result)
    assert executed == [1, 2]


def test_loop_with_exit_success() -> None:
    """run_sync_exit returns Success(list) for a successful loop."""
    result = effect.loop(
        1,
        while_=lambda s: s <= 3,  # noqa: PLR2004
        step=lambda s: s + 1,
        body=effect.succeed,
    )
    match effect.run_sync_exit(result):
        case effect.Success(value):
            assert value == [1, 2, 3]
        case effect.Failure(e):
            msg = f"Unexpected failure: {e}"
            raise AssertionError(msg)


def test_loop_with_exit_failure() -> None:
    """run_sync_exit captures body failure."""
    result = effect.loop(
        1,
        while_=lambda s: s <= 3,  # noqa: PLR2004
        step=lambda s: s + 1,
        body=lambda s: effect.fail("bad") if s == 2 else effect.succeed(s),  # type: ignore[return-value]  # noqa: PLR2004
    )
    match effect.run_sync_exit(result):
        case effect.Failure(e):
            assert e == "bad"
        case effect.Success(_):
            msg = "Expected failure"
            raise AssertionError(msg)


# ── Discarding (discard=True) ─────────────────────────────────────────────────


def test_loop_discard_returns_none() -> None:
    """With discard=True, loop returns None."""
    result = effect.loop(
        1,
        while_=lambda s: s <= 3,  # noqa: PLR2004
        step=lambda s: s + 1,
        body=lambda s: effect.sync(lambda: print(s)),
        discard=True,
    )
    assert effect.run_sync(result) is None


def test_loop_discard_runs_all_iterations() -> None:
    """With discard=True, all body effects still execute."""
    executed: list[int] = []
    result = effect.loop(
        1,
        while_=lambda s: s <= 5,  # noqa: PLR2004
        step=lambda s: s + 1,
        body=lambda s: effect.sync(lambda: executed.append(s)),
        discard=True,
    )
    effect.run_sync(result)
    assert executed == [1, 2, 3, 4, 5]


def test_loop_discard_zero_iterations_returns_none() -> None:
    """With discard=True and no iterations, returns None."""
    result = effect.loop(
        10,
        while_=lambda s: s <= 5,  # noqa: PLR2004
        step=lambda s: s + 1,
        body=effect.succeed,
        discard=True,
    )
    assert effect.run_sync(result) is None


def test_loop_discard_failure_propagates() -> None:
    """With discard=True, body failures still propagate."""
    result = effect.loop(
        1,
        while_=lambda s: s <= 3,  # noqa: PLR2004
        step=lambda s: s + 1,
        body=lambda s: effect.fail(RuntimeError("oops")) if s == 2 else effect.succeed(s),  # type: ignore[return-value]  # noqa: PLR2004
        discard=True,
    )
    with pytest.raises(RuntimeError, match="oops"):
        effect.run_sync(result)


# ── Async ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_loop_async_collects_results() -> None:
    """loop works with the async runtime."""
    result = effect.loop(
        1,
        while_=lambda s: s <= 4,  # noqa: PLR2004
        step=lambda s: s + 1,
        body=effect.succeed,
    )
    assert await effect.run_async(result) == [1, 2, 3, 4]


@pytest.mark.asyncio
async def test_loop_async_discard() -> None:
    """loop with discard=True works with the async runtime."""
    executed: list[int] = []
    result = effect.loop(
        1,
        while_=lambda s: s <= 3,  # noqa: PLR2004
        step=lambda s: s + 1,
        body=lambda s: effect.sync(lambda: executed.append(s)),
        discard=True,
    )
    assert await effect.run_async(result) is None
    assert executed == [1, 2, 3]


def test_loop_with_tuple_state() -> None:
    """loop should handle tuple state with mixed literals."""
    result = effect.loop(
        (5, 1),  # (counter, accumulator)
        while_=lambda state: state[0] > 0,
        step=lambda state: (state[0] - 1, state[1] * state[0]),
        body=effect.succeed,
    )

    final = effect.run_sync(result)
    # Should collect all states where condition is true
    assert len(final) == 5  # noqa: PLR2004
    assert final[-1] == (1, 120)  # Last state where counter > 0
    # Final accumulator value is in the tuple
    assert final[-1][1] == 120  # noqa: PLR2004
