"""Tests for the map combinator."""

import asyncio

import pytest

from pyfect import effect, pipe


def test_map_succeed() -> None:
    """Test that map transforms a success value."""
    eff = effect.succeed(21)
    mapped = effect.map(lambda x: x * 2)(eff)  # type: ignore
    result = effect.run_sync(mapped)
    assert result == 42  # noqa: PLR2004


def test_map_with_pipe() -> None:
    """Test that map works with pipe for composition."""
    result = pipe(
        effect.succeed(10),
        effect.map(lambda x: x + 5),
        effect.map(lambda x: x * 2),
    )
    assert effect.run_sync(result) == 30  # noqa: PLR2004


def test_map_sync_effect() -> None:
    """Test that map works with sync effects."""
    eff = effect.sync(lambda: 21)
    mapped = effect.map(lambda x: x * 2)(eff)  # type: ignore
    result = effect.run_sync(mapped)
    assert result == 42  # noqa: PLR2004


async def test_map_async_effect() -> None:
    """Test that map works with async effects."""

    async def async_value() -> int:
        await asyncio.sleep(0.01)
        return 21

    eff = effect.async_(async_value)
    mapped = effect.map(lambda x: x * 2)(eff)  # type: ignore
    result = await effect.run_async(mapped)
    assert result == 42  # noqa: PLR2004


def test_map_preserves_errors() -> None:
    """Test that map doesn't affect errors - they pass through unchanged."""
    eff = effect.fail(ValueError("oops"))
    mapped = effect.map(lambda x: x * 2)(eff)  # type: ignore

    with pytest.raises(ValueError, match="oops"):
        effect.run_sync(mapped)


def test_map_preserves_errors_with_exit() -> None:
    """Test that map preserves errors when using run_sync_exit."""
    eff = effect.fail("error message")
    mapped = effect.map(lambda x: x * 2)(eff)  # type: ignore
    result = effect.run_sync_exit(mapped)

    match result:
        case effect.Failure(error):
            assert error == "error message"
        case effect.Success(_):
            pytest.fail("Expected failure but got success")


async def test_map_preserves_errors_async_exit() -> None:
    """Test that map preserves errors when using run_async_exit."""
    eff = effect.fail("async error")
    mapped = effect.map(lambda x: x * 2)(eff)  # type: ignore
    result = await effect.run_async_exit(mapped)

    match result:
        case effect.Failure(error):
            assert error == "async error"
        case effect.Success(_):
            pytest.fail("Expected failure but got success")


def test_map_composition() -> None:
    """Test composing multiple map operations."""
    result = pipe(
        effect.succeed(5),
        effect.map(lambda x: x + 3),  # 8
        effect.map(lambda x: x * 2),  # 16
        effect.map(lambda x: x - 6),  # 10
    )
    assert effect.run_sync(result) == 10  # noqa: PLR2004


def test_map_with_type_transformation() -> None:
    """Test that map can transform types (int -> str)."""
    eff = effect.succeed(42)
    mapped = effect.map(str)(eff)  # type: ignore
    result = effect.run_sync(mapped)
    assert result == "42"
    assert isinstance(result, str)


def test_map_with_complex_transformation() -> None:
    """Test map with a more complex transformation function."""

    def transform(x: int) -> dict[str, int]:
        return {"value": x, "doubled": x * 2}

    eff = effect.succeed(21)
    mapped = effect.map(transform)(eff)
    result = effect.run_sync(mapped)

    assert result == {"value": 21, "doubled": 42}


def test_map_is_lazy() -> None:
    """Test that map doesn't execute until the effect is run."""
    executed = []

    def track_execution(x: int) -> int:
        executed.append(x)
        return x * 2

    eff = effect.succeed(21)
    mapped = effect.map(track_execution)(eff)

    # Map is created but not executed
    assert len(executed) == 0

    # Now run it
    result = effect.run_sync(mapped)
    assert result == 42  # noqa: PLR2004
    assert executed == [21]


def test_map_with_try_sync() -> None:
    """Test that map works with try_sync effects."""
    eff = effect.try_sync(lambda: 21)
    mapped = effect.map(lambda x: x * 2)(eff)  # type: ignore
    result = effect.run_sync_exit(mapped)

    match result:
        case effect.Success(value):
            assert value == 42  # noqa: PLR2004
        case effect.Failure(_):
            pytest.fail("Expected success but got failure")


def test_map_with_try_sync_that_fails() -> None:
    """Test that map preserves exceptions from try_sync."""

    def will_fail() -> int:
        msg = "computation failed"
        raise ValueError(msg)

    eff = effect.try_sync(will_fail)
    mapped = effect.map(lambda x: x * 2)(eff)  # type: ignore
    result = effect.run_sync_exit(mapped)

    match result:
        case effect.Failure(error):
            assert isinstance(error, ValueError)
            assert str(error) == "computation failed"
        case effect.Success(_):
            pytest.fail("Expected failure but got success")


async def test_map_with_try_async() -> None:
    """Test that map works with try_async effects."""

    async def async_computation() -> int:
        await asyncio.sleep(0.01)
        return 21

    eff = effect.try_async(async_computation)
    mapped = effect.map(lambda x: x * 2)(eff)  # type: ignore
    result = await effect.run_async_exit(mapped)

    match result:
        case effect.Success(value):
            assert value == 42  # noqa: PLR2004
        case effect.Failure(_):
            pytest.fail("Expected success but got failure")


def test_map_after_tap() -> None:
    """Test that map works after tap."""
    tapped_values = []

    result = pipe(
        effect.succeed(10),
        effect.tap(lambda x: effect.sync(lambda: tapped_values.append(x))),
        effect.map(lambda x: x * 2),
    )

    final = effect.run_sync(result)
    assert final == 20  # noqa: PLR2004
    assert tapped_values == [10]


def test_tap_after_map() -> None:
    """Test that tap works after map."""
    tapped_values = []

    result = pipe(
        effect.succeed(10),
        effect.map(lambda x: x * 2),
        effect.tap(lambda x: effect.sync(lambda: tapped_values.append(x))),
    )

    final = effect.run_sync(result)
    assert final == 20  # noqa: PLR2004
    assert tapped_values == [20]  # Tap sees the mapped value
