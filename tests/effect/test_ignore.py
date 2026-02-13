"""Tests for the ignore combinator."""

import asyncio

import pytest

from pyfect import effect, pipe


def test_ignore_success() -> None:
    """Test that ignore discards success value."""
    result = pipe(
        effect.succeed(42),
        effect.ignore(),
    )
    assert effect.run_sync(result) is None


def test_ignore_failure() -> None:
    """Test that ignore also discards failures."""
    result = pipe(
        effect.fail("error"),
        effect.ignore(),
    )
    # No exception raised - error is ignored
    assert effect.run_sync(result) is None


def test_ignore_with_exception() -> None:
    """Test that ignore catches exceptions too."""

    def will_fail() -> int:
        msg = "computation failed"
        raise ValueError(msg)

    result = pipe(
        effect.try_sync(will_fail),
        effect.ignore(),
    )
    # No exception raised - error is ignored
    assert effect.run_sync(result) is None


async def test_ignore_async_success() -> None:
    """Test ignore with async effects that succeed."""

    async def async_value() -> int:
        await asyncio.sleep(0.01)
        return 42

    result = pipe(
        effect.async_(async_value),
        effect.ignore(),
    )
    assert await effect.run_async(result) is None


async def test_ignore_async_failure() -> None:
    """Test ignore with async effects that fail."""

    async def will_fail() -> int:
        await asyncio.sleep(0.01)
        msg = "async error"
        raise ValueError(msg)

    result = pipe(
        effect.try_async(will_fail),
        effect.ignore(),
    )
    # No exception raised - error is ignored
    assert await effect.run_async(result) is None


def test_ignore_with_exit() -> None:
    """Test that ignore always produces Success(None)."""
    result = pipe(
        effect.succeed(42),
        effect.ignore(),
    )
    exit_result = effect.run_sync_exit(result)

    match exit_result:
        case effect.Success(value):
            assert value is None
        case effect.Failure(_):
            pytest.fail("Ignore should never fail")


def test_ignore_failure_with_exit() -> None:
    """Test that ignore converts failures to Success(None)."""
    result = pipe(
        effect.fail("error"),
        effect.ignore(),
    )
    exit_result = effect.run_sync_exit(result)

    match exit_result:
        case effect.Success(value):
            assert value is None
        case effect.Failure(_):
            pytest.fail("Ignore should never fail")


async def test_ignore_async_exit() -> None:
    """Test ignore with async exit."""

    async def async_value() -> int:
        await asyncio.sleep(0.01)
        return 42

    result = pipe(
        effect.async_(async_value),
        effect.ignore(),
    )
    exit_result = await effect.run_async_exit(result)

    match exit_result:
        case effect.Success(value):
            assert value is None
        case effect.Failure(_):
            pytest.fail("Ignore should never fail")


def test_ignore_side_effects_still_run() -> None:
    """Test that ignore still executes side effects."""
    executed = []

    result = pipe(
        effect.sync(lambda: executed.append("ran")),
        effect.ignore(),
    )

    assert len(executed) == 0  # Not run yet

    effect.run_sync(result)
    assert executed == ["ran"]  # Side effect executed


def test_ignore_in_chain() -> None:
    """Test ignore in a chain of effects."""
    values = []

    result = pipe(
        effect.succeed(10),
        effect.tap(lambda x: effect.sync(lambda: values.append(x))),
        effect.ignore(),
        effect.flat_map(lambda _: effect.succeed(20)),
        effect.tap(lambda x: effect.sync(lambda: values.append(x))),
    )

    final = effect.run_sync(result)
    assert final == 20  # noqa: PLR2004
    assert values == [10, 20]


def test_ignore_vs_as_none() -> None:
    """Test that ignore is different from as_(None) for failures."""
    # as_(None) doesn't catch errors
    with_as = pipe(
        effect.fail("error"),
        effect.as_(None),
    )
    with pytest.raises(RuntimeError, match="error"):
        effect.run_sync(with_as)

    # ignore catches errors
    with_ignore = pipe(
        effect.fail("error"),
        effect.ignore(),
    )
    assert effect.run_sync(with_ignore) is None


def test_ignore_for_fire_and_forget() -> None:
    """Test ignore for fire-and-forget operations."""
    log = []

    def risky_operation() -> str:
        log.append("attempted")
        msg = "operation failed"
        raise ValueError(msg)

    # We don't care if it fails
    result = pipe(
        effect.try_sync(risky_operation),
        effect.ignore(),
    )

    effect.run_sync(result)
    assert log == ["attempted"]
    # No exception raised despite the failure


def test_ignore_with_map_before() -> None:
    """Test ignore after map."""
    result = pipe(
        effect.succeed(10),
        effect.map(lambda x: x * 2),
        effect.ignore(),
    )
    assert effect.run_sync(result) is None


def test_ignore_with_flat_map_before() -> None:
    """Test ignore after flat_map."""
    result = pipe(
        effect.succeed(10),
        effect.flat_map(lambda x: effect.succeed(x * 2)),
        effect.ignore(),
    )
    assert effect.run_sync(result) is None


def test_ignore_doesnt_prevent_chaining() -> None:
    """Test that effects can be chained after ignore."""
    result = pipe(
        effect.succeed(42),
        effect.ignore(),  # Returns None
        effect.map(lambda _: "after ignore"),
    )
    assert effect.run_sync(result) == "after ignore"


def test_ignore_with_multiple_failures() -> None:
    """Test ignore with multiple potential failure points."""

    def first_fail() -> int:
        msg = "first error"
        raise ValueError(msg)

    result = pipe(
        effect.try_sync(first_fail),
        effect.ignore(),  # Catches first error
        effect.flat_map(lambda _: effect.fail("second error")),
        effect.ignore(),  # Catches second error
    )

    assert effect.run_sync(result) is None


def test_ignore_return_type_is_never() -> None:
    """Test that ignore returns Effect[None, Never, R]."""
    # This is more of a type-checking test, but we can verify the behavior

    result = pipe(
        effect.fail("error"),
        effect.ignore(),
    )

    # Should never raise
    exit_result = effect.run_sync_exit(result)

    # Should always be success
    match exit_result:
        case effect.Success(value):
            assert value is None
        case effect.Failure(_):
            pytest.fail("Effect[None, Never, R] should never fail")


async def test_ignore_async_exception_handling() -> None:
    """Test that ignore properly handles async exceptions."""

    async def async_fail() -> int:
        await asyncio.sleep(0.01)
        msg = "async failure"
        raise RuntimeError(msg)

    result = pipe(
        effect.try_async(async_fail),
        effect.ignore(),
    )

    # Should not raise
    assert await effect.run_async(result) is None


def test_ignore_preserves_context_type() -> None:
    """Test that ignore preserves the context type R."""
    # This is mainly for type checking, but we can verify behavior
    # Effect[int, str] -> ignore() -> Effect[None]

    result = pipe(
        effect.succeed(42),
        effect.ignore(),
    )

    assert effect.run_sync(result) is None


def test_ignore_example_from_docs() -> None:
    """Test the example from Effect-TS documentation."""
    # Effect.fail("Uh oh!").pipe(Effect.as(5))
    task = pipe(
        effect.fail("Uh oh!"),
        effect.as_(5),
    )

    # Effect.ignore(task) - should not care about success or failure
    program = pipe(task, effect.ignore())

    # Should succeed with None, no error raised
    assert effect.run_sync(program) is None
