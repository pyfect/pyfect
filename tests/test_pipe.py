"""Tests for the pipe utility."""

import asyncio

import pytest

from pyfect import effect, pipe


def test_pipe_with_no_functions() -> None:
    """Test that pipe with no functions returns the value unchanged."""
    result = pipe(42)
    assert result == 42  # noqa: PLR2004


def test_pipe_with_single_function() -> None:
    """Test pipe with a single function."""
    result = pipe(10, lambda x: x * 2)
    assert result == 20  # noqa: PLR2004


def test_pipe_with_multiple_functions() -> None:
    """Test pipe with multiple functions."""
    result = pipe(10, lambda x: x + 1, lambda x: x * 2, lambda x: x - 3)
    assert result == 19  # noqa: PLR2004 (10 + 1 = 11, 11 * 2 = 22, 22 - 3 = 19)


def test_pipe_with_effects() -> None:
    """Test pipe composing effects."""
    executed = []

    result_effect = pipe(
        effect.succeed(42),
        effect.tap(lambda x: effect.sync(lambda: executed.append(f"First: {x}"))),
        effect.tap(lambda x: effect.sync(lambda: executed.append(f"Second: {x}"))),
    )

    result = effect.run_sync(result_effect)

    assert result == 42  # noqa: PLR2004
    assert executed == ["First: 42", "Second: 42"]


def test_pipe_with_mixed_effects() -> None:
    """Test pipe with different effect types."""
    executed = []

    result_effect = pipe(
        effect.sync(lambda: 100),
        effect.tap(lambda x: effect.sync(lambda: executed.append(x))),
    )

    result = effect.run_sync(result_effect)

    assert result == 100  # noqa: PLR2004
    assert executed == [100]


@pytest.mark.asyncio
async def test_pipe_with_async_effects() -> None:
    """Test pipe with async effects."""
    executed = []

    async def async_log(x: int) -> None:
        await asyncio.sleep(0.01)
        executed.append(f"Logged: {x}")

    result_effect = pipe(
        effect.succeed(42),
        effect.tap(lambda x: effect.async_(lambda: async_log(x))),
    )

    result = await effect.run_async(result_effect)

    assert result == 42  # noqa: PLR2004
    assert executed == ["Logged: 42"]


def test_pipe_preserves_types() -> None:
    """Test that pipe preserves type information through the chain."""
    # This test mainly checks that type inference works correctly
    result: int = pipe(10, lambda x: x + 1, lambda x: x * 2)
    assert result == 22  # noqa: PLR2004
