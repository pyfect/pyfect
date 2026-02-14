"""Tests for the flat_map combinator."""

import asyncio

import pytest

from pyfect import effect, pipe


def test_flat_map_basic() -> None:
    """Test basic flat_map chaining."""
    result = pipe(
        effect.succeed(21),
        effect.flat_map(lambda x: effect.succeed(x * 2)),
    )
    assert effect.run_sync(result) == 42  # noqa: PLR2004


def test_flat_map_multiple_chains() -> None:
    """Test chaining multiple flat_map operations."""
    result = pipe(
        effect.succeed(1),
        effect.flat_map(lambda x: effect.succeed(x + 1)),  # 2
        effect.flat_map(lambda x: effect.succeed(x * 3)),  # 6
        effect.flat_map(lambda x: effect.succeed(x - 2)),  # 4
    )
    assert effect.run_sync(result) == 4  # noqa: PLR2004


def test_flat_map_dependent_computation() -> None:
    """Test flat_map where each step depends on previous result."""

    result = pipe(
        effect.succeed(42),
        effect.flat_map(lambda id: effect.succeed(f"User{id}")),
        effect.flat_map(lambda username: effect.succeed(f"{username}@example.com")),
    )
    assert effect.run_sync(result) == "User42@example.com"


def test_flat_map_with_failure() -> None:
    """Test that flat_map propagates failures."""
    result = pipe(
        effect.succeed(10),
        effect.flat_map(lambda _: effect.fail(ValueError("failed"))),
        effect.flat_map(lambda x: effect.succeed(x * 2)),  # Should not execute
    )

    with pytest.raises(ValueError, match="failed"):
        effect.run_sync(result)


def test_flat_map_failure_in_first_effect() -> None:
    """Test that flat_map doesn't execute if first effect fails."""
    executed = []

    def should_not_run(x: int) -> effect.Effect[int, str]:
        executed.append(x)
        return effect.succeed(x * 2)

    result = pipe(
        effect.fail("initial failure"),
        effect.flat_map(should_not_run),
    )

    with pytest.raises(RuntimeError, match="initial failure"):
        effect.run_sync(result)

    assert len(executed) == 0  # Function was not called


def test_flat_map_with_exit() -> None:
    """Test flat_map with run_sync_exit."""
    result = pipe(
        effect.succeed(10),
        effect.flat_map(lambda x: effect.succeed(x * 2)),
    )
    exit_result = effect.run_sync_exit(result)

    match exit_result:
        case effect.Success(value):
            assert value == 20  # noqa: PLR2004
        case effect.Failure(_):
            pytest.fail("Expected success but got failure")


def test_flat_map_failure_with_exit() -> None:
    """Test flat_map failure with run_sync_exit."""
    result = pipe(
        effect.succeed(10),
        effect.flat_map(lambda x: effect.fail("error in chain")),
    )
    exit_result = effect.run_sync_exit(result)

    match exit_result:
        case effect.Failure(error):
            assert error == "error in chain"
        case effect.Success(_):
            pytest.fail("Expected failure but got success")


async def test_flat_map_async() -> None:
    """Test flat_map with async effects."""

    async def async_double(x: int) -> int:
        await asyncio.sleep(0.01)
        return x * 2

    result = pipe(
        effect.async_(lambda: asyncio.sleep(0.01, result=10)),
        effect.flat_map(lambda x: effect.async_(lambda: async_double(x))),
    )
    assert await effect.run_async(result) == 20  # noqa: PLR2004


async def test_flat_map_async_exit() -> None:
    """Test flat_map with async effects and exit."""

    async def async_value(x: int) -> int:
        await asyncio.sleep(0.01)
        return x + 5

    result = pipe(
        effect.async_(lambda: asyncio.sleep(0.01, result=10)),
        effect.flat_map(lambda x: effect.async_(lambda: async_value(x))),
    )
    exit_result = await effect.run_async_exit(result)

    match exit_result:
        case effect.Success(value):
            assert value == 15  # noqa: PLR2004
        case effect.Failure(_):
            pytest.fail("Expected success but got failure")


def test_flat_map_with_sync_effect() -> None:
    """Test flat_map with sync effects."""
    result = pipe(
        effect.sync(lambda: 10),
        effect.flat_map(lambda x: effect.sync(lambda: x * 2)),
    )
    assert effect.run_sync(result) == 20  # noqa: PLR2004


def test_flat_map_vs_map() -> None:
    """Test the difference between flat_map and map."""
    # map transforms values
    map_result = pipe(
        effect.succeed(10),
        effect.map(lambda x: x * 2),
    )
    assert effect.run_sync(map_result) == 20  # noqa: PLR2004

    # flat_map chains effects
    flat_map_result = pipe(
        effect.succeed(10),
        effect.flat_map(lambda x: effect.succeed(x * 2)),
    )
    assert effect.run_sync(flat_map_result) == 20  # noqa: PLR2004


def test_flat_map_avoids_nesting() -> None:
    """Test that flat_map flattens nested effects."""
    # Without flat_map, you'd get Effect[Effect[int]]
    # With flat_map, you get Effect[int]

    def get_nested(x: int) -> effect.Effect[int, str]:
        return effect.succeed(x * 2)

    result = pipe(
        effect.succeed(10),
        effect.flat_map(get_nested),
    )
    # Result is Effect[int], not Effect[Effect[int]]  # noqa: ERA001
    assert effect.run_sync(result) == 20  # noqa: PLR2004


def test_flat_map_with_type_change() -> None:
    """Test flat_map can change types (int -> str)."""
    result = pipe(
        effect.succeed(42),
        effect.flat_map(lambda x: effect.succeed(str(x))),
        effect.flat_map(lambda s: effect.succeed(f"Value: {s}")),
    )
    assert effect.run_sync(result) == "Value: 42"


def test_flat_map_composition_with_map() -> None:
    """Test composing flat_map with map."""
    result = pipe(
        effect.succeed(5),
        effect.map(lambda x: x + 1),  # 6
        effect.flat_map(lambda x: effect.succeed(x * 2)),  # 12
        effect.map(lambda x: x - 2),  # 10
    )
    assert effect.run_sync(result) == 10  # noqa: PLR2004


def test_flat_map_with_tap() -> None:
    """Test flat_map with tap."""
    tapped_values = []

    result = pipe(
        effect.succeed(10),
        effect.tap(lambda x: effect.sync(lambda: tapped_values.append(x))),
        effect.flat_map(lambda x: effect.succeed(x * 2)),
        effect.tap(lambda x: effect.sync(lambda: tapped_values.append(x))),
    )

    final = effect.run_sync(result)
    assert final == 20  # noqa: PLR2004
    assert tapped_values == [10, 20]


def test_flat_map_is_lazy() -> None:
    """Test that flat_map doesn't execute until run."""
    executed = []

    def track_execution(x: int) -> effect.Effect[int, str]:
        executed.append(x)
        return effect.succeed(x * 2)

    result = pipe(
        effect.succeed(10),
        effect.flat_map(track_execution),
    )

    # Not executed yet
    assert len(executed) == 0

    # Now run it
    final = effect.run_sync(result)
    assert final == 20  # noqa: PLR2004
    assert executed == [10]


def test_flat_map_with_try_sync() -> None:
    """Test flat_map with try_sync effects."""
    result = pipe(
        effect.try_sync(lambda: 10),
        effect.flat_map(lambda x: effect.succeed(x * 2)),
    )
    exit_result = effect.run_sync_exit(result)

    match exit_result:
        case effect.Success(value):
            assert value == 20  # noqa: PLR2004
        case effect.Failure(_):
            pytest.fail("Expected success but got failure")


def test_flat_map_with_try_sync_that_fails() -> None:
    """Test flat_map when try_sync fails."""

    def will_fail() -> int:
        msg = "initial error"
        raise ValueError(msg)

    def should_not_run(x: int) -> effect.Effect[int, Exception]:
        return effect.succeed(x * 2)

    result = pipe(
        effect.try_sync(will_fail),
        effect.flat_map(should_not_run),
    )
    exit_result = effect.run_sync_exit(result)

    match exit_result:
        case effect.Failure(error):
            assert isinstance(error, ValueError)
            assert str(error) == "initial error"
        case effect.Success(_):
            pytest.fail("Expected failure but got success")


def test_flat_map_that_returns_failure() -> None:
    """Test flat_map where the returned effect fails."""

    def return_failure(x: int) -> effect.Effect[int, str]:
        return effect.fail(f"Failed at {x}")

    result = pipe(
        effect.succeed(10),
        effect.flat_map(return_failure),
    )
    exit_result = effect.run_sync_exit(result)

    match exit_result:
        case effect.Failure(error):
            assert error == "Failed at 10"
        case effect.Success(_):
            pytest.fail("Expected failure but got success")


def test_flat_map_complex_chain() -> None:
    """Test a complex chain simulating a real-world scenario."""

    result = pipe(
        effect.succeed(42),
        effect.flat_map(
            lambda user_id: (
                effect.fail("Invalid user ID") if user_id <= 0 else effect.succeed(user_id)
            )
        ),
        effect.flat_map(lambda user_id: effect.succeed({"id": user_id, "name": f"User{user_id}"})),
        effect.flat_map(lambda user: effect.succeed(str(user["name"]))),
    )

    assert effect.run_sync(result) == "User42"


def test_flat_map_complex_chain_with_failure() -> None:
    """Test complex chain that fails at validation."""

    result = pipe(
        effect.succeed(-1),  # Invalid ID
        effect.flat_map(
            lambda user_id: (
                effect.fail("Invalid user ID") if user_id <= 0 else effect.succeed(user_id)
            )
        ),
        effect.flat_map(lambda user_id: effect.succeed({"id": user_id, "name": f"User{user_id}"})),
    )

    exit_result = effect.run_sync_exit(result)

    match exit_result:
        case effect.Failure(error):
            assert error == "Invalid user ID"
        case effect.Success(_):
            pytest.fail("Expected failure but got success")
