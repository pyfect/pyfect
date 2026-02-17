"""Tests for for_each control flow combinator."""

import pytest

from pyfect import effect

# ── Sequential, collecting ───────────────────────────────────────────────────


def test_for_each_basic() -> None:
    """for_each should apply effect to each element and collect results."""
    result = effect.for_each(
        [1, 2, 3, 4, 5],
        lambda n, _: effect.succeed(n * 2),
    )
    assert effect.run_sync(result) == [2, 4, 6, 8, 10]


def test_for_each_empty_iterable() -> None:
    """for_each with empty iterable returns empty list."""
    result = effect.for_each(
        [],
        lambda n, _: effect.succeed(n),
    )
    assert effect.run_sync(result) == []


def test_for_each_single_element() -> None:
    """for_each with single element returns single-element list."""
    result = effect.for_each(
        [42],
        lambda n, _: effect.succeed(n * 2),
    )
    assert effect.run_sync(result) == [84]


def test_for_each_with_index() -> None:
    """for_each body receives correct index for each element."""
    result = effect.for_each(
        ["a", "b", "c"],
        lambda elem, i: effect.succeed((i, elem)),
    )
    assert effect.run_sync(result) == [(0, "a"), (1, "b"), (2, "c")]


def test_for_each_preserves_order() -> None:
    """for_each executes effects in order and preserves result order."""
    executed: list[int] = []
    result = effect.for_each(
        [1, 2, 3],
        lambda n, _: effect.sync(lambda: executed.append(n) or n),
    )
    final = effect.run_sync(result)
    assert executed == [1, 2, 3]
    assert final == [1, 2, 3]


def test_for_each_short_circuits_on_failure() -> None:
    """for_each stops immediately when an effect fails."""
    executed: list[int] = []

    def body(n: int, _: int) -> effect.Effect[int, ValueError]:
        if n == 3:  # noqa: PLR2004
            return effect.fail(ValueError("stop at 3"))
        return effect.sync(lambda: executed.append(n) or n)

    result = effect.for_each([1, 2, 3, 4, 5], body)

    with pytest.raises(ValueError, match="stop at 3"):
        effect.run_sync(result)

    # Only 1 and 2 were processed before failure
    assert executed == [1, 2]


def test_for_each_with_tuple() -> None:
    """for_each works with tuple iterables."""
    result = effect.for_each(
        (10, 20, 30),
        lambda n, i: effect.succeed(n + i),
    )
    assert effect.run_sync(result) == [10, 21, 32]


def test_for_each_with_string() -> None:
    """for_each works with string iterables."""
    result = effect.for_each(
        "abc",
        lambda char, i: effect.succeed((i, char.upper())),
    )
    assert effect.run_sync(result) == [(0, "A"), (1, "B"), (2, "C")]


def test_for_each_with_exit_success() -> None:
    """run_sync_exit returns Success with list for successful for_each."""
    result = effect.for_each(
        [1, 2, 3],
        lambda n, _: effect.succeed(n * 2),
    )
    match effect.run_sync_exit(result):
        case effect.Success(value):
            assert value == [2, 4, 6]
        case effect.Failure(e):
            msg = f"Unexpected failure: {e}"
            raise AssertionError(msg)


def test_for_each_with_exit_failure() -> None:
    """run_sync_exit captures failure from for_each body."""
    result = effect.for_each(
        [1, 2, 3],
        lambda n, _: effect.fail("bad") if n == 2 else effect.succeed(n),  # noqa: PLR2004
    )
    match effect.run_sync_exit(result):
        case effect.Failure(e):
            assert e == "bad"
        case effect.Success(_):
            msg = "Expected failure"
            raise AssertionError(msg)


# ── Sequential, discarding ───────────────────────────────────────────────────


def test_for_each_discard_returns_none() -> None:
    """for_each with discard=True returns None."""
    result = effect.for_each(
        [1, 2, 3],
        lambda n, i: effect.succeed(n * 2),
        discard=True,
    )
    assert effect.run_sync(result) is None


def test_for_each_discard_executes_all() -> None:
    """for_each with discard=True still executes all effects."""
    executed: list[int] = []
    result = effect.for_each(
        [1, 2, 3, 4, 5],
        lambda n, i: effect.sync(lambda: executed.append(n)),
        discard=True,
    )
    effect.run_sync(result)
    assert executed == [1, 2, 3, 4, 5]


def test_for_each_discard_empty_returns_none() -> None:
    """for_each with discard=True and empty iterable returns None."""
    result = effect.for_each(
        [],
        lambda n, i: effect.succeed(n),
        discard=True,
    )
    assert effect.run_sync(result) is None


def test_for_each_discard_failure_propagates() -> None:
    """for_each with discard=True still propagates failures."""
    result = effect.for_each(
        [1, 2, 3],
        lambda n, _: effect.fail(RuntimeError("oops")) if n == 2 else effect.succeed(n),  # noqa: PLR2004
        discard=True,
    )
    with pytest.raises(RuntimeError, match="oops"):
        effect.run_sync(result)


# ── Async ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_for_each_async() -> None:
    """for_each works with async runtime."""
    result = effect.for_each(
        [1, 2, 3, 4],
        lambda n, _: effect.succeed(n * 2),
    )
    assert await effect.run_async(result) == [2, 4, 6, 8]


@pytest.mark.asyncio
async def test_for_each_async_discard() -> None:
    """for_each with discard=True works with async runtime."""
    executed: list[int] = []
    result = effect.for_each(
        [1, 2, 3],
        lambda n, _: effect.sync(lambda: executed.append(n)),
        discard=True,
    )
    assert await effect.run_async(result) is None
    assert executed == [1, 2, 3]


# ── Concurrent ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_for_each_concurrent_collects() -> None:
    """for_each with concurrent=True collects results."""
    result = effect.for_each(
        [1, 2, 3, 4],
        lambda n, _: effect.succeed(n * 2),
        concurrent=True,
    )
    assert await effect.run_async(result) == [2, 4, 6, 8]


@pytest.mark.asyncio
async def test_for_each_concurrent_empty() -> None:
    """for_each concurrent with empty iterable returns empty list."""
    result = effect.for_each(
        [],
        lambda n, _: effect.succeed(n),
        concurrent=True,
    )
    assert await effect.run_async(result) == []


@pytest.mark.asyncio
async def test_for_each_concurrent_discard() -> None:
    """for_each with concurrent=True and discard=True returns None."""
    executed: list[int] = []
    result = effect.for_each(
        [1, 2, 3],
        lambda n, _: effect.sync(lambda: executed.append(n)),
        concurrent=True,
        discard=True,
    )
    assert await effect.run_async(result) is None
    # All should have executed (order not guaranteed in concurrent mode)
    assert sorted(executed) == [1, 2, 3]


@pytest.mark.asyncio
async def test_for_each_concurrent_with_async_effects() -> None:
    """for_each concurrent works with async effects."""

    async def async_double(n: int) -> int:
        return n * 2

    result = effect.for_each(
        [1, 2, 3],
        lambda n, _: effect.async_(lambda: async_double(n)),
        concurrent=True,
    )
    assert await effect.run_async(result) == [2, 4, 6]
